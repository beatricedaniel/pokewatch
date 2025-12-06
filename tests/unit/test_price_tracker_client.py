"""
Unit tests for PokemonPriceTrackerClient.

Tests cover:
- Authentication headers
- Request parameters (language, includeHistory, days, etc.)
- URL construction
- Error handling (401, 404, 429, timeouts)
- Response parsing
"""

import pytest
from unittest.mock import Mock, patch
from requests.exceptions import Timeout, HTTPError, RequestException

from pokewatch.data.price_tracker_client import (
    PokemonPriceTrackerClient,
    PokemonPriceTrackerError,
    PokemonPriceTrackerAuthError,
    PokemonPriceTrackerNotFoundError,
    PokemonPriceTrackerRateLimitError,
)


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"success": True, "data": []}
    return response


@pytest.fixture
def client():
    """Create a PokemonPriceTrackerClient instance."""
    return PokemonPriceTrackerClient(
        api_key="test_api_key_12345",
        base_url="https://api.test.com",
        timeout=10,
        default_language="japanese",
    )


class TestClientInitialization:
    """Test client initialization and configuration."""

    def test_client_initialization(self):
        """Test that client initializes with correct attributes."""
        client = PokemonPriceTrackerClient(
            api_key="my_key",
            base_url="https://example.com/api",
            timeout=15,
            default_language="japanese",
        )

        assert client.api_key == "my_key"
        assert client.base_url == "https://example.com/api"
        assert client.timeout == 15
        assert client.default_language == "japanese"

    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from base_url."""
        client = PokemonPriceTrackerClient(
            api_key="key",
            base_url="https://example.com/api/",
        )
        assert client.base_url == "https://example.com/api"

    def test_authorization_header_set(self, client):
        """Test that Authorization header is set correctly."""
        assert "Authorization" in client._session.headers
        assert client._session.headers["Authorization"] == "Bearer test_api_key_12345"

    def test_default_headers(self, client):
        """Test that default headers are set."""
        headers = client._session.headers
        assert headers["Content-Type"] == "application/json"
        assert "User-Agent" in headers
        assert "PokeWatch" in headers["User-Agent"]


class TestMakeRequest:
    """Test the internal _make_request method."""

    @patch("requests.Session.request")
    def test_successful_request(self, mock_request, client, mock_response):
        """Test successful API request."""
        mock_request.return_value = mock_response

        result = client._make_request("GET", "/test", params={"key": "value"})

        assert result == {"success": True, "data": []}
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "https://api.test.com/test"
        assert call_args[1]["params"] == {"key": "value"}
        assert call_args[1]["timeout"] == 10

    @patch("requests.Session.request")
    def test_none_params_filtered(self, mock_request, client, mock_response):
        """Test that None values are removed from params."""
        mock_request.return_value = mock_response

        client._make_request(
            "GET", "/test", params={"key1": "value1", "key2": None, "key3": "value3"}
        )

        call_args = mock_request.call_args
        assert call_args[1]["params"] == {"key1": "value1", "key3": "value3"}

    @patch("requests.Session.request")
    def test_401_raises_auth_error(self, mock_request, client):
        """Test that 401 status raises PokemonPriceTrackerAuthError."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response

        with pytest.raises(PokemonPriceTrackerAuthError) as exc_info:
            client._make_request("GET", "/test")

        assert "Authentication failed" in str(exc_info.value)

    @patch("requests.Session.request")
    def test_404_raises_not_found_error(self, mock_request, client):
        """Test that 404 status raises PokemonPriceTrackerNotFoundError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        with pytest.raises(PokemonPriceTrackerNotFoundError) as exc_info:
            client._make_request("GET", "/test")

        assert "Resource not found" in str(exc_info.value)

    @patch("requests.Session.request")
    def test_429_raises_rate_limit_error(self, mock_request, client):
        """Test that 429 status raises PokemonPriceTrackerRateLimitError."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_request.return_value = mock_response

        with pytest.raises(PokemonPriceTrackerRateLimitError) as exc_info:
            client._make_request("GET", "/test")

        assert "Rate limit exceeded" in str(exc_info.value)

    @patch("requests.Session.request")
    def test_500_raises_generic_error(self, mock_request, client):
        """Test that 500 status raises generic PokemonPriceTrackerError."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = HTTPError("Server error")
        mock_request.return_value = mock_response

        with pytest.raises(PokemonPriceTrackerError) as exc_info:
            client._make_request("GET", "/test")

        assert "HTTP error occurred" in str(exc_info.value)

    @patch("requests.Session.request")
    def test_timeout_raises_error(self, mock_request, client):
        """Test that timeout raises PokemonPriceTrackerError."""
        mock_request.side_effect = Timeout("Request timed out")

        with pytest.raises(PokemonPriceTrackerError) as exc_info:
            client._make_request("GET", "/test")

        assert "timed out" in str(exc_info.value)

    @patch("requests.Session.request")
    def test_invalid_json_raises_error(self, mock_request, client):
        """Test that invalid JSON response raises error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_request.return_value = mock_response

        with pytest.raises(PokemonPriceTrackerError) as exc_info:
            client._make_request("GET", "/test")

        assert "Invalid JSON response" in str(exc_info.value)

    @patch("requests.Session.request")
    def test_request_exception_raises_error(self, mock_request, client):
        """Test that RequestException raises PokemonPriceTrackerError."""
        mock_request.side_effect = RequestException("Network error")

        with pytest.raises(PokemonPriceTrackerError) as exc_info:
            client._make_request("GET", "/test")

        assert "Request failed" in str(exc_info.value)


class TestGetSets:
    """Test the get_sets method."""

    @patch("requests.Session.request")
    def test_get_sets_basic(self, mock_request, client, mock_response):
        """Test basic get_sets call."""
        mock_response.json.return_value = {"sets": [{"_id": "1", "name": "Test Set"}]}
        mock_request.return_value = mock_response

        result = client.get_sets()

        # Verify request
        call_args = mock_request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "https://api.test.com/sets"

        # Verify params include default language
        params = call_args[1]["params"]
        assert params["language"] == "japanese"

        # Verify response
        assert "sets" in result
        assert len(result["sets"]) == 1

    @patch("requests.Session.request")
    def test_get_sets_with_search(self, mock_request, client, mock_response):
        """Test get_sets with search parameter."""
        mock_request.return_value = mock_response

        client.get_sets(search="Pokemon Card 151")

        params = mock_request.call_args[1]["params"]
        assert params["search"] == "Pokemon Card 151"
        assert params["language"] == "japanese"

    @patch("requests.Session.request")
    def test_get_sets_with_all_params(self, mock_request, client, mock_response):
        """Test get_sets with all parameters."""
        mock_request.return_value = mock_response

        client.get_sets(
            search="151",
            language="english",
            sort_by="releaseDate",
            sort_order="desc",
            limit=10,
        )

        params = mock_request.call_args[1]["params"]
        assert params["search"] == "151"
        assert params["language"] == "english"
        assert params["sortBy"] == "releaseDate"
        assert params["sortOrder"] == "desc"
        assert params["limit"] == 10

    @patch("requests.Session.request")
    def test_get_sets_uses_default_language(self, mock_request, client, mock_response):
        """Test that get_sets uses default language when not specified."""
        mock_request.return_value = mock_response

        client.get_sets()

        params = mock_request.call_args[1]["params"]
        assert params["language"] == "japanese"


class TestGetCardsInSet:
    """Test the get_cards_in_set method."""

    @patch("requests.Session.request")
    def test_get_cards_in_set_basic(self, mock_request, client, mock_response):
        """Test basic get_cards_in_set call."""
        mock_response.json.return_value = {"cards": [{"name": "Charizard", "cardNumber": "1/100"}]}
        mock_request.return_value = mock_response

        result = client.get_cards_in_set("test_set_id")

        # Verify request
        call_args = mock_request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "https://api.test.com/cards"

        # Verify params
        params = call_args[1]["params"]
        assert params["setId"] == "test_set_id"  # Changed from "set" to "setId"
        assert params["language"] == "japanese"
        assert params["includeHistory"] == "true"
        assert params["days"] == 7
        assert params["fetchAllInSet"] == "true"

        # Verify response
        assert "cards" in result

    @patch("requests.Session.request")
    def test_get_cards_in_set_with_history(self, mock_request, client, mock_response):
        """Test get_cards_in_set with price history."""
        mock_response.json.return_value = {
            "cards": [
                {
                    "name": "Charizard",
                    "priceHistory": [
                        {"date": "2024-01-01", "price": 100.0},
                        {"date": "2024-01-02", "price": 105.0},
                    ],
                }
            ]
        }
        mock_request.return_value = mock_response

        result = client.get_cards_in_set(
            "test_set_id_2",
            include_history=True,
            days=14,
        )

        params = mock_request.call_args[1]["params"]
        assert params["includeHistory"] == "true"
        assert params["days"] == 14

        # Verify history in response
        assert len(result["cards"][0]["priceHistory"]) == 2

    @patch("requests.Session.request")
    def test_get_cards_in_set_without_history(self, mock_request, client, mock_response):
        """Test get_cards_in_set without price history."""
        mock_request.return_value = mock_response

        client.get_cards_in_set("test_set", include_history=False)

        params = mock_request.call_args[1]["params"]
        assert params["includeHistory"] == "false"

    @patch("requests.Session.request")
    def test_get_cards_in_set_with_limit(self, mock_request, client, mock_response):
        """Test get_cards_in_set with limit parameter."""
        mock_request.return_value = mock_response

        client.get_cards_in_set("test_set", limit=5)

        params = mock_request.call_args[1]["params"]
        assert params["limit"] == 5

    @patch("requests.Session.request")
    def test_get_cards_in_set_custom_language(self, mock_request, client, mock_response):
        """Test get_cards_in_set with custom language."""
        mock_request.return_value = mock_response

        client.get_cards_in_set("test_set", language="english")

        params = mock_request.call_args[1]["params"]
        assert params["language"] == "english"


class TestGetSingleCardWithHistory:
    """Test the get_single_card_with_history method."""

    @patch("requests.Session.request")
    def test_get_card_by_tcgplayer_id(self, mock_request, client, mock_response):
        """Test getting card by TCGPlayer ID."""
        mock_response.json.return_value = {"cards": [{"name": "Charizard", "tcgPlayerId": 490294}]}
        mock_request.return_value = mock_response

        _result = client.get_single_card_with_history(tcgplayer_id=490294, days=7)

        params = mock_request.call_args[1]["params"]
        assert params["tcgPlayerId"] == 490294
        assert params["includeHistory"] == "true"
        assert params["days"] == 7
        assert params["language"] == "japanese"

    @patch("requests.Session.request")
    def test_get_card_by_card_number_and_set(self, mock_request, client, mock_response):
        """Test getting card by card number and set."""
        mock_request.return_value = mock_response

        client.get_single_card_with_history(
            card_number="201/165",
            set_id_or_code="test_set_id_2",
            days=14,
        )

        params = mock_request.call_args[1]["params"]
        assert params["cardNumber"] == "201/165"
        assert (
            params["set"] == "test_set_id_2"
        )  # get_single_card_with_history uses "set", not "setId"
        assert params["days"] == 14

    def test_get_card_missing_params_raises_error(self, client):
        """Test that missing required params raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            client.get_single_card_with_history()

        assert "Must provide either" in str(exc_info.value)

    def test_get_card_partial_params_raises_error(self, client):
        """Test that partial params (card_number without set) raises error."""
        with pytest.raises(ValueError):
            client.get_single_card_with_history(card_number="201/165")

    @patch("requests.Session.request")
    def test_get_card_custom_language(self, mock_request, client, mock_response):
        """Test getting card with custom language."""
        mock_request.return_value = mock_response

        client.get_single_card_with_history(
            tcgplayer_id=490294,
            language="english",
        )

        params = mock_request.call_args[1]["params"]
        assert params["language"] == "english"


class TestSearchCards:
    """Test the search_cards method."""

    @patch("requests.Session.request")
    def test_search_cards_basic(self, mock_request, client, mock_response):
        """Test basic card search."""
        mock_response.json.return_value = {"cards": [{"name": "Charizard"}]}
        mock_request.return_value = mock_response

        _result = client.search_cards("Charizard")

        params = mock_request.call_args[1]["params"]
        assert params["search"] == "Charizard"
        assert params["language"] == "japanese"
        assert params["includeHistory"] == "false"

    @patch("requests.Session.request")
    def test_search_cards_with_filters(self, mock_request, client, mock_response):
        """Test card search with filters."""
        mock_request.return_value = mock_response

        client.search_cards(
            "Charizard",
            min_price=100.0,
            include_history=True,
            days=30,
            limit=10,
        )

        params = mock_request.call_args[1]["params"]
        assert params["search"] == "Charizard"
        assert params["minPrice"] == 100.0
        assert params["includeHistory"] == "true"
        assert params["days"] == 30
        assert params["limit"] == 10


class TestContextManager:
    """Test context manager functionality."""

    @patch("requests.Session.close")
    def test_context_manager_closes_session(self, mock_close):
        """Test that context manager closes session on exit."""
        with PokemonPriceTrackerClient(api_key="test") as client:
            assert client is not None

        mock_close.assert_called_once()

    def test_close_method(self, client):
        """Test that close method works."""
        with patch.object(client._session, "close") as mock_close:
            client.close()
            mock_close.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @patch("requests.Session.request")
    def test_empty_response(self, mock_request, client):
        """Test handling of empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        result = client.get_sets()
        assert result == {}

    @patch("requests.Session.request")
    def test_large_days_parameter(self, mock_request, client, mock_response):
        """Test with large days parameter (API may limit this)."""
        mock_request.return_value = mock_response

        client.get_cards_in_set("test_set", days=90)

        params = mock_request.call_args[1]["params"]
        assert params["days"] == 90

    def test_special_characters_in_search(self, client, mock_response):
        """Test search with special characters."""
        with patch("requests.Session.request") as mock_request:
            mock_request.return_value = mock_response

            client.search_cards("Pikachu & Zekrom GX")

            params = mock_request.call_args[1]["params"]
            assert params["search"] == "Pikachu & Zekrom GX"
