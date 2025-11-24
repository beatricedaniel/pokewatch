#!/bin/bash
# Script to run unit tests for PokemonPriceTrackerClient

echo "Installing dependencies..."
python -m uv pip install -e .

echo ""
echo "Running unit tests for price_tracker_client..."
python -m pytest tests/unit/test_price_tracker_client.py -v

echo ""
echo "Running tests with coverage..."
python -m pytest tests/unit/test_price_tracker_client.py --tb=short -v
