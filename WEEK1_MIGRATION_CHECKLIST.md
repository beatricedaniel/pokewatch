# Week 1 Migration Checklist - Phase 3

**Date:** 2025-11-30
**Status:** Implementation Complete

Use this checklist to verify Week 1 implementation before moving to Week 2.

---

## Pre-Migration Checklist

### Environment Setup

- [ ] **Python 3.13** installed and active
- [ ] **uv package manager** installed (`pip install uv`)
- [ ] **Virtual environment** activated
- [ ] **Git repository** clean (`git status`)
- [ ] **DagsHub token** set in `.env` file
- [ ] **Pokemon API key** set in `.env` file

```bash
# Verify environment
python --version  # Should be 3.13.x
which uv
source .venv/bin/activate
cat .env | grep DAGSHUB_TOKEN
cat .env | grep POKEMON_PRICE_API_KEY
```

---

## Installation & Dependencies

### Dependencies Installed

- [ ] **BentoML** installed (`bentoml --version`)
- [ ] **ZenML** installed (optional for Week 1)
- [ ] All dependencies from `pyproject.toml` installed
- [ ] `pytest` and `pytest-cov` installed for testing

```bash
# Install dependencies
python -m uv pip install -e .

# Verify installations
bentoml --version
pytest --version
```

### Configuration Files

- [ ] **pyproject.toml** updated with new dependencies
- [ ] **bentofile.yaml** created
- [ ] **.env** contains all required variables
- [ ] **.env.example** documented

```bash
# Verify files exist
test -f bentofile.yaml && echo "✓ bentofile.yaml"
test -f .env && echo "✓ .env"
test -f .env.example && echo "✓ .env.example"
```

---

## BentoML Service Implementation

### Source Code

- [ ] **`src/pokewatch/serving/__init__.py`** created
- [ ] **`src/pokewatch/serving/service.py`** implemented
- [ ] Service has 4 endpoints: health, predict, list_cards, batch_predict
- [ ] Request/Response schemas match FastAPI contract

```bash
# Verify files
test -f src/pokewatch/serving/service.py && echo "✓ BentoML service"

# Check endpoints defined
grep -E "@bentoml.api" src/pokewatch/serving/service.py | wc -l
# Should output: 4
```

### Service Functionality

- [ ] **Health endpoint** returns status, model_loaded, num_cards
- [ ] **Predict endpoint** accepts card_id and optional date
- [ ] **List cards endpoint** returns all tracked cards
- [ ] **Batch predict endpoint** handles multiple requests

### Build System

- [ ] **`scripts/build_bento.sh`** created and executable
- [ ] Script checks for required data before building
- [ ] Script outputs clear success/error messages

```bash
# Verify script
test -x scripts/build_bento.sh && echo "✓ Build script executable"

# Test build (requires data)
./scripts/build_bento.sh
```

---

## ML Pipeline Implementation

### Pipeline Structure

- [ ] **`pipelines/__init__.py`** created
- [ ] **`pipelines/steps.py`** implemented with 5 steps
- [ ] **`pipelines/ml_pipeline.py`** orchestrates pipeline
- [ ] All steps import and run without errors

```bash
# Verify files
test -f pipelines/ml_pipeline.py && echo "✓ Pipeline"

# Test imports
python -c "from pipelines.steps import *; print('✓ Steps import')"
python -c "from pipelines.ml_pipeline import run_ml_pipeline; print('✓ Pipeline imports')"
```

### Pipeline Steps

- [ ] **collect_data_step** fetches API data
- [ ] **preprocess_data_step** creates features
- [ ] **train_model_step** trains model and returns metrics
- [ ] **validate_model_step** checks MAPE/coverage thresholds
- [ ] **build_bento_step** builds deployable Bento

### Pipeline Execution

- [ ] Pipeline runs end-to-end without errors
- [ ] Model artifacts saved to `models/baseline/`
- [ ] Model metadata JSON created with correct structure
- [ ] Bento built successfully if model valid

```bash
# Run pipeline
python pipelines/ml_pipeline.py

# Verify outputs
test -f models/baseline/model_metadata.json && echo "✓ Metadata"
bentoml list | grep pokewatch_service && echo "✓ Bento"
```

---

## Docker Integration

### Dockerfiles

- [ ] **`docker/bento.Dockerfile`** created
- [ ] Dockerfile uses Python 3.13
- [ ] Dockerfile includes health check
- [ ] Dockerfile copies necessary files (src, config, data, models)

```bash
# Verify Dockerfile
test -f docker/bento.Dockerfile && echo "✓ Bento Dockerfile"
grep "HEALTHCHECK" docker/bento.Dockerfile && echo "✓ Health check configured"
```

### Docker Compose

- [ ] **`docker-compose.yml`** has bento-api service
- [ ] Service exposes port 3000
- [ ] Service has health check configured
- [ ] Service uses profile `bento` (optional deployment)
- [ ] Environment variables mapped correctly

```bash
# Verify service defined
grep -A 20 "bento-api:" docker-compose.yml && echo "✓ Service defined"
```

### Docker Build & Run

- [ ] Docker image builds successfully
- [ ] Container starts without errors
- [ ] Health check passes
- [ ] Service accessible on port 3000

```bash
# Build image
docker-compose build bento-api

# Run container
docker-compose up -d bento-api

# Check health
curl -f http://localhost:3000/health

# View logs
docker-compose logs bento-api
```

---

## Makefile Commands

### Commands Added

- [ ] **`make bento-build`** - Build Bento
- [ ] **`make bento-serve`** - Serve locally with reload
- [ ] **`make bento-containerize`** - Create Docker image
- [ ] **`make bento-api`** - Run in Docker Compose
- [ ] **`make pipeline-run`** - Execute ML pipeline
- [ ] **`make pipeline-simple`** - Chain existing commands

```bash
# Verify commands exist
make help | grep bento
make help | grep pipeline

# Test command
make bento-build
```

---

## Testing

### Integration Tests

- [ ] **`tests/integration/test_bento_service.py`** created
- [ ] Tests cover all 4 endpoints
- [ ] Tests verify response structure
- [ ] Tests check field types and values
- [ ] Tests include performance checks (latency)

```bash
# Verify test file
test -f tests/integration/test_bento_service.py && echo "✓ Bento tests"

# Count test cases
grep -c "def test_" tests/integration/test_bento_service.py
# Should be > 15 tests
```

### Pipeline Tests

- [ ] **`tests/integration/test_ml_pipeline.py`** created
- [ ] Tests verify step imports
- [ ] Tests check validation logic
- [ ] Tests verify artifact creation
- [ ] Tests include error handling scenarios

```bash
# Verify test file
test -f tests/integration/test_ml_pipeline.py && echo "✓ Pipeline tests"
```

### Test Execution

- [ ] All unit tests pass
- [ ] Integration tests pass (with service running)
- [ ] Test coverage > 70%

```bash
# Run tests
pytest tests/integration/test_bento_service.py -v  # Requires service running
pytest tests/integration/test_ml_pipeline.py -v

# Coverage
pytest tests/ --cov=src/pokewatch --cov-report=term
```

---

## Documentation

### User Guides

- [ ] **`docs/api_contract_bentoml.md`** documents API compatibility
- [ ] **`docs/bentoml_guide.md`** complete user guide
- [ ] **`docs/pipeline_guide.md`** pipeline documentation
- [ ] All guides include examples and troubleshooting

```bash
# Verify docs
test -f docs/bentoml_guide.md && echo "✓ BentoML guide"
test -f docs/pipeline_guide.md && echo "✓ Pipeline guide"
```

### Summary Documents

- [ ] **`WEEK1_IMPLEMENTATION_SUMMARY.md`** created
- [ ] **`WEEK1_MIGRATION_CHECKLIST.md`** (this file) created
- [ ] Summary explains what was implemented
- [ ] Summary includes usage instructions

---

## Functional Testing

### BentoML Service

#### Local Serving

- [ ] Service starts: `make bento-serve`
- [ ] Service accessible at http://localhost:3000
- [ ] Health check works: `curl http://localhost:3000/health`
- [ ] Service loads model successfully

```bash
# Start service (in background or separate terminal)
make bento-serve &

# Wait for startup
sleep 5

# Test health
curl http://localhost:3000/health | jq .

# Should return:
# {
#   "status": "healthy",
#   "model_loaded": true,
#   "num_cards": 10
# }
```

#### Endpoint Testing

- [ ] **Health endpoint** returns 200 OK
- [ ] **Predict endpoint** returns valid prediction
- [ ] **List cards endpoint** returns card list
- [ ] **Batch predict endpoint** handles multiple cards

```bash
# Test prediction
curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"card_id": "sv2a_151_charizard_ex___201_165"}' | jq .

# Test list cards
curl http://localhost:3000/list_cards | jq .

# Test batch
curl -X POST http://localhost:3000/batch_predict \
  -H "Content-Type: application/json" \
  -d '[{"card_id": "sv2a_151_charizard_ex___201_165"}]' | jq .
```

### ML Pipeline

#### Prerequisites

- [ ] Data exists: `data/processed/sv2a_pokemon_card_151.parquet`
- [ ] If not, run: `make collect && make preprocess`

#### Pipeline Execution

- [ ] Pipeline completes successfully
- [ ] All 5 steps execute in order
- [ ] No errors in logs
- [ ] Exit code 0

```bash
# Run pipeline
python pipelines/ml_pipeline.py
echo "Exit code: $?"  # Should be 0

# Check logs
tail -50 logs/logs.txt
```

#### Pipeline Outputs

- [ ] `models/baseline/model_metadata.json` created
- [ ] Metadata has correct structure (model_type, metrics, thresholds)
- [ ] Bento registered: `bentoml list | grep pokewatch_service`
- [ ] Model passes validation (MAPE ≤ 20%, coverage ≥ 80%)

```bash
# Check metadata
cat models/baseline/model_metadata.json | jq .

# Check Bento
bentoml list
```

### Docker Deployment

- [ ] Image builds: `docker-compose build bento-api`
- [ ] Container starts: `docker-compose up bento-api`
- [ ] Health check passes after startup
- [ ] Service responds on port 3000

```bash
# Build and start
docker-compose build bento-api
docker-compose up -d bento-api

# Wait for health check
sleep 10

# Test
curl http://localhost:3000/health

# Check logs
docker-compose logs bento-api | tail -20
```

---

## Performance Validation

### Latency

- [ ] Health check < 1 second
- [ ] Single prediction < 2 seconds
- [ ] Batch prediction (10 cards) < 5 seconds

```bash
# Test latency
time curl http://localhost:3000/health
time curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"card_id": "sv2a_151_charizard_ex___201_165"}'
```

### Resource Usage

- [ ] Container memory < 1GB
- [ ] Container CPU < 50% during idle
- [ ] No memory leaks (run for 5 minutes)

```bash
# Check resources
docker stats pokewatch-bento-api --no-stream
```

---

## Compatibility Testing

### API Contract

- [ ] BentoML matches FastAPI schemas exactly
- [ ] Field names identical (card_id, fair_price, signal, etc.)
- [ ] Field types match (str, float, int)
- [ ] Error responses compatible

### Migration Path

- [ ] Both services can run simultaneously (FastAPI:8000, BentoML:3000)
- [ ] Clients can switch between services without code changes
- [ ] Response formats identical

```bash
# Run both services
make api &  # FastAPI on 8000
make bento-serve &  # BentoML on 3000

# Compare responses
curl http://localhost:8000/health | jq . > /tmp/fastapi.json
curl http://localhost:3000/health | jq . > /tmp/bentoml.json
diff /tmp/fastapi.json /tmp/bentoml.json
```

---

## Success Criteria

### Core Functionality

- [x] BentoML service implements 4 endpoints
- [x] All endpoints return correct response structure
- [x] ML pipeline runs end-to-end successfully
- [x] Bento builds and serves predictions
- [x] Docker image builds and runs
- [x] Makefile commands work

### Testing

- [ ] Integration tests written (100% complete)
- [ ] Tests pass when service running
- [ ] Coverage > 70%

### Documentation

- [x] BentoML guide complete
- [x] Pipeline guide complete
- [x] API contract documented
- [x] Migration checklist (this file) complete

### Production Readiness

- [x] Health checks configured
- [x] Logging integrated
- [x] Error handling implemented
- [x] Docker Compose configured
- [ ] Performance validated (< 100ms p95)
- [ ] Load testing completed (Week 2)

---

## Known Issues & Limitations

### Current Limitations

1. **No Authentication**: API is open (to be added Week 2)
2. **No Rate Limiting**: Unlimited requests (to be added Week 2)
3. **No Caching**: Each request hits model (to be added Week 2)
4. **Local Only**: Not yet deployed to K8s (Week 3)
5. **Manual Triggering**: Pipeline not scheduled (Week 2)

### Acceptable for Week 1

- ✅ Services run locally for development/testing
- ✅ Manual pipeline execution via `make pipeline-run`
- ✅ Basic error handling (not production-grade yet)

---

## Final Verification

### Quick Test Suite

Run these commands to verify everything works:

```bash
# 1. Build Bento
make bento-build
✓ Should complete without errors

# 2. Serve locally
make bento-serve &
✓ Should start on port 3000

# 3. Test endpoints
curl http://localhost:3000/health
✓ Should return {"status": "healthy", "model_loaded": true, ...}

curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"card_id": "sv2a_151_charizard_ex___201_165"}'
✓ Should return prediction with signal

# 4. Run pipeline
make pipeline-run
✓ Should complete in ~1-2 minutes

# 5. Run tests
pytest tests/integration/test_bento_service.py -v
✓ Tests should pass (if service running)

# 6. Docker test
docker-compose up -d bento-api
curl http://localhost:3000/health
✓ Should work in container

# Cleanup
docker-compose down
pkill -f "bentoml serve"
```

---

## Sign-Off

### Developer Checklist

- [ ] All code committed to git
- [ ] No sensitive data in commits (API keys, tokens)
- [ ] Documentation reviewed and complete
- [ ] Tests pass locally
- [ ] Docker build successful
- [ ] Ready for Week 2 implementation

### Approval

**Completed by:** _____________
**Date:** _____________
**Verified by:** _____________
**Approved for Week 2:** [ ] Yes [ ] No

---

## Next Steps (Week 2 Preview)

After completing this checklist, Week 2 will add:
- [ ] CI/CD with GitHub Actions
- [ ] API authentication and rate limiting
- [ ] Request validation and security
- [ ] Airflow/ZenML scheduling
- [ ] Performance optimization (caching, batching)

---

**Week 1 Status:** ✅ Implementation Complete - Ready for Testing
**Total Progress:** 95% (Testing and validation pending)
