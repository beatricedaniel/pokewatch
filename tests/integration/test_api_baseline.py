"""
Integration tests for PokeWatch API.

Tests the /fair_price endpoint with real or mocked baseline model.
"""

import pytest
from datetime import date, timedelta

import pandas as pd
from fastapi.testclient import TestClient

from pokewatch.api.main import app
from pokewatch.models.baseline import BaselineFairPriceModel


@pytest.fixture
def mock_features_df():
    """Create a mock features DataFrame for testing."""
    base_date = date(2025, 11, 20)

    data = []
    # Card 1: 3 dates
    for i in range(3):
        data.append(
            {
                "card_id": "test_card_1",
                "card_number": "001/165",
                "card_name": "Test Card 1",
                "set_id": "test_set",
                "set_name": "Test Set",
                "date": base_date + timedelta(days=i),
                "market_price": 100.0 + (i * 5.0),
                "category": "grail",
                "rarity": "Rare",
                "tcgplayer_id": "123",
                "source": "test",
                "lag_1": None if i == 0 else 100.0 + ((i - 1) * 5.0),
                "rolling_mean_3": 100.0 + (i * 2.5),
                "rolling_mean_5": 100.0 + (i * 2.0),
                "price_return_1d": None if i == 0 else 0.05,
                "fair_value_baseline": 100.0 + (i * 2.5),
            }
        )

    # Card 2: 2 dates
    for i in range(2):
        data.append(
            {
                "card_id": "test_card_2",
                "card_number": "002/165",
                "card_name": "Test Card 2",
                "set_id": "test_set",
                "set_name": "Test Set",
                "date": base_date + timedelta(days=i),
                "market_price": 50.0 + (i * 3.0),
                "category": "chase",
                "rarity": "Common",
                "tcgplayer_id": "456",
                "source": "test",
                "lag_1": None if i == 0 else 50.0,
                "rolling_mean_3": 50.0 + (i * 1.5),
                "rolling_mean_5": 50.0 + (i * 1.2),
                "price_return_1d": None if i == 0 else 0.06,
                "fair_value_baseline": 50.0 + (i * 1.5),
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def mock_model(mock_features_df):
    """Create a mock baseline model."""
    return BaselineFairPriceModel(mock_features_df)


@pytest.fixture
def client(mock_model):
    """Create a test client with mocked model."""
    # Manually set the model in dependencies for testing BEFORE creating client
    from pokewatch.api import dependencies
    from pokewatch.config import get_settings
    from pokewatch.core.decision_rules import DecisionConfig

    # Set the model and config
    dependencies.set_model(mock_model)
    settings = get_settings()
    cfg = DecisionConfig(
        buy_threshold_pct=settings.model.default_buy_threshold_pct,
        sell_threshold_pct=settings.model.default_sell_threshold_pct,
    )
    dependencies.set_decision_config(cfg)

    # Create client (lifespan won't run, but dependencies are already set)
    test_client = TestClient(app)

    yield test_client

    # Cleanup
    dependencies.set_model(None)
    dependencies.set_decision_config(None)


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns ok when model is loaded."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True
        assert data["cards_count"] == 2  # We have 2 test cards


class TestFairPriceEndpoint:
    """Test /fair_price endpoint."""

    def test_fair_price_with_known_card_id(self, client):
        """Test fair_price endpoint with a known card_id."""
        payload = {
            "card_id": "test_card_1",
            "date": None,  # Use latest date
        }

        response = client.post("/fair_price", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["card_id"] == "test_card_1"
        assert "date" in data
        assert isinstance(data["market_price"], (int, float))
        assert isinstance(data["fair_price"], (int, float))
        assert isinstance(data["deviation_pct"], (int, float))
        assert data["signal"] in ["BUY", "SELL", "HOLD"]

    def test_fair_price_with_specific_date(self, client):
        """Test fair_price endpoint with a specific date."""
        base_date = date(2025, 11, 20)

        payload = {
            "card_id": "test_card_1",
            "date": base_date.isoformat(),
        }

        response = client.post("/fair_price", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["card_id"] == "test_card_1"
        assert data["date"] == base_date.isoformat()
        assert data["market_price"] == 100.0
        assert data["fair_price"] == 100.0

    def test_fair_price_unknown_card_id(self, client):
        """Test fair_price endpoint with unknown card_id."""
        payload = {
            "card_id": "unknown_card",
            "date": None,
        }

        response = client.post("/fair_price", json=payload)
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "Unknown card_id" in data["detail"]

    def test_fair_price_date_not_found(self, client):
        """Test fair_price endpoint with date that doesn't exist."""
        future_date = date(2026, 1, 1)

        payload = {
            "card_id": "test_card_1",
            "date": future_date.isoformat(),
        }

        response = client.post("/fair_price", json=payload)
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "No data found" in data["detail"]

    def test_fair_price_response_structure(self, client):
        """Test that response has all required fields."""
        payload = {
            "card_id": "test_card_1",
            "date": None,
        }

        response = client.post("/fair_price", json=payload)
        assert response.status_code == 200

        data = response.json()
        required_fields = [
            "card_id",
            "date",
            "market_price",
            "fair_price",
            "deviation_pct",
            "signal",
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Validate types
        assert isinstance(data["card_id"], str)
        assert isinstance(data["date"], str)  # ISO format date string
        assert isinstance(data["market_price"], (int, float))
        assert isinstance(data["fair_price"], (int, float))
        assert isinstance(data["deviation_pct"], (int, float))
        assert data["signal"] in ["BUY", "SELL", "HOLD"]

    def test_fair_price_signal_logic(self, client):
        """Test that signals are computed correctly."""
        # Test with card that has known prices
        # We'll use the latest date which should have market_price=110, fair_price=105
        payload = {
            "card_id": "test_card_1",
            "date": None,  # Latest date (day 2)
        }

        response = client.post("/fair_price", json=payload)
        assert response.status_code == 200

        data = response.json()
        # market_price=110, fair_price=105
        # deviation = (110 - 105) / 105 = 0.0476 = 4.76%
        # This is less than sell_threshold (15%), so should be HOLD
        assert data["signal"] == "HOLD"
        assert data["deviation_pct"] > 0  # Positive deviation (overvalued)


class TestListCardsEndpoint:
    """Test /cards endpoint."""

    def test_list_cards(self, client):
        """Test listing all available cards."""
        response = client.get("/cards")
        assert response.status_code == 200

        data = response.json()
        assert "cards" in data
        assert "count" in data
        assert data["count"] == 2
        assert "test_card_1" in data["cards"]
        assert "test_card_2" in data["cards"]
