# ZenML Pipeline Guide

**Week 2, Day 5: ZenML Integration**

This guide explains how to use ZenML for ML pipeline orchestration and experiment tracking in PokeWatch.

## Overview

ZenML provides:
- **Pipeline Orchestration**: Automatic step execution with dependency management
- **Experiment Tracking**: Integration with DagsHub MLflow for metrics and artifacts
- **Artifact Management**: Automatic versioning of data, models, and predictions
- **Caching**: Smart caching to skip unchanged steps

## Quick Start

### 1. Setup ZenML (First Time Only)

```bash
cd pokewatch

# Run setup script
bash scripts/setup_zenml.sh

# Verify installation
zenml version
zenml stack list
```

This will:
- Install ZenML
- Initialize local ZenML repository
- Register artifact store (local filesystem)
- Register orchestrator (local)
- Register experiment tracker (DagsHub MLflow)
- Create and activate the `local_stack`

### 2. Run the Pipeline

```bash
# Activate virtual environment
source .venv/bin/activate

# Run pipeline manually
python -m pipelines.ml_pipeline
```

### 3. View Results

**ZenML Dashboard:**
```bash
zenml up
```

Opens web UI at http://localhost:8237 to view:
- Pipeline runs
- Step execution status
- Artifacts produced
- Cached vs executed steps

**MLflow Dashboard (DagsHub):**

Visit: https://dagshub.com/beatricedaniel/pokewatch.mlflow

View:
- Experiment metrics (MAPE, RMSE, coverage)
- Model artifacts
- Parameters
- Run comparisons

## Pipeline Structure

### Pipeline Definition

Located in `pipelines/ml_pipeline.py`:

```python
@pipeline(enable_cache=True)
def pokewatch_training_pipeline():
    """
    Execute the complete ML pipeline with ZenML tracking.
    """
    # Step 1: Collect data
    raw_data_path = collect_data_step()

    # Step 2: Preprocess
    features_path = preprocess_data_step(raw_data_path)

    # Step 3: Train model
    model_path, metrics = train_model_step(features_path)

    # Step 4: Validate
    is_valid = validate_model_step(metrics)

    # Step 5: Build Bento (only if valid)
    bento_tag = build_bento_step(model_path, is_valid)

    return bento_tag
```

### Pipeline Steps

Located in `pipelines/steps.py`:

1. **`collect_data_step()`** - Collect daily prices from API
   - Calls: `pokewatch.data.collectors.daily_price_collector`
   - Output: Path to raw data file

2. **`preprocess_data_step(raw_data_path)`** - Create features
   - Calls: `pokewatch.data.preprocessing.make_features`
   - Input: Raw data path
   - Output: Path to processed features

3. **`train_model_step(features_path)`** - Train baseline model
   - Calls: `pokewatch.models.train_baseline`
   - Input: Features path
   - Output: Model path, metrics dict

4. **`validate_model_step(metrics)`** - Validate quality
   - Checks: MAPE < 15%, Coverage > 90%
   - Input: Metrics dict
   - Output: Boolean (is_valid)

5. **`build_bento_step(model_path, is_valid)`** - Build BentoML service
   - Calls: `scripts/build_bento.sh`
   - Input: Model path, validation flag
   - Output: Bento tag string

## Features

### Automatic Experiment Tracking

All pipeline runs are automatically tracked in DagsHub MLflow:

```python
# Metrics logged automatically
{
    "mape": 8.5,
    "rmse": 12.3,
    "coverage_rate": 0.95,
    "total_cards": 40,
    "date_range_days": 30
}
```

### Smart Caching

ZenML automatically caches step outputs:

```bash
# First run - executes all steps
python -m pipelines.ml_pipeline

# Second run - uses cache if inputs unchanged
python -m pipelines.ml_pipeline
# ✓ Step 1: CACHED (data unchanged)
# ✓ Step 2: CACHED (features unchanged)
# → Step 3: RUNNING (model config changed)
```

### Artifact Versioning

Every step output is versioned:

```
artifacts/
├── raw_data/
│   └── version_1/  # 2024-01-15 run
│   └── version_2/  # 2024-01-16 run
├── features/
│   └── version_1/
├── models/
│   └── version_1/
└── bentos/
    └── version_1/
```

## Scheduling

### Manual Runs

```bash
# Run now
python -m pipelines.ml_pipeline
```

### Cron Scheduling

```bash
# Install daily cron job (3:00 AM)
bash scripts/schedule_pipeline.sh install

# Check status
bash scripts/schedule_pipeline.sh status

# View logs
tail -f logs/pipeline_cron.log

# Remove schedule
bash scripts/schedule_pipeline.sh remove
```

### Docker Scheduling

```bash
# Run pipeline in Docker
docker-compose --profile training up

# With cron inside container
docker-compose --profile training up -d
docker-compose exec training bash scripts/schedule_pipeline.sh install
```

## ZenML Stack Configuration

### Current Stack: `local_stack`

```yaml
Stack Name: local_stack
Components:
  - Artifact Store: local_store (local filesystem)
  - Orchestrator: local_orchestrator (local Python)
  - Experiment Tracker: dagshub_mlflow (MLflow @ DagsHub)
```

View stack details:
```bash
zenml stack describe
```

### Stack Components

**Artifact Store (local_store):**
- Stores step outputs locally
- Location: `~/.config/zenml/local_stores/`
- Use case: Development and small datasets

**Orchestrator (local_orchestrator):**
- Runs steps sequentially in local Python
- Use case: Development and testing
- Upgrade path: Use Airflow/Kubernetes orchestrator for production

**Experiment Tracker (dagshub_mlflow):**
- Tracks experiments in DagsHub MLflow
- URI: https://dagshub.com/beatricedaniel/pokewatch.mlflow
- Use case: All environments (dev + prod)

## Common Commands

### Pipeline Management

```bash
# Run pipeline
python -m pipelines.ml_pipeline

# List all runs
zenml pipeline runs list

# Describe specific run
zenml pipeline runs describe RUN_NAME
```

### Stack Management

```bash
# List stacks
zenml stack list

# Describe current stack
zenml stack describe

# Switch stack
zenml stack set STACK_NAME

# Register new stack
zenml stack register NEW_STACK -a ARTIFACT_STORE -o ORCHESTRATOR
```

### Artifact Management

```bash
# List artifacts
zenml artifact list

# Describe artifact
zenml artifact describe ARTIFACT_NAME

# Version artifact
zenml artifact version list ARTIFACT_NAME
```

### Dashboard

```bash
# Start ZenML dashboard
zenml up

# Stop dashboard
zenml down

# Dashboard runs on: http://localhost:8237
```

## Troubleshooting

### Pipeline Fails to Start

**Error:** `zenml.exceptions.StackComponentNotFound`

**Solution:**
```bash
# Re-run setup
bash scripts/setup_zenml.sh

# Verify stack
zenml stack list
```

### MLflow Connection Issues

**Error:** `mlflow.exceptions.RestException: API request failed`

**Solution:**
```bash
# Check environment variables
echo $DAGSHUB_TOKEN
echo $MLFLOW_TRACKING_URI

# Re-export from .env
source .env
export MLFLOW_TRACKING_PASSWORD=$DAGSHUB_TOKEN
```

### Cache Not Working

**Error:** Steps always re-execute even when unchanged

**Solution:**
```bash
# Clear cache and re-run
zenml clean

# Verify caching enabled
# Check @pipeline(enable_cache=True) in ml_pipeline.py
```

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'zenml'`

**Solution:**
```bash
# Reinstall ZenML
python -m uv pip install "zenml[server]>=0.55.0"

# Verify installation
python -c "import zenml; print(zenml.__version__)"
```

## Best Practices

### 1. Keep Steps Small

Each step should do one thing:
- ✓ Good: `collect_data_step()`, `train_model_step()`
- ✗ Bad: `do_everything_step()`

### 2. Use Type Hints

ZenML uses type hints for artifact management:
```python
@step
def train_model_step(features_path: str) -> Tuple[str, dict]:
    ...
```

### 3. Return Serializable Objects

Steps should return objects that can be saved:
- ✓ Good: strings, dicts, ints, floats, paths
- ✗ Bad: database connections, file handles

### 4. Handle Errors Gracefully

```python
@step
def collect_data_step() -> str:
    try:
        # Collect data
        ...
    except Exception as e:
        logger.error(f"Data collection failed: {e}")
        raise  # Let ZenML handle the failure
```

### 5. Use Logging

```python
@step
def train_model_step(features_path: str) -> Tuple[str, dict]:
    logger.info(f"Training model with features: {features_path}")
    # ... training code ...
    logger.info(f"Model trained with MAPE: {metrics['mape']:.2f}")
```

## Integration with Existing Code

ZenML is designed to work with existing code:

```python
# Before (existing code)
def collect_data():
    # Your existing logic
    ...

# After (ZenML step)
@step
def collect_data_step() -> str:
    # Call existing code via subprocess
    subprocess.run(["python", "-m", "pokewatch.data.collectors.daily_price_collector"])
    return str(data_path)
```

**No refactoring required!** The `@step` decorator wraps existing code without changes.

## Upgrading to Production

When ready to scale, upgrade components:

### Artifact Store
```bash
# Register S3 artifact store
zenml artifact-store register s3_store \
    --flavor=s3 \
    --path=s3://pokewatch-artifacts

# Update stack
zenml stack update -a s3_store
```

### Orchestrator
```bash
# Register Airflow orchestrator
zenml orchestrator register airflow_orchestrator \
    --flavor=airflow \
    --airflow_home=/path/to/airflow

# Update stack
zenml stack update -o airflow_orchestrator
```

### Step Operator (Optional)
```bash
# Register Kubernetes step operator
zenml step-operator register k8s_operator \
    --flavor=kubernetes \
    --kubernetes_context=production

# Update stack
zenml stack update --step-operator k8s_operator
```

## Resources

- **ZenML Documentation**: https://docs.zenml.io
- **DagsHub MLflow**: https://dagshub.com/beatricedaniel/pokewatch.mlflow
- **PokeWatch Pipeline Code**: `pipelines/ml_pipeline.py`
- **PokeWatch Steps Code**: `pipelines/steps.py`
- **Setup Script**: `scripts/setup_zenml.sh`
- **Schedule Script**: `scripts/schedule_pipeline.sh`

## Summary

ZenML provides professional ML pipeline orchestration with:
- ✅ Automatic experiment tracking (MLflow)
- ✅ Smart caching for efficiency
- ✅ Artifact versioning
- ✅ Easy integration with existing code
- ✅ Scalable to production (Airflow, Kubernetes)

**Week 2, Day 5 Complete!** 🎉
