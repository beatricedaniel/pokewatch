"""
Unit tests for BaselineFairPriceModel.
"""

import pytest
from datetime import date, timedelta
import pandas as pd

from pokewatch.models.baseline import BaselineFairPriceModel


class TestBaselineFairPriceModel:
    """Test baseline fair price model."""

    def test_init_with_valid_data(self):
        """Test model initialization with valid data."""
        base_date = date(2025, 11, 20)

        data = []
        # Card 1: 3 dates
        for i in range(3):
            data.append({
                "card_id": "card_1",
                "card_number": "001/165",
                "card_name": "Card 1",
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
            })

        # Card 2: 2 dates
        for i in range(2):
            data.append({
                "card_id": "card_2",
                "card_number": "002/165",
                "card_name": "Card 2",
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
            })

        df = pd.DataFrame(data)
        model = BaselineFairPriceModel(df)

        assert len(model.known_card_ids) == 2
        assert "card_1" in model.known_card_ids
        assert "card_2" in model.known_card_ids
        assert model.latest_dates["card_1"] == base_date + timedelta(days=2)
        assert model.latest_dates["card_2"] == base_date + timedelta(days=1)

    def test_init_missing_columns(self):
        """Test that initialization fails with missing required columns."""
        df = pd.DataFrame({
            "card_id": ["card_1"],
            "date": [date(2025, 11, 20)],
            "market_price": [100.0],
            # Missing fair_value_baseline
        })

        with pytest.raises(ValueError, match="Missing required columns"):
            BaselineFairPriceModel(df)

    def test_predict_with_specific_date(self):
        """Test prediction with a specific date."""
        base_date = date(2025, 11, 20)

        data = [{
            "card_id": "card_1",
            "card_number": "001/165",
            "card_name": "Card 1",
            "set_id": "test_set",
            "set_name": "Test Set",
            "date": base_date,
            "market_price": 100.0,
            "category": "grail",
            "rarity": "Rare",
            "tcgplayer_id": "123",
            "source": "test",
            "lag_1": None,
            "rolling_mean_3": 100.0,
            "rolling_mean_5": 100.0,
            "price_return_1d": None,
            "fair_value_baseline": 100.0,
        }]

        df = pd.DataFrame(data)
        model = BaselineFairPriceModel(df)

        resolved_date, market_price, fair_price = model.predict("card_1", date=base_date)

        assert resolved_date == base_date
        assert market_price == 100.0
        assert fair_price == 100.0

    def test_predict_with_none_date_uses_latest(self):
        """Test that prediction with date=None uses latest available date."""
        base_date = date(2025, 11, 20)

        data = []
        for i in range(3):
            data.append({
                "card_id": "card_1",
                "card_number": "001/165",
                "card_name": "Card 1",
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
            })

        df = pd.DataFrame(data)
        model = BaselineFairPriceModel(df)

        # Predict with date=None should use latest date (base_date + 2 days)
        resolved_date, market_price, fair_price = model.predict("card_1", date=None)

        assert resolved_date == base_date + timedelta(days=2)
        assert market_price == 110.0
        assert fair_price == 105.0  # rolling_mean_3 for day 2

    def test_predict_unknown_card_id(self):
        """Test that prediction raises error for unknown card_id."""
        base_date = date(2025, 11, 20)

        data = [{
            "card_id": "card_1",
            "card_number": "001/165",
            "card_name": "Card 1",
            "set_id": "test_set",
            "set_name": "Test Set",
            "date": base_date,
            "market_price": 100.0,
            "category": "grail",
            "rarity": "Rare",
            "tcgplayer_id": "123",
            "source": "test",
            "lag_1": None,
            "rolling_mean_3": 100.0,
            "rolling_mean_5": 100.0,
            "price_return_1d": None,
            "fair_value_baseline": 100.0,
        }]

        df = pd.DataFrame(data)
        model = BaselineFairPriceModel(df)

        with pytest.raises(ValueError, match="Unknown card_id"):
            model.predict("unknown_card")

    def test_predict_date_not_found(self):
        """Test that prediction raises error when date is not found."""
        base_date = date(2025, 11, 20)

        data = [{
            "card_id": "card_1",
            "card_number": "001/165",
            "card_name": "Card 1",
            "set_id": "test_set",
            "set_name": "Test Set",
            "date": base_date,
            "market_price": 100.0,
            "category": "grail",
            "rarity": "Rare",
            "tcgplayer_id": "123",
            "source": "test",
            "lag_1": None,
            "rolling_mean_3": 100.0,
            "rolling_mean_5": 100.0,
            "price_return_1d": None,
            "fair_value_baseline": 100.0,
        }]

        df = pd.DataFrame(data)
        model = BaselineFairPriceModel(df)

        with pytest.raises(ValueError, match="No data found"):
            model.predict("card_1", date=base_date + timedelta(days=10))

    def test_get_latest_date(self):
        """Test getting latest date for a card."""
        base_date = date(2025, 11, 20)

        data = []
        for i in range(3):
            data.append({
                "card_id": "card_1",
                "card_number": "001/165",
                "card_name": "Card 1",
                "set_id": "test_set",
                "set_name": "Test Set",
                "date": base_date + timedelta(days=i),
                "market_price": 100.0,
                "category": "grail",
                "rarity": "Rare",
                "tcgplayer_id": "123",
                "source": "test",
                "lag_1": None,
                "rolling_mean_3": 100.0,
                "rolling_mean_5": 100.0,
                "price_return_1d": None,
                "fair_value_baseline": 100.0,
            })

        df = pd.DataFrame(data)
        model = BaselineFairPriceModel(df)

        latest = model.get_latest_date("card_1")
        assert latest == base_date + timedelta(days=2)

        # Unknown card returns None
        assert model.get_latest_date("unknown") is None

    def test_get_all_card_ids(self):
        """Test getting all card IDs."""
        base_date = date(2025, 11, 20)

        data = []
        for card_id in ["card_1", "card_2", "card_3"]:
            data.append({
                "card_id": card_id,
                "card_number": "001/165",
                "card_name": "Card",
                "set_id": "test_set",
                "set_name": "Test Set",
                "date": base_date,
                "market_price": 100.0,
                "category": "grail",
                "rarity": "Rare",
                "tcgplayer_id": "123",
                "source": "test",
                "lag_1": None,
                "rolling_mean_3": 100.0,
                "rolling_mean_5": 100.0,
                "price_return_1d": None,
                "fair_value_baseline": 100.0,
            })

        df = pd.DataFrame(data)
        model = BaselineFairPriceModel(df)

        card_ids = model.get_all_card_ids()
        assert len(card_ids) == 3
        assert card_ids == ["card_1", "card_2", "card_3"]

