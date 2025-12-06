# Migration Guide: Local MLflow → DagsHub MLflow

This guide helps you migrate from the local Docker MLflow stack to DagsHub's cloud MLflow for unified tracking.

## What Changed

### Before (Local Stack)
- MLflow server running in Docker (`pokewatch-mlflow` container)
- MinIO for S3-compatible artifact storage
- Experiments stored locally in `mlflow_data/`
- Access via http://localhost:5001

### After (DagsHub Cloud)
- MLflow hosted on DagsHub cloud
- Experiments stored on DagsHub
- Unified view: data (DVC) + experiments (MLflow) + code (Git)
- Access via https://dagshub.com/beatricedaniel/pokewatch/experiments

## Migration Steps

### 1. Stop Local MLflow Services

```bash
# Stop and remove local MLflow containers
docker-compose down

# Optional: Remove old MLflow data (BACKUP FIRST if needed)
# mkdir -p backups
# mv mlflow_data backups/mlflow_data_$(date +%Y%m%d)
# mv minio_data backups/minio_data_$(date +%Y%m%d)
```

### 2. Update Environment Configuration

Your `.env` file has already been updated with:

```bash
# DagsHub MLflow Integration (Production)
DAGSHUB_TOKEN=487b005332f3fa5a515ecaa48d7b546907407c13
MLFLOW_TRACKING_URI=https://dagshub.com/beatricedaniel/pokewatch.mlflow
MLFLOW_TRACKING_USERNAME=beatricedaniel
```

**Verify:**
```bash
cat .env | grep DAGSHUB
```

### 3. Test DagsHub Connectivity

```bash
# Test DagsHub authentication
curl -H "Authorization: token $DAGSHUB_TOKEN" \
  https://dagshub.com/api/v1/user

# Should return your user info
```

### 4. Run First Training Experiment

```bash
# Build training container with new config
docker-compose build training

# Run training with DagsHub MLflow tracking
make train

# OR:
docker-compose run --rm training python -m pokewatch.models.train_baseline
```

**Expected output:**
```
Using remote MLflow server: https://dagshub.com/beatricedaniel/pokewatch.mlflow
Using experiment: pokewatch_baseline (ID: ...)
```

### 5. Verify Experiment on DagsHub

Open your browser:
```bash
# View experiments
open https://dagshub.com/beatricedaniel/pokewatch/experiments

# View MLflow UI
open https://dagshub.com/beatricedaniel/pokewatch.mlflow
```

You should see:
- ✅ New experiment run
- ✅ Metrics: RMSE, MAPE, coverage_rate, etc.
- ✅ Parameters: buy_threshold_pct, sell_threshold_pct, etc.
- ✅ Artifacts: plots (error distribution, scatter plots, signal distribution)

### 6. Test Full Pipeline

```bash
# Run complete pipeline (collect → preprocess → train)
make pipeline

# Push data and models to DagsHub
make dvc-push
```

### 7. Verify Model Versioning

```bash
# Check models directory
ls -lah models/baseline/

# Should contain:
# - sv2a_pokemon_card_151.parquet (features)
# - model_metadata.json (metadata with MLflow run ID)

# Check DVC status
make dvc-status

# Push models to DagsHub
make dvc-push
```

## Rollback to Local MLflow (If Needed)

If you need to use local MLflow for offline development:

```bash
# 1. Update .env to use local tracking
sed -i.bak 's|^MLFLOW_TRACKING_URI=.*|MLFLOW_TRACKING_URI=http://localhost:5001|' .env

# 2. Uncomment local MLflow variables in .env
# AWS_ACCESS_KEY_ID=minioadmin
# AWS_SECRET_ACCESS_KEY=minioadmin
# MLFLOW_S3_ENDPOINT_URL=http://localhost:9000

# 3. Start local MLflow stack
make mlflow-local

# 4. Run training
make train
```

## Troubleshooting

### Issue: "Authentication failed"

**Problem:** DagsHub token invalid or missing

**Solution:**
```bash
# Check token is set
echo $DAGSHUB_TOKEN

# If empty, update .env
vim .env  # Set DAGSHUB_TOKEN=your_token_here

# Rebuild containers
docker-compose build training
```

### Issue: "Experiments not appearing on DagsHub"

**Problem:** Training might still be using local MLflow

**Solution:**
```bash
# Check training logs
docker-compose run --rm training python -m pokewatch.models.train_baseline

# Look for: "Using remote MLflow server: https://dagshub.com/..."
# If you see "Using local file tracking", check .env

# Verify environment variables in container
docker-compose run --rm training env | grep MLFLOW
```

### Issue: "Artifacts not uploading"

**Problem:** Network issues or authentication

**Solution:**
```bash
# Test network connectivity
curl https://dagshub.com/beatricedaniel/pokewatch.mlflow/api/2.0/mlflow/experiments/list

# Check logs for errors
docker-compose logs training

# Verify DAGSHUB_TOKEN has correct permissions
# Go to: https://dagshub.com/user/settings/tokens
```

### Issue: "Model files not in models/baseline/"

**Problem:** Training script might have failed

**Solution:**
```bash
# Check training logs
docker-compose logs training

# Verify data exists
ls -lah data/processed/

# Run training with verbose logging
docker-compose run --rm training python -m pokewatch.models.train_baseline --help
```

## Verification Checklist

After migration, verify:

- [ ] `.env` contains `DAGSHUB_TOKEN` and DagsHub tracking URI
- [ ] Local MLflow containers stopped (`docker ps` shows no `pokewatch-mlflow`)
- [ ] Training runs successfully with `make train`
- [ ] Experiments visible on https://dagshub.com/beatricedaniel/pokewatch/experiments
- [ ] Metrics logged (RMSE, MAPE, coverage_rate, etc.)
- [ ] Artifacts uploaded (plots visible on DagsHub)
- [ ] Model files saved to `models/baseline/`
- [ ] DVC tracks `models/baseline/` directory
- [ ] `make dvc-push` uploads models to DagsHub
- [ ] Full pipeline works: `make pipeline`

## Benefits of DagsHub MLflow

✅ **Unified Platform**: Data (DVC) + Experiments (MLflow) + Code (Git) in one place
✅ **No Infrastructure**: No need to manage MLflow/MinIO containers
✅ **Team Collaboration**: Share experiments with team members
✅ **Persistent Storage**: Experiments don't disappear when containers restart
✅ **Web Access**: View experiments from anywhere
✅ **Integration**: DVC and MLflow share the same storage backend

## Next Steps

1. **Phase 2 Complete**: You now have unified MLOps with DagsHub
2. **Phase 3**: Add orchestration (Prefect/Airflow) and Kubernetes deployment
3. **Phase 4**: Add monitoring (Prometheus), drift detection, A/B testing

## Support

- DagsHub Docs: https://dagshub.com/docs
- MLflow Docs: https://mlflow.org/docs/latest/index.html
- DVC Docs: https://dvc.org/doc

For issues:
- Check logs: `docker-compose logs training`
- Run `make help` for available commands
- Consult `MLOPS.md` for workflows
