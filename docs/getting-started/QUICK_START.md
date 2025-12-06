# Quick Start: Verify Week 2 Features

Fast guide to verify all new Week 2 implementations are working.

---

## Option 1: Automated Verification (Fastest)

```bash
cd /Users/beatrice/Documents/data_scientest/projet/pokewatch

# Run complete verification
bash scripts/verify_week2.sh

# Or run quick verification
bash scripts/quick_verify.sh
```

Expected: All checks pass ✓

---

## Option 2: Manual Step-by-Step (5 minutes)

### Setup

```bash
cd /Users/beatrice/Documents/data_scientest/projet/pokewatch
source .venv/bin/activate
```

### 1. Test Security (1 min)

```bash
# Generate API key
python scripts/manage_api_keys.py generate --add

# Run security tests
pytest tests/integration/test_auth.py tests/integration/test_rate_limiting.py -v
```

**Expected**: 55+ tests pass ✓

### 2. Test Performance (1 min)

```bash
# Run performance tests
python scripts/test_performance.py
```

**Expected Output**:
```
Test 1: Cold vs Warm Cache
  Speedup: 50x+ faster ✓

Test 2: Bulk Performance
  p95: < 2ms ✓

Test 3: Cache Hit Rate
  Hit Rate: 70-90% ✓
```

### 3. Test ZenML Pipeline (2 min)

```bash
# Setup ZenML
bash scripts/setup_zenml.sh

# Run pipeline
python -m pipelines.ml_pipeline
```

**Expected**: All 5 steps complete ✓

### 4. Test CI/CD (1 min)

```bash
# Install pre-commit
pre-commit install

# Run hooks
pre-commit run --all-files
```

**Expected**: All hooks pass ✓

---

## Option 3: Test Individual Features

### Security Only

```bash
# Start API
uvicorn src.pokewatch.api.main:app --reload &

# Generate key
API_KEY=$(python scripts/manage_api_keys.py generate --add | grep "pk_" | awk '{print $NF}')

# Test authentication
curl -H "X-API-Key: $API_KEY" http://localhost:8000/health

# Expected: {"status":"healthy",...}

# Test rate limiting (make 65 requests)
for i in {1..65}; do
  curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/health -I | grep "HTTP"
done

# Expected: First 60 succeed (200), then 429 Too Many Requests

# Stop API
killall uvicorn
```

### Performance Only

```bash
python scripts/test_performance.py
```

### ZenML Only

```bash
bash scripts/setup_zenml.sh
python -m pipelines.ml_pipeline
zenml up  # Opens dashboard at http://localhost:8237
```

### CI/CD Only

```bash
pre-commit install
pre-commit run --all-files
```

---

## Quick Health Check

Run these commands to verify everything is in place:

```bash
cd /Users/beatrice/Documents/data_scientest/projet/pokewatch

# 1. Check files exist (should show ~26 files)
ls .github/workflows/*.yml \
   src/pokewatch/api/auth.py \
   src/pokewatch/api/rate_limiter.py \
   scripts/manage_api_keys.py \
   scripts/test_performance.py \
   scripts/setup_zenml.sh \
   pipelines/steps.py \
   docs/ci_cd_guide.md \
   docs/security_guide.md \
   docs/zenml_guide.md

# 2. Check Python imports work
python -c "
from pokewatch.api.auth import APIKeyAuth
from pokewatch.api.rate_limiter import RateLimiter
from pokewatch.api.middleware import setup_middleware
from pipelines.steps import collect_data_step
print('✓ All imports successful')
"

# 3. Check cache implementation
grep -q "get_cache_stats" src/pokewatch/models/baseline.py && echo "✓ Cache implemented"

# 4. Check ZenML decorators
grep -q "@step" pipelines/steps.py && echo "✓ ZenML steps ready"
grep -q "@pipeline" pipelines/ml_pipeline.py && echo "✓ ZenML pipeline ready"
```

If all commands succeed: **Week 2 is fully implemented** ✓

---

## Troubleshooting

### Issue: Tests fail with "ModuleNotFoundError"

```bash
# Reinstall dependencies
python -m uv pip install -e .
```

### Issue: API key tests fail

```bash
# Generate new API key
python scripts/manage_api_keys.py generate --add

# Verify it's in .env
cat .env | grep API_KEYS
```

### Issue: ZenML setup fails

```bash
# Check environment variables
source .env
echo $MLFLOW_TRACKING_URI
echo $DAGSHUB_TOKEN

# Re-run setup
bash scripts/setup_zenml.sh
```

### Issue: Performance tests fail

```bash
# Train model first
python -m pokewatch.models.train_baseline

# Re-run performance tests
python scripts/test_performance.py
```

---

## Success Checklist

Week 2 is verified when:

- [x] **Security**: 55+ tests pass, API authentication works
- [x] **Performance**: Performance tests show 10x+ speedup
- [x] **ZenML**: Pipeline runs successfully end-to-end
- [x] **CI/CD**: Pre-commit hooks run successfully
- [x] **Documentation**: 5 guides exist (2,500+ lines total)

---

## Next Steps

After verification:

1. **Read Documentation**
   - [CI/CD Guide](docs/ci_cd_guide.md) - Workflows and automation
   - [Security Guide](docs/security_guide.md) - API keys and rate limiting
   - [ZenML Guide](docs/zenml_guide.md) - Pipeline orchestration

2. **Schedule Pipeline**
   ```bash
   bash scripts/schedule_pipeline.sh install
   ```

3. **Start Using**
   ```bash
   # Run pipeline manually
   python -m pipelines.ml_pipeline

   # View pipeline dashboard
   zenml up

   # Monitor performance
   python scripts/test_performance.py
   ```

---

## Documentation

- **Detailed Verification**: [VERIFICATION_GUIDE.md](VERIFICATION_GUIDE.md)
- **Week 2 Summary**: [WEEK2_COMPLETE.md](WEEK2_COMPLETE.md)
- **Implementation Report**: [PHASE3_WEEK2_IMPLEMENTATION_REPORT.md](PHASE3_WEEK2_IMPLEMENTATION_REPORT.md)
- **CI/CD Guide**: [docs/ci_cd_guide.md](docs/ci_cd_guide.md)
- **Security Guide**: [docs/security_guide.md](docs/security_guide.md)
- **ZenML Guide**: [docs/zenml_guide.md](docs/zenml_guide.md)

---

**Questions?** Check the detailed verification guide: `VERIFICATION_GUIDE.md`
