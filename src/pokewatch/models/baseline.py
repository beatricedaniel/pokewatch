"""
Baseline fair price model.

A minimal "model" that looks up values from processed features.
No training required - just uses the fair_value_baseline from feature engineering.
"""

import logging
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class BaselineFairPriceModel:
    """
    Baseline model that predicts fair price using pre-computed features.

    This model simply looks up values from the processed features DataFrame.
    It uses the fair_value_baseline column which is computed as:
    - rolling_mean_3 if available
    - market_price as fallback
    """

    def __init__(self, features_df: pd.DataFrame):
        """
        Initialize the baseline model with processed features.

        Args:
            features_df: DataFrame with columns: card_id, date, market_price, fair_value_baseline

        Raises:
            ValueError: If required columns are missing
        """
        required_columns = ["card_id", "date", "market_price", "fair_value_baseline"]
        missing_columns = set(required_columns) - set(features_df.columns)

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_columns}. "
                f"Available columns: {list(features_df.columns)}"
            )

        self.features_df = features_df.copy()

        # Ensure date is date type (not datetime)
        if pd.api.types.is_datetime64_any_dtype(self.features_df["date"]):
            self.features_df["date"] = self.features_df["date"].dt.date

        # Build index keyed by (card_id, date) for fast lookups
        self.features_df = self.features_df.sort_values(["card_id", "date"]).reset_index(
            drop=True
        )
        self.features_df.set_index(["card_id", "date"], inplace=True)

        # Keep latest date per card handy
        self.latest_dates = (
            self.features_df.reset_index()
            .groupby("card_id")["date"]
            .max()
            .to_dict()
        )

        # Track known card IDs
        self.known_card_ids = set(self.features_df.index.get_level_values("card_id").unique())

        logger.info(
            f"Initialized BaselineFairPriceModel with {len(self.known_card_ids)} cards, "
            f"date range: {min(self.latest_dates.values())} to {max(self.latest_dates.values())}"
        )

    def predict(
        self,
        card_id: str,
        date: Optional[date] = None,
    ) -> tuple[date, float, float]:
        """
        Predict fair price for a card.

        Args:
            card_id: Unique card identifier
            date: Date for prediction. If None, uses the latest available date for that card.

        Returns:
            Tuple of (resolved_date, market_price, fair_price)
            - resolved_date: The date used for prediction
            - market_price: Market price on that date
            - fair_price: Fair value baseline (predicted fair price)

        Raises:
            ValueError: If card_id is unknown
            ValueError: If date is specified but not found for that card
        """
        if card_id not in self.known_card_ids:
            raise ValueError(
                f"Unknown card_id: {card_id}. "
                f"Known card_ids: {sorted(list(self.known_card_ids))[:5]}..."
            )

        # If date is None, use latest available date for that card
        if date is None:
            resolved_date = self.latest_dates[card_id]
        else:
            resolved_date = date

        # Lookup values
        try:
            row = self.features_df.loc[(card_id, resolved_date)]
            market_price = float(row["market_price"])
            fair_price = float(row["fair_value_baseline"])
        except KeyError:
            raise ValueError(
                f"No data found for card_id={card_id} on date={resolved_date}. "
                f"Available dates for this card: {sorted(self._get_available_dates(card_id))}"
            )

        return (resolved_date, market_price, fair_price)

    def _get_available_dates(self, card_id: str) -> list[date]:
        """Get all available dates for a card."""
        return sorted(
            self.features_df.reset_index()[self.features_df.reset_index()["card_id"] == card_id][
                "date"
            ].unique()
        )

    def get_latest_date(self, card_id: str) -> Optional[date]:
        """
        Get the latest available date for a card.

        Args:
            card_id: Unique card identifier

        Returns:
            Latest date or None if card_id is unknown
        """
        return self.latest_dates.get(card_id)

    def get_all_card_ids(self) -> list[str]:
        """Get list of all known card IDs."""
        return sorted(list(self.known_card_ids))


def load_baseline_model(processed_data_path: Optional[Path] = None) -> BaselineFairPriceModel:
    """
    Load baseline model from processed data file.

    Args:
        processed_data_path: Path to processed parquet file.
            If None, loads from default location based on cards.yaml.

    Returns:
        Initialized BaselineFairPriceModel instance

    Raises:
        FileNotFoundError: If processed data file doesn't exist
    """
    if processed_data_path is None:
        from pokewatch.config import get_data_path
        from pokewatch.data.collectors.daily_price_collector import load_cards_config

        cards_config = load_cards_config()
        set_name = cards_config["set"]["name"]

        # Sanitize set name for filename
        safe_set_name = (
            set_name.lower().replace(" ", "_").replace(":", "").replace("-", "_")
        )
        safe_set_name = "".join(c for c in safe_set_name if c.isalnum() or c == "_")

        processed_data_path = get_data_path("processed") / f"{safe_set_name}.parquet"

    if not processed_data_path.exists():
        raise FileNotFoundError(
            f"Processed data file not found: {processed_data_path}\n"
            f"Please run feature engineering first: "
            f"python -m pokewatch.data.preprocessing.make_features"
        )

    logger.info(f"Loading baseline model from: {processed_data_path}")
    features_df = pd.read_parquet(processed_data_path)

    return BaselineFairPriceModel(features_df)

