"""
Feature engineering for Pokemon card price data.

Converts daily raw price files into a clean time-series table with engineered features.

Usage:
    python -m pokewatch.data.preprocessing.make_features
"""

import logging
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from pokewatch.config import get_settings, get_data_path
from pokewatch.data.collectors.daily_price_collector import load_cards_config

logger = logging.getLogger(__name__)


def load_raw_files(raw_dir: Path, set_name: str) -> pd.DataFrame:
    """
    Load all raw parquet files for a given set.

    Files should match pattern: {set_name}_prices_{date}.parquet

    Args:
        raw_dir: Directory containing raw data files
        set_name: Name of the set (sanitized, e.g., "sv2a_pokemon_card_151")

    Returns:
        Concatenated DataFrame with all raw data

    Raises:
        FileNotFoundError: If no matching files are found
    """
    # Sanitize set name for filename matching
    safe_set_name = set_name.lower().replace(" ", "_").replace(":", "").replace("-", "_")
    safe_set_name = "".join(c for c in safe_set_name if c.isalnum() or c == "_")

    # Find all matching files
    pattern = f"{safe_set_name}_prices_*.parquet"
    files = list(raw_dir.glob(pattern))

    if not files:
        raise FileNotFoundError(
            f"No raw files found matching pattern: {pattern} in {raw_dir}"
        )

    logger.info(f"Found {len(files)} raw files matching pattern: {pattern}")

    # Load and concatenate all files
    dfs = []
    for file_path in sorted(files):
        try:
            df = pd.read_parquet(file_path)
            dfs.append(df)
            logger.debug(f"Loaded {len(df)} rows from {file_path.name}")
        except Exception as e:
            logger.warning(f"Failed to load {file_path.name}: {e}")
            continue

    if not dfs:
        raise ValueError("No valid files could be loaded")

    # Concatenate all DataFrames
    combined_df = pd.concat(dfs, ignore_index=True)

    logger.info(f"Combined {len(combined_df)} total rows from {len(dfs)} files")

    return combined_df


def ensure_consistent_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure consistent schema across all loaded data.

    Args:
        df: Input DataFrame

    Returns:
        DataFrame with consistent schema
    """
    # Expected columns
    expected_columns = [
        "card_id",
        "card_number",
        "card_name",
        "set_id",
        "set_name",
        "date",
        "market_price",
        "category",
        "rarity",
        "tcgplayer_id",
        "source",
    ]

    # Check for missing columns
    missing_columns = set(expected_columns) - set(df.columns)
    if missing_columns:
        logger.warning(f"Missing columns: {missing_columns}. Adding with None values.")
        for col in missing_columns:
            df[col] = None

    # Select only expected columns (in order)
    df = df[expected_columns]

    # Cast date to datetime.date
    if "date" in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = df["date"].dt.date
        elif isinstance(df["date"].iloc[0] if len(df) > 0 else None, str):
            df["date"] = pd.to_datetime(df["date"]).dt.date

    # Ensure market_price is numeric
    df["market_price"] = pd.to_numeric(df["market_price"], errors="coerce")

    # Sort by (card_id, date)
    df = df.sort_values(["card_id", "date"]).reset_index(drop=True)

    logger.info(f"Schema standardized. Shape: {df.shape}")

    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build time-series features for each card.

    Features created:
    - lag_1: Price of previous day (if available)
    - rolling_mean_3: 3-day rolling mean
    - rolling_mean_5: 5-day rolling mean (if enough history)
    - price_return_1d: Daily return (price_t / price_{t-1} - 1)
    - fair_value_baseline: rolling_mean_3 if available, else market_price

    Args:
        df: DataFrame with columns: card_id, date, market_price

    Returns:
        DataFrame with additional feature columns
    """
    df = df.copy()

    # Group by card_id to compute features per card
    feature_dfs = []

    for card_id, card_df in df.groupby("card_id"):
        card_df = card_df.sort_values("date").reset_index(drop=True)

        # lag_1: price of previous day
        card_df["lag_1"] = card_df["market_price"].shift(1)

        # rolling_mean_3: 3-day rolling mean
        card_df["rolling_mean_3"] = (
            card_df["market_price"].rolling(window=3, min_periods=1).mean()
        )

        # rolling_mean_5: 5-day rolling mean (if enough history)
        card_df["rolling_mean_5"] = (
            card_df["market_price"].rolling(window=5, min_periods=1).mean()
        )

        # price_return_1d: (price_t / price_{t-1} - 1)
        card_df["price_return_1d"] = card_df["market_price"].pct_change()

        # fair_value_baseline: rolling_mean_3 if available, else market_price
        card_df["fair_value_baseline"] = card_df["rolling_mean_3"].fillna(
            card_df["market_price"]
        )

        feature_dfs.append(card_df)

    # Combine all cards
    result_df = pd.concat(feature_dfs, ignore_index=True)

    # Sort by (card_id, date) again
    result_df = result_df.sort_values(["card_id", "date"]).reset_index(drop=True)

    logger.info(f"Features built. Shape: {result_df.shape}")
    logger.debug(
        f"Feature columns: {[col for col in result_df.columns if col not in df.columns]}"
    )

    return result_df


def process_raw_data(
    output_dir: Optional[Path] = None,
    set_name: Optional[str] = None,
) -> Path:
    """
    Process all raw data files into a clean time-series table with features.

    Args:
        output_dir: Output directory for processed data. If None, uses data/processed.
        set_name: Name of the set. If None, loads from cards.yaml.

    Returns:
        Path to the saved processed file

    Raises:
        FileNotFoundError: If no raw files are found or cards.yaml doesn't exist
    """
    # Load settings
    settings = get_settings()

    # Set output directory
    if output_dir is None:
        output_dir = get_data_path("processed")

    # Load cards config to get set name
    if set_name is None:
        cards_config = load_cards_config()
        set_name = cards_config["set"]["name"]

    logger.info(f"Processing raw data for set: {set_name}")

    # Load raw files
    raw_dir = get_data_path("raw")
    df = load_raw_files(raw_dir, set_name)

    # Ensure consistent schema
    df = ensure_consistent_schema(df)

    # Build features
    df = build_features(df)

    # Save to processed directory
    safe_set_name = set_name.lower().replace(" ", "_").replace(":", "").replace("-", "_")
    safe_set_name = "".join(c for c in safe_set_name if c.isalnum() or c == "_")

    output_file = output_dir / f"{safe_set_name}.parquet"
    df.to_parquet(output_file, index=False, engine="pyarrow")

    logger.info(f"Processed data saved to: {output_file}")
    logger.info(f"Total rows: {len(df)}")
    logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
    logger.info(f"Unique cards: {df['card_id'].nunique()}")

    return output_file


def main():
    """Main entry point for feature engineering."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        logger.info("Starting feature engineering")
        output_file = process_raw_data()
        logger.info(f"Feature engineering complete! Data saved to: {output_file}")
        return 0
    except Exception as e:
        logger.error(f"Feature engineering failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())

