#!/usr/bin/env python3
"""
Utility script to update cards.yaml with the current top 10 most expensive cards.

This script:
1. Fetches all cards from the configured set
2. Sorts by current market price (descending)
3. Updates cards.yaml with the top 10 most expensive cards
4. Includes unique identifiers (tcgplayer_id, card_id) to handle variants

Usage:
    python scripts/update_top_cards.py
"""

import logging
import sys
from pathlib import Path

import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pokewatch.config import get_settings
from pokewatch.data import PokemonPriceTrackerClient
from pokewatch.data.collectors.daily_price_collector import load_cards_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_top_expensive_cards(set_id: str, language: str, top_n: int = 10):
    """
    Fetch and return the top N most expensive cards from a set.

    Args:
        set_id: Set ID from the API
        language: Card language
        top_n: Number of top cards to return

    Returns:
        List of card dictionaries sorted by price (descending)
    """
    settings = get_settings()
    client = PokemonPriceTrackerClient(
        api_key=settings.pokemon_price_api_key,
        base_url=settings.api.base_url,
        timeout=settings.api.timeout_seconds,
        default_language=language,
    )

    try:
        # Fetch all cards without history to get current prices
        logger.info(f"Fetching cards from set {set_id}")
        response = client.get_cards_in_set(
            set_id_or_code=set_id,
            language=language,
            include_history=False,
            days=0,
            fetch_all_in_set=True,
            limit=1000,
        )
    finally:
        client.close()

    cards = response.get("data", [])
    logger.info(f"Fetched {len(cards)} cards from API")

    # Extract cards with prices
    cards_with_prices = []
    for card in cards:
        prices = card.get("prices", {})
        market_price = prices.get("market")

        if market_price is not None:
            try:
                price = float(market_price)
                cards_with_prices.append({
                    "id": card.get("id"),
                    "tcgPlayerId": card.get("tcgPlayerId"),
                    "name": card.get("name"),
                    "cardNumber": card.get("cardNumber"),
                    "rarity": card.get("rarity"),
                    "price": price,
                })
            except (ValueError, TypeError):
                pass

    # Sort by price descending
    cards_with_prices.sort(key=lambda x: x["price"], reverse=True)

    logger.info(f"Found {len(cards_with_prices)} cards with prices")
    return cards_with_prices[:top_n]


def generate_card_config(card: dict, index: int) -> dict:
    """
    Generate YAML configuration for a single card.

    Args:
        card: Card data from API
        index: Position in the top list (1-based)

    Returns:
        Dictionary with card configuration
    """
    # Determine category (top 5 = grail, rest = chase)
    category = "grail" if index <= 5 else "chase"
    priority = 3 if index <= 5 else 2

    # Generate tags based on card characteristics
    tags = []
    name_lower = card["name"].lower()

    if "ex" in name_lower:
        tags.append("ex")
    if "master ball" in name_lower:
        tags.append("master-ball")
    if "poke ball" in name_lower:
        tags.append("poke-ball")

    if card["rarity"]:
        tags.append(card["rarity"].lower().replace(" ", "-"))

    # Determine type tags (simplified)
    if "charizard" in name_lower:
        tags.append("fire")
    if "blastoise" in name_lower or "water" in name_lower:
        tags.append("water")
    if "venusaur" in name_lower or "grass" in name_lower:
        tags.append("grass")
    if "mew" in name_lower or "mewtwo" in name_lower:
        tags.append("psychic")
        tags.append("legendary")
    if "zapdos" in name_lower:
        tags.append("electric")
        tags.append("legendary")
    if "dragonite" in name_lower:
        tags.append("dragon")
    if "alakazam" in name_lower:
        tags.append("psychic")

    # Create internal_id from card name
    internal_id = (
        card["name"]
        .lower()
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("-", "_")
        .replace("/", "_")
    )
    internal_id = "".join(c for c in internal_id if c.isalnum() or c == "_")

    return {
        "internal_id": internal_id,
        "name": card["name"],
        "card_number": card["cardNumber"],
        "tcgplayer_id": str(card["tcgPlayerId"]),  # Unique identifier for variants
        "card_id": card["id"],  # API internal ID as backup
        "category": category,
        "tags": sorted(list(set(tags))),  # Remove duplicates and sort
        "monitoring": {
            "active": True,
            "priority": priority,
        },
    }


def update_cards_yaml(config_path: Path | None = None):
    """
    Update cards.yaml with the current top 10 most expensive cards.

    Args:
        config_path: Path to cards.yaml. If None, uses default location.
    """
    # Load existing config to get set info
    cards_config = load_cards_config(config_path)
    set_id = cards_config["set"]["id"]
    set_name = cards_config["set"]["name"]
    set_language = cards_config["set"]["language"]

    logger.info(f"Updating cards.yaml for set: {set_name} (ID: {set_id})")

    # Get top 10 most expensive cards
    top_cards = get_top_expensive_cards(set_id, set_language, top_n=10)

    if not top_cards:
        logger.error("No cards with prices found!")
        return

    # Generate YAML structure
    yaml_cards = []
    for i, card in enumerate(top_cards, 1):
        card_config = generate_card_config(card, i)
        yaml_cards.append(card_config)
        logger.info(
            f"{i}. {card['name']} - ${card['price']:.2f} "
            f"(TCGPlayer ID: {card_config['tcgplayer_id']})"
        )

    # Create full YAML structure
    yaml_data = {
        "set": {
            "id": set_id,
            "name": set_name,
            "language": set_language,
        },
        "cards": yaml_cards,
    }

    # Write to file
    if config_path is None:
        settings = get_settings()
        config_path = settings.config_dir / "cards.yaml"

    with open(config_path, "w") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    logger.info(f"\n✓ Updated {config_path} with {len(yaml_cards)} cards")


def main():
    """Main entry point."""
    try:
        update_cards_yaml()
        return 0
    except Exception as e:
        logger.error(f"Failed to update cards.yaml: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())

