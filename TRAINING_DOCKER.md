# Docker-Based Training Guide

## Overview

This guide explains how to run model training inside Docker containers with MLflow experiment tracking and MinIO artifact storage.

## Architecture

The training setup consists of three main services:

1. **MinIO**: S3-compatible object storage for MLflow artifacts (plots, models, etc.)
2. **MLflow Tracking Server**: Experiment tracking with SQLite backend and MinIO artifact storage
3. **Training Container**: Isolated environment for running model training scripts

## Quick Start

### 1. Start MLflow and MinIO Services

```bash
cd pokewatch
docker-compose up -d minio mlflow
```

Wait ~10 seconds for services to initialize.

### 2. Run Training

```bash
# Using the helper script (recommended)
./scripts/train_baseline_docker.sh

# Or directly with docker-compose
docker-compose run --rm training python -m pokewatch.models.train_baseline
```

### 3. View Results

- **MLflow UI**: http://127.0.0.1:5001
- **MinIO Console**: http://127.0.0.1:9001 (login: minioadmin/minioadmin)

## Service Details

### MinIO (Artifact Storage)

- **Ports**: 9000 (API), 9001 (Console)
- **Credentials**: minioadmin / minioadmin
- **Bucket**: `mlflow-artifacts`
- **Data**: Stored in `./minio_data/`

### MLflow Tracking Server

- **Port**: 5001 (mapped to 5000 in container)
- **Backend Store**: SQLite database at `./mlflow_data/mlflow.db`
- **Artifact Root**: `s3://mlflow-artifacts/` (MinIO)
- **UI**: http://127.0.0.1:5001

### Training Service

- **Image**: Built from `docker/training.Dockerfile`
- **Python**: 3.13
- **Dependencies**: Installed via `uv` (pyproject.toml)
- **Environment Variables**:
  - `MLFLOW_TRACKING_URI=http://mlflow:5000`
  - `AWS_ACCESS_KEY_ID=minioadmin`
  - `AWS_SECRET_ACCESS_KEY=minioadmin`
  - `MLFLOW_S3_ENDPOINT_URL=http://minio:9000`
  - `POKEMON_PRICE_API_KEY` (from host `.env`)

## Training Scripts

### train_baseline_docker.sh

Convenience script that:
1. Checks if MLflow is running (starts it if needed)
2. Builds training image if needed
3. Runs training
4. Displays results URL

```bash
./scripts/train_baseline_docker.sh [--data_path PATH] [--experiment_name NAME]
```

### train_baseline_docker_clean.sh

Starts with a fresh MLflow instance:
1. Stops existing MLflow
2. Starts new MLflow
3. Builds training image
4. Runs training

```bash
./scripts/train_baseline_docker_clean.sh
```

## Logged Artifacts

Each training run logs:

1. **Metrics**:
   - RMSE (Root Mean Square Error)
   - MAPE (Mean Absolute Percentage Error)
   - Dataset size
   - Coverage rate
   - Signal distribution (BUY/SELL/HOLD rates)

2. **Parameters**:
   - Model type (baseline_moving_average)
   - Window size (3)
   - Buy/Sell thresholds

3. **Artifacts**:
   - `plots/error_distribution.png`
   - `plots/scatter_true_vs_predicted.png`
   - `plots/signal_distribution.png`
   - `summary/evaluation_summary.txt`

## Troubleshooting

### MLflow Connection Refused

Wait longer for MLflow to start. It needs to install boto3 on first startup (~15-20 seconds).

```bash
docker logs pokewatch-mlflow --tail 50
```

### Artifacts Not Appearing

1. Check MinIO is running:
   ```bash
   docker ps | grep minio
   ```

2. Verify bucket exists:
   ```bash
   docker logs pokewatch-minio-setup
   ```

3. Check MLflow environment variables are set correctly in training container

### Permission Issues

Ensure the following directories are writable:
- `./minio_data/`
- `./mlflow_data/`
- `./mlruns_artifacts/`

## Data Volumes

The training container mounts:

- `./src` → `/app/src` (read-only, source code)
- `./config` → `/app/config` (read-only, configuration)
- `./data/processed` → `/app/data/processed` (read-only, training data)
- `./models` → `/app/models` (read-write, model outputs)
- `./mlruns_artifacts` → `/app/mlruns_artifacts` (read-write, temporary artifacts)
- `./logs` → `/app/logs` (read-write, logs)

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop only MLflow and MinIO (keep API running)
docker-compose stop mlflow minio
```

## Cleaning Up

```bash
# Remove containers and networks
docker-compose down

# Also remove volumes (WARNING: deletes all data)
docker-compose down -v
rm -rf minio_data/ mlflow_data/ mlruns_artifacts/
```

## Integration with CI/CD

The Docker-based training can be integrated into CI/CD pipelines:

```bash
# Example: Run training in CI
docker-compose up -d minio mlflow
sleep 15  # Wait for services
docker-compose run --rm training python -m pokewatch.models.train_baseline
docker-compose down
```

## Next Steps (Phase 2+)

- Add model versioning and registration
- Implement hyperparameter tuning
- Add model comparison visualization
- Set up scheduled training with orchestration (Prefect/Airflow)
- Deploy to Kubernetes
