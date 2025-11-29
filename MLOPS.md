# MLOps Documentation - MLflow Tracking

This document explains how to use MLflow for experiment tracking in the PokeWatch project.

## Overview

MLflow is used to track:
- Model parameters (model type, thresholds, etc.)
- Evaluation metrics (RMSE, MAPE, coverage rate, signal distribution)
- Model artifacts (serialized models, visualizations, summaries)
- Experiment runs for comparison

## Setup

### 1. Install Dependencies

Using `uv` (recommended):
```bash
uv sync
```

Or manually:
```bash
uv pip install mlflow matplotlib
```

### 2. Configure MLflow Tracking URI

**For Local Development (Recommended)**:
- Don't set `MLFLOW_TRACKING_URI` in `.env`, or comment it out
- The script will automatically use local file tracking (`file://./mlruns`)
- This avoids artifact storage issues when running locally

**For Remote Server**:
- Set `MLFLOW_TRACKING_URI=http://localhost:5001` in `.env`
- **Note**: Remote server requires proper artifact storage (S3/MinIO) for artifacts to work correctly
- For local development, local file tracking is simpler and recommended

### 3. Start MLflow Server

Start the MLflow tracking server using Docker Compose:
```bash
docker-compose up mlflow
```

Or start it directly:
```bash
docker-compose up -d mlflow
```

The MLflow UI will be available at: http://localhost:5001

## Usage

### Running Experiments

#### Method 1: Direct Script Execution

Run the training/evaluation script directly:
```bash
# Using uv
uv run python -m pokewatch.models.train_baseline

# Or with Python (if environment is activated)
python -m pokewatch.models.train_baseline
```

With custom parameters:
```bash
uv run python -m pokewatch.models.train_baseline \
    --data_path data/processed/sv2a_pokemon_card_151.parquet \
    --experiment_name pokewatch_baseline \
    --run_name my_custom_run
```

#### Method 2: MLflow Projects

Run using MLflow Projects for better reproducibility:
```bash
mlflow run . -e train --env-manager local
```

With custom parameters:
```bash
mlflow run . -e train \
    -P data_path=data/processed/sv2a_pokemon_card_151.parquet \
    -P experiment_name=pokewatch_baseline \
    -P run_name=mlflow_project_run \
    --env-manager local
```

### Viewing Results

1. **Access the MLflow UI**: Open http://localhost:5001 in your browser

2. **Navigate to Experiments**:
   - Select the "pokewatch_baseline" experiment
   - View all runs in the experiment

3. **Compare Runs**:
   - Select multiple runs
   - Compare metrics, parameters, and artifacts side-by-side

4. **View Run Details**:
   - Click on a specific run
   - View logged metrics, parameters, and artifacts
   - Download model artifacts and visualizations

### Logged Information

Each run logs:

**Parameters**:
- `model_type`: "baseline_moving_average"
- `window_size`: 3 (rolling window size)
- `buy_threshold_pct`: Buy threshold percentage
- `sell_threshold_pct`: Sell threshold percentage

**Metrics**:
- `rmse`: Root Mean Squared Error
- `mape`: Mean Absolute Percentage Error (%)
- `dataset_size`: Number of samples evaluated
- `coverage_rate`: Percentage of valid predictions
- `buy_rate`: Percentage of BUY signals
- `sell_rate`: Percentage of SELL signals
- `hold_rate`: Percentage of HOLD signals

**Artifacts**:
- `baseline_model/`: Serialized model (MLflow format)
- `plots/error_distribution.png`: Histogram of prediction errors
- `plots/scatter_true_vs_predicted.png`: Scatter plot of true vs predicted prices
- `plots/signal_distribution.png`: Pie chart of signal distribution
- `summary/evaluation_summary.txt`: Text summary of evaluation results

## MLflow Projects

The project includes an `MLproject` file that defines:
- Project name: `pokewatch_baseline`
- Entry point: `train`
- Parameters: `data_path`, `experiment_name`, `run_name`

This allows for reproducible runs using `mlflow run`.

## Model Wrapper

The baseline model is wrapped in `BaselineModelWrapper` (using `mlflow.pyfunc.PythonModel`) to make it compatible with MLflow's model logging and serving capabilities.

The wrapper implements:
- `predict()`: Takes DataFrame with `card_id` and optional `date`, returns predictions

## Troubleshooting

### MLflow Server Not Accessible

1. Check if the server is running:
   ```bash
   docker-compose ps mlflow
   ```

2. Check logs:
   ```bash
   docker-compose logs mlflow
   ```

3. Verify port 5001 is not in use:
   ```bash
   lsof -i :5001
   ```

### No Experiments Visible

1. Ensure `MLFLOW_TRACKING_URI` is set correctly in `.env`
2. Verify the script is connecting to the server (check logs)
3. Check that the experiment name matches in the UI

### Model Loading Issues

1. Ensure processed data exists:
   ```bash
   ls data/processed/*.parquet
   ```

2. Run feature engineering if needed:
   ```bash
   uv run python -m pokewatch.data.preprocessing.make_features
   ```

### Artifact Storage Issues

If you see errors like `[Errno 30] Read-only file system: '/mlruns'`:

1. **Use Local File Tracking (Recommended for Development)**:
   - Comment out or remove `MLFLOW_TRACKING_URI` from `.env`
   - The script will use local file tracking automatically
   - Artifacts will be stored in `./mlruns/` directory

2. **If Using Remote Server**:
   - Ensure the MLflow server is running: `docker-compose up mlflow`
   - For production, configure S3/MinIO for artifact storage
   - See docker-compose.yml for artifact storage configuration

## Best Practices

1. **Use Descriptive Run Names**: Include date, model version, or key parameters
2. **Compare Multiple Runs**: Run experiments with different parameters to compare
3. **Tag Important Runs**: Use MLflow tags to mark production-ready models
4. **Regular Backups**: Backup the `mlruns/` directory and `mlflow.db` for important experiments

## Next Steps

- **Model Registry**: Register production models in MLflow Model Registry
- **Model Serving**: Use MLflow's model serving for production deployments
- **Automated Tracking**: Integrate MLflow tracking into CI/CD pipelines
- **Advanced Metrics**: Add business-specific metrics (BUY/SELL precision/recall)

