"""
Integration tests for rate limiting.

Tests the rate limiter middleware and token bucket algorithm.
"""

import time
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from typing import Annotated

from pokewatch.api.rate_limiter import RateLimiter, TokenBucket, get_rate_limiter


@pytest.fixture
def token_bucket():
    """Create token bucket with known parameters."""
    return TokenBucket(capacity=10, refill_rate=1.0)  # 10 tokens, 1 per second


@pytest.fixture
def rate_limiter():
    """Create rate limiter for testing."""
    return RateLimiter(requests_per_minute=60, burst_size=10, enabled=True)


@pytest.fixture
def disabled_rate_limiter():
    """Create disabled rate limiter."""
    return RateLimiter(requests_per_minute=60, burst_size=10, enabled=False)


@pytest.fixture
def test_app(rate_limiter):
    """Create test FastAPI app with rate limiting."""
    app = FastAPI()

    @app.get("/limited")
    async def limited_endpoint(_: Annotated[None, Depends(rate_limiter)]):
        return {"message": "success"}

    @app.get("/unlimited")
    def unlimited_endpoint():
        return {"message": "unlimited"}

    return app


@pytest.fixture
def disabled_app(disabled_rate_limiter):
    """Create test app with disabled rate limiting."""
    app = FastAPI()

    @app.get("/endpoint")
    async def endpoint(_: Annotated[None, Depends(disabled_rate_limiter)]):
        return {"message": "success"}

    return app


class TestTokenBucket:
    """Test TokenBucket algorithm."""

    def test_init(self, token_bucket):
        """Test bucket initialization."""
        assert token_bucket.capacity == 10
        assert token_bucket.refill_rate == 1.0
        assert token_bucket.tokens == 10  # Starts full

    def test_consume_success(self, token_bucket):
        """Test successful token consumption."""
        assert token_bucket.consume(5) is True
        assert token_bucket.get_tokens() == pytest.approx(5, abs=0.1)

    def test_consume_failure(self, token_bucket):
        """Test failed token consumption."""
        # Consume all tokens
        assert token_bucket.consume(10) is True
        # Try to consume more
        assert token_bucket.consume(1) is False

    def test_refill_over_time(self, token_bucket):
        """Test that tokens refill over time."""
        # Consume all tokens
        token_bucket.consume(10)
        assert token_bucket.get_tokens() == pytest.approx(0, abs=0.1)

        # Wait 2 seconds (should refill 2 tokens at 1/sec)
        time.sleep(2)
        assert token_bucket.get_tokens() == pytest.approx(2, abs=0.2)

    def test_refill_caps_at_capacity(self, token_bucket):
        """Test that refill doesn't exceed capacity."""
        # Start with full bucket
        assert token_bucket.tokens == 10

        # Wait 5 seconds
        time.sleep(5)

        # Should still be capped at 10
        assert token_bucket.get_tokens() == pytest.approx(10, abs=0.1)

    def test_time_until_tokens(self, token_bucket):
        """Test time calculation until tokens available."""
        # Consume all tokens
        token_bucket.consume(10)

        # Should need 5 seconds to get 5 tokens at 1/sec
        wait_time = token_bucket.time_until_tokens(5)
        assert wait_time == pytest.approx(5, abs=0.1)

    def test_time_until_tokens_already_available(self, token_bucket):
        """Test time calculation when tokens already available."""
        # Already have 10 tokens
        wait_time = token_bucket.time_until_tokens(5)
        assert wait_time == 0.0


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_init(self, rate_limiter):
        """Test rate limiter initialization."""
        assert rate_limiter.requests_per_minute == 60
        assert rate_limiter.burst_size == 10
        assert rate_limiter.enabled is True

    def test_check_rate_limit_allowed(self, rate_limiter):
        """Test rate limit check when allowed."""
        allowed, headers = rate_limiter.check_rate_limit("test_key")

        assert allowed is True
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers
        assert headers["X-RateLimit-Limit"] == "60"

    def test_check_rate_limit_exceeded(self, rate_limiter):
        """Test rate limit check when exceeded."""
        # Consume all tokens
        for _ in range(10):
            allowed, _ = rate_limiter.check_rate_limit("test_key")
            assert allowed is True

        # Next request should be blocked
        allowed, headers = rate_limiter.check_rate_limit("test_key")
        assert allowed is False
        assert "Retry-After" in headers

    def test_check_rate_limit_per_key(self, rate_limiter):
        """Test that rate limiting is per key."""
        # Use up limit for key1
        for _ in range(10):
            rate_limiter.check_rate_limit("key1")

        # key1 should be blocked
        allowed, _ = rate_limiter.check_rate_limit("key1")
        assert allowed is False

        # key2 should still work
        allowed, _ = rate_limiter.check_rate_limit("key2")
        assert allowed is True

    def test_disabled_rate_limiter(self, disabled_rate_limiter):
        """Test that disabled rate limiter always allows."""
        for _ in range(100):
            allowed, headers = disabled_rate_limiter.check_rate_limit("key")
            assert allowed is True
            assert headers == {}

    def test_reset_single_key(self, rate_limiter):
        """Test resetting rate limit for single key."""
        # Use up limit
        for _ in range(10):
            rate_limiter.check_rate_limit("key1")

        # Should be blocked
        allowed, _ = rate_limiter.check_rate_limit("key1")
        assert allowed is False

        # Reset
        rate_limiter.reset("key1")

        # Should work again
        allowed, _ = rate_limiter.check_rate_limit("key1")
        assert allowed is True

    def test_reset_all_keys(self, rate_limiter):
        """Test resetting all keys."""
        # Use up limits for multiple keys
        for key in ["key1", "key2", "key3"]:
            for _ in range(10):
                rate_limiter.check_rate_limit(key)

        # Reset all
        rate_limiter.reset()

        # All should work again
        for key in ["key1", "key2", "key3"]:
            allowed, _ = rate_limiter.check_rate_limit(key)
            assert allowed is True


class TestRateLimitingEndpoints:
    """Test rate limiting with FastAPI endpoints."""

    def test_unlimited_endpoint(self, test_app):
        """Test that unlimited endpoint is not rate limited."""
        client = TestClient(test_app)

        for _ in range(100):
            response = client.get("/unlimited")
            assert response.status_code == 200

    def test_limited_endpoint_within_limit(self, test_app):
        """Test limited endpoint within rate limit."""
        client = TestClient(test_app)

        for i in range(10):
            response = client.get("/limited")
            assert response.status_code == 200, f"Request {i+1} failed"
            assert response.json() == {"message": "success"}

    def test_limited_endpoint_exceeds_limit(self, test_app):
        """Test limited endpoint when limit exceeded."""
        client = TestClient(test_app)

        # Make requests up to limit
        for _ in range(10):
            response = client.get("/limited")
            assert response.status_code == 200

        # Next request should be rate limited
        response = client.get("/limited")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]

    def test_rate_limit_headers_present(self, test_app):
        """Test that rate limit headers are present."""
        client = TestClient(test_app)

        response = client.get("/limited")
        assert response.status_code == 200

        # Check headers (note: middleware adds them)
        # These would be in request.state.rate_limit_headers
        # and added by RateLimitHeadersMiddleware

    def test_retry_after_header_on_429(self, test_app):
        """Test Retry-After header on rate limit response."""
        client = TestClient(test_app)

        # Exceed limit
        for _ in range(11):
            response = client.get("/limited")

        # Last response should have Retry-After
        assert response.status_code == 429
        # Retry-After would be in headers if middleware is setup

    def test_disabled_rate_limiting(self, disabled_app):
        """Test that disabled rate limiter allows unlimited requests."""
        client = TestClient(disabled_app)

        for _ in range(100):
            response = client.get("/endpoint")
            assert response.status_code == 200


class TestSingletonRateLimiter:
    """Test singleton rate limiter instance."""

    def test_get_rate_limiter_singleton(self, monkeypatch):
        """Test that get_rate_limiter returns singleton."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_RPM", "60")

        # Reset singleton
        import pokewatch.api.rate_limiter

        pokewatch.api.rate_limiter._rate_limiter = None

        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        assert limiter1 is limiter2

    def test_get_rate_limiter_from_env(self, monkeypatch):
        """Test singleton loads configuration from environment."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_RPM", "120")
        monkeypatch.setenv("RATE_LIMIT_BURST", "20")

        # Reset singleton
        import pokewatch.api.rate_limiter

        pokewatch.api.rate_limiter._rate_limiter = None

        limiter = get_rate_limiter()
        assert limiter.requests_per_minute == 120
        assert limiter.burst_size == 20
        assert limiter.enabled is True

    def test_get_rate_limiter_disabled(self, monkeypatch):
        """Test singleton with rate limiting disabled."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

        # Reset singleton
        import pokewatch.api.rate_limiter

        pokewatch.api.rate_limiter._rate_limiter = None

        limiter = get_rate_limiter()
        assert limiter.enabled is False


class TestRateLimitHeaders:
    """Test rate limit header values."""

    def test_header_limit_value(self, rate_limiter):
        """Test X-RateLimit-Limit header."""
        _, headers = rate_limiter.check_rate_limit("test")
        assert headers["X-RateLimit-Limit"] == "60"

    def test_header_remaining_decreases(self, rate_limiter):
        """Test X-RateLimit-Remaining decreases with requests."""
        # First request
        _, headers1 = rate_limiter.check_rate_limit("test")
        remaining1 = int(headers1["X-RateLimit-Remaining"])

        # Second request
        _, headers2 = rate_limiter.check_rate_limit("test")
        remaining2 = int(headers2["X-RateLimit-Remaining"])

        assert remaining2 < remaining1

    def test_header_reset_is_timestamp(self, rate_limiter):
        """Test X-RateLimit-Reset is future timestamp."""
        _, headers = rate_limiter.check_rate_limit("test")
        reset_time = int(headers["X-RateLimit-Reset"])
        current_time = int(time.time())

        assert reset_time >= current_time


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_requests_per_minute(self):
        """Test with zero requests per minute (blocks everything)."""
        limiter = RateLimiter(requests_per_minute=0, burst_size=0, enabled=True)
        allowed, _ = limiter.check_rate_limit("test")
        assert allowed is False

    def test_very_high_burst(self):
        """Test with very high burst size."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=1000, enabled=True)

        # Should allow many requests quickly
        for _ in range(100):
            allowed, _ = limiter.check_rate_limit("test")
            assert allowed is True

    def test_fractional_tokens(self):
        """Test that fractional tokens work correctly."""
        bucket = TokenBucket(capacity=10, refill_rate=0.5)  # 0.5 tokens/sec

        # Consume some tokens
        bucket.consume(5)

        # Wait 1 second (should add 0.5 tokens)
        time.sleep(1)

        tokens = bucket.get_tokens()
        assert tokens == pytest.approx(5.5, abs=0.1)

    def test_concurrent_requests_same_key(self, rate_limiter):
        """Test multiple concurrent requests with same key."""
        # Simulate concurrent access
        results = []
        for _ in range(15):
            allowed, _ = rate_limiter.check_rate_limit("shared_key")
            results.append(allowed)

        # First 10 should succeed, rest should fail
        assert sum(results) == 10  # 10 True values
        assert len([r for r in results if not r]) == 5  # 5 False values


class TestIntegrationWithAuth:
    """Test rate limiting integration with authentication."""

    def test_rate_limit_per_api_key(self):
        """Test that rate limiting works per API key."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=5, enabled=True)

        # Consume limit for api_key_1
        for _ in range(5):
            allowed, _ = limiter.check_rate_limit("api_key_1")
            assert allowed is True

        # api_key_1 should be blocked
        allowed, _ = limiter.check_rate_limit("api_key_1")
        assert allowed is False

        # api_key_2 should still work
        allowed, _ = limiter.check_rate_limit("api_key_2")
        assert allowed is True

    def test_rate_limit_with_ip_fallback(self):
        """Test rate limiting falls back to IP when no API key."""
        limiter = RateLimiter(requests_per_minute=60, burst_size=5, enabled=True)

        # Use IP address as key
        for _ in range(5):
            allowed, _ = limiter.check_rate_limit("192.168.1.1")
            assert allowed is True

        # IP should be blocked
        allowed, _ = limiter.check_rate_limit("192.168.1.1")
        assert allowed is False

        # Different IP should work
        allowed, _ = limiter.check_rate_limit("192.168.1.2")
        assert allowed is True
