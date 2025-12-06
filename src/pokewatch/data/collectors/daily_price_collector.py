"""
Daily price collector for Pok�mon cards.

Fetches price data from Pok�mon Price Tracker API for cards specified in cards.yaml
and saves raw data to Parquet files.

Usage:
    # Basic usage (today's date)
    python -m pokewatch.data.collectors.daily_price_collector

    # With custom date for filename
    python -m pokewatch.data.collectors.daily_price_collector --date 2025-11-23

    # Fetch more history
    python -m pokewatch.data.collectors.daily_price_collector --days 14

    # See all options
    python -m pokewatch.data.collectors.daily_price_collector --help
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
import pandas as pd

from pokewatch.config import get_settings, get_data_path
from pokewatch.data import PokemonPriceTrackerClient


logger = logging.getLogger(__name__)


def load_cards_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load cards configuration from cards.yaml.

    Args:
        config_path: Path to cards.yaml. If None, uses default location.

    Returns:
        Dictionary with set info and cards list.

    Raises:
        FileNotFoundError: If cards.yaml doesn't exist.
    """
    if config_path is None:
        settings = get_settings()
        config_path = settings.config_dir / "cards.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Cards configuration not found: {config_path}\n"
            f"Please ensure config/cards.yaml exists."
        )

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def extract_price_history(card_data: dict) -> list[dict]:
    """
    Extract price history from a card's API response.

    Args:
        card_data: Card data from API containing priceHistory.

    Returns:
        List of dictionaries with date and price information.

    Example:
        >>> card = {"priceHistory": {"2024-01-01": 100.0, "2024-01-02": 105.0}}
        >>> extract_price_history(card)
        [
            {"date": "2024-01-01", "market_price": 100.0},
            {"date": "2024-01-02", "market_price": 105.0}
        ]
    """
    price_history = []

    if "priceHistory" in card_data and card_data["priceHistory"]:
        for date_str, price in card_data["priceHistory"].items():
            price_history.append(
                {
                    "date": date_str,
                    "market_price": float(price) if price is not None else None,
                }
            )

    return price_history


def process_card_data(
    api_card: dict,
    internal_id: str,
    card_number: str,
    set_id: str,
    category: str,
) -> list[dict]:
    """
    Process a single card's API data into rows for DataFrame.

    Args:
        api_card: Card data from API
        internal_id: Internal card ID from cards.yaml
        card_number: Card number (e.g., "201/165")
        set_id: Set ID
        category: Card category (grail, chase, meta, personal)

    Returns:
        List of row dictionaries (one per date in price history).
    """
    rows = []

    # Extract current price
    current_price = None
    if "prices" in api_card and api_card["prices"]:
        # Try to get market price from prices object
        prices = api_card["prices"]
        if isinstance(prices, dict):
            current_price = prices.get("market") or prices.get("mid")

    # Extract price history
    price_history = extract_price_history(api_card)

    # If no price history, create a single row with current data
    if not price_history:
        rows.append(
            {
                "card_id": internal_id,
                "card_number": card_number,
                "card_name": api_card.get("name", "Unknown"),
                "set_id": set_id,
                "set_name": (
                    api_card.get("set", {}).get("name")
                    if isinstance(api_card.get("set"), dict)
                    else None
                ),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "market_price": current_price,
                "category": category,
                "rarity": api_card.get("rarity"),
                "tcgplayer_id": api_card.get("tcgPlayerId"),
                "source": "pokemonpricetracker",
            }
        )
    else:
        # Create a row for each date in price history
        for price_entry in price_history:
            rows.append(
                {
                    "card_id": internal_id,
                    "card_number": card_number,
                    "card_name": api_card.get("name", "Unknown"),
                    "set_id": set_id,
                    "set_name": (
                        api_card.get("set", {}).get("name")
                        if isinstance(api_card.get("set"), dict)
                        else None
                    ),
                    "date": price_entry["date"],
                    "market_price": price_entry["market_price"],
                    "category": category,
                    "rarity": api_card.get("rarity"),
                    "tcgplayer_id": api_card.get("tcgPlayerId"),
                    "source": "pokemonpricetracker",
                }
            )

    return rows


def collect_daily_prices(
    output_dir: Path | None = None,
    days_history: int = 7,
    save_format: str = "parquet",
    output_date: str | None = None,
) -> Path:
    """
    Collect daily prices for cards specified in cards.yaml.

    This function:
    1. Loads cards configuration from cards.yaml
    2. Fetches all cards from the specified set with price history
    3. Filters to only the cards we're tracking
    4. Processes and saves data to Parquet file

    Args:
        output_dir: Output directory for raw data. If None, uses data/raw.
        days_history: Number of days of price history to fetch (default: 7).
        save_format: Output format, "parquet" or "csv" (default: "parquet").
        output_date: Date string for filename (YYYY-MM-DD). If None, uses today.

    Returns:
        Path to the saved data file.

    Raises:
        FileNotFoundError: If cards.yaml doesn't exist.
        PokemonPriceTrackerError: If API request fails.
    """
    # Load settings
    settings = get_settings()

    # Set output directory
    if output_dir is None:
        output_dir = get_data_path("raw")

    # Load cards configuration
    logger.info("Loading cards configuration from cards.yaml")
    cards_config = load_cards_config()

    set_id = cards_config["set"]["id"]
    set_name = cards_config["set"]["name"]
    set_language = cards_config["set"]["language"]

    logger.info(f"Set: {set_name} (ID: {set_id}, Language: {set_language})")

    # Build mapping of unique identifiers -> card config
    # Priority: tcgplayer_id > card_id > card_number (only if no tcgplayer_id)
    tracked_cards_by_tcgplayer = {}
    tracked_cards_by_card_id = {}
    tracked_cards_by_number = {}  # Only used if tcgplayer_id is not available

    for card in cards_config["cards"]:
        if card.get("monitoring", {}).get("active", True):
            # Primary: match by tcgplayer_id (most reliable for variants)
            if "tcgplayer_id" in card:
                tracked_cards_by_tcgplayer[str(card["tcgplayer_id"])] = card
            # Secondary: match by card_id (API internal ID)
            if "card_id" in card:
                tracked_cards_by_card_id[card["card_id"]] = card
            # Fallback: match by card_number (ONLY if no tcgplayer_id - for backward compatibility)
            if "tcgplayer_id" not in card:
                tracked_cards_by_number[card["card_number"]] = card

    # Count unique cards being tracked (using internal_id as unique identifier)
    unique_tracked = set()
    for card in cards_config["cards"]:
        if card.get("monitoring", {}).get("active", True):
            unique_tracked.add(card.get("internal_id", card.get("card_number", "")))

    logger.info(f"Tracking {len(unique_tracked)} cards")

    # Create API client
    client = PokemonPriceTrackerClient(
        api_key=settings.pokemon_price_api_key,
        base_url=settings.api.base_url,
        timeout=settings.api.timeout_seconds,
        default_language=set_language,
    )

    # Fetch only the specific cards we're tracking (more efficient than fetching all cards)
    logger.info(f"Fetching {len(unique_tracked)} tracked cards with {days_history} days of history")
    all_rows = []
    matched_cards = 0
    failed_cards = []

    try:
        for card_config in cards_config["cards"]:
            if not card_config.get("monitoring", {}).get("active", True):
                continue

            try:
                # Try to fetch by tcgplayer_id first (most efficient)
                if "tcgplayer_id" in card_config:
                    tcgplayer_id = int(card_config["tcgplayer_id"])
                    logger.debug(
                        f"Fetching card by tcgplayer_id: {tcgplayer_id} ({card_config['name']})"
                    )
                    response = client.get_single_card_with_history(
                        tcgplayer_id=tcgplayer_id,
                        language=set_language,
                        days=days_history,
                    )
                    # Single card response: data is a dict, not a list
                    api_card = response.get("data")

                # Fallback: fetch by card_id if available
                elif "card_id" in card_config:
                    logger.debug(
                        f"Fetching card by card_id: {card_config['card_id']} ({card_config['name']})"
                    )
                    # Note: API might not support direct card_id lookup, so we'll need to use card_number + set
                    response = client.get_single_card_with_history(
                        card_number=card_config["card_number"],
                        set_id_or_code=set_id,
                        language=set_language,
                        days=days_history,
                    )
                    api_card = response.get("data")

                # Last resort: fetch by card_number + set
                else:
                    logger.debug(
                        f"Fetching card by card_number: {card_config['card_number']} ({card_config['name']})"
                    )
                    response = client.get_single_card_with_history(
                        card_number=card_config["card_number"],
                        set_id_or_code=set_id,
                        language=set_language,
                        days=days_history,
                    )
                    api_card = response.get("data")

                if not api_card:
                    logger.warning(f"No data returned for card: {card_config['name']}")
                    failed_cards.append(card_config["name"])
                    continue

                matched_cards += 1
                api_card_number = api_card.get("cardNumber") or api_card.get(
                    "number", card_config.get("card_number", "")
                )

                logger.debug(
                    f"Processing card: {card_config['name']} "
                    f"({api_card_number}) - {card_config['category']}"
                )

                # Process card data
                rows = process_card_data(
                    api_card=api_card,
                    internal_id=card_config["internal_id"],
                    card_number=api_card_number,
                    set_id=set_id,
                    category=card_config["category"],
                )

                all_rows.extend(rows)

            except Exception as e:
                logger.warning(f"Failed to fetch card {card_config['name']}: {e}")
                failed_cards.append(card_config["name"])
                continue

    finally:
        client.close()

    if failed_cards:
        logger.warning(f"Failed to fetch {len(failed_cards)} cards: {', '.join(failed_cards)}")

    logger.info(f"Matched {matched_cards}/{len(unique_tracked)} tracked cards")
    logger.info(f"Generated {len(all_rows)} total price records")

    # Create DataFrame
    df = pd.DataFrame(all_rows)

    # Convert date column to datetime
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        # Sort by card_id and date
        df = df.sort_values(["card_id", "date"])

    # Save to file with set name in filename
    # Use provided date or default to today
    file_date = output_date if output_date else datetime.now().strftime("%Y-%m-%d")

    # Create a safe filename from set name (remove special chars, replace spaces with underscores)
    safe_set_name = set_name.lower().replace(" ", "_").replace(":", "").replace("-", "_")
    safe_set_name = "".join(c for c in safe_set_name if c.isalnum() or c == "_")

    if save_format == "parquet":
        output_file = output_dir / f"{safe_set_name}_prices_{file_date}.parquet"
        df.to_parquet(output_file, index=False, engine="pyarrow")
    elif save_format == "csv":
        output_file = output_dir / f"{safe_set_name}_prices_{file_date}.csv"
        df.to_csv(output_file, index=False)
    else:
        raise ValueError(f"Unsupported save format: {save_format}")

    logger.info(f"Saved {len(df)} rows to {output_file}")

    # Print summary
    if not df.empty:
        logger.info("\nSummary:")
        logger.info(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        logger.info(f"  Unique cards: {df['card_id'].nunique()}")
        logger.info(f"  Total records: {len(df)}")
        logger.info("\nPrice statistics:")
        logger.info(f"  Min: ${df['market_price'].min():.2f}")
        logger.info(f"  Max: ${df['market_price'].max():.2f}")
        logger.info(f"  Mean: ${df['market_price'].mean():.2f}")

    return output_file


def main():
    """Main entry point for daily price collector with CLI arguments."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Collect daily Pokémon card prices from the API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect prices with today's date
  python -m pokewatch.data.collectors.daily_price_collector

  # Collect prices with custom date for filename
  python -m pokewatch.data.collectors.daily_price_collector --date 2025-11-23

  # Collect 14 days of history
  python -m pokewatch.data.collectors.daily_price_collector --days 14

  # Save as CSV instead of Parquet
  python -m pokewatch.data.collectors.daily_price_collector --format csv
        """,
    )

    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date for output filename (YYYY-MM-DD). Default: today's date. "
        "Note: This only affects the filename, not the data fetched from API.",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days of price history to fetch (default: 7)",
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["parquet", "csv"],
        default="parquet",
        help="Output file format (default: parquet)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for raw data (default: data/raw)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )

    args = parser.parse_args()

    # Validate date format if provided
    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            parser.error(f"Invalid date format: {args.date}. Expected YYYY-MM-DD")

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        logger.info("Starting daily price collection")
        if args.date:
            logger.info(f"Using custom date for filename: {args.date}")

        output_dir = Path(args.output_dir) if args.output_dir else None

        output_file = collect_daily_prices(
            output_dir=output_dir,
            days_history=args.days,
            save_format=args.format,
            output_date=args.date,
        )

        logger.info(f"Collection complete! Data saved to: {output_file}")
        return 0
    except Exception as e:
        logger.error(f"Collection failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
