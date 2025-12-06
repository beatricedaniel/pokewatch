"""
Integration tests for API key authentication.

Tests the authentication middleware and API key validation.
"""

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from typing import Annotated

from pokewatch.api.auth import APIKeyAuth, get_api_key_auth, generate_api_key, mask_api_key


@pytest.fixture
def test_api_keys():
    """Generate test API keys."""
    return [
        "pk_test_key_1",
        "pk_test_key_2",
        "pk_test_key_3",
    ]


@pytest.fixture
def auth_handler(test_api_keys):
    """Create authentication handler with test keys."""
    return APIKeyAuth(api_keys=test_api_keys, required=True)


@pytest.fixture
def optional_auth_handler(test_api_keys):
    """Create authentication handler with optional auth."""
    return APIKeyAuth(api_keys=test_api_keys, required=False)


@pytest.fixture
def test_app(auth_handler):
    """Create test FastAPI app with authentication."""
    app = FastAPI()

    @app.get("/public")
    def public_endpoint():
        return {"message": "public"}

    @app.get("/protected")
    def protected_endpoint(api_key: Annotated[str, Depends(auth_handler)]):
        return {"message": "protected", "api_key": mask_api_key(api_key)}

    @app.get("/user-info")
    def user_info_endpoint(api_key: Annotated[str, Depends(auth_handler)]):
        return {"api_key": api_key}

    return app


@pytest.fixture
def optional_app(optional_auth_handler):
    """Create test app with optional authentication."""
    app = FastAPI()

    @app.get("/optional")
    def optional_endpoint(api_key: Annotated[str, Depends(optional_auth_handler)]):
        return {"message": "optional", "api_key": api_key}

    return app


class TestAPIKeyAuth:
    """Test APIKeyAuth class."""

    def test_init_with_keys(self, test_api_keys):
        """Test initialization with explicit keys."""
        auth = APIKeyAuth(api_keys=test_api_keys)
        assert len(auth.api_keys) == 3
        assert "pk_test_key_1" in auth.api_keys

    def test_init_from_env(self, monkeypatch):
        """Test initialization from environment variable."""
        monkeypatch.setenv("API_KEYS", "key1,key2,key3")
        auth = APIKeyAuth()
        assert len(auth.api_keys) == 3
        assert "key1" in auth.api_keys

    def test_init_required_no_keys_raises(self):
        """Test that required auth with no keys raises ValueError."""
        with pytest.raises(ValueError, match="No API keys configured"):
            APIKeyAuth(api_keys=[], required=True)

    def test_init_optional_no_keys_ok(self):
        """Test that optional auth with no keys is OK."""
        auth = APIKeyAuth(api_keys=[], required=False)
        assert len(auth.api_keys) == 0

    def test_validate_valid_key(self, auth_handler):
        """Test validation with valid key."""
        assert auth_handler.validate("pk_test_key_1") is True

    def test_validate_invalid_key(self, auth_handler):
        """Test validation with invalid key."""
        assert auth_handler.validate("invalid_key") is False

    def test_validate_none_required(self, auth_handler):
        """Test validation with None when required."""
        assert auth_handler.validate(None) is False

    def test_validate_none_optional(self, optional_auth_handler):
        """Test validation with None when optional."""
        assert optional_auth_handler.validate(None) is True

    def test_add_key(self, auth_handler):
        """Test adding a new key."""
        auth_handler.add_key("new_key")
        assert "new_key" in auth_handler.api_keys
        assert len(auth_handler.api_keys) == 4

    def test_remove_key(self, auth_handler):
        """Test removing a key."""
        auth_handler.remove_key("pk_test_key_1")
        assert "pk_test_key_1" not in auth_handler.api_keys
        assert len(auth_handler.api_keys) == 2

    def test_rotate_key(self, auth_handler):
        """Test rotating a key."""
        old_key = "pk_test_key_1"
        new_key = "pk_new_key"

        auth_handler.rotate_key(old_key, new_key)

        assert old_key not in auth_handler.api_keys
        assert new_key in auth_handler.api_keys
        assert len(auth_handler.api_keys) == 3


class TestAuthenticationEndpoints:
    """Test authentication with FastAPI endpoints."""

    def test_public_endpoint_no_auth(self, test_app):
        """Test public endpoint without authentication."""
        client = TestClient(test_app)
        response = client.get("/public")
        assert response.status_code == 200
        assert response.json() == {"message": "public"}

    def test_protected_endpoint_valid_key(self, test_app):
        """Test protected endpoint with valid API key."""
        client = TestClient(test_app)
        response = client.get("/protected", headers={"X-API-Key": "pk_test_key_1"})
        assert response.status_code == 200
        assert response.json()["message"] == "protected"
        assert "api_key" in response.json()

    def test_protected_endpoint_invalid_key(self, test_app):
        """Test protected endpoint with invalid API key."""
        client = TestClient(test_app)
        response = client.get("/protected", headers={"X-API-Key": "invalid_key"})
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_protected_endpoint_no_key(self, test_app):
        """Test protected endpoint without API key."""
        client = TestClient(test_app)
        response = client.get("/protected")
        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]

    def test_protected_endpoint_all_keys(self, test_app, test_api_keys):
        """Test protected endpoint with all valid keys."""
        client = TestClient(test_app)
        for key in test_api_keys:
            response = client.get("/protected", headers={"X-API-Key": key})
            assert response.status_code == 200

    def test_optional_endpoint_with_key(self, optional_app):
        """Test optional auth endpoint with key."""
        client = TestClient(optional_app)
        response = client.get("/optional", headers={"X-API-Key": "pk_test_key_1"})
        assert response.status_code == 200
        assert response.json()["api_key"] == "pk_test_key_1"

    def test_optional_endpoint_without_key(self, optional_app):
        """Test optional auth endpoint without key."""
        client = TestClient(optional_app)
        response = client.get("/optional")
        assert response.status_code == 200
        assert response.json()["api_key"] == "anonymous"

    def test_auth_headers_present(self, test_app):
        """Test that WWW-Authenticate header is present on 401."""
        client = TestClient(test_app)
        response = client.get("/protected")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == "ApiKey"


class TestKeyGeneration:
    """Test API key generation utilities."""

    def test_generate_api_key_default(self):
        """Test key generation with defaults."""
        key = generate_api_key()
        assert key.startswith("pk_")
        assert len(key) > 10

    def test_generate_api_key_custom_prefix(self):
        """Test key generation with custom prefix."""
        key = generate_api_key(prefix="custom")
        assert key.startswith("custom_")

    def test_generate_api_key_custom_length(self):
        """Test key generation with custom length."""
        key = generate_api_key(length=16)
        # Note: urlsafe_b64 encoding may produce slightly different lengths
        assert key.startswith("pk_")
        assert len(key) >= 16

    def test_generate_unique_keys(self):
        """Test that generated keys are unique."""
        keys = [generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100  # All unique

    def test_mask_api_key(self):
        """Test API key masking."""
        key = "pk_abc123def456ghi789"
        masked = mask_api_key(key)
        assert masked.startswith("pk_")
        assert "***" in masked
        assert masked.endswith("i789")  # Last 4 chars of the key (after prefix)

    def test_mask_short_key(self):
        """Test masking very short key."""
        key = "abc"
        masked = mask_api_key(key)
        assert masked == "***"

    def test_mask_key_no_prefix(self):
        """Test masking key without underscore."""
        key = "abcdefghijk"
        masked = mask_api_key(key)
        assert masked.startswith("***")
        assert masked.endswith("hijk")


class TestSingletonAuth:
    """Test singleton auth instance."""

    def test_get_api_key_auth_singleton(self, monkeypatch):
        """Test that get_api_key_auth returns singleton."""
        monkeypatch.setenv("API_KEYS", "key1,key2")
        monkeypatch.setenv("AUTH_ENABLED", "true")

        auth1 = get_api_key_auth()
        auth2 = get_api_key_auth()

        assert auth1 is auth2

    def test_get_api_key_auth_from_env(self, monkeypatch):
        """Test singleton loads from environment."""
        monkeypatch.setenv("API_KEYS", "env_key1,env_key2")
        monkeypatch.setenv("AUTH_ENABLED", "true")

        # Reset singleton
        import pokewatch.api.auth

        pokewatch.api.auth._api_key_auth = None

        auth = get_api_key_auth()
        assert "env_key1" in auth.api_keys
        assert auth.required is True

    def test_get_api_key_auth_disabled(self, monkeypatch):
        """Test singleton with auth disabled."""
        monkeypatch.setenv("API_KEYS", "key1,key2")
        monkeypatch.setenv("AUTH_ENABLED", "false")

        # Reset singleton
        import pokewatch.api.auth

        pokewatch.api.auth._api_key_auth = None

        auth = get_api_key_auth()
        assert auth.required is False


class TestRequestState:
    """Test that API key is stored in request state."""

    def test_api_key_in_request_state(self, test_app):
        """Test that validated API key is stored in request state."""
        client = TestClient(test_app)
        response = client.get("/user-info", headers={"X-API-Key": "pk_test_key_1"})
        assert response.status_code == 200
        assert response.json()["api_key"] == "pk_test_key_1"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_api_key_header(self, test_app):
        """Test with empty API key header."""
        client = TestClient(test_app)
        response = client.get("/protected", headers={"X-API-Key": ""})
        assert response.status_code == 401

    def test_whitespace_api_key(self, test_app):
        """Test with whitespace API key."""
        client = TestClient(test_app)
        response = client.get("/protected", headers={"X-API-Key": "   "})
        assert response.status_code == 401

    def test_case_sensitive_key(self, auth_handler):
        """Test that API keys are case-sensitive."""
        assert auth_handler.validate("pk_test_key_1") is True
        assert auth_handler.validate("PK_TEST_KEY_1") is False
        assert auth_handler.validate("pk_test_KEY_1") is False

    def test_api_key_with_special_chars(self):
        """Test API key with special characters."""
        special_key = "pk_test!@#$%^&*()"
        auth = APIKeyAuth(api_keys=[special_key])
        assert auth.validate(special_key) is True
