# Pokewatch

## Project Goals

**PokeWatch: Pokémon Card Price Drift & Alerting Platform**

PokeWatch is a small MLOps-driven platform that helps collectors and small investors monitor a fixed universe of ~40 Pokémon cards and spot potential BUY/SELL opportunities.

The core idea is to estimate a **“fair value”** for each card (based on recent price history and simple models) and compare it to the current market price. When the market price deviates too much from the estimated fair value, PokeWatch raises a BUY, SELL, or HOLD suggestion.

The project is designed as an end-to-end MLOps example:
- Real price data from public Pokémon pricing APIs.
- Simple time-series/tabular models for fair value.
- FastAPI service for inference and data collection.
- Experiment tracking, data/model versioning, orchestration, deployment, and monitoring.


## Business Objectives

- Help a Pokémon card collector/investor **prioritize actions** across a curated list of cards (chase cards, grails, meta-relevant, and personal favorites).
- Detect **undervalued** cards (good BUY candidates) and **overpriced** cards (good SELL candidates) as early as possible.
- Provide a **simple, explainable signal** (BUY/HOLD/SELL) rather than a black-box “magic” score.

At a high level:

> For each card and day, estimate a fair value using historical price data and compare it with the current market price. If the deviation exceeds configurable thresholds, emit a BUY or SELL alert; otherwise, suggest HOLD.


## Key Performance Indicators (KPIs)

### 1. Alert Quality (Primary KPI)

**Goal:** Measure how useful BUY/SELL signals are over a chosen evaluation horizon (e.g. the next 7–30 days).

- **BUY Precision**
  Of all BUY alerts generated, how many were actually good buys?
  A BUY is considered “good” if the price increases by at least a configurable percentage within the evaluation horizon.

- **BUY Recall**
  Of all situations where the card later became a good buy, how many times did the system issue a BUY alert?

- **SELL Precision**
  Of all SELL alerts generated, how many were actually good sells?
  A SELL is considered “good” if the price drops by at least a configurable percentage within the evaluation horizon.

- **SELL Recall**
  Of all situations where the card later dropped significantly, how many times did the system issue a SELL alert?

These KPIs are computed offline on historical data (backtesting).


### 2. Pricing Accuracy (Secondary KPIs)

**Goal:** Measure how close the model’s fair value is to the observed market prices.

- **MAPE (Mean Absolute Percentage Error)**
  Average percentage error between predicted fair value and actual market price, reported:
  - Globally (all cards),
  - Per card,
  - Per card category (grail, chase, meta, personal).

- **RMSE (Root Mean Squared Error)**
  Average squared error in absolute price units, useful for comparing models.

- **Coverage / Signal Rate**
  Percentage of (card, day) pairs for which:
  - A valid fair value is produced,
  - A BUY or SELL alert is emitted (vs HOLD).

  This helps avoid a model that “never says anything”.


### 3. Stability & User Experience

**Goal:** Avoid noisy, flip-flopping signals that confuse the user.

- **Signal Stability**
  Fraction of days where the signal changes for a given card (e.g. BUY → SELL → BUY).
  Lower is generally better, as long as alert quality remains high.

- **Alert Distribution**
  Ratio of BUY / SELL / HOLD over time.
  Useful to see if the system is overly biased toward one type of signal.


### 4. Operational & Monitoring Metrics (for MLOps)

These KPIs are more about the "platform health" than pure model performance:

- **API Latency (p95)**
  95th percentile response time for the `/fair_price` endpoint.
  *Monitored via Prometheus + Grafana dashboard.*

- **API Error Rate**
  Percentage of failed requests (5xx) over time.
  *Monitored via Prometheus + Grafana dashboard.*

- **Model Version Adoption**
  Which model version is currently serving traffic, and how often it is updated.
  *Tracked via MLflow on DagsHub.*

- **Drift Indicators** (Phase 4 - Implemented)
  - Data drift on input features (price distributions, volatility, etc.).
  - Prediction drift (distribution of fair values and deviations over time).
  - HTML reports generated via Evidently.

Together, these metrics make PokeWatch look and behave like a small but realistic MLOps production system, while keeping the actual implementation lightweight and focused.


## MLOps Setup

### Data Versioning (DVC)

PokeWatch uses DVC (Data Version Control) with DagsHub for data versioning and pipeline orchestration.

#### First-time Setup
```bash
# Clone repository
git clone git@github.com:beatricedaniel/pokewatch.git
cd pokewatch

# Pull versioned data from DagsHub
dvc pull
```

#### Reproduce Pipeline
```bash
# Run entire pipeline: collect → preprocess → train
dvc repro

# Run specific stage
dvc repro train

# Visualize pipeline
dvc dag
```

#### Update Data
```bash
# After collecting new data
dvc add data/raw
dvc push
git add data/raw.dvc dvc.lock
git commit -m "data: Update raw data with new prices"
git push
```

### Experiment Tracking (MLflow)

PokeWatch uses MLflow with DagsHub for experiment tracking and model registry. For local development, an optional MinIO-based MLflow stack is available via Docker Compose.

#### Production (DagsHub)
MLflow tracking is configured to use DagsHub by default:
- **Tracking URI**: `https://dagshub.com/beatricedaniel/pokewatch.mlflow`
- Configure credentials via environment variables:
  ```bash
  export MLFLOW_TRACKING_URI="https://dagshub.com/beatricedaniel/pokewatch.mlflow"
  export MLFLOW_TRACKING_USERNAME="beatricedaniel"
  export MLFLOW_TRACKING_PASSWORD="your_dagshub_token"
  ```

#### Local Development (Optional)
For local MLflow with MinIO:
```bash
# Start MLflow and MinIO
docker-compose --profile mlflow up -d

# MLflow UI: http://127.0.0.1:5001
# MinIO Console: http://127.0.0.1:9001 (minioadmin/minioadmin)
```

#### Run Training
```bash
# Using helper script
./scripts/train_baseline_docker.sh

# Or directly
docker-compose --profile training run --rm training python -m pokewatch.models.train_baseline
```

### Airflow Pipeline Orchestration

PokeWatch uses Apache Airflow for ML pipeline orchestration on Kubernetes:

#### Architecture
- **Airflow Deployment**: Helm chart on K3s (remote VM) with LocalExecutor
- **Task Execution**: KubernetesPodOperator creates pods with custom Docker images
- **DAG Sync**: Git-sync automatically pulls DAGs from GitHub every 60 seconds
- **Container Registry**: Docker Hub (`beatricedaniel/pokewatch:latest`)

#### ML Pipeline DAG (`pokewatch_ml_pipeline`)
The pipeline runs daily at 2 AM UTC with two tasks:
1. **run_pipeline**: Data collection → Feature engineering → Model training (single pod)
2. **reload_model**: Triggers API `/reload` endpoint to load new model

#### Quick Start (VM Deployment)
```bash
# 1. Build and push Docker image (local machine)
docker build --platform linux/amd64 -t beatricedaniel/pokewatch:latest -f docker/api.Dockerfile .
docker push beatricedaniel/pokewatch:latest

# 2. Deploy Airflow (on VM)
helm repo add apache-airflow https://airflow.apache.org
helm install airflow apache-airflow/airflow -f k8s/airflow-values.yaml -n airflow

# 3. Create secrets (on VM)
kubectl create secret generic pokewatch-secrets -n pokewatch \
  --from-literal=POKEMON_PRICE_API_KEY="your_key" \
  --from-literal=MLFLOW_TRACKING_URI="https://dagshub.com/beatricedaniel/pokewatch.mlflow" \
  --from-literal=MLFLOW_TRACKING_USERNAME="beatricedaniel" \
  --from-literal=MLFLOW_TRACKING_PASSWORD="token"

# 4. Access Airflow UI
# http://VM-IP:30081 (default: admin/admin)
```

### CI/CD (GitHub Actions)

PokeWatch uses GitHub Actions for continuous integration and deployment with 5 workflows:

#### Workflows

1. **Test** (`.github/workflows/test.yml`)
   - Runs on push/PR to `main` and `develop` branches
   - Unit and integration tests with pytest
   - Code coverage reporting (Codecov)
   - Coverage threshold: 70%

2. **Quality** (`.github/workflows/quality.yml`)
   - Code quality checks: ruff linting, black formatting, mypy type checking
   - Import order validation
   - Security scanning with bandit

3. **Docker Build** (`.github/workflows/docker-build.yml`)
   - Builds API and BentoML Docker images on push to `main` or tags
   - Multi-platform builds (linux/amd64, linux/arm64)
   - Pushes to GitHub Container Registry (ghcr.io)
   - Image testing after build

4. **Bento Build** (`.github/workflows/bento-build.yml`)
   - BentoML-specific build and validation

5. **Release** (`.github/workflows/release.yml`)
   - Triggered on version tags (`v*.*.*`)
   - Full test suite execution
   - Builds and pushes versioned Docker images
   - Creates GitHub releases with changelog

#### Container Registry

Docker images are published to GitHub Container Registry:
- **API**: `ghcr.io/beatricedaniel/pokewatch/pokewatch-api:latest`
- **Bento**: `ghcr.io/beatricedaniel/pokewatch/pokewatch-bento:latest`

### Monitoring (Prometheus + Grafana)

PokeWatch uses Prometheus for metrics collection and Grafana for visualization.

#### Metrics Exposed

The API exposes Prometheus metrics at `/metrics`:
- `pokewatch_requests_total` - Request count by endpoint, method, status
- `pokewatch_request_latency_seconds` - Request latency histogram
- `pokewatch_predictions_total` - Predictions by signal (BUY/SELL/HOLD)
- `pokewatch_errors_total` - Errors by type
- `pokewatch_model_reloads_total` - Model reload events
- `pokewatch_model_info` - Current model version

#### Deploy Monitoring Stack
```bash
# On VM
kubectl apply -f k8s/prometheus-configmap.yaml
kubectl apply -f k8s/prometheus-deployment.yaml
kubectl apply -f k8s/grafana-configmap.yaml
kubectl apply -f k8s/grafana-deployment.yaml
```

#### Access Services
- **Prometheus**: `http://VM-IP:30090`
- **Grafana**: `http://VM-IP:30300` (admin/admin)
- **Dashboard**: Dashboards → Browse → PokeWatch Dashboard

For detailed setup, see [docs/monitoring/MONITORING_GUIDE.md](docs/monitoring/MONITORING_GUIDE.md).

### Drift Detection (Evidently)

PokeWatch uses Evidently for data and prediction drift detection.

#### Run Drift Detection
```bash
python -m pokewatch.monitoring.drift_detector \
    data/processed/reference.parquet \
    data/processed/current.parquet
```

Reports are saved to `data/drift_reports/` as HTML files.

For detailed usage, see [docs/monitoring/DRIFT_DETECTION.md](docs/monitoring/DRIFT_DETECTION.md).

### Kubernetes Deployment

PokeWatch API can be deployed to Kubernetes (Minikube for local development, K3s for remote VM) for scalability and high availability.

#### Quick Start
```bash
# Deploy to Minikube
./scripts/deploy_k8s.sh
```

#### Manual Deployment
```bash
# Start Minikube
minikube start --driver=docker --memory=4096 --cpus=2
eval $(minikube docker-env)

# Build Docker image
docker build -t pokewatch-api:latest -f docker/api.Dockerfile .

# Deploy API service
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml

# Enable auto-scaling (optional)
kubectl apply -f k8s/hpa.yaml
```

#### Access the API
```bash
# Get Minikube IP
minikube ip

# Access API via NodePort (port 30080)
curl http://$(minikube ip):30080/health

# Or port-forward
kubectl port-forward -n pokewatch svc/pokewatch-api 8000:8000
curl http://localhost:8000/health
```

#### Monitoring and Management
```bash
# Monitor deployment
./scripts/monitor_k8s.sh

# Scale manually
kubectl scale deployment/pokewatch-api --replicas=5 -n pokewatch

# View logs
kubectl logs -l app=pokewatch-api -n pokewatch

# Verify deployment
./scripts/verify_k8s.sh
```

For detailed Kubernetes deployment, see:
- [Phase 4 VM Deployment Guide](docs/deployment/PHASE4_VM_DEPLOYMENT.md)
- [Monitoring Guide](docs/monitoring/MONITORING_GUIDE.md)


## Project structure

```
pokewatch/
├── README.md
├── pyproject.toml              # Python project configuration
├── requirements.txt            # Python dependencies
├── .gitignore                  # Files to ignore by Git
├── .env.example                # Example environment variables (POKEMON_PRICE_API_KEY, etc.)
├── data/
│   ├── raw/                    # Raw dumps from Pokemon Price Tracker (JSON/Parquet)
│   ├── interim/                # Intermediate data (normalized)
│   ├── processed/              # Features ready for the model
│   └── synthetic/              # Synthetic data (later)
├── models/
│   ├── baseline/               # Simple artifacts (Phase 1)
│   └── trained/                # Trained ML models (Later phases)
├── notebooks/                  # Jupyter explorations (optional)
├── config/
│   ├── cards.yaml              # List of ~40 tracked cards
│   ├── settings.yaml           # Global config (API URL, paths, thresholds, etc.)
│   └── logging.yaml            # Python logging configuration
├── docs/
│   ├── deployment/            # Deployment guides
│   │   └── PHASE4_VM_DEPLOYMENT.md  # Phase 4 monitoring deployment
│   ├── monitoring/            # Monitoring documentation (Phase 4)
│   │   ├── MONITORING_GUIDE.md      # Prometheus/Grafana setup
│   │   └── DRIFT_DETECTION.md       # Evidently drift detection
│   └── planning/              # Development plans & roadmaps
│       └── phase4.md               # Phase 4 requirements
├── src/
│   └── pokewatch/
│       ├── __init__.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py     # Reads settings.yaml + env variables
│       ├── core/
│       │   ├── __init__.py
│       │   ├── business_metrics.py  # KPI definitions (Phase 1)
│       │   └── decision_rules.py    # BUY/HOLD/SELL rules (Phase 1)
│       ├── data/
│       │   ├── __init__.py
│       │   ├── price_tracker_client.py   # PokemonPriceTracker client (Phase 1)
│       │   ├── collectors/
│       │   │   ├── __init__.py
│       │   │   └── daily_price_collector.py  # Collection pipeline (Phase 1)
│       │   └── preprocessing/
│       │       ├── __init__.py
│       │       └── make_features.py     # Flatten priceHistory → timeseries (Phase 1)
│       ├── models/
│       │   ├── __init__.py
│       │   ├── baseline.py              # Baseline model (Phase 1)
│       │   └── train_baseline.py        # Simple training script (Phase 1)
│       ├── api/
│       │   ├── __init__.py
│       │   ├── main.py                  # FastAPI app, endpoints (Phase 1)
│       │   ├── schemas.py               # Pydantic request/response models (Phase 1)
│       │   └── dependencies.py          # Dependencies (config, model, etc.)
│       ├── monitoring/
│       │   ├── __init__.py              # Module exports
│       │   ├── metrics.py               # Prometheus metrics exposure (Phase 4)
│       │   └── drift_detector.py        # Evidently drift detection (Phase 4)
│       ├── orchestration/
│       │   ├── __init__.py              # Placeholder (Phase 3)
│       │   └── flows.py                 # Prefect/Airflow
│       └── utils/
│           ├── __init__.py
│           ├── io.py                    # File read/write helpers
│           └── time.py                  # Date helpers
├── tests/
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_price_tracker_client.py   # Phase 1
│   │   ├── test_baseline.py               # Phase 1
│   │   └── test_decision_rules.py         # Phase 1
│   └── integration/
│       ├── __init__.py
│       └── test_api_baseline.py           # Phase 1 (simple happy path)
├── docker/
│   ├── api.Dockerfile          # FastAPI container (Phase 1)
│   └── bento.Dockerfile        # BentoML container (experimental)
├── k8s/
│   ├── namespace.yaml          # Kubernetes namespace
│   ├── api-deployment.yaml     # API deployment with health probes
│   ├── api-service.yaml        # NodePort service (30080)
│   ├── hpa.yaml                # Horizontal Pod Autoscaler
│   ├── ml-secrets.yaml         # Template for ML secrets
│   ├── airflow-values.yaml     # Helm values for Airflow
│   ├── airflow-pv.yaml         # Persistent volume for Airflow
│   ├── airflow-rbac.yaml       # RBAC for Airflow
│   ├── prometheus-configmap.yaml    # Prometheus scrape config (Phase 4)
│   ├── prometheus-deployment.yaml   # Prometheus server (Phase 4)
│   ├── grafana-configmap.yaml       # Grafana datasource + dashboard (Phase 4)
│   └── grafana-deployment.yaml      # Grafana server (Phase 4)
├── airflow/
│   └── dags/
│       ├── ml_pipeline.py      # ML pipeline DAG
│       └── .airflowignore      # Exclude non-DAG files
└── .github/
    └── workflows/
        ├── test.yml            # Unit and integration tests
        ├── quality.yml         # Code quality checks (ruff, black, mypy, bandit)
        ├── docker-build.yml    # Docker image builds (API and Bento)
        ├── bento-build.yml     # BentoML-specific builds
        └── release.yml         # Release automation
```
