"""
Client for Pokémon Price Tracker API.

This module provides a client to interact with the Pokémon Price Tracker API
(https://www.pokemonpricetracker.com/api/v2).

The client focuses on Japanese cards and includes price history data.
"""

import logging
from typing import Optional, Any

import requests
from requests.exceptions import RequestException, Timeout, HTTPError


logger = logging.getLogger(__name__)


class PokemonPriceTrackerError(Exception):
    """Base exception for Pokémon Price Tracker API errors."""

    pass


class PokemonPriceTrackerAuthError(PokemonPriceTrackerError):
    """Authentication error (401)."""

    pass


class PokemonPriceTrackerNotFoundError(PokemonPriceTrackerError):
    """Resource not found error (404)."""

    pass


class PokemonPriceTrackerRateLimitError(PokemonPriceTrackerError):
    """Rate limit exceeded error (429)."""

    pass


class PokemonPriceTrackerClient:
    """
    Client for Pokémon Price Tracker API v2.

    Handles authentication, request formatting, and error handling
    for the Pokémon Price Tracker API.

    Attributes:
        base_url: Base URL for the API (default: https://www.pokemonpricetracker.com/api/v2)
        timeout: Request timeout in seconds
        default_language: Default language for requests (default: "japanese")

    Example:
        >>> client = PokemonPriceTrackerClient(api_key="your_api_key")
        >>> sets = client.get_sets(language="japanese")
        >>> cards = client.get_cards_in_set("set_id_from_config", include_history=True, days=7)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://www.pokemonpricetracker.com/api/v2",
        timeout: int = 10,
        default_language: str = "japanese",
    ):
        """
        Initialize the Pokémon Price Tracker client.

        Args:
            api_key: API key for authentication
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            default_language: Default language for requests
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.default_language = default_language

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "PokeWatch/0.1.0",
            }
        )

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> dict:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/sets", "/cards")
            params: Query parameters
            **kwargs: Additional arguments for requests

        Returns:
            JSON response as dictionary

        Raises:
            PokemonPriceTrackerAuthError: If authentication fails (401)
            PokemonPriceTrackerNotFoundError: If resource not found (404)
            PokemonPriceTrackerRateLimitError: If rate limit exceeded (429)
            PokemonPriceTrackerError: For other API errors
        """
        url = f"{self.base_url}{endpoint}"

        # Remove None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        try:
            logger.debug(f"Making {method} request to {url} with params: {params}")
            response = self._session.request(
                method,
                url,
                params=params,
                timeout=self.timeout,
                **kwargs,
            )

            # Handle specific HTTP errors
            if response.status_code == 401:
                raise PokemonPriceTrackerAuthError(
                    "Authentication failed. Please check your API key."
                )
            elif response.status_code == 404:
                raise PokemonPriceTrackerNotFoundError(f"Resource not found: {url}")
            elif response.status_code == 429:
                raise PokemonPriceTrackerRateLimitError(
                    "Rate limit exceeded. Please try again later."
                )

            # Raise for other HTTP errors
            response.raise_for_status()

            # Parse JSON response
            try:
                return response.json()
            except ValueError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise PokemonPriceTrackerError(f"Invalid JSON response from API: {e}")

        except Timeout:
            raise PokemonPriceTrackerError(f"Request timed out after {self.timeout} seconds")
        except HTTPError as e:
            raise PokemonPriceTrackerError(f"HTTP error occurred: {e}")
        except RequestException as e:
            raise PokemonPriceTrackerError(f"Request failed: {e}")

    def get_sets(
        self,
        search: Optional[str] = None,
        language: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """
        Get Pokémon card sets.

        Wraps: GET /api/v2/sets

        Args:
            search: Filter sets by name (e.g., "Pokemon Card 151")
            language: Filter by language (default: self.default_language)
            sort_by: Sort field (e.g., "releaseDate")
            sort_order: Sort order ("asc" or "desc")
            limit: Maximum number of results

        Returns:
            Dictionary containing sets data

        Example:
            >>> client = PokemonPriceTrackerClient(api_key="...")
            >>> sets = client.get_sets(language="japanese", search="151")
            >>> print(sets["sets"][0]["name"])
        """
        params = {
            "search": search,
            "language": language or self.default_language,
            "sortBy": sort_by,
            "sortOrder": sort_order,
            "limit": limit,
        }

        logger.info(f"Fetching sets with params: {params}")
        return self._make_request("GET", "/sets", params=params)

    def get_cards_in_set(
        self,
        set_id_or_code: str,
        language: Optional[str] = None,
        include_history: bool = True,
        days: int = 7,
        fetch_all_in_set: bool = True,
        limit: Optional[int] = None,
    ) -> dict:
        """
        Get all cards in a specific set with price history.

        Wraps: GET /api/v2/cards?set=<...>&language=japanese&includeHistory=true&days=7

        Args:
            set_id_or_code: Set ID or code (e.g., "set_id_from_config" or "set-code")
            language: Card language (default: self.default_language)
            include_history: Include price history data
            days: Number of days of price history (max 90 on paid tiers, 7 on free)
            fetch_all_in_set: Fetch all cards in set efficiently
            limit: Maximum number of results (optional)

        Returns:
            Dictionary containing cards data with price history

        Example:
            >>> client = PokemonPriceTrackerClient(api_key="...")
            >>> cards = client.get_cards_in_set(
            ...     "set_id_from_config",
            ...     include_history=True,
            ...     days=7
            ... )
            >>> for card in cards["data"]:
            ...     print(card["name"], card.get("priceHistory", []))
        """
        params = {
            "setId": set_id_or_code,
            "language": language or self.default_language,
            "includeHistory": str(include_history).lower(),
            "days": days,
            "fetchAllInSet": str(fetch_all_in_set).lower(),
            "limit": limit,
        }

        logger.info(f"Fetching cards in set {set_id_or_code} with {days} days of history")
        return self._make_request("GET", "/cards", params=params)

    def get_single_card_with_history(
        self,
        tcgplayer_id: Optional[int] = None,
        card_number: Optional[str] = None,
        set_id_or_code: Optional[str] = None,
        language: Optional[str] = None,
        days: int = 7,
    ) -> dict:
        """
        Get a single card's data with price history.

        Wraps: GET /api/v2/cards with specific card filters

        You must provide either:
        - tcgplayer_id, OR
        - card_number + set_id_or_code

        Args:
            tcgplayer_id: TCGPlayer ID for the card
            card_number: Card number (e.g., "201/165")
            set_id_or_code: Set ID or code (required if using card_number)
            language: Card language (default: self.default_language)
            days: Number of days of price history

        Returns:
            Dictionary containing card data with price history

        Raises:
            ValueError: If neither tcgplayer_id nor (card_number + set) provided

        Example:
            >>> client = PokemonPriceTrackerClient(api_key="...")
            >>> # By TCGPlayer ID
            >>> card = client.get_single_card_with_history(tcgplayer_id=490294, days=7)
            >>> # By card number and set
            >>> card = client.get_single_card_with_history(
            ...     card_number="201/165",
            ...     set_id_or_code="set_id_from_config",
            ...     days=7
            ... )
        """
        if not tcgplayer_id and not (card_number and set_id_or_code):
            raise ValueError("Must provide either tcgplayer_id OR (card_number + set_id_or_code)")

        params = {
            "language": language or self.default_language,
            "includeHistory": "true",
            "days": days,
        }

        if tcgplayer_id:
            params["tcgPlayerId"] = tcgplayer_id
            logger.info(f"Fetching card with TCGPlayer ID {tcgplayer_id}")
        else:
            params["cardNumber"] = card_number
            params["set"] = set_id_or_code
            logger.info(f"Fetching card {card_number} from set {set_id_or_code}")

        return self._make_request("GET", "/cards", params=params)

    def search_cards(
        self,
        search: str,
        language: Optional[str] = None,
        min_price: Optional[float] = None,
        include_history: bool = False,
        days: int = 7,
        limit: Optional[int] = None,
    ) -> dict:
        """
        Search for cards by name.

        Wraps: GET /api/v2/cards?search=<...>

        Args:
            search: Search query (card name)
            language: Card language (default: self.default_language)
            min_price: Minimum price filter
            include_history: Include price history data
            days: Number of days of price history
            limit: Maximum number of results

        Returns:
            Dictionary containing matching cards

        Example:
            >>> client = PokemonPriceTrackerClient(api_key="...")
            >>> cards = client.search_cards("Charizard", min_price=100.0)
        """
        params = {
            "search": search,
            "language": language or self.default_language,
            "minPrice": min_price,
            "includeHistory": str(include_history).lower(),
            "days": days,
            "limit": limit,
        }

        logger.info(f"Searching cards with query: {search}")
        return self._make_request("GET", "/cards", params=params)

    def close(self):
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
