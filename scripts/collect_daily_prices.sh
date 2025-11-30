#!/bin/bash
# Collect daily Pokemon card prices using the collector microservice
#
# This script runs the data collection pipeline in a Docker container
# and updates the DVC-tracked raw data.
#
# Usage:
#   ./scripts/collect_daily_prices.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "========================================="
echo "PokeWatch - Daily Price Collection"
echo "========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and configure your API key."
    exit 1
fi

# Build collector image if not exists
echo "Building collector image..."
docker-compose build collector

# Run collector
echo ""
echo "Running data collection..."
docker-compose run --rm collector

# Check if data was collected
if [ -d "data/raw" ] && [ "$(ls -A data/raw)" ]; then
    echo ""
    echo "✓ Data collection completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Update DVC: dvc add data/raw"
    echo "  2. Commit: git commit data/raw.dvc -m 'Update raw data'"
    echo "  3. Push to DagsHub: dvc push"
    echo ""
else
    echo ""
    echo "WARNING: No data found in data/raw/"
    echo "Check logs for errors."
    exit 1
fi
