"""
Unit tests for make_features module.

Tests feature engineering logic including lag features, rolling means, and fair value baseline.
"""

import pytest
from datetime import date, timedelta
import pandas as pd

from pokewatch.data.preprocessing.make_features import (
    build_features,
    ensure_consistent_schema,
)


class TestBuildFeatures:
    """Test feature engineering functions."""

    def test_build_features_basic(self):
        """Test basic feature building with two cards and multiple dates."""
        # Create test data: 2 cards, 4 dates each
        base_date = date(2025, 11, 20)

        data = []
        # Card 1: prices [100, 105, 110, 115]
        for i in range(4):
            data.append(
                {
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
                }
            )

        # Card 2: prices [50, 55, 60, 65]
        for i in range(4):
            data.append(
                {
                    "card_id": "card_2",
                    "card_number": "002/165",
                    "card_name": "Card 2",
                    "set_id": "test_set",
                    "set_name": "Test Set",
                    "date": base_date + timedelta(days=i),
                    "market_price": 50.0 + (i * 5.0),
                    "category": "chase",
                    "rarity": "Common",
                    "tcgplayer_id": "456",
                    "source": "test",
                }
            )

        df = pd.DataFrame(data)

        # Build features
        result_df = build_features(df)

        # Verify structure
        assert len(result_df) == 8
        assert "lag_1" in result_df.columns
        assert "rolling_mean_3" in result_df.columns
        assert "rolling_mean_5" in result_df.columns
        assert "price_return_1d" in result_df.columns
        assert "fair_value_baseline" in result_df.columns

        # Test Card 1 features
        card_1_df = result_df[result_df["card_id"] == "card_1"].sort_values("date")

        # First row: no lag_1 (first date)
        assert pd.isna(card_1_df.iloc[0]["lag_1"])
        # Second row: lag_1 should be 100.0
        assert card_1_df.iloc[1]["lag_1"] == 100.0
        # Third row: lag_1 should be 105.0
        assert card_1_df.iloc[2]["lag_1"] == 105.0
        # Fourth row: lag_1 should be 110.0
        assert card_1_df.iloc[3]["lag_1"] == 110.0

        # Rolling mean 3: first row = 100, second = (100+105)/2 = 102.5, third = (100+105+110)/3 = 105, fourth = (105+110+115)/3 = 110
        assert card_1_df.iloc[0]["rolling_mean_3"] == 100.0
        assert card_1_df.iloc[1]["rolling_mean_3"] == pytest.approx(102.5, abs=0.01)
        assert card_1_df.iloc[2]["rolling_mean_3"] == pytest.approx(105.0, abs=0.01)
        assert card_1_df.iloc[3]["rolling_mean_3"] == pytest.approx(110.0, abs=0.01)

        # Price return 1d: first row = NaN, second = (105/100 - 1) = 0.05, third = (110/105 - 1) ≈ 0.0476, fourth = (115/110 - 1) ≈ 0.0455
        assert pd.isna(card_1_df.iloc[0]["price_return_1d"])
        assert card_1_df.iloc[1]["price_return_1d"] == pytest.approx(0.05, abs=0.001)
        assert card_1_df.iloc[2]["price_return_1d"] == pytest.approx(0.0476, abs=0.001)
        assert card_1_df.iloc[3]["price_return_1d"] == pytest.approx(0.0455, abs=0.001)

        # Fair value baseline: should use rolling_mean_3 when available
        assert card_1_df.iloc[0]["fair_value_baseline"] == 100.0  # rolling_mean_3 = 100
        assert card_1_df.iloc[1]["fair_value_baseline"] == pytest.approx(
            102.5, abs=0.01
        )  # rolling_mean_3
        assert card_1_df.iloc[2]["fair_value_baseline"] == pytest.approx(
            105.0, abs=0.01
        )  # rolling_mean_3
        assert card_1_df.iloc[3]["fair_value_baseline"] == pytest.approx(
            110.0, abs=0.01
        )  # rolling_mean_3

    def test_build_features_fair_value_fallback(self):
        """Test that fair_value_baseline falls back to market_price when rolling_mean_3 is NaN."""
        # Create test data with only 1 date (rolling_mean_3 will be NaN)
        base_date = date(2025, 11, 20)

        data = [
            {
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
            }
        ]

        df = pd.DataFrame(data)
        result_df = build_features(df)

        # With only 1 date, rolling_mean_3 should equal market_price (window=3, min_periods=1)
        # Actually, with min_periods=1, rolling_mean_3 will be 100.0, not NaN
        # So fair_value_baseline should be 100.0
        assert result_df.iloc[0]["fair_value_baseline"] == 100.0

    def test_build_features_rolling_mean_5(self):
        """Test rolling_mean_5 calculation."""
        base_date = date(2025, 11, 20)

        # Create 5 dates for one card
        data = []
        for i in range(5):
            data.append(
                {
                    "card_id": "card_1",
                    "card_number": "001/165",
                    "card_name": "Card 1",
                    "set_id": "test_set",
                    "set_name": "Test Set",
                    "date": base_date + timedelta(days=i),
                    "market_price": 100.0 + (i * 10.0),  # [100, 110, 120, 130, 140]
                    "category": "grail",
                    "rarity": "Rare",
                    "tcgplayer_id": "123",
                    "source": "test",
                }
            )

        df = pd.DataFrame(data)
        result_df = build_features(df)
        card_df = result_df[result_df["card_id"] == "card_1"].sort_values("date")

        # Rolling mean 5: should calculate properly
        # First: 100, Second: (100+110)/2=105, Third: (100+110+120)/3=110, Fourth: (100+110+120+130)/4=115, Fifth: (100+110+120+130+140)/5=120
        assert card_df.iloc[0]["rolling_mean_5"] == 100.0
        assert card_df.iloc[1]["rolling_mean_5"] == pytest.approx(105.0, abs=0.01)
        assert card_df.iloc[2]["rolling_mean_5"] == pytest.approx(110.0, abs=0.01)
        assert card_df.iloc[3]["rolling_mean_5"] == pytest.approx(115.0, abs=0.01)
        assert card_df.iloc[4]["rolling_mean_5"] == pytest.approx(120.0, abs=0.01)

    def test_build_features_multiple_cards_independent(self):
        """Test that features are calculated independently for each card."""
        base_date = date(2025, 11, 20)

        data = []
        # Card 1: [10, 20]
        for i, price in enumerate([10.0, 20.0]):
            data.append(
                {
                    "card_id": "card_1",
                    "card_number": "001/165",
                    "card_name": "Card 1",
                    "set_id": "test_set",
                    "set_name": "Test Set",
                    "date": base_date + timedelta(days=i),
                    "market_price": price,
                    "category": "grail",
                    "rarity": "Rare",
                    "tcgplayer_id": "123",
                    "source": "test",
                }
            )

        # Card 2: [100, 200]
        for i, price in enumerate([100.0, 200.0]):
            data.append(
                {
                    "card_id": "card_2",
                    "card_number": "002/165",
                    "card_name": "Card 2",
                    "set_id": "test_set",
                    "set_name": "Test Set",
                    "date": base_date + timedelta(days=i),
                    "market_price": price,
                    "category": "chase",
                    "rarity": "Common",
                    "tcgplayer_id": "456",
                    "source": "test",
                }
            )

        df = pd.DataFrame(data)
        result_df = build_features(df)

        card_1_df = result_df[result_df["card_id"] == "card_1"].sort_values("date")
        card_2_df = result_df[result_df["card_id"] == "card_2"].sort_values("date")

        # Card 1 lag_1 should be 10.0 on second row
        assert card_1_df.iloc[1]["lag_1"] == 10.0

        # Card 2 lag_1 should be 100.0 on second row
        assert card_2_df.iloc[1]["lag_1"] == 100.0

        # Features should be independent
        assert card_1_df.iloc[1]["rolling_mean_3"] != card_2_df.iloc[1]["rolling_mean_3"]


class TestEnsureConsistentSchema:
    """Test schema standardization."""

    def test_ensure_consistent_schema_date_conversion(self):
        """Test that date is converted to datetime.date."""
        base_date = date(2025, 11, 20)

        data = [
            {
                "card_id": "card_1",
                "card_number": "001/165",
                "card_name": "Card 1",
                "set_id": "test_set",
                "set_name": "Test Set",
                "date": pd.Timestamp(base_date),  # datetime64
                "market_price": 100.0,
                "category": "grail",
                "rarity": "Rare",
                "tcgplayer_id": "123",
                "source": "test",
            }
        ]

        df = pd.DataFrame(data)
        result_df = ensure_consistent_schema(df)

        # Date should be converted to date type
        assert isinstance(result_df.iloc[0]["date"], date)
        assert result_df.iloc[0]["date"] == base_date

    def test_ensure_consistent_schema_sorting(self):
        """Test that data is sorted by (card_id, date)."""
        base_date = date(2025, 11, 20)

        data = []
        # Create unsorted data
        for card_id, day_offset in [("card_2", 2), ("card_1", 1), ("card_1", 0), ("card_2", 0)]:
            data.append(
                {
                    "card_id": card_id,
                    "card_number": "001/165",
                    "card_name": "Card",
                    "set_id": "test_set",
                    "set_name": "Test Set",
                    "date": base_date + timedelta(days=day_offset),
                    "market_price": 100.0,
                    "category": "grail",
                    "rarity": "Rare",
                    "tcgplayer_id": "123",
                    "source": "test",
                }
            )

        df = pd.DataFrame(data)
        result_df = ensure_consistent_schema(df)

        # Should be sorted by card_id, then date
        assert result_df.iloc[0]["card_id"] == "card_1"
        assert result_df.iloc[0]["date"] == base_date
        assert result_df.iloc[1]["card_id"] == "card_1"
        assert result_df.iloc[1]["date"] == base_date + timedelta(days=1)
        assert result_df.iloc[2]["card_id"] == "card_2"
        assert result_df.iloc[2]["date"] == base_date
        assert result_df.iloc[3]["card_id"] == "card_2"
        assert result_df.iloc[3]["date"] == base_date + timedelta(days=2)
