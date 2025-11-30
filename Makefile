# ========================================
# PokeWatch MLOps Makefile
# ========================================
# Standardized commands for data collection, training, and deployment
#
# Usage:
#   make help          - Show this help message
#   make collect       - Collect latest card prices
#   make preprocess    - Run feature engineering
#   make train         - Train baseline model
#   make pipeline      - Run full DVC pipeline (collect → preprocess → train)
#   make api           - Start API server
#   make test          - Run all tests
#   make clean         - Clean temporary files

.PHONY: help collect preprocess train pipeline api test clean setup docker-build docker-clean dvc-status dvc-push

# Default target
.DEFAULT_GOAL := help

# ========================================
# HELP
# ========================================

help:  ## Show this help message
	@echo "PokeWatch MLOps Commands"
	@echo "========================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make collect        # Collect latest prices"
	@echo "  make pipeline       # Run full ML pipeline"
	@echo "  make train          # Train model with DagsHub MLflow"

# ========================================
# DATA COLLECTION
# ========================================

collect:  ## Collect latest card prices (Docker microservice)
	@echo "Running data collection microservice..."
	docker-compose run --rm collector
	@echo "✓ Data collection complete!"
	@echo "  Data saved to: data/raw/"
	@echo "  Next: make preprocess or make pipeline"

# ========================================
# PREPROCESSING
# ========================================

preprocess:  ## Run feature engineering
	@echo "Running feature engineering..."
	python -m pokewatch.data.preprocessing.make_features
	@echo "✓ Feature engineering complete!"
	@echo "  Features saved to: data/processed/"
	@echo "  Next: make train"

# ========================================
# TRAINING
# ========================================

train:  ## Train baseline model with DagsHub MLflow tracking
	@echo "Training baseline model (Docker container)..."
	@echo "MLflow tracking: https://dagshub.com/beatricedaniel/pokewatch/experiments"
	docker-compose run --rm training python -m pokewatch.models.train_baseline
	@echo "✓ Training complete!"
	@echo "  View experiments: https://dagshub.com/beatricedaniel/pokewatch/experiments"
	@echo "  Model saved to: models/baseline/"

# ========================================
# DVC PIPELINE
# ========================================

pipeline:  ## Run full DVC pipeline (collect → preprocess → train)
	@echo "Running full DVC pipeline..."
	dvc repro
	@echo "✓ Pipeline complete!"
	@echo "  Run 'make dvc-push' to upload data/models to DagsHub"

dvc-status:  ## Check DVC status (data/model changes)
	@echo "DVC Status:"
	@echo "==========="
	dvc status

dvc-push:  ## Push data and models to DagsHub DVC remote
	@echo "Pushing data and models to DagsHub..."
	dvc push
	@echo "✓ Data pushed to DagsHub!"
	@echo "  View data: https://dagshub.com/beatricedaniel/pokewatch/data"

dvc-pull:  ## Pull data and models from DagsHub DVC remote
	@echo "Pulling data and models from DagsHub..."
	dvc pull
	@echo "✓ Data pulled from DagsHub!"

# ========================================
# API & SERVICES
# ========================================

api:  ## Start API server (Docker)
	@echo "Starting API server..."
	docker-compose up api

api-dev:  ## Start API server in development mode (with reload)
	@echo "Starting API server in development mode..."
	uvicorn src.pokewatch.api.main:app --reload --host 0.0.0.0 --port 8000

# ========================================
# TESTING
# ========================================

test:  ## Run all tests (unit + integration)
	@echo "Running tests..."
	python -m pytest tests/ -v

test-unit:  ## Run unit tests only
	@echo "Running unit tests..."
	python -m pytest tests/unit/ -v

test-integration:  ## Run integration tests only
	@echo "Running integration tests..."
	python -m pytest tests/integration/ -v

test-docker:  ## Run tests in Docker
	@echo "Running tests in Docker..."
	docker-compose --profile test run --rm tests

# ========================================
# DOCKER MANAGEMENT
# ========================================

docker-build:  ## Build all Docker images
	@echo "Building Docker images..."
	docker-compose build api collector training

docker-clean:  ## Remove all Docker containers and images
	@echo "Cleaning Docker containers and images..."
	docker-compose down --volumes --remove-orphans
	docker-compose rm -f
	@echo "✓ Docker cleaned!"

# ========================================
# SETUP & INITIALIZATION
# ========================================

setup:  ## Initial project setup (venv, install deps, DVC init)
	@echo "Setting up PokeWatch development environment..."
	@if [ ! -d .venv ]; then \
		echo "Creating virtual environment..."; \
		python -m uv venv; \
	fi
	@echo "Installing dependencies..."
	@. .venv/bin/activate && python -m uv pip install -e .
	@echo "Checking DVC remote..."
	@if ! dvc remote list | grep -q dagshub; then \
		echo "Configuring DVC remote..."; \
		dvc remote add -d dagshub https://dagshub.com/beatricedaniel/pokewatch.dvc; \
	fi
	@echo "✓ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and add your API keys"
	@echo "  2. Run 'make collect' to fetch data"
	@echo "  3. Run 'make pipeline' to train model"

# ========================================
# CLEANING
# ========================================

clean:  ## Clean temporary files and caches
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .mypy_cache 2>/dev/null || true
	rm -rf mlruns_artifacts/* 2>/dev/null || true
	@echo "✓ Cleaned!"

clean-data:  ## Clean all data (WARNING: destructive!)
	@echo "WARNING: This will delete all data in data/raw, data/processed, data/interim"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	rm -rf data/raw/* data/processed/* data/interim/*
	@echo "✓ Data cleaned!"

# ========================================
# MONITORING & LOGS
# ========================================

logs-api:  ## Show API server logs
	docker-compose logs -f api

logs-collector:  ## Show collector logs
	docker-compose logs -f collector

logs-training:  ## Show training logs
	docker-compose logs -f training

# ========================================
# MLFLOW (LOCAL - OPTIONAL)
# ========================================

mlflow-local:  ## Start local MLflow server (for development only)
	@echo "Starting local MLflow stack (MinIO + MLflow)..."
	@echo "Note: Production uses DagsHub MLflow"
	docker-compose --profile mlflow up

mlflow-local-stop:  ## Stop local MLflow server
	docker-compose --profile mlflow down

# ========================================
# BENTOML SERVING (PHASE 3)
# ========================================

bento-build:  ## Build BentoML service
	@echo "Building BentoML service..."
	./scripts/build_bento.sh

bento-serve:  ## Serve BentoML locally with hot-reload
	@echo "Starting BentoML service..."
	@echo "Access at: http://localhost:3000"
	uv run bentoml serve pokewatch.serving.service:PokeWatchService --reload

bento-containerize:  ## Build BentoML Docker image
	@echo "Containerizing BentoML service..."
	uv run bentoml containerize pokewatch_service:latest -t pokewatch-bento:latest

bento-api:  ## Start BentoML API in Docker
	@echo "Starting BentoML API (port 3000)..."
	docker-compose up bento-api

# ========================================
# ML PIPELINE (PHASE 3)
# ========================================

pipeline-run:  ## Run complete ML pipeline (collect → preprocess → train → deploy)
	@echo "Running ML pipeline..."
	PYTHONPATH=. python pipelines/ml_pipeline.py

pipeline-simple:  ## Run pipeline using existing make commands
	@echo "Running simple pipeline..."
	make collect && make preprocess && make train && make bento-build
