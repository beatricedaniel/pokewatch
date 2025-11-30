# PokeWatch - Quick Reference Card

## 🚀 Common Commands

```bash
# DATA COLLECTION
make collect              # Collect latest card prices
make dvc-status          # Check data changes
make dvc-push            # Upload data to DagsHub

# TRAINING
make train               # Train model (logs to DagsHub MLflow)
make pipeline            # Run full pipeline (collect → preprocess → train)

# API
make api                 # Start API server (port 8000)
make api-dev             # Start with hot-reload

# TESTING
make test                # Run all tests
make test-unit           # Unit tests only

# UTILITIES
make help                # Show all commands
make clean               # Clean temp files
make docker-build        # Rebuild all images
```

## 📊 View Results

**DagsHub (Primary):**
- Experiments: https://dagshub.com/beatricedaniel/pokewatch/experiments
- Data: https://dagshub.com/beatricedaniel/pokewatch/data
- MLflow UI: https://dagshub.com/beatricedaniel/pokewatch.mlflow

**Local API:**
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (API keys, DagsHub token) |
| `config/settings.yaml` | Model thresholds, paths |
| `config/cards.yaml` | Tracked cards list |
| `dvc.yaml` | Pipeline definition |

## 🐳 Docker Services

| Service | Command | Purpose |
|---------|---------|---------|
| **collector** | `make collect` | Fetch card prices |
| **training** | `make train` | Train models |
| **api** | `make api` | Serve predictions |
| **mlflow** (optional) | `make mlflow-local` | Local MLflow for offline dev |

## 📝 Typical Workflows

### Daily Data Collection
```bash
make collect             # Fetch latest prices
make dvc-push           # Upload to DagsHub
git add dvc.lock
git commit -m "data: Update daily prices"
git push
```

### Experiment with New Threshold
```bash
# 1. Edit config
vim config/settings.yaml  # Change buy_threshold_pct

# 2. Train model
make train

# 3. View on DagsHub
open https://dagshub.com/beatricedaniel/pokewatch/experiments

# 4. If good, commit config
git add config/settings.yaml
git commit -m "exp: Test buy threshold -15%"
git push
```

### Full Pipeline Run
```bash
make pipeline            # Collect → Preprocess → Train
make dvc-push           # Upload data + models
git add dvc.lock
git commit -m "pipeline: Full run with updated data"
git push
```

### Deploy API
```bash
make api                 # Start API server
# OR for production:
docker-compose up -d api  # Detached mode
```

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Authentication failed" | Check `DAGSHUB_TOKEN` in `.env` |
| "Experiments not on DagsHub" | Verify `MLFLOW_TRACKING_URI` in `.env` |
| "Data not found" | Run `make dvc-pull` to download data |
| "API key invalid" | Update `POKEMON_PRICE_API_KEY` in `.env` |
| "Docker build fails" | Run `make docker-clean && make docker-build` |

## 📚 Documentation

- **Getting Started**: `MLOPS.md` → Quick Start Guide
- **Migration**: `MIGRATION_GUIDE.md`
- **API Usage**: `API_USAGE.md`
- **Docker**: `DOCKER.md`
- **This Summary**: `PHASE2_STEP3_SUMMARY.md`

## 🎯 Quick Health Check

```bash
# 1. Check environment
cat .env | grep DAGSHUB_TOKEN  # Should show token

# 2. Check Docker
docker ps                      # See running containers

# 3. Check DVC
make dvc-status               # See data status

# 4. Test API
curl http://localhost:8000/health  # If API running

# 5. Check latest experiment
open https://dagshub.com/beatricedaniel/pokewatch/experiments
```

## 🔐 Environment Variables

**Required:**
```bash
POKEMON_PRICE_API_KEY=your_api_key_here
DAGSHUB_TOKEN=your_dagshub_token_here
```

**DagsHub MLflow (auto-set):**
```bash
MLFLOW_TRACKING_URI=https://dagshub.com/beatricedaniel/pokewatch.mlflow
MLFLOW_TRACKING_USERNAME=beatricedaniel
```

**Optional (for local development):**
```bash
ENV=dev                        # dev, test, prod, training
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR
```

## 🎨 Project Structure

```
pokewatch/
├── config/              # Configuration files
│   ├── settings.yaml    # Model config
│   └── cards.yaml       # Tracked cards
├── data/                # Data (DVC-tracked)
│   ├── raw/            # API responses
│   └── processed/      # Features
├── models/              # Models (DVC-tracked)
│   └── baseline/       # Baseline model artifacts
├── docker/              # Docker configurations
│   ├── api.Dockerfile
│   ├── collector.Dockerfile
│   └── training.Dockerfile
├── src/pokewatch/       # Source code
│   ├── api/            # FastAPI application
│   ├── data/           # Data collection/processing
│   ├── models/         # Model training
│   └── core/           # Business logic
├── tests/               # Test suite
├── scripts/             # Utility scripts
├── Makefile            # Command orchestration
└── dvc.yaml            # DVC pipeline definition
```

## 💡 Tips

1. **Always use `make` commands** - they handle environment setup and error checking
2. **Check DagsHub after training** - experiments appear immediately
3. **Use `make dvc-status` before `make dvc-push`** - see what will be uploaded
4. **For offline work** - use `make mlflow-local` to start local MLflow
5. **Git commit DVC files** - always commit `dvc.lock` and `.dvc` files
6. **Check logs** - `docker-compose logs training` for troubleshooting

## 🚨 Emergency Commands

```bash
# Stop all containers
docker-compose down

# Clean everything
make clean
make docker-clean

# Reset to fresh state
git pull
make dvc-pull
make setup

# Force rebuild
docker-compose build --no-cache training
```

---

**Need help?** Run `make help` or check `MLOPS.md`
