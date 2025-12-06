"""Quick test script for PokemonPriceTrackerClient."""

import sys
sys.path.insert(0, 'src')

from pokewatch.config import get_settings
from pokewatch.data import PokemonPriceTrackerClient

def main():
    # Load settings
    settings = get_settings()

    # Create client
    client = PokemonPriceTrackerClient(
        api_key=settings.pokemon_price_api_key,
        base_url=settings.api.base_url,
        timeout=settings.api.timeout_seconds,
        default_language=settings.api.language,
    )

    print("✓ Client initialized successfully")
    print(f"  Base URL: {client.base_url}")
    print(f"  Default language: {client.default_language}")

    # Test 1: Get sets (using language from config)
    print(f"\n--- Test 1: Get sets (language: {settings.api.language}) ---")
    try:
        sets_response = client.get_sets(language=settings.api.language, limit=5)
        print(f"✓ Found {len(sets_response.get('sets', []))} sets")
        if sets_response.get('sets'):
            first_set = sets_response['sets'][0]
            print(f"  Example: {first_set.get('name', 'N/A')} (ID: {first_set.get('_id', 'N/A')})")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test 2: Get cards from the set defined in cards.yaml
    print("\n--- Test 2: Get cards from set defined in cards.yaml ---")
    from pokewatch.data.collectors.daily_price_collector import load_cards_config
    cards_config = load_cards_config()
    set_id = cards_config["set"]["id"]
    set_name = cards_config["set"]["name"]
    set_language = cards_config["set"]["language"]
    print(f"  Set: {set_name} (ID: {set_id}, Language: {set_language})")
    try:
        cards_response = client.get_cards_in_set(
            set_id,
            language=set_language,
            include_history=True,
            days=7,
            limit=5
        )
        # API returns data in "data" key, not "cards"
        cards = cards_response.get("data", [])
        print(f"✓ Found {len(cards)} cards")
        if cards:
            first_card = cards[0]
            print(f"  Example: {first_card.get('name', 'N/A')} ({first_card.get('cardNumber', 'N/A')})")
            if 'priceHistory' in first_card:
                print(f"  Price history entries: {len(first_card['priceHistory'])}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Close client
    client.close()
    print("\n✓ Client closed successfully")

if __name__ == "__main__":
    main()
