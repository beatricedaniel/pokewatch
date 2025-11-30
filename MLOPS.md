# MLOps Documentation - PokeWatch

## Overview

PokeWatch implements a complete MLOps stack for managing the machine learning lifecycle, from data versioning to model deployment and monitoring.

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Data Versioning** | DVC + DagsHub | Track and version datasets |
| **Experiment Tracking** | MLflow (Docker) | Log metrics, parameters, and artifacts |
| **Artifact Storage** | MinIO (S3-compatible) | Store MLflow artifacts (plots, models) |
| **Pipeline Orchestration** | DVC Pipelines | Reproducible ML workflows |
| **Model Registry** | MLflow Registry | Manage model versions and stages |
| **Containerization** | Docker + docker-compose | Isolated execution environments |
| **Version Control** | Git + GitHub | Code and pipeline versioning |

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

```
Docker Container (training)
       │
       ├─→ MLflow Server (port 5001)
       │        │
       │        ├─→ SQLite (metrics/params)
       │        └─→ MinIO (artifacts: plots, models)
       │
       └─→ Artifacts logged via HTTP
```

### Running Experiments

**Docker-based training (recommended):**
```bash
# Using helper script
./scripts/train_baseline_docker.sh

# Or directly
docker-compose run --rm training python -m pokewatch.models.train_baseline

# With custom parameters
docker-compose run --rm training python -m pokewatch.models.train_baseline \
  --experiment_name my_experiment \
  --run_name my_run
```

**View results:**
- **MLflow UI**: http://127.0.0.1:5001
- **MinIO Console**: http://127.0.0.1:9001 (login: minioadmin/minioadmin)

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

## Integration: Git + DVC + MLflow

### Complete Workflow

**1. Modify code/config**
```bash
# Edit threshold in config/settings.yaml
vim config/settings.yaml
```

**2. Collect new data (optional)**
```bash
dvc repro collect
```

**3. Re-run pipeline**
```bash
dvc repro
```

**4. Push data to DagsHub**
```bash
dvc push
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
