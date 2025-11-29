#!/bin/bash
# Run baseline model training with clean MLflow startup
#
# This script ensures a fresh MLflow server start before running training.
# Useful for troubleshooting or ensuring a clean state.
#
# Usage:
#   ./scripts/train_baseline_docker_clean.sh

set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

echo "Stopping existing MLflow service..."
docker-compose down mlflow

echo "Starting fresh MLflow service..."
docker-compose up -d mlflow

echo "Waiting for MLflow to be ready..."
sleep 5

echo "Building training image..."
docker-compose build training

echo "Running baseline model training..."
docker-compose run --rm training python -m pokewatch.models.train_baseline "$@"

echo ""
echo "Training complete!"
echo "View results at: http://127.0.0.1:5001"
