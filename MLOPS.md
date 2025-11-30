# MLOps Documentation - PokeWatch

## Overview

PokeWatch implements a complete MLOps stack for managing the machine learning lifecycle, from data versioning to model deployment and monitoring.

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Data Versioning** | DVC + DagsHub | Track and version datasets and models |
| **Experiment Tracking** | DagsHub MLflow | Cloud-hosted experiment tracking and metrics |
| **Artifact Storage** | DagsHub Storage | Store MLflow artifacts (plots, models, summaries) |
| **Pipeline Orchestration** | DVC Pipelines + Makefile | Reproducible ML workflows with standardized commands |
| **Model Versioning** | DVC + MLflow | Version models with DVC, track with MLflow |
| **Microservices** | Docker + docker-compose | Isolated collector, API, and training services |
| **Version Control** | Git + DagsHub | Code, pipeline, and metadata versioning |

**Note:** A local MLflow stack (MLflow + MinIO) is available for offline development via `docker-compose --profile mlflow up`, but production uses DagsHub's cloud MLflow.

---

## Quick Start Guide

### Prerequisites
1. **DagsHub Account**: Create account at https://dagshub.com
2. **API Keys**:
   - Pokémon Price Tracker API key
   - DagsHub token (from https://dagshub.com/user/settings/tokens)
3. **Environment**: Copy `.env.example` to `.env` and fill in credentials

### Initial Setup
```bash
# Clone repository
git clone https://dagshub.com/beatricedaniel/pokewatch.git
cd pokewatch

# Setup environment and dependencies
make setup

# Configure credentials in .env
cp .env.example .env
vim .env  # Add POKEMON_PRICE_API_KEY and DAGSHUB_TOKEN

# Pull latest data from DagsHub
make dvc-pull
```

### Common Workflows

**Collect fresh data:**
```bash
make collect        # Run collector microservice
make dvc-push       # Upload to DagsHub
```

**Train model:**
```bash
make train          # Train with DagsHub MLflow tracking
```

**Run full pipeline:**
```bash
make pipeline       # Collect → Preprocess → Train
make dvc-push       # Upload data/models to DagsHub
```

**Start API server:**
```bash
make api            # Start prediction API on port 8000
```

**View experiments:**
- Experiments: https://dagshub.com/beatricedaniel/pokewatch/experiments
- Data: https://dagshub.com/beatricedaniel/pokewatch/data

### Available Commands
Run `make help` to see all available commands.

---

## Data Versioning with DVC

### Architecture

```
DagsHub (Remote Storage)
         ↑
         │ dvc push/pull
         ↓
   Local DVC Cache
         ↑
         │
    .dvc files (Git)
```

### Initial Setup

**First-time clone:**
```bash
# Clone repository
git clone git@github.com:beatricedaniel/pokewatch.git
cd pokewatch

# Pull versioned data from DagsHub
dvc pull
```

This downloads all data files referenced by `.dvc` metadata files.

### Working with Data

#### Viewing Data Status
```bash
# Check if data is up-to-date
dvc status

# List all DVC-tracked files
dvc list . data/raw
dvc list . data/processed
```

#### Updating Data
```bash
# After collecting new data
python -m pokewatch.data.collectors.daily_price_collector

# DVC will automatically detect changes in pipeline outputs
dvc status

# Re-run pipeline to update downstream stages
dvc repro
```

#### Versioning Data Changes
```bash
# Push updated data to DagsHub
dvc push

# Commit the pipeline changes
git add dvc.lock
git commit -m "data: Update with latest card prices"
git push origin main
```

### Data Lineage

DVC tracks which data version was used to train which model:

```bash
# View data dependencies for a specific stage
dvc dag

# Show metrics from a specific pipeline run
dvc metrics show
```

---

## Pipeline Management

### Pipeline Overview

PokeWatch uses a 3-stage pipeline:

```
┌─────────┐
│ collect │  ← Fetch daily prices from API
└────┬────┘
     │
     ↓
┌────────────┐
│ preprocess │  ← Transform raw data → features
└─────┬──────┘
      │
      ↓
┌───────┐
│ train │  ← Train model in Docker + log to MLflow
└───────┘
```

### Running the Pipeline

**Full pipeline reproduction:**
```bash
# Run all stages (collect → preprocess → train)
dvc repro

# Force re-run even if nothing changed
dvc repro --force
```

**Run specific stage:**
```bash
# Run only training (if data hasn't changed)
dvc repro train

# Run only data collection
dvc repro collect
```

### Pipeline Configuration

The pipeline is defined in `dvc.yaml`:

```yaml
stages:
  collect:
    cmd: python -m pokewatch.data.collectors.daily_price_collector
    deps: [config/cards.yaml, config/settings.yaml, ...]
    outs: [data/raw]

  preprocess:
    cmd: python -m pokewatch.data.preprocessing.make_features
    deps: [data/raw, ...]
    outs: [data/processed/sv2a_pokemon_card_151.parquet]
    params:
      - config/settings.yaml:
          - data.raw_data_dir
          - data.processed_data_dir

  train:
    cmd: docker-compose run --rm training python -m pokewatch.models.train_baseline
    deps: [data/processed/sv2a_pokemon_card_151.parquet, ...]
    params:
      - config/settings.yaml:
          - model.default_buy_threshold_pct
          - model.default_sell_threshold_pct
```

### Pipeline Benefits

✅ **Reproducibility**: Anyone can reproduce results with `dvc repro`
✅ **Caching**: DVC only re-runs stages when dependencies change
✅ **Versioning**: Pipeline definition versioned in Git
✅ **Lineage**: Track which data → which model

---

## Experiment Tracking with MLflow

### Architecture

PokeWatch uses **DagsHub MLflow** for experiment tracking in production. All experiments, metrics, and artifacts are logged to DagsHub's cloud platform.

```
Training Container
       │
       ├─→ DagsHub MLflow (Cloud)
       │        │
       │        ├─→ PostgreSQL (metrics/params)
       │        └─→ DagsHub Storage (artifacts: plots, summaries)
       │
       └─→ HTTPS API (authenticated)
```

**Configuration:**
- **Tracking URI**: `https://dagshub.com/beatricedaniel/pokewatch.mlflow`
- **Authentication**: Via `DAGSHUB_TOKEN` environment variable
- **Web UI**: https://dagshub.com/beatricedaniel/pokewatch/experiments

### Running Experiments

**Using Makefile (recommended):**
```bash
# Train model with DagsHub MLflow tracking
make train

# Run full pipeline (collect → preprocess → train)
make pipeline
```

**Using Docker Compose:**
```bash
# Direct docker-compose command
docker-compose run --rm training python -m pokewatch.models.train_baseline

# With custom parameters
docker-compose run --rm training python -m pokewatch.models.train_baseline \
  --experiment_name my_experiment \
  --run_name my_run
```

**View results:**
- **DagsHub Experiments**: https://dagshub.com/beatricedaniel/pokewatch/experiments
- **MLflow UI**: https://dagshub.com/beatricedaniel/pokewatch.mlflow

### Local MLflow Stack (Optional)

For offline development, a local MLflow stack is available:

```bash
# Start local MLflow + MinIO
make mlflow-local
# OR: docker-compose --profile mlflow up

# Update .env to use local tracking
# Uncomment these lines in .env:
# MLFLOW_TRACKING_URI=http://localhost:5001
# AWS_ACCESS_KEY_ID=minioadmin
# AWS_SECRET_ACCESS_KEY=minioadmin
# MLFLOW_S3_ENDPOINT_URL=http://localhost:9000

# View local MLflow UI
open http://127.0.0.1:5001
```

**Note:** Local experiments won't sync to DagsHub. For production, always use DagsHub MLflow.

### What Gets Logged

Each training run logs:

**Parameters:**
- `model_type`: baseline_moving_average
- `window_size`: 3
- `buy_threshold_pct`: -10.0
- `sell_threshold_pct`: 15.0

**Metrics:**
- `rmse`: Root Mean Square Error
- `mape`: Mean Absolute Percentage Error
- `dataset_size`: Number of samples
- `coverage_rate`: Percentage of valid predictions
- `buy_rate`, `sell_rate`, `hold_rate`: Signal distribution

**Artifacts:**
- `plots/error_distribution.png`
- `plots/scatter_true_vs_predicted.png`
- `plots/signal_distribution.png`
- `summary/evaluation_summary.txt`

### Comparing Experiments

```bash
# Via MLflow UI
open http://127.0.0.1:5001

# Select multiple runs → Compare
# View metrics side-by-side, plot comparisons, diff parameters
```

---

## Microservices Architecture

PokeWatch uses Docker microservices for isolated, scalable components:

### Services

**1. Collector Service** (`pokewatch-collector`)
- **Purpose**: Fetch daily card prices from Pokémon Price Tracker API
- **Trigger**: Scheduled (cron/manual) or via `make collect`
- **Output**: Raw JSON/Parquet files in `data/raw/`
- **Dockerfile**: `docker/collector.Dockerfile`

```bash
# Run collector
make collect
# OR: docker-compose run --rm collector
```

**2. Training Service** (`pokewatch-training`)
- **Purpose**: Train baseline model and log to DagsHub MLflow
- **Trigger**: Manual via `make train` or `dvc repro train`
- **Output**: Model artifacts in `models/baseline/`, experiments on DagsHub
- **Dockerfile**: `docker/training.Dockerfile`

```bash
# Run training
make train
# OR: docker-compose run --rm training
```

**3. API Service** (`pokewatch-api`)
- **Purpose**: Serve predictions via REST API
- **Trigger**: Long-running service
- **Port**: 8000
- **Dockerfile**: `docker/api.Dockerfile`

```bash
# Start API
make api
# OR: docker-compose up api
```

### Benefits

- **Isolation**: Each service has its own environment and dependencies
- **Scalability**: Services can be scaled independently (e.g., multiple collectors)
- **Reproducibility**: Dockerfile ensures consistent execution
- **Deployment**: Easy migration to Kubernetes (Phase 3)

---

## Integration: Git + DVC + MLflow + Makefile

### Complete Workflow with Makefile

**1. Collect new data**
```bash
# Run collector microservice
make collect

# Check DVC status
make dvc-status
```

**2. Run full pipeline**
```bash
# Collect → Preprocess → Train
make pipeline
```

**3. Push data and models to DagsHub**
```bash
# Push DVC-tracked data/models
make dvc-push
```

**4. View experiments**
```bash
# Open DagsHub experiments page
open https://dagshub.com/beatricedaniel/pokewatch/experiments
```

**5. Commit changes**
```bash
git add dvc.lock config/settings.yaml
git commit -m "exp: Test higher sell threshold (20%)"
git tag exp-v0.2.1
git push origin main --tags
```

**6. View experiment in MLflow**
```bash
open http://127.0.0.1:5001
```

### Linking Versions

Each Git commit is linked to:
- **Code version**: Git SHA
- **Data version**: `dvc.lock` checksums
- **Model version**: MLflow run ID

This ensures full reproducibility:
```bash
# Checkout specific version
git checkout exp-v0.2.1

# Pull corresponding data
dvc pull

# Reproduce exact results
dvc repro
```

---

## Best Practices

### Data Versioning

✅ **DO:**
- Use `dvc push` after every data update
- Commit `dvc.lock` with data changes
- Use meaningful commit messages: `data: Add prices for 2025-11-30`
- Keep data outside Git (use DVC)

❌ **DON'T:**
- Commit raw data files to Git
- Manually edit `.dvc` files
- Skip `dvc push` (data will be missing for others)

### Experiment Tracking

✅ **DO:**
- Use descriptive experiment names: `baseline_tuning`, `threshold_optimization`
- Log all relevant parameters and metrics
- Add tags to important runs
- Document significant findings in run notes

❌ **DON'T:**
- Run experiments without MLflow tracking
- Delete runs from UI (they contain valuable history)
- Forget to start MLflow/MinIO services

### Pipeline Management

✅ **DO:**
- Run `dvc repro` instead of manual commands
- Keep pipeline stages small and focused
- Document stage purposes in `dvc.yaml` comments
- Use `dvc dag` to visualize dependencies

❌ **DON'T:**
- Bypass the pipeline (breaks reproducibility)
- Create circular dependencies
- Hardcode paths (use params from `settings.yaml`)

---

## Troubleshooting

### DVC Issues

**Problem: `dvc push` fails with authentication error**
```bash
# Solution: Re-configure DagsHub credentials
dvc remote modify dagshub --local user beatricedaniel
dvc remote modify dagshub --local password <YOUR_DAGSHUB_TOKEN>
```

**Problem: `dvc pull` downloads nothing**
```bash
# Check remote configuration
dvc remote list

# Verify data exists on DagsHub
# Visit: https://dagshub.com/beatricedaniel/pokewatch/data
```

**Problem: Pipeline stage won't re-run**
```bash
# Force re-run specific stage
dvc repro --force train

# Or clear cache and re-run
dvc remove data/processed.dvc
dvc repro preprocess
```

### MLflow Issues

**Problem: MLflow UI not accessible**
```bash
# Check if MLflow service is running
docker ps | grep mlflow

# Start MLflow if stopped
docker-compose up -d mlflow

# Check logs
docker logs pokewatch-mlflow
```

**Problem: Artifacts not appearing in UI**
```bash
# Ensure MinIO is running
docker ps | grep minio

# Verify MinIO bucket exists
docker exec pokewatch-minio mc ls myminio/mlflow-artifacts

# Check MLflow environment variables
docker exec pokewatch-training env | grep MLFLOW
```

**Problem: Training fails with "Connection refused"**
```bash
# MLflow server may still be starting
# Wait 15-20 seconds for boto3 installation
docker logs pokewatch-mlflow --tail 50
```

### Pipeline Issues

**Problem: `dvc repro` fails on train stage**
```bash
# Ensure Docker services are running
docker-compose ps

# Start required services
docker-compose up -d minio mlflow

# Check training container logs
docker-compose run --rm training python -m pokewatch.models.train_baseline
```

---

## Resources

- **DVC Documentation**: https://dvc.org/doc
- **MLflow Documentation**: https://mlflow.org/docs/latest/
- **DagsHub Guide**: https://dagshub.com/docs
- **Project Repository**: https://github.com/beatricedaniel/pokewatch
- **DagsHub Data**: https://dagshub.com/beatricedaniel/pokewatch

---

## Phase 2 Deliverables ✅

- [x] DVC configured with DagsHub remote
- [x] Data versioned (data/raw, data/processed)
- [x] 3-stage reproducible pipeline (dvc.yaml)
- [x] MLflow tracking with Docker + MinIO
- [x] Git integration (dvc.lock, tags)
- [x] Documentation (this file)

**Next Phase**: Model Registry, CI/CD, Kubernetes deployment
