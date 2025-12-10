# Pokewatch

## Project Goals

**PokeWatch: Pokémon Card Price Drift & Alerting Platform**

PokeWatch is a small MLOps-driven platform that helps collectors and small investors monitor a fixed universe of 30 Pokémon cards and spot potential BUY/SELL opportunities.

The core idea is to estimate a **“fair value”** for each card (based on recent price history and simple models) and compare it to the current market price. When the market price deviates too much from the estimated fair value, PokeWatch raises a BUY, SELL, or HOLD suggestion.

The project is designed as an end-to-end MLOps example:
- Real price data from public Pokémon pricing APIs.
- Simple time-series/tabular models for fair value.
- Microservices for data collection and inference.
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

These KPIs are more about the “platform health” than pure model performance:

- **API Latency (p95)**
  95th percentile response time for the `/fair_price` endpoint.

- **API Error Rate**
  Percentage of failed requests (5xx) over time.

- **Model Version Adoption**
  Which model version is currently serving traffic, and how often it is updated.

- **Drift Indicators** (later phases)
  - Data drift on input features (price distributions, volatility, etc.).
  - Prediction drift (distribution of fair values and deviations over time).
  - Number of drift events that trigger retraining per month.

Together, these metrics make PokeWatch look and behave like a small but realistic MLOps production system, while keeping the actual implementation lightweight and focused.


## Documentation

All project documentation is organized in the [`docs/`](docs/) directory. See the [Documentation Index](docs/README.md) for a complete overview.

**Key Documentation:**
- **[Architecture](docs/architecture/MICROSERVICES_ARCHITECTURE.md)** - Microservices architecture overview
- **[Deployment Guide](docs/deployment/MICROSERVICES_DEPLOYMENT.md)** - Complete deployment instructions
- **[Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)** - What was built and how

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

MLflow runs in Docker with MinIO for artifact storage.

#### Start Services
```bash
# Start MLflow and MinIO
docker-compose up -d minio mlflow
```

#### Run Training
```bash
# Using helper script
./scripts/train_baseline_docker.sh

# Or directly
docker-compose run --rm training python -m pokewatch.models.train_baseline
```

#### View Results
- **MLflow UI**: http://127.0.0.1:5001
- **MinIO Console**: http://127.0.0.1:9001 (minioadmin/minioadmin)

For detailed documentation, see [docs/README.md](docs/README.md).

### Pipeline Orchestration (ZenML)

PokeWatch uses ZenML for ML pipeline orchestration with experiment tracking.

#### Setup ZenML (First Time)
```bash
# Run setup script
bash scripts/setup_zenml.sh

# Verify installation
zenml stack list
```

#### Run Pipeline
```bash
# Run complete ML pipeline
python -m pipelines.ml_pipeline

# View pipeline runs
zenml up
```

#### Schedule Pipeline
```bash
# Install daily cron job (3:00 AM)
bash scripts/schedule_pipeline.sh install

# Check schedule status
bash scripts/schedule_pipeline.sh status

# Remove schedule
bash scripts/schedule_pipeline.sh remove
```

For detailed documentation, see [docs/README.md](docs/README.md).

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
  --from-literal=MLFLOW_TRACKING_URI="https://dagshub.com/user/repo.mlflow" \
  --from-literal=MLFLOW_TRACKING_USERNAME="user" \
  --from-literal=MLFLOW_TRACKING_PASSWORD="token"

# 4. Access Airflow UI
# http://VM-IP:30081 (default: admin/admin)
```

For detailed architecture information, see [docs/architecture/MICROSERVICES_ARCHITECTURE.md](docs/architecture/MICROSERVICES_ARCHITECTURE.md).

### Kubernetes Deployment

PokeWatch microservices can be deployed to Kubernetes for scalability and high availability.

#### Quick Start
```bash
# Deploy to Minikube
./scripts/deploy_k8s.sh
```

#### Manual Deployment
```bash
# Start Minikube
minikube start --driver=docker --memory=4096 --cpus=4

# Build all microservice images
./scripts/build_microservices.sh --minikube

# Deploy all microservices
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/model-service-deployment.yaml
kubectl apply -f k8s/model-service-service.yaml
kubectl apply -f k8s/decision-service-deployment.yaml
kubectl apply -f k8s/decision-service-service.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml

# Enable auto-scaling (optional)
kubectl apply -f k8s/model-service-hpa.yaml
```

For complete deployment instructions, see [docs/deployment/MICROSERVICES_DEPLOYMENT.md](docs/deployment/MICROSERVICES_DEPLOYMENT.md).

#### Access the API
```bash
# Get Minikube IP
minikube ip

# Access API Gateway via NodePort (port 30080)
curl http://$(minikube ip):30080/health

# Or port-forward
kubectl port-forward -n pokewatch svc/api-gateway 8000:8000
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

For detailed Kubernetes and microservices deployment, see:
- [Microservices Deployment Guide](docs/deployment/MICROSERVICES_DEPLOYMENT.md)
- [Microservices Architecture](docs/architecture/MICROSERVICES_ARCHITECTURE.md)
- [Documentation Index](docs/README.md)


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
│   ├── README.md               # Documentation index
│   ├── IMPLEMENTATION_SUMMARY.md  # Implementation summary
│   ├── architecture/           # Architecture & design docs
│   │   └── MICROSERVICES_ARCHITECTURE.md
│   ├── deployment/            # Deployment guides
│   │   └── MICROSERVICES_DEPLOYMENT.md
│   ├── planning/              # Development plans & roadmaps
│   │   ├── MICROSERVICES_TRANSITION_PLAN.md
│   │   ├── phase1.md
│   │   └── phase2.md
│   └── technical-guides/      # Technical documentation
│       └── airflow_guide.md
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
│       │   ├── __init__.py              # Placeholder (Phase 4)
│       │   └── metrics.py               # Prometheus metrics exposure (Phase 3–4)
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
│   ├── dev.Dockerfile          # Reproducible dev environment (Phase 1 optional)
│   └── docker-compose.dev.yml  # Local API launch + hot-reload
├── k8s/
│   ├── namespace.yaml          # Kubernetes namespace
│   ├── api-deployment.yaml     # API deployment with health probes
│   ├── api-service.yaml        # NodePort service (30080)
│   ├── hpa.yaml                # Horizontal Pod Autoscaler
│   └── airflow-values.yaml     # Helm values for Airflow
├── airflow/
│   └── dags/
│       ├── ml_pipeline.py      # ML pipeline DAG
│       └── .airflowignore      # Exclude non-DAG files
└── .github/
    └── workflows/
        └── ci.yml              # CI (Phase 3)
```
