# Phase 3 - Week 1: Orchestration & BentoML Migration

**Duration:** Week 1 (5-7 days)
**Prerequisites:** Phase 2 Step 3 complete (DagsHub MLflow, DVC, Docker microservices, Makefile)

---

## Overview

Week 1 focuses on two major transitions:
1. **Migrate from FastAPI to BentoML** for production-grade model serving
2. **Implement orchestration** with ZenML (recommended) or Airflow for automated ML pipeline

These changes build directly on the existing Docker microservices architecture and DagsHub integration.

---

## Current State (End of Phase 2)

✅ **What We Have:**
- FastAPI application serving predictions ([src/pokewatch/api/main.py](src/pokewatch/api/main.py))
- Baseline model ([src/pokewatch/models/baseline.py](src/pokewatch/models/baseline.py))
- Docker microservices: collector, training, API
- DVC pipeline in [dvc.yaml](dvc.yaml): collect → preprocess → train
- DagsHub MLflow tracking
- Makefile commands: `make collect`, `make train`, `make pipeline`

❌ **What We Need:**
- BentoML service replacing FastAPI
- Automated orchestration (manual `make` commands → automated scheduled pipeline)
- Model versioning with BentoML + DVC integration
- Production-ready serving with batching, caching, monitoring

---

## Week 1 Goals

By end of Week 1, we should have:
- [ ] **BentoML service** replacing FastAPI with same API contract
- [ ] **ZenML pipeline** automating data collection → training → deployment
- [ ] **Model registry** integration with DagsHub MLflow
- [ ] **Automated deployment** from pipeline to BentoML service
- [ ] **Testing** proving the new stack works end-to-end

---

## Step-by-Step Plan

### **Day 1: Setup & Planning (3-4 hours)**

#### Task 1.1: Install Dependencies
```bash
cd pokewatch

# Install BentoML
python -m uv pip install bentoml

# Install ZenML (or Airflow)
python -m uv pip install "zenml[server]"

# Update pyproject.toml
# Add to dependencies:
# - bentoml>=1.2.0
# - zenml[server]>=0.55.0
```

#### Task 1.2: Initialize ZenML
```bash
# Initialize ZenML repository
zenml init

# Start ZenML dashboard (optional but helpful)
zenml up

# Configure DagsHub integration
zenml integration install mlflow s3 -y

# Set up stack with DagsHub
zenml experiment-tracker register dagshub_tracker --flavor=mlflow \
  --tracking_uri="https://dagshub.com/beatricedaniel/pokewatch.mlflow" \
  --tracking_username="beatricedaniel" \
  --tracking_password="${DAGSHUB_TOKEN}"

# Register stack
zenml stack register dagshub_stack \
  -o default \
  -a default \
  -e dagshub_tracker

zenml stack set dagshub_stack
```

#### Task 1.3: Study Existing API Contract
```bash
# Analyze current API endpoints
cat src/pokewatch/api/main.py
cat src/pokewatch/api/schemas.py

# Test current API
make api  # In terminal 1
curl http://localhost:8000/docs  # In terminal 2

# Document endpoints to preserve:
# - GET /health
# - POST /api/v1/predict
# - GET /api/v1/cards (if exists)
```

**Deliverables:**
- ✅ Dependencies installed
- ✅ ZenML initialized and connected to DagsHub
- ✅ API contract documented

---

### **Day 2: BentoML Service Implementation (4-6 hours)**

#### Task 2.1: Create BentoML Service Structure
```bash
mkdir -p src/pokewatch/serving
touch src/pokewatch/serving/__init__.py
touch src/pokewatch/serving/service.py
touch bentofile.yaml
```

#### Task 2.2: Implement BentoML Service

**File: `src/pokewatch/serving/service.py`**
```python
"""
BentoML service for PokeWatch fair price predictions.

Replaces the FastAPI application with production-grade serving.
"""

import logging
from typing import Optional
from datetime import date

import bentoml
from pydantic import BaseModel, Field

from pokewatch.models.baseline import BaselineFairPriceModel, load_baseline_model
from pokewatch.core.decision_rules import DecisionConfig, compute_signal
from pokewatch.config import get_settings

logger = logging.getLogger(__name__)


# Request/Response schemas (matching FastAPI schemas)
class PredictionRequest(BaseModel):
    """Request schema for fair price prediction."""
    card_id: str = Field(..., description="Card identifier (e.g., 'sv2a-pokemon-card-151')")
    date: Optional[str] = Field(None, description="Date for prediction (YYYY-MM-DD). Defaults to latest.")


class PredictionResponse(BaseModel):
    """Response schema for fair price prediction."""
    card_id: str
    date: str
    market_price: float
    fair_value: float
    delta_pct: float
    signal: str  # BUY, SELL, HOLD
    metadata: dict


# Load model globally (happens once at service startup)
settings = get_settings()
decision_cfg = DecisionConfig(
    buy_threshold_pct=settings.model.default_buy_threshold_pct,
    sell_threshold_pct=settings.model.default_sell_threshold_pct,
)

# Create BentoML service
@bentoml.service(
    name="pokewatch_service",
    resources={
        "cpu": "1",
        "memory": "1Gi",
    },
    traffic={
        "timeout": 30,
        "concurrency": 32,  # Max concurrent requests
    },
)
class PokeWatchService:
    """PokeWatch BentoML service for card price predictions."""

    def __init__(self):
        """Initialize service and load model."""
        logger.info("Initializing PokeWatch service...")
        self.model = load_baseline_model()
        self.decision_cfg = decision_cfg
        logger.info(f"Model loaded with {len(self.model.get_all_card_ids())} cards")

    @bentoml.api(
        route="/health",
        input_spec=None,
        output_spec=None,
    )
    def health(self) -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "model_loaded": self.model is not None,
            "num_cards": len(self.model.get_all_card_ids()),
        }

    @bentoml.api(
        route="/api/v1/predict",
        input_spec=PredictionRequest,
        output_spec=PredictionResponse,
    )
    def predict(self, request: PredictionRequest) -> PredictionResponse:
        """
        Predict fair value and trading signal for a card.

        Args:
            request: Prediction request with card_id and optional date

        Returns:
            Prediction response with fair value, market price, and signal

        Raises:
            ValueError: If card_id is unknown or date is invalid
        """
        card_id = request.card_id

        # Parse date
        pred_date = None
        if request.date:
            from datetime import datetime
            pred_date = datetime.strptime(request.date, "%Y-%m-%d").date()

        # Get prediction from model
        resolved_date, market_price, fair_value = self.model.predict(
            card_id=card_id,
            date=pred_date
        )

        # Compute signal
        signal, delta_pct = compute_signal(
            market_price=market_price,
            fair_value=fair_value,
            config=self.decision_cfg,
        )

        # Build response
        return PredictionResponse(
            card_id=card_id,
            date=resolved_date.isoformat(),
            market_price=market_price,
            fair_value=fair_value,
            delta_pct=delta_pct,
            signal=signal,
            metadata={
                "model_type": "baseline_moving_average",
                "buy_threshold": self.decision_cfg.buy_threshold_pct,
                "sell_threshold": self.decision_cfg.sell_threshold_pct,
            },
        )

    @bentoml.api(
        route="/api/v1/cards",
    )
    def list_cards(self) -> dict:
        """List all tracked cards."""
        card_ids = self.model.get_all_card_ids()

        return {
            "total": len(card_ids),
            "cards": sorted(list(card_ids)),
        }

    @bentoml.api(
        route="/api/v1/batch_predict",
    )
    async def batch_predict(self, requests: list[PredictionRequest]) -> list[PredictionResponse]:
        """
        Batch prediction for multiple cards.

        Uses async for better performance with multiple requests.
        """
        results = []
        for req in requests:
            try:
                result = self.predict(req)
                results.append(result)
            except Exception as e:
                logger.error(f"Batch prediction failed for {req.card_id}: {e}")
                # Continue with other requests

        return results
```

**File: `bentofile.yaml`**
```yaml
service: "src/pokewatch/serving/service.py:PokeWatchService"
name: pokewatch_service
description: "PokeWatch card price prediction service"
labels:
  owner: beatricedaniel
  project: pokewatch
  stage: production

include:
  - "src/"
  - "config/"
  - "data/processed/"  # Include processed data for model loading
  - "models/baseline/"  # Include model artifacts

python:
  packages:
    - pandas>=2.0.0
    - numpy>=1.24.0
    - pyarrow>=12.0.0
    - pydantic>=2.0.0
    - pyyaml>=6.0.0
    - python-dotenv>=1.0.0
  lock_packages: false  # Set to true for reproducibility

docker:
  python_version: "3.13"
  system_packages:
    - git
  dockerfile_template: |
    FROM python:3.13-slim

    # Install system dependencies
    RUN apt-get update && apt-get install -y \
        gcc \
        g++ \
        git \
        && rm -rf /var/lib/apt/lists/*

    # Set working directory
    WORKDIR /app

    # Copy application
    COPY . /app

    # Install Python dependencies
    RUN pip install --no-cache-dir -r requirements.txt

    # Set environment
    ENV PYTHONUNBUFFERED=1
    ENV PYTHONPATH=/app

    # Expose port
    EXPOSE 3000

    # Run BentoML service
    CMD ["bentoml", "serve", ".", "--host", "0.0.0.0", "--port", "3000"]
```

#### Task 2.3: Build and Test Bento Locally
```bash
# Build Bento
cd pokewatch
bentoml build

# List built Bentos
bentoml list

# Serve locally
bentoml serve pokewatch_service:latest --reload

# Test in another terminal
curl http://localhost:3000/health

curl -X POST http://localhost:3000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"card_id": "sv2a-pokemon-card-151"}'

# Check Swagger UI
open http://localhost:3000
```

#### Task 2.4: Create Helper Scripts

**File: `scripts/build_bento.sh`**
```bash
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

# Build Bento
echo "Building Bento..."
bentoml build

# List Bentos
echo ""
echo "Built Bentos:"
bentoml list | head -5

echo ""
echo "✓ Bento build complete!"
echo ""
echo "To serve locally:"
echo "  bentoml serve pokewatch_service:latest"
echo ""
echo "To containerize:"
echo "  bentoml containerize pokewatch_service:latest"
```

```bash
chmod +x scripts/build_bento.sh
```

**Deliverables:**
- ✅ BentoML service implementation
- ✅ bentofile.yaml configuration
- ✅ Service tested locally
- ✅ Build script created

---

### **Day 3: ZenML Pipeline Implementation (5-6 hours)**

#### Task 3.1: Create ZenML Pipeline Structure
```bash
mkdir -p pipelines
touch pipelines/__init__.py
touch pipelines/ml_pipeline.py
touch pipelines/steps.py
```

#### Task 3.2: Define ZenML Steps

**File: `pipelines/steps.py`**
```python
"""
ZenML pipeline steps for PokeWatch ML workflow.
"""

import logging
from typing import Tuple
from pathlib import Path

import pandas as pd
from zenml import step

from pokewatch.data.collectors.daily_price_collector import main as collect_main
from pokewatch.data.preprocessing.make_features import main as preprocess_main
from pokewatch.models.baseline import BaselineFairPriceModel
from pokewatch.models.train_baseline import calculate_metrics
from pokewatch.core.decision_rules import DecisionConfig
from pokewatch.config import get_settings

logger = logging.getLogger(__name__)


@step
def collect_data_step() -> pd.DataFrame:
    """
    Collect latest card prices from Pokémon Price Tracker API.

    Returns:
        DataFrame with raw price data
    """
    logger.info("Collecting data from API...")

    # Run data collection
    collect_main()

    # Load collected data
    from pokewatch.config import get_data_path
    raw_dir = get_data_path("raw")

    # Find latest parquet file
    parquet_files = list(raw_dir.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError("No data collected")

    latest_file = max(parquet_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Loading data from: {latest_file}")

    df = pd.read_parquet(latest_file)
    logger.info(f"Collected {len(df)} records")

    return df


@step
def preprocess_data_step(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform raw data into features for modeling.

    Args:
        raw_df: Raw price data

    Returns:
        DataFrame with engineered features
    """
    logger.info("Preprocessing data...")

    # Run preprocessing
    preprocess_main()

    # Load processed data
    from pokewatch.config import get_data_path
    from pokewatch.data.collectors.daily_price_collector import load_cards_config

    cards_config = load_cards_config()
    set_name = cards_config["set"]["name"]
    safe_set_name = (
        set_name.lower().replace(" ", "_").replace(":", "").replace("-", "_")
    )
    safe_set_name = "".join(c for c in safe_set_name if c.isalnum() or c == "_")

    processed_file = get_data_path("processed") / f"{safe_set_name}.parquet"

    if not processed_file.exists():
        raise FileNotFoundError(f"Processed data not found: {processed_file}")

    features_df = pd.read_parquet(processed_file)
    logger.info(f"Processed {len(features_df)} feature records")

    return features_df


@step
def train_model_step(features_df: pd.DataFrame) -> BaselineFairPriceModel:
    """
    Train baseline model on features.

    Args:
        features_df: Feature DataFrame

    Returns:
        Trained model
    """
    logger.info("Training baseline model...")

    model = BaselineFairPriceModel(features_df)

    logger.info(f"Model trained with {len(model.get_all_card_ids())} cards")

    return model


@step
def evaluate_model_step(
    model: BaselineFairPriceModel,
    features_df: pd.DataFrame
) -> Tuple[dict, bool]:
    """
    Evaluate model and validate quality thresholds.

    Args:
        model: Trained model
        features_df: Feature DataFrame for evaluation

    Returns:
        Tuple of (metrics dict, is_valid boolean)
    """
    logger.info("Evaluating model...")

    settings = get_settings()
    decision_cfg = DecisionConfig(
        buy_threshold_pct=settings.model.default_buy_threshold_pct,
        sell_threshold_pct=settings.model.default_sell_threshold_pct,
    )

    # Calculate metrics
    metrics = calculate_metrics(features_df, model, decision_cfg)

    # Validation thresholds
    MAPE_THRESHOLD = 15.0
    COVERAGE_THRESHOLD = 0.90

    is_valid = (
        metrics["mape"] <= MAPE_THRESHOLD and
        metrics["coverage_rate"] >= COVERAGE_THRESHOLD
    )

    logger.info(f"Model metrics: MAPE={metrics['mape']:.2f}, Coverage={metrics['coverage_rate']:.2%}")
    logger.info(f"Model valid: {is_valid}")

    return metrics, is_valid


@step
def save_model_step(
    model: BaselineFairPriceModel,
    metrics: dict,
    is_valid: bool
) -> str:
    """
    Save model artifacts to DVC-tracked directory.

    Args:
        model: Trained model
        metrics: Model evaluation metrics
        is_valid: Whether model passed validation

    Returns:
        Path to saved model
    """
    if not is_valid:
        raise ValueError("Model failed validation, not saving")

    logger.info("Saving model artifacts...")

    from datetime import datetime
    import json
    import shutil
    from pokewatch.config import get_data_path

    # Get project root
    project_root = Path(__file__).parent.parent
    models_dir = project_root / "models" / "baseline"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Save processed features (model data source)
    processed_file = get_data_path("processed") / "sv2a_pokemon_card_151.parquet"
    shutil.copy2(processed_file, models_dir / processed_file.name)

    # Save metadata
    metadata = {
        "model_type": "baseline_moving_average",
        "window_size": 3,
        "trained_at": datetime.now().isoformat(),
        "metrics": {
            "rmse": float(metrics["rmse"]),
            "mape": float(metrics["mape"]),
            "coverage_rate": float(metrics["coverage_rate"]),
        },
    }

    metadata_path = models_dir / "model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Model saved to: {models_dir}")

    return str(models_dir)


@step
def build_bento_step(model_path: str) -> str:
    """
    Build BentoML service with the trained model.

    Args:
        model_path: Path to model artifacts

    Returns:
        Bento tag (name:version)
    """
    logger.info("Building BentoML service...")

    import subprocess

    # Run build script
    result = subprocess.run(
        ["./scripts/build_bento.sh"],
        capture_output=True,
        text=True,
        check=True
    )

    logger.info(result.stdout)

    # Get latest Bento tag
    result = subprocess.run(
        ["bentoml", "list", "--output=json"],
        capture_output=True,
        text=True,
        check=True
    )

    import json
    bentos = json.loads(result.stdout)

    if not bentos:
        raise ValueError("No Bentos found after build")

    latest_bento = bentos[0]
    bento_tag = f"{latest_bento['name']}:{latest_bento['version']}"

    logger.info(f"Built Bento: {bento_tag}")

    return bento_tag
```

#### Task 3.3: Create ZenML Pipeline

**File: `pipelines/ml_pipeline.py`**
```python
"""
ZenML ML pipeline for PokeWatch.

Automates: data collection → preprocessing → training → validation → deployment
"""

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.mlflow.steps import mlflow_model_deployer_step

from pipelines.steps import (
    collect_data_step,
    preprocess_data_step,
    train_model_step,
    evaluate_model_step,
    save_model_step,
    build_bento_step,
)


# Docker settings for pipeline execution
docker_settings = DockerSettings(
    python_package_installer="uv",
    required_integrations=["mlflow"],
)


@pipeline(
    enable_cache=True,  # Cache step outputs for faster reruns
    settings={"docker": docker_settings},
)
def pokewatch_ml_pipeline():
    """
    Complete ML pipeline for PokeWatch.

    Steps:
        1. Collect data from API
        2. Preprocess and engineer features
        3. Train baseline model
        4. Evaluate and validate model
        5. Save model artifacts (DVC-tracked)
        6. Build BentoML service
    """
    # Data collection and preprocessing
    raw_data = collect_data_step()
    features = preprocess_data_step(raw_data)

    # Model training and evaluation
    model = train_model_step(features)
    metrics, is_valid = evaluate_model_step(model, features)

    # Save and deploy (only if valid)
    model_path = save_model_step(model, metrics, is_valid)
    bento_tag = build_bento_step(model_path)

    return bento_tag


if __name__ == "__main__":
    # Run the pipeline
    pokewatch_ml_pipeline()
```

#### Task 3.4: Test Pipeline Locally
```bash
# Run pipeline
cd pokewatch
python pipelines/ml_pipeline.py

# Check ZenML dashboard
zenml up
open http://localhost:8237

# Verify pipeline execution
zenml pipeline runs list
```

**Deliverables:**
- ✅ ZenML steps defined
- ✅ ML pipeline created
- ✅ Pipeline tested locally

---

### **Day 4: Integration & Docker Updates (4-5 hours)**

#### Task 4.1: Update Docker Compose for BentoML

**File: `docker-compose.yml` - Add BentoML service**
```yaml
  # BentoML API service (replaces old FastAPI)
  bento-api:
    build:
      context: .
      dockerfile: docker/bento.Dockerfile
    container_name: pokewatch-bento-api
    ports:
      - "3000:3000"
    environment:
      - POKEMON_PRICE_API_KEY=${POKEMON_PRICE_API_KEY:-}
      - DAGSHUB_TOKEN=${DAGSHUB_TOKEN}
      - MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI}
      - PYTHONPATH=/app
      - ENV=${ENV:-prod}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      # Data (read-only)
      - ./data/processed:/app/data/processed:ro
      - ./models/baseline:/app/models/baseline:ro
      # Logs
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

#### Task 4.2: Create BentoML Dockerfile

**File: `docker/bento.Dockerfile`**
```dockerfile
# BentoML Dockerfile for PokeWatch
FROM bentoml/bento-server:1.2.0-python3.13

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY src/ src/
COPY config/ config/
COPY data/processed/ data/processed/
COPY models/baseline/ models/baseline/
COPY bentofile.yaml .

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir uv && \
    python -m uv pip install --system --no-cache -e .

# Build Bento (creates standalone service)
RUN bentoml build

# Expose BentoML port
EXPOSE 3000

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run BentoML service
CMD ["bentoml", "serve", "pokewatch_service:latest", "--host", "0.0.0.0", "--port", "3000"]
```

#### Task 4.3: Update Makefile

**Add to `Makefile`:**
```makefile
# ========================================
# BENTOML SERVING
# ========================================

bento-build:  ## Build BentoML service
	@echo "Building BentoML service..."
	./scripts/build_bento.sh

bento-serve:  ## Serve BentoML locally
	@echo "Starting BentoML service..."
	bentoml serve pokewatch_service:latest --reload

bento-containerize:  ## Build BentoML Docker image
	@echo "Containerizing BentoML service..."
	bentoml containerize pokewatch_service:latest -t pokewatch-bento:latest

bento-api:  ## Start BentoML API in Docker
	@echo "Starting BentoML API..."
	docker-compose up bento-api

# ========================================
# ZENML PIPELINE
# ========================================

pipeline-run:  ## Run ZenML ML pipeline
	@echo "Running ZenML ML pipeline..."
	python pipelines/ml_pipeline.py

pipeline-ui:  ## Open ZenML dashboard
	@echo "Opening ZenML dashboard..."
	zenml up

pipeline-list:  ## List pipeline runs
	zenml pipeline runs list
```

#### Task 4.4: Test Complete Flow
```bash
# 1. Build Bento
make bento-build

# 2. Run BentoML API
make bento-api

# 3. Test API
curl http://localhost:3000/health
curl -X POST http://localhost:3000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"card_id": "sv2a-pokemon-card-151"}'

# 4. Run ZenML pipeline
make pipeline-run

# 5. Check pipeline in dashboard
make pipeline-ui
```

**Deliverables:**
- ✅ Docker Compose updated
- ✅ BentoML Dockerfile created
- ✅ Makefile updated with new commands
- ✅ Complete flow tested

---

### **Day 5: Testing & Documentation (4-5 hours)**

#### Task 5.1: Create Integration Tests

**File: `tests/integration/test_bento_service.py`**
```python
"""
Integration tests for BentoML service.
"""

import pytest
import requests
from datetime import date


@pytest.fixture(scope="module")
def bento_url():
    """BentoML service URL."""
    return "http://localhost:3000"


def test_health_endpoint(bento_url):
    """Test health check endpoint."""
    response = requests.get(f"{bento_url}/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True


def test_predict_endpoint(bento_url):
    """Test prediction endpoint."""
    payload = {
        "card_id": "sv2a-pokemon-card-151",
    }

    response = requests.post(
        f"{bento_url}/api/v1/predict",
        json=payload
    )

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "card_id" in data
    assert "fair_value" in data
    assert "market_price" in data
    assert "signal" in data
    assert data["signal"] in ["BUY", "SELL", "HOLD"]


def test_list_cards_endpoint(bento_url):
    """Test list cards endpoint."""
    response = requests.get(f"{bento_url}/api/v1/cards")

    assert response.status_code == 200
    data = response.json()

    assert "total" in data
    assert "cards" in data
    assert len(data["cards"]) > 0


def test_batch_predict_endpoint(bento_url):
    """Test batch prediction endpoint."""
    payload = [
        {"card_id": "sv2a-pokemon-card-151"},
        {"card_id": "sv2a-pokemon-card-151"},  # Duplicate to test
    ]

    response = requests.post(
        f"{bento_url}/api/v1/batch_predict",
        json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
```

**File: `tests/integration/test_zenml_pipeline.py`**
```python
"""
Integration tests for ZenML pipeline.
"""

import pytest
from pipelines.ml_pipeline import pokewatch_ml_pipeline


def test_pipeline_execution():
    """Test full pipeline execution."""
    # Run pipeline
    result = pokewatch_ml_pipeline()

    # Verify Bento was built
    assert result is not None
    assert "pokewatch_service" in result
```

#### Task 5.2: Run All Tests
```bash
# Unit tests
make test-unit

# Integration tests (requires services running)
make bento-api  # In terminal 1
make test-integration  # In terminal 2

# Coverage report
pytest tests/ --cov=src/pokewatch --cov-report=html
open htmlcov/index.html
```

#### Task 5.3: Update Documentation

**File: `docs/bentoml_guide.md`**
```markdown
# BentoML Service Guide

## Overview

PokeWatch uses BentoML for production-grade model serving, replacing the original FastAPI implementation.

## Building the Service

```bash
# Build Bento
make bento-build

# Serve locally with hot-reload
make bento-serve

# Containerize
make bento-containerize
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Prediction
```bash
POST /api/v1/predict
Content-Type: application/json

{
  "card_id": "sv2a-pokemon-card-151",
  "date": "2025-11-30"  # Optional
}
```

### List Cards
```bash
GET /api/v1/cards
```

### Batch Prediction
```bash
POST /api/v1/batch_predict
Content-Type: application/json

[
  {"card_id": "sv2a-pokemon-card-151"},
  {"card_id": "sv2a-pokemon-card-152"}
]
```

## Deployment

```bash
# Docker Compose
make bento-api

# Access API
curl http://localhost:3000/health
```
```

**File: `docs/zenml_guide.md`**
```markdown
# ZenML Pipeline Guide

## Overview

ZenML orchestrates the complete ML workflow:
- Data collection
- Preprocessing
- Training
- Validation
- Model deployment

## Running the Pipeline

```bash
# One-time setup
zenml init
zenml stack set dagshub_stack

# Run pipeline
make pipeline-run

# View in dashboard
make pipeline-ui
```

## Pipeline Steps

1. **collect_data_step**: Fetch latest card prices
2. **preprocess_data_step**: Feature engineering
3. **train_model_step**: Train baseline model
4. **evaluate_model_step**: Validate model quality
5. **save_model_step**: Save to DVC-tracked directory
6. **build_bento_step**: Build BentoML service

## Scheduling

```python
# Schedule daily at 2 AM
from zenml.config import Schedule

schedule = Schedule(cron_expression="0 2 * * *")
pokewatch_ml_pipeline.run(schedule=schedule)
```
```

#### Task 5.4: Create Migration Checklist

**File: `WEEK1_MIGRATION_CHECKLIST.md`**
```markdown
# Week 1 Migration Checklist

## BentoML Migration

- [ ] BentoML service implemented (`src/pokewatch/serving/service.py`)
- [ ] bentofile.yaml configured
- [ ] Health endpoint works: `curl http://localhost:3000/health`
- [ ] Prediction endpoint works with same API contract as FastAPI
- [ ] Batch prediction endpoint added
- [ ] Docker image builds: `make bento-containerize`
- [ ] Docker Compose service runs: `make bento-api`
- [ ] Integration tests pass

## ZenML Pipeline

- [ ] ZenML initialized: `zenml init`
- [ ] DagsHub integration configured
- [ ] Pipeline steps defined (`pipelines/steps.py`)
- [ ] ML pipeline created (`pipelines/ml_pipeline.py`)
- [ ] Pipeline runs successfully: `make pipeline-run`
- [ ] Pipeline visible in ZenML dashboard
- [ ] Model artifacts saved to DVC-tracked directory
- [ ] Bento built automatically by pipeline

## Documentation

- [ ] BentoML guide written (`docs/bentoml_guide.md`)
- [ ] ZenML guide written (`docs/zenml_guide.md`)
- [ ] Makefile updated with new commands
- [ ] README updated with Week 1 changes

## Cleanup

- [ ] Old FastAPI service still works (for comparison)
- [ ] Both services can coexist during migration
- [ ] Migration path documented
- [ ] Rollback plan documented
```

**Deliverables:**
- ✅ Integration tests created and passing
- ✅ Documentation completed
- ✅ Migration checklist created

---

## Week 1 Success Criteria

At the end of Week 1, verify:

- [ ] **BentoML service serves predictions** with same API contract as FastAPI
- [ ] **ZenML pipeline runs end-to-end** from data collection to Bento build
- [ ] **All tests pass** (unit + integration)
- [ ] **Documentation complete** for both BentoML and ZenML
- [ ] **Makefile commands work**: `make bento-api`, `make pipeline-run`
- [ ] **Services run in Docker**: Both standalone and via docker-compose
- [ ] **Model versioning works**: Models saved with metadata, tracked by DVC

---

## Troubleshooting

### BentoML Issues

**Problem:** Model not loading in Bento
```bash
# Check model files exist
ls -lah models/baseline/
ls -lah data/processed/

# Verify bentofile.yaml includes correct paths
cat bentofile.yaml

# Check Bento logs
docker logs pokewatch-bento-api
```

**Problem:** Port 3000 already in use
```bash
# Change port in docker-compose.yml
ports:
  - "3001:3000"  # Host:Container
```

### ZenML Issues

**Problem:** Pipeline fails with import errors
```bash
# Ensure all dependencies installed
python -m uv pip install -e ".[dev]"

# Check ZenML integrations
zenml integration list
```

**Problem:** DagsHub connection fails
```bash
# Verify token
echo $DAGSHUB_TOKEN

# Re-configure experiment tracker
zenml experiment-tracker update dagshub_tracker \
  --tracking_password="${DAGSHUB_TOKEN}"
```

---

## Next Steps (Week 2)

After completing Week 1:
- [ ] Implement CI/CD with GitHub Actions
- [ ] Add API authentication and rate limiting
- [ ] Performance testing and optimization
- [ ] Prepare for Kubernetes deployment (Week 3)

---

## Resources

- **BentoML Docs**: https://docs.bentoml.com/
- **ZenML Docs**: https://docs.zenml.io/
- **DagsHub Integration**: https://docs.zenml.io/stack-components/experiment-trackers/mlflow
- **Migration Guide**: See `MIGRATION_GUIDE.md` for Phase 2 → Phase 3 transition

---

**Let's execute Week 1! 🚀**
