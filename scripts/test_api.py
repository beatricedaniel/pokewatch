#!/usr/bin/env python3
"""
Example script to test the PokeWatch API endpoints.

This script demonstrates how to call the different API endpoints.
"""

import json
from datetime import date

import requests

# API base URL (adjust if running on different host/port)
BASE_URL = "http://localhost:8000"


def test_health():
    """Test the /health endpoint."""
    print("\n" + "=" * 60)
    print("Testing /health endpoint")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_list_cards():
    """Test the /cards endpoint to list all available cards."""
    print("\n" + "=" * 60)
    print("Testing /cards endpoint")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/cards")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Total cards: {data['count']}")
    print(f"\nAvailable card IDs:")
    for i, card_id in enumerate(data["cards"], 1):
        print(f"  {i}. {card_id}")


def test_fair_price(card_id: str, date_str: str | None = None):
    """Test the /fair_price endpoint."""
    print("\n" + "=" * 60)
    print(f"Testing /fair_price endpoint for card: {card_id}")
    if date_str:
        print(f"Date: {date_str}")
    else:
        print("Date: None (using latest available date)")
    print("=" * 60)

    payload = {"card_id": card_id}
    if date_str:
        payload["date"] = date_str

    response = requests.post(f"{BASE_URL}/fair_price", json=payload)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nResponse:")
        print(f"  Card ID: {data['card_id']}")
        print(f"  Date: {data['date']}")
        print(f"  Market Price: ${data['market_price']:.2f}")
        print(f"  Fair Price: ${data['fair_price']:.2f}")
        print(f"  Deviation: {data['deviation_pct']*100:.2f}%")
        print(f"  Signal: {data['signal']}")
    else:
        print(f"Error: {response.json()}")


def main():
    """Run all API tests."""
    print("PokeWatch API Test Script")
    print("=" * 60)
    print(f"API Base URL: {BASE_URL}")
    print("\nMake sure the API server is running:")
    print("  uv run uvicorn pokewatch.api.main:app --reload")

    # Test health endpoint
    try:
        test_health()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server.")
        print("   Please start the server first:")
        print("   uv run uvicorn pokewatch.api.main:app --reload")
        return

    # Test list cards endpoint
    test_list_cards()

    # Get a card ID to test with
    response = requests.get(f"{BASE_URL}/cards")
    if response.status_code == 200:
        cards = response.json()["cards"]
        if cards:
            # Test fair_price with latest date
            test_fair_price(cards[0])

            # Test fair_price with specific date (if available)
            # Try a date from a few days ago
            test_date = date.today().isoformat()
            test_fair_price(cards[0], test_date)

            # Test with unknown card
            print("\n" + "=" * 60)
            print("Testing /fair_price with unknown card_id")
            print("=" * 60)
            test_fair_price("unknown_card_12345")
        else:
            print("\n⚠️  No cards available in the model.")


if __name__ == "__main__":
    main()

