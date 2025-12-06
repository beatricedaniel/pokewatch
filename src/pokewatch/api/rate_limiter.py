"""
Rate Limiting Module

Implements token bucket algorithm for API rate limiting.
Supports per-API-key and per-IP rate limiting with Redis backend.
"""

import os
import time
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, Request, status


class TokenBucket:
    """
    Token bucket algorithm implementation for rate limiting.

    Each bucket has a maximum capacity and refills at a constant rate.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens (burst size)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens: float = float(capacity)
        self.last_refill = time.time()

    def _refill(self) -> None:
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate

        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if successful, False if insufficient tokens
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def get_tokens(self) -> float:
        """Get current number of tokens."""
        self._refill()
        return self.tokens

    def time_until_tokens(self, tokens: int) -> float:
        """
        Calculate time until specified tokens are available.

        Args:
            tokens: Desired number of tokens

        Returns:
            Seconds to wait (0 if already available, inf if refill_rate is 0)
        """
        self._refill()
        if self.tokens >= tokens:
            return 0.0

        # If refill_rate is 0, tokens will never be available
        if self.refill_rate == 0:
            return float("inf")

        needed = tokens - self.tokens
        return needed / self.refill_rate


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.

    Supports per-key rate limiting with configurable limits.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: Optional[int] = None,
        enabled: bool = True,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute per key
            burst_size: Maximum burst size (defaults to requests_per_minute)
            enabled: Whether rate limiting is enabled
        """
        self.enabled = enabled
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size or requests_per_minute

        # Refill rate in tokens per second
        self.refill_rate = requests_per_minute / 60.0

        # In-memory buckets (use Redis for distributed systems)
        self.buckets: Dict[str, TokenBucket] = {}

    def _get_bucket(self, key: str) -> TokenBucket:
        """Get or create token bucket for a key."""
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(self.burst_size, self.refill_rate)
        return self.buckets[key]

    def check_rate_limit(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Identifier for rate limiting (API key, IP, etc.)

        Returns:
            Tuple of (allowed, headers_dict)
            - allowed: Whether request is allowed
            - headers_dict: Rate limit headers to include in response
        """
        if not self.enabled:
            return True, {}

        bucket = self._get_bucket(key)
        allowed = bucket.consume()

        # Calculate rate limit headers
        remaining = int(bucket.get_tokens())
        time_until = bucket.time_until_tokens(1)

        # Handle infinity case (when refill_rate is 0)
        if time_until == float("inf"):
            reset_time = int(time.time() + 86400)  # Use 24 hours as fallback
        else:
            reset_time = int(time.time() + time_until)

        headers = {
            "X-RateLimit-Limit": str(self.requests_per_minute),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(reset_time),
        }

        if not allowed:
            if time_until == float("inf"):
                retry_after = 86400  # Use 24 hours as fallback
            else:
                retry_after = int(time_until) + 1
            headers["Retry-After"] = str(retry_after)

        return allowed, headers

    async def __call__(self, request: Request) -> None:
        """
        FastAPI dependency for rate limiting.

        Args:
            request: FastAPI request object

        Raises:
            HTTPException: If rate limit exceeded
        """
        if not self.enabled:
            return

        # Use API key if available, otherwise use IP address
        rate_limit_key = getattr(request.state, "api_key", None)
        if not rate_limit_key:
            rate_limit_key = request.client.host if request.client else "unknown"

        allowed, headers = self.check_rate_limit(rate_limit_key)

        # Store headers in request state to add to response
        request.state.rate_limit_headers = headers

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {headers.get('Retry-After', 'a few')} seconds.",
                headers=headers,
            )

    def reset(self, key: Optional[str] = None) -> None:
        """
        Reset rate limit for a key or all keys.

        Args:
            key: Specific key to reset, or None to reset all
        """
        if key:
            self.buckets.pop(key, None)
        else:
            self.buckets.clear()


# Redis-backed rate limiter for distributed systems
try:
    import redis.asyncio as redis  # type: ignore[import-untyped]

    class RedisRateLimiter(RateLimiter):
        """
        Redis-backed rate limiter for distributed deployments.

        Uses Redis for shared state across multiple API instances.
        """

        def __init__(
            self,
            requests_per_minute: int = 60,
            burst_size: Optional[int] = None,
            redis_url: Optional[str] = None,
            enabled: bool = True,
        ):
            super().__init__(requests_per_minute, burst_size, enabled)

            redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)

        async def check_rate_limit_redis(self, key: str) -> Tuple[bool, Dict[str, Any]]:
            """Check rate limit using Redis."""
            if not self.enabled:
                return True, {}

            redis_key = f"rate_limit:{key}"
            now = time.time()
            window = 60  # 1 minute window

            # Use Redis sorted set for sliding window
            async with self.redis_client.pipeline() as pipe:
                # Remove old entries outside the window
                pipe.zremrangebyscore(redis_key, 0, now - window)

                # Count requests in current window
                pipe.zcard(redis_key)

                # Add current request
                pipe.zadd(redis_key, {str(now): now})

                # Set expiry
                pipe.expire(redis_key, window)

                results = await pipe.execute()

            current_count = results[1]  # Count before adding new request

            allowed = current_count < self.requests_per_minute
            remaining = max(0, self.requests_per_minute - current_count - 1)
            reset_time = int(now + window)

            headers = {
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time),
            }

            if not allowed:
                headers["Retry-After"] = str(window)

            return allowed, headers

        async def __call__(self, request: Request) -> None:
            """FastAPI dependency using Redis backend."""
            if not self.enabled:
                return

            rate_limit_key = getattr(request.state, "api_key", None)
            if not rate_limit_key:
                rate_limit_key = request.client.host if request.client else "unknown"

            allowed, headers = await self.check_rate_limit_redis(rate_limit_key)

            request.state.rate_limit_headers = headers

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {headers.get('Retry-After', 'a few')} seconds.",
                    headers=headers,
                )

except ImportError:
    RedisRateLimiter = None  # type: ignore[misc]  # Redis not available


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(use_redis: bool = False) -> RateLimiter:
    """
    Get or create singleton rate limiter instance.

    Args:
        use_redis: Whether to use Redis-backed rate limiter

    Returns:
        RateLimiter instance
    """
    global _rate_limiter

    if _rate_limiter is None:
        # Check configuration
        enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        rpm = int(os.getenv("RATE_LIMIT_RPM", "60"))
        burst = int(os.getenv("RATE_LIMIT_BURST", str(rpm)))

        # Use Redis if available and requested
        redis_url = os.getenv("REDIS_URL")
        if use_redis and redis_url and RedisRateLimiter:
            _rate_limiter = RedisRateLimiter(
                requests_per_minute=rpm,
                burst_size=burst,
                redis_url=redis_url,
                enabled=enabled,
            )
        else:
            _rate_limiter = RateLimiter(requests_per_minute=rpm, burst_size=burst, enabled=enabled)

    return _rate_limiter
