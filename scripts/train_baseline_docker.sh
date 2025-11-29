#!/bin/bash
# Run baseline model training in Docker container
#
# This script runs the baseline model training inside a Docker container
# that connects to the MLflow tracking server for experiment tracking.
#
# Usage:
#   ./scripts/train_baseline_docker.sh
#   ./scripts/train_baseline_docker.sh --data_path data/processed/custom_data.parquet
#   ./scripts/train_baseline_docker.sh --experiment_name my_experiment --run_name my_run

set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Check if MLflow service is running
echo "Checking MLflow service status..."
if ! docker ps | grep -q pokewatch-mlflow; then
    echo "MLflow service is not running. Starting it now..."
    docker-compose up -d mlflow
    echo "Waiting for MLflow to be ready..."
    sleep 5
fi

# Build training image if it doesn't exist
echo "Checking training image..."
if ! docker images | grep -q pokewatch-training; then
    echo "Building training image..."
    docker-compose build training
fi

# Run training
echo "Running baseline model training in Docker..."
docker-compose run --rm training python -m pokewatch.models.train_baseline "$@"

echo ""
echo "Training complete!"
echo "View results at: http://127.0.0.1:5001"
