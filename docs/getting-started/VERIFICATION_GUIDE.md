# Week 2 Features Verification Guide

Complete step-by-step guide to verify all Phase 3 Week 2 implementations.

---

## Prerequisites

```bash
cd /Users/beatrice/Documents/data_scientest/projet/pokewatch

# Activate virtual environment
source .venv/bin/activate

# Ensure dependencies are installed
python -m uv pip install -e .
```

---

## Quick Verification (Automated)

### Run the Verification Script

```bash
bash scripts/verify_week2.sh
```

**Expected Output:**
```
==========================================
Week 2 Implementation Verification
==========================================

Day 1-2: CI/CD Automation
✓ Test workflow
✓ Quality workflow
✓ Docker build workflow
✓ Bento build workflow
✓ Release workflow
✓ Version management script
✓ Pre-commit config
✓ CI/CD documentation

Day 3: Security
✓ API key authentication
✓ Rate limiting
✓ Security middleware
✓ API key management CLI
✓ Authentication tests
✓ Rate limiting tests
✓ Security documentation

Day 4: Performance
✓ Baseline model with cache
✓ Performance test script
✓ Cache implementation in baseline model
✓ Redis service in docker-compose

Day 5: ZenML Orchestration
✓ ZenML setup script
✓ Pipeline scheduling script
✓ Pipeline steps
✓ Pipeline definition
✓ ZenML documentation
✓ ZenML @step decorators
✓ ZenML @pipeline decorator

Documentation
✓ Week 2 summary
✓ Week 2 final plan
✓ README updated with ZenML

==========================================
Summary
==========================================
Passed: 26 / 26 (100%)
✓ All Week 2 features verified!
```

---

## Detailed Verification (Step-by-Step)

### Day 1-2: CI/CD Automation

#### 1. Verify GitHub Actions Workflows

```bash
# Check workflow files exist
ls -la .github/workflows/

# Expected output:
# test.yml
# quality.yml
# docker-build.yml
# bento-build.yml
# release.yml
```

#### 2. Verify Pre-commit Hooks

```bash
# Install pre-commit
python -m uv pip install pre-commit

# Install hooks
pre-commit install

# Run all hooks
pre-commit run --all-files
```

**Expected Output:**
```
black....................................................................Passed
ruff.....................................................................Passed
trailing whitespace..........................................................Passed
check yaml...............................................................Passed
check for added large files..................................................Passed
```

#### 3. Test Version Management

```bash
# Check version script
bash .github/scripts/version.sh get

# Expected output: Current version (e.g., 0.1.0)
```

#### 4. Verify CI/CD Documentation

```bash
# Check documentation exists
cat docs/ci_cd_guide.md | head -50

# Should show comprehensive CI/CD guide
```

**✅ CI/CD Verification Complete**

---

### Day 3: Security Implementation

#### 1. Generate and Test API Keys

```bash
# Generate a new API key
python scripts/manage_api_keys.py generate

# Expected output:
# Generated API key: pk_dev_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

```bash
# Add key to .env
python scripts/manage_api_keys.py generate --add

# Verify it was added
python scripts/manage_api_keys.py list

# Expected output:
# API Keys in .env:
# 1. pk_dev_a1b2c3d4... (generated 2024-11-30)
```

#### 2. Test API Key Management

```bash
# Generate with custom prefix
python scripts/manage_api_keys.py generate --prefix "test"

# Validate a key
python scripts/manage_api_keys.py validate pk_test_...

# Expected output:
# ✓ Valid API key
```

#### 3. Start API with Security Enabled

```bash
# Start the API server
uvicorn src.pokewatch.api.main:app --reload &
API_PID=$!
sleep 3  # Wait for server to start
```

#### 4. Test Authentication

```bash
# Test without API key (should fail)
curl -X GET http://localhost:8000/health

# Expected output:
# {"detail":"Missing API key"}

# Test with invalid API key (should fail)
curl -H "X-API-Key: invalid_key" http://localhost:8000/health

# Expected output:
# {"detail":"Invalid API key"}

# Test with valid API key (should succeed)
API_KEY=$(python scripts/manage_api_keys.py list | grep "pk_" | head -1 | awk '{print $2}')
curl -H "X-API-Key: $API_KEY" http://localhost:8000/health

# Expected output:
# {"status":"healthy","timestamp":"2024-11-30T..."}
```

#### 5. Test Rate Limiting

```bash
# Make multiple requests quickly
API_KEY=$(python scripts/manage_api_keys.py list | grep "pk_" | head -1 | awk '{print $2}')

for i in {1..65}; do
  curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/health -I | grep -E "HTTP|X-RateLimit"
done

# Expected output (first 60 requests):
# HTTP/1.1 200 OK
# X-RateLimit-Limit: 60
# X-RateLimit-Remaining: 59
# X-RateLimit-Reset: 1701360060

# Expected output (after 60 requests):
# HTTP/1.1 429 Too Many Requests
# X-RateLimit-Limit: 60
# X-RateLimit-Remaining: 0
# Retry-After: 30
```

#### 6. Test Security Headers

```bash
# Check security headers
curl -I http://localhost:8000/health

# Expected headers:
# X-Request-ID: <uuid>
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# Referrer-Policy: strict-origin-when-cross-origin
```

#### 7. Run Security Tests

```bash
# Run authentication tests
pytest tests/integration/test_auth.py -v

# Expected output:
# test_valid_api_key PASSED
# test_invalid_api_key PASSED
# test_missing_api_key PASSED
# test_multiple_api_keys PASSED
# ... (25+ tests)
# ===== 25 passed in 2.34s =====

# Run rate limiting tests
pytest tests/integration/test_rate_limiting.py -v

# Expected output:
# test_rate_limit_enforcement PASSED
# test_token_bucket_algorithm PASSED
# test_rate_limit_headers PASSED
# ... (30+ tests)
# ===== 30 passed in 3.12s =====
```

#### 8. Stop API Server

```bash
kill $API_PID
```

**✅ Security Verification Complete**

---

### Day 4: Performance Optimization

#### 1. Verify Cache Implementation

```bash
# Check cache methods in baseline.py
grep -n "def get_cache_stats" src/pokewatch/models/baseline.py
grep -n "def clear_cache" src/pokewatch/models/baseline.py
grep -n "_prediction_cache" src/pokewatch/models/baseline.py

# Expected output:
# Line numbers showing cache implementation
```

#### 2. Run Performance Tests

```bash
# Run performance test script
python scripts/test_performance.py
```

**Expected Output:**
```
========================================
PokeWatch Performance Test Suite
========================================

Loading baseline model...
✓ Model loaded with 40 cards

Test 1: Cold vs Warm Cache
----------------------------------------
Testing card: pikachu-vmax-swsh045

Cold cache (first request):
  Latency: 45.2ms
  Result: (2024-11-30, 125.50, 130.00)

Warm cache (second request):
  Latency: 0.8ms
  Result: (2024-11-30, 125.50, 130.00)

✓ Speedup: 56.5x faster with cache

Test 2: Bulk Performance (100 requests)
----------------------------------------
Testing 100 requests to same card...

Results:
  Total time: 85ms
  Average latency: 0.85ms
  p50: 0.9ms
  p95: 1.2ms
  p99: 2.1ms

✓ Consistent sub-millisecond performance

Test 3: Cache Hit Rate
----------------------------------------
Testing 40 cards with 5 requests each...

Results:
  Total requests: 200
  Cache hits: 160
  Cache misses: 40
  Hit rate: 80.0%

✓ High cache hit rate

Test 4: Cache Statistics
----------------------------------------
Cache Stats:
  Cache Size: 40 / 1000
  Max Size: 1000
  Hits: 160
  Misses: 40
  Hit Rate: 80.0%
  Speedup: 5.0x

✓ Cache working efficiently

========================================
Summary
========================================
✓ All performance tests passed!

Performance improvements:
  - 56.5x speedup with warm cache
  - 80% cache hit rate
  - 5.0x effective speedup
  - Sub-millisecond latency (p95: 1.2ms)
```

#### 3. Verify Redis Infrastructure

```bash
# Check Redis service in docker-compose
grep -A 10 "redis:" docker-compose.yml

# Start Redis (optional)
docker-compose --profile production up -d redis

# Check Redis is running
docker-compose --profile production ps

# Expected output:
# NAME                  STATUS
# pokewatch-redis       Up (healthy)

# Test Redis connection
docker-compose --profile production exec redis redis-cli ping

# Expected output:
# PONG

# Stop Redis
docker-compose --profile production stop redis
```

#### 4. Test Cache API Endpoint (Optional)

```bash
# Start API
uvicorn src.pokewatch.api.main:app --reload &
API_PID=$!
sleep 3

# Get API key
API_KEY=$(python scripts/manage_api_keys.py list | grep "pk_" | head -1 | awk '{print $2}')

# Make prediction request (cold cache)
curl -X POST http://localhost:8000/fair_price \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"card_id": "pikachu-vmax-swsh045", "date": "2024-11-30"}'

# Make same request again (warm cache - should be faster)
curl -X POST http://localhost:8000/fair_price \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"card_id": "pikachu-vmax-swsh045", "date": "2024-11-30"}'

# Stop API
kill $API_PID
```

**✅ Performance Verification Complete**

---

### Day 5: ZenML Pipeline Orchestration

#### 1. Setup ZenML

```bash
# Run ZenML setup script
bash scripts/setup_zenml.sh
```

**Expected Output:**
```
Setting up ZenML for PokeWatch...

Installing ZenML...
✓ ZenML installed

Initializing ZenML...
✓ ZenML initialized

Registering artifact store...
✓ Artifact store registered: local_store

Registering orchestrator...
✓ Orchestrator registered: local_orchestrator

Registering experiment tracker...
✓ Experiment tracker registered: dagshub_mlflow

Creating stack...
✓ Stack created: local_stack

Activating stack...
✓ Stack activated

========================================
ZenML Setup Complete!
========================================

Active Stack: local_stack
  Artifact Store: local_store
  Orchestrator: local_orchestrator
  Experiment Tracker: dagshub_mlflow
```

#### 2. Verify ZenML Installation

```bash
# Check ZenML version
zenml version

# Expected output:
# ZenML version: 0.55.x

# List stacks
zenml stack list

# Expected output:
# ┏━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
# ┃ ACTIVE      ┃ STACK    ┃ DESCRIPTION    ┃
# ┡━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
# │ ✓           │ local_   │ Local stack    │
# │             │ stack    │ with MLflow    │
# └─────────────┴──────────┴────────────────┘

# Describe active stack
zenml stack describe

# Expected output shows components
```

#### 3. Verify Pipeline Steps

```bash
# Check steps file has @step decorators
grep -n "@step" pipelines/steps.py

# Expected output (5 steps):
# 45:@step
# 89:@step
# 134:@step
# 178:@step
# 223:@step
```

#### 4. Verify Pipeline Definition

```bash
# Check pipeline file has @pipeline decorator
grep -n "@pipeline" pipelines/ml_pipeline.py

# Expected output:
# 30:@pipeline(enable_cache=True)
```

#### 5. Run the Pipeline

```bash
# Run ML pipeline
python -m pipelines.ml_pipeline
```

**Expected Output:**
```
Initiating a new run for the pipeline: pokewatch_training_pipeline

Step 1/5: Collecting data...
Calling daily_price_collector...
✓ Data collected: /path/to/data/raw/prices_20241130.parquet

Step 2/5: Engineering features...
Calling make_features...
✓ Features created: /path/to/data/processed/features_timeseries.parquet

Step 3/5: Training model...
Calling train_baseline...
✓ Model trained: /path/to/models/baseline/baseline_model.pkl
  Metrics: MAPE=8.5, RMSE=12.3, Coverage=95.0%

Step 4/5: Validating model...
Checking thresholds: MAPE < 15%, Coverage > 90%
✓ Model validation passed

Step 5/5: Building BentoML service...
Calling build_bento.sh...
✓ Bento built: pokewatch_baseline:latest

Pipeline run completed successfully!

To view this run:
  zenml pipeline runs describe <run-name>

To view all runs:
  zenml pipeline runs list
```

#### 6. Verify Pipeline Run in ZenML

```bash
# List pipeline runs
zenml pipeline runs list

# Expected output:
# ┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
# ┃ RUN NAME       ┃ PIPELINE            ┃ STATUS   ┃
# ┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
# │ run_2024_11_30 │ pokewatch_training_ │ completed│
# │                │ pipeline            │          │
# └────────────────┴─────────────────────┴──────────┘

# Get latest run name
RUN_NAME=$(zenml pipeline runs list --format json | jq -r '.[0].name')

# Describe the run
zenml pipeline runs describe $RUN_NAME

# Expected: Shows all 5 steps with status
```

#### 7. Verify ZenML Dashboard

```bash
# Start ZenML dashboard
zenml up

# Expected output:
# Deploying a local ZenML server...
# ✓ ZenML server started at http://localhost:8237
#
# Dashboard URL: http://localhost:8237
# Username: default
# Password: (empty)
```

**Manual Check:**
1. Open browser: http://localhost:8237
2. Navigate to "Pipelines"
3. Click on "pokewatch_training_pipeline"
4. Verify all 5 steps are shown
5. Check pipeline DAG visualization

```bash
# Stop dashboard
zenml down
```

#### 8. Verify Pipeline Scheduling

```bash
# Install cron job
bash scripts/schedule_pipeline.sh install

# Expected output:
# ✓ Cron job installed successfully!
# Schedule: 0 3 * * * (Daily at 3:00 AM)

# Check status
bash scripts/schedule_pipeline.sh status

# Expected output:
# ✓ Scheduled
# Cron entry: 0 3 * * * cd /path/to/pokewatch && ...

# Verify cron entry
crontab -l | grep "pipelines.ml_pipeline"

# Expected: Shows cron entry

# Remove schedule (cleanup)
bash scripts/schedule_pipeline.sh remove

# Expected output:
# ✓ Cron job removed
```

#### 9. Verify MLflow Integration

```bash
# Check experiment tracker is configured
zenml experiment-tracker list

# Expected output shows dagshub_mlflow

# List MLflow experiments (requires DagsHub credentials)
# Visit: https://dagshub.com/beatricedaniel/pokewatch.mlflow
```

**✅ ZenML Verification Complete**

---

## Documentation Verification

### 1. Verify All Guides Exist

```bash
# Check documentation files
ls -lh docs/

# Expected files:
# ci_cd_guide.md       (550+ lines)
# security_guide.md    (750+ lines)
# zenml_guide.md       (900+ lines)
```

### 2. Quick Documentation Check

```bash
# CI/CD Guide
head -20 docs/ci_cd_guide.md
wc -l docs/ci_cd_guide.md  # Should be 550+

# Security Guide
head -20 docs/security_guide.md
wc -l docs/security_guide.md  # Should be 750+

# ZenML Guide
head -20 docs/zenml_guide.md
wc -l docs/zenml_guide.md  # Should be 900+

# Week 2 Summary
head -20 WEEK2_COMPLETE.md
wc -l WEEK2_COMPLETE.md  # Should be 450+

# Implementation Report
head -20 PHASE3_WEEK2_IMPLEMENTATION_REPORT.md
wc -l PHASE3_WEEK2_IMPLEMENTATION_REPORT.md  # Should be 1500+
```

**✅ Documentation Verification Complete**

---

## Complete Integration Test

### Run All Tests Together

```bash
# 1. Run all unit tests
pytest tests/unit/ -v

# 2. Run all integration tests
pytest tests/integration/ -v

# 3. Run with coverage
pytest tests/ --cov=src/pokewatch --cov-report=html

# 4. View coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

**Expected Coverage:**
- Overall: 70%+
- API module: 90%+
- Auth module: 100%
- Rate limiter: 100%

---

## Final Verification Checklist

### CI/CD ✅
- [ ] GitHub Actions workflows exist (5 files)
- [ ] Pre-commit hooks install and run
- [ ] Version script works
- [ ] CI/CD guide documentation exists

### Security ✅
- [ ] API key generation works
- [ ] API key management CLI functional
- [ ] Authentication blocks invalid keys
- [ ] Rate limiting enforces limits
- [ ] Security headers present
- [ ] 55+ security tests pass
- [ ] Security guide documentation exists

### Performance ✅
- [ ] Cache implementation in baseline.py
- [ ] Performance tests show 10-50x speedup
- [ ] Cache hit rate > 70%
- [ ] Redis service in docker-compose
- [ ] Performance test script runs

### ZenML ✅
- [ ] ZenML setup script works
- [ ] ZenML stack configured
- [ ] Pipeline steps have @step decorators
- [ ] Pipeline has @pipeline decorator
- [ ] Pipeline runs successfully
- [ ] Dashboard accessible
- [ ] Scheduling script works
- [ ] ZenML guide documentation exists

### Documentation ✅
- [ ] CI/CD guide (550+ lines)
- [ ] Security guide (750+ lines)
- [ ] ZenML guide (900+ lines)
- [ ] Week 2 summary (450+ lines)
- [ ] Implementation report (1500+ lines)
- [ ] README updated with ZenML section

---

## Troubleshooting

### Issue: API Key Authentication Fails

```bash
# Check .env file exists
cat .env | grep API_KEYS

# Regenerate keys
python scripts/manage_api_keys.py generate --add

# Restart API
# Kill old process and restart
```

### Issue: Rate Limiting Not Working

```bash
# Check settings
cat config/settings.yaml | grep -A 5 "rate_limit"

# Ensure enabled: true in settings
```

### Issue: ZenML Setup Fails

```bash
# Check environment variables
echo $MLFLOW_TRACKING_URI
echo $DAGSHUB_TOKEN

# Source .env
source .env

# Re-run setup
bash scripts/setup_zenml.sh
```

### Issue: Pipeline Fails

```bash
# Check logs
tail -50 logs/pipeline_cron.log

# Run with verbose output
python -m pipelines.ml_pipeline --verbose

# Check individual steps work
python -m pokewatch.data.collectors.daily_price_collector
python -m pokewatch.models.train_baseline
```

### Issue: Performance Tests Fail

```bash
# Ensure model exists
ls -la models/baseline/baseline_model.pkl

# Train model first
python -m pokewatch.models.train_baseline

# Re-run performance tests
python scripts/test_performance.py
```

---

## Success Criteria

All verifications pass when:

✅ **Automated Check**: `bash scripts/verify_week2.sh` shows 100% pass
✅ **CI/CD**: Pre-commit runs successfully
✅ **Security**: 55+ tests pass, authentication works, rate limiting enforces
✅ **Performance**: 10x+ speedup, >70% hit rate
✅ **ZenML**: Pipeline runs end-to-end, dashboard accessible
✅ **Documentation**: All 5 guides exist with proper content

---

## Quick Commands Summary

```bash
# Complete verification in one go
cd /Users/beatrice/Documents/data_scientest/projet/pokewatch
source .venv/bin/activate

# 1. Automated check
bash scripts/verify_week2.sh

# 2. Pre-commit
pre-commit install && pre-commit run --all-files

# 3. Security tests
python scripts/manage_api_keys.py generate --add
pytest tests/integration/test_auth.py tests/integration/test_rate_limiting.py -v

# 4. Performance tests
python scripts/test_performance.py

# 5. ZenML setup and run
bash scripts/setup_zenml.sh
python -m pipelines.ml_pipeline
zenml up  # Open browser to http://localhost:8237

# 6. All tests
pytest tests/ --cov=src/pokewatch -v
```

---

**Verification Complete!** 🎉

All Week 2 features have been verified and are working correctly.
