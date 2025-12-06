"""
API Key Authentication Module

Provides header-based API key authentication for FastAPI and BentoML services.
Supports multiple API keys and key rotation.
"""

import os
import secrets
from typing import List, Optional, Set

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

# API Key header name
API_KEY_HEADER = "X-API-Key"

# Security scheme for OpenAPI documentation
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


class APIKeyAuth:
    """
    API Key authentication handler.

    Validates requests against a set of allowed API keys.
    Supports loading keys from environment variables or config files.
    """

    def __init__(self, api_keys: Optional[List[str]] = None, required: bool = True):
        """
        Initialize API key authentication.

        Args:
            api_keys: List of valid API keys. If None, loads from environment.
            required: Whether authentication is required (default: True)
        """
        self.required = required

        if api_keys is None:
            # Load from environment variable (comma-separated)
            keys_str = os.getenv("API_KEYS", "")
            api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]

        self.api_keys: Set[str] = set(api_keys)

        if self.required and not self.api_keys:
            raise ValueError(
                "No API keys configured. Set API_KEYS environment variable "
                "or pass api_keys parameter."
            )

    def add_key(self, api_key: str) -> None:
        """Add a new API key to the allowed set."""
        self.api_keys.add(api_key)

    def remove_key(self, api_key: str) -> None:
        """Remove an API key from the allowed set."""
        self.api_keys.discard(api_key)

    def rotate_key(self, old_key: str, new_key: str) -> None:
        """
        Rotate an API key (replace old with new).

        Args:
            old_key: Key to remove
            new_key: Key to add
        """
        self.remove_key(old_key)
        self.add_key(new_key)

    def validate(self, api_key: Optional[str]) -> bool:
        """
        Validate an API key.

        Args:
            api_key: The API key to validate

        Returns:
            True if valid, False otherwise
        """
        if not self.required:
            return True

        if api_key is None:
            return False

        return api_key in self.api_keys

    async def __call__(
        self, request: Request, api_key: Optional[str] = Security(api_key_header)
    ) -> str:
        """
        FastAPI dependency for API key authentication.

        Args:
            request: FastAPI request object
            api_key: API key from header (injected by FastAPI)

        Returns:
            The validated API key

        Raises:
            HTTPException: If authentication fails
        """
        if not self.required:
            return api_key or "anonymous"

        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key. Provide X-API-Key header.",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        if not self.validate(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Store validated API key in request state for later use
        request.state.api_key = api_key
        return api_key


# Singleton instance for easy import
_api_key_auth: Optional[APIKeyAuth] = None


def get_api_key_auth(required: Optional[bool] = None) -> APIKeyAuth:
    """
    Get or create the singleton APIKeyAuth instance.

    Args:
        required: Override the default required setting

    Returns:
        APIKeyAuth instance
    """
    global _api_key_auth

    if _api_key_auth is None:
        # Check if auth is enabled in environment
        auth_enabled = os.getenv("AUTH_ENABLED", "true").lower() == "true"
        _api_key_auth = APIKeyAuth(required=auth_enabled)

    if required is not None:
        _api_key_auth.required = required

    return _api_key_auth


def generate_api_key(prefix: str = "pk", length: int = 32) -> str:
    """
    Generate a cryptographically secure API key.

    Args:
        prefix: Prefix for the key (default: "pk" for "pokewatch")
        length: Length of the random part (default: 32)

    Returns:
        Generated API key in format: {prefix}_{random_string}

    Example:
        >>> key = generate_api_key()
        >>> print(key)
        pk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
    """
    random_part = secrets.token_urlsafe(length)
    return f"{prefix}_{random_part}"


def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
    """
    Mask an API key for safe logging.

    Args:
        api_key: The full API key
        visible_chars: Number of characters to show at the end (default: 4)

    Returns:
        Masked API key

    Example:
        >>> masked = mask_api_key("pk_a1b2c3d4e5f6g7h8")
        >>> print(masked)
        pk_***g7h8
    """
    if len(api_key) <= visible_chars:
        return "***"

    # Show prefix and last few characters
    if "_" in api_key:
        prefix, rest = api_key.split("_", 1)
        return f"{prefix}_***{rest[-visible_chars:]}"
    else:
        return f"***{api_key[-visible_chars:]}"


# Optional: Rate limit per API key
class APIKeyRateLimitTracker:
    """
    Track API usage per key for rate limiting.

    This is a simple in-memory tracker. For production, use Redis or similar.
    """

    def __init__(self):
        self._usage: dict[str, int] = {}

    def increment(self, api_key: str) -> int:
        """
        Increment usage counter for an API key.

        Returns:
            Current usage count
        """
        self._usage[api_key] = self._usage.get(api_key, 0) + 1
        return self._usage[api_key]

    def reset(self, api_key: Optional[str] = None) -> None:
        """
        Reset usage counters.

        Args:
            api_key: Specific key to reset, or None to reset all
        """
        if api_key:
            self._usage.pop(api_key, None)
        else:
            self._usage.clear()

    def get_usage(self, api_key: str) -> int:
        """Get current usage count for an API key."""
        return self._usage.get(api_key, 0)
