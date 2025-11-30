#!/bin/bash
# Build BentoML service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "========================================="
echo "Building BentoML Service"
echo "========================================="

# Ensure latest data is available
echo "Checking data availability..."
if [ ! -f "data/processed/sv2a_pokemon_card_151.parquet" ]; then
    echo "ERROR: Processed data not found!"
    echo "Run 'make preprocess' first."
    exit 1
fi

# Check if models exist
if [ ! -d "models/baseline" ]; then
    echo "WARNING: models/baseline/ not found, creating..."
    mkdir -p models/baseline
fi

# Build Bento
echo ""
echo "Building Bento..."
uv run bentoml build

# List Bentos
echo ""
echo "✓ Bento build complete!"
echo ""
echo "Built Bentos:"
uv run bentoml list | head -10

echo ""
echo "To serve locally:"
echo "  uv run bentoml serve pokewatch_service:latest"
echo ""
echo "To containerize:"
echo "  uv run bentoml containerize pokewatch_service:latest"
