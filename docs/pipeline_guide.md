# ML Pipeline Guide - PokeWatch

**Version:** 1.0
**Last Updated:** 2025-11-30

This guide covers the automated ML pipeline for PokeWatch, which orchestrates data collection, preprocessing, training, validation, and deployment.

---

## Overview

The PokeWatch ML pipeline automates the complete workflow:
1. **Collect**: Fetch latest card prices from API
2. **Preprocess**: Engineer features from raw data
3. **Train**: Train baseline model
4. **Validate**: Check model quality thresholds
5. **Deploy**: Build BentoML service (if valid)

---

## Quick Start

### Run Complete Pipeline

```bash
# Using Makefile (recommended)
make pipeline-run

# OR manually
python pipelines/ml_pipeline.py
```

### Run Individual Steps

```bash
# Step by step
make collect      # 1. Collect data
make preprocess   # 2. Create features
make train        # 3. Train model
make bento-build  # 4. Build Bento

# OR chain with simple pipeline
make pipeline-simple
```

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   ML Pipeline                           │
│                                                         │
│  ┌──────────┐   ┌───────────┐   ┌───────┐   ┌──────┐ │
│  │ Collect  │──→│Preprocess │──→│ Train │──→│Valid │ │
│  │  Data    │   │ Features  │   │ Model │   │ ate  │ │
│  └──────────┘   └───────────┘   └───────┘   └──────┘ │
│       │              │               │           │     │
│       ↓              ↓               ↓           ↓     │
│  data/raw/    data/processed/  models/      Metrics   │
│                                baseline/               │
│                                                         │
│                           ↓                             │
│                    ┌──────────────┐                    │
│                    │ Build Bento  │                    │
│                    │  (if valid)  │                    │
│                    └──────────────┘                    │
│                           │                             │
│                           ↓                             │
│                   BentoML Service                       │
└─────────────────────────────────────────────────────────┘
```

---

## Pipeline Steps

### Step 1: Data Collection

**Purpose**: Fetch latest card prices from Pokémon Price Tracker API

**Implementation**: `pipelines/steps.py::collect_data_step()`

**What it does**:
- Calls existing collector: `pokewatch.data.collectors.daily_price_collector`
- Saves raw data to `data/raw/`
- Returns path to collected data file

**Output**: `data/raw/YYYYMMDD_HHMMSS.parquet`

**Manual run**:
```bash
python -m pokewatch.data.collectors.daily_price_collector
```

---

### Step 2: Feature Engineering

**Purpose**: Transform raw price history into model features

**Implementation**: `pipelines/steps.py::preprocess_data_step()`

**What it does**:
- Calls existing preprocessor: `pokewatch.data.preprocessing.make_features`
- Computes rolling averages, fair values
- Saves features to `data/processed/`
- Returns path to features file

**Output**: `data/processed/sv2a_pokemon_card_151.parquet`

**Manual run**:
```bash
python -m pokewatch.data.preprocessing.make_features
```

---

### Step 3: Model Training

**Purpose**: Train baseline model on features

**Implementation**: `pipelines/steps.py::train_model_step()`

**What it does**:
- Loads features DataFrame
- Creates `BaselineFairPriceModel` instance
- Calculates evaluation metrics (MAPE, RMSE, coverage)
- Saves model artifacts to `models/baseline/`
- Returns model path and metrics

**Outputs**:
- `models/baseline/sv2a_pokemon_card_151.parquet` (copy of features)
- `models/baseline/model_metadata.json` (metrics, thresholds, timestamp)

**Manual run**:
```bash
make train
```

---

### Step 4: Model Validation

**Purpose**: Verify model meets quality thresholds

**Implementation**: `pipelines/steps.py::validate_model_step()`

**What it does**:
- Checks MAPE ≤ 20%
- Checks coverage ≥ 80%
- Returns boolean (pass/fail)

**Thresholds** (configurable in code):
```python
MAPE_THRESHOLD = 20.0      # Max error percentage
COVERAGE_THRESHOLD = 0.80  # Min prediction coverage
```

**Validation logic**:
```python
is_valid = (
    metrics["mape"] <= 20.0 and
    metrics["coverage_rate"] >= 0.80
)
```

---

### Step 5: Bento Build

**Purpose**: Package model into deployable BentoML service

**Implementation**: `pipelines/steps.py::build_bento_step()`

**What it does**:
- Only runs if model is valid
- Calls `./scripts/build_bento.sh`
- Creates versioned Bento artifact
- Returns Bento tag (e.g., `pokewatch_service:abc123`)

**Output**: Bento registered in BentoML store

**Manual run**:
```bash
./scripts/build_bento.sh
# OR
make bento-build
```

---

## Pipeline Configuration

### Validation Thresholds

Edit `pipelines/steps.py::validate_model_step()`:

```python
# Current thresholds (relaxed for baseline)
MAPE_THRESHOLD = 20.0  # 20% error
COVERAGE_THRESHOLD = 0.80  # 80% coverage

# Production thresholds (stricter)
MAPE_THRESHOLD = 15.0
COVERAGE_THRESHOLD = 0.90
```

### Model Metadata

Saved to `models/baseline/model_metadata.json`:

```json
{
  "model_type": "baseline_moving_average",
  "window_size": 3,
  "trained_at": "2025-11-30T12:34:56",
  "metrics": {
    "rmse": 5.23,
    "mape": 12.45,
    "coverage_rate": 0.95
  },
  "thresholds": {
    "buy_threshold_pct": -10.0,
    "sell_threshold_pct": 15.0
  }
}
```

---

## Running the Pipeline

### Option 1: Complete Pipeline (Recommended)

```bash
# Run all steps in sequence
make pipeline-run

# Expected output:
# [Step 1/5] Collecting data...
# ✓ Data collected: data/raw/20251130_123456.parquet
# [Step 2/5] Preprocessing features...
# ✓ Features created: data/processed/sv2a_pokemon_card_151.parquet
# [Step 3/5] Training model...
# ✓ Model trained: models/baseline/
# [Step 4/5] Validating model...
# ✓ Model validated successfully
# [Step 5/5] Building BentoML service...
# ✓ Bento built: pokewatch_service:abc123
```

### Option 2: Step-by-Step

```bash
# Run each step manually
make collect
make preprocess
make train
make bento-build
```

### Option 3: From Python

```python
from pipelines.ml_pipeline import run_ml_pipeline

# Run pipeline
bento_tag = run_ml_pipeline()

if bento_tag:
    print(f"Success! Bento: {bento_tag}")
else:
    print("Pipeline failed")
```

---

## Pipeline Outputs

### Data Artifacts

```
pokewatch/
├── data/
│   ├── raw/
│   │   └── 20251130_123456.parquet  # Collected prices
│   └── processed/
│       └── sv2a_pokemon_card_151.parquet  # Features
```

### Model Artifacts

```
pokewatch/
├── models/
│   └── baseline/
│       ├── sv2a_pokemon_card_151.parquet  # Model data
│       └── model_metadata.json  # Metrics & metadata
```

### Bento Artifacts

```bash
# List built Bentos
bentoml list

# Output:
# Tag                              Size    Creation Time
# pokewatch_service:abc123        123 MiB  2025-11-30 12:34:56
```

---

## Error Handling

### Validation Failure

If model fails validation, pipeline stops:

```
[Step 4/5] Validating model...
✗ Model invalid: MAPE=25.0 > 20.0 or Coverage=0.75 < 0.80
Pipeline stopped. Model not deployed.
```

**Resolution**:
- Check data quality
- Adjust thresholds in `pipelines/steps.py`
- Retrain with more data

### Missing Data

If data files missing:

```
FileNotFoundError: Processed data not found: data/processed/...
```

**Resolution**:
```bash
# Run prerequisites
make collect
make preprocess
# Then retry
make pipeline-run
```

---

## Scheduling (Future - Phase 3 Week 2)

### Daily Execution

**Using cron:**
```bash
# Add to crontab
0 2 * * * cd /path/to/pokewatch && make pipeline-run >> logs/pipeline.log 2>&1
```

**Using Airflow (Week 2+):**
```python
from airflow import DAG
from airflow.operators.bash import BashOperator

dag = DAG("pokewatch_ml_pipeline", schedule_interval="0 2 * * *")

run_pipeline = BashOperator(
    task_id="run_pipeline",
    bash_command="cd /opt/pokewatch && make pipeline-run",
    dag=dag
)
```

**Using ZenML (Week 2+):**
```python
from zenml.config import Schedule

schedule = Schedule(cron_expression="0 2 * * *")
ml_pipeline.run(schedule=schedule)
```

---

## Monitoring

### Pipeline Logs

```bash
# View logs during execution
tail -f logs/logs.txt

# Check for errors
grep ERROR logs/logs.txt
```

### Pipeline Success Rate

```bash
# Count successful runs
grep "Pipeline completed successfully" logs/logs.txt | wc -l

# Count failures
grep "Pipeline failed" logs/logs.txt | wc -l
```

### Model Performance Tracking

```bash
# View latest metrics
cat models/baseline/model_metadata.json | jq '.metrics'

# Compare with previous
git diff HEAD~1 models/baseline/model_metadata.json
```

---

## Integration with DVC

### Track Pipeline Outputs

```bash
# After pipeline run
dvc status

# Add updated data/models
dvc add data/raw data/processed models/baseline
dvc push

# Commit changes
git add data/raw.dvc data/processed.dvc models/baseline.dvc dvc.lock
git commit -m "pipeline: Daily run $(date +%Y-%m-%d)"
git push
```

### Reproduce Pipeline with DVC

```bash
# Run DVC pipeline (alternative to make pipeline-run)
dvc repro

# This runs collect → preprocess → train stages
# Defined in dvc.yaml
```

---

## Testing

### Run Pipeline Tests

```bash
# Unit tests for individual steps
pytest tests/integration/test_ml_pipeline.py -v

# Test with real data (slow)
pytest tests/integration/test_ml_pipeline.py -v -m slow
```

### Validate Pipeline Output

```bash
# Check model metadata exists
test -f models/baseline/model_metadata.json && echo "✓ Metadata OK"

# Check Bento built
bentoml list | grep pokewatch_service && echo "✓ Bento OK"

# Check data fresh
find data/raw -name "*.parquet" -mtime -1 && echo "✓ Data fresh"
```

---

## Troubleshooting

### Pipeline Hangs

**Problem**: Pipeline appears stuck

**Solution**:
```bash
# Check which step is running
ps aux | grep python

# Kill if needed
pkill -f "pipelines/ml_pipeline.py"

# Check logs
tail -n 50 logs/logs.txt
```

### Bento Build Fails

**Problem**: Step 5 fails with "No Bentos found"

**Solution**:
```bash
# Ensure BentoML installed
pip list | grep bentoml

# Check bentofile.yaml exists
test -f bentofile.yaml && echo "✓ Config OK"

# Try manual build
./scripts/build_bento.sh
```

### Import Errors

**Problem**: "ModuleNotFoundError: No module named 'pipelines'"

**Solution**:
```bash
# Ensure in project root
pwd  # Should be .../pokewatch

# Set PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH

# Retry
python pipelines/ml_pipeline.py
```

---

## Performance

### Pipeline Duration

Typical execution times (local machine):
- **Collect**: ~30 seconds (depends on API)
- **Preprocess**: ~5 seconds
- **Train**: ~10 seconds
- **Validate**: <1 second
- **Build Bento**: ~30 seconds

**Total**: ~1-2 minutes for complete pipeline

### Optimization Tips

1. **Skip unchanged stages**: Use DVC caching
   ```bash
   dvc repro  # Only runs changed stages
   ```

2. **Parallel execution**: Future enhancement
   - Run data collection in background
   - Preprocess while collecting next batch

3. **Incremental training**: Future enhancement
   - Update model with new data only
   - Don't retrain from scratch

---

## Next Steps

- **Week 2**: Add Airflow/ZenML for scheduling
- **Week 2**: Integrate with CI/CD (GitHub Actions)
- **Week 3**: Deploy pipeline to Kubernetes CronJobs
- **Week 4**: Add model validation tests, drift detection

---

## Resources

- **Source Code**: `pipelines/ml_pipeline.py`, `pipelines/steps.py`
- **Tests**: `tests/integration/test_ml_pipeline.py`
- **DVC Pipeline**: `dvc.yaml`
- **Model Training**: `src/pokewatch/models/train_baseline.py`

---

**Status:** ✅ Operational
**Run Command:** `make pipeline-run`
**Duration:** ~1-2 minutes
