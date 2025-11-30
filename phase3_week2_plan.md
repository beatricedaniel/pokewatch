# Phase 3 - Week 2 Development Plan

**Duration**: 5 days
**Focus**: CI/CD, Security, Performance Optimization, and Automation
**Prerequisites**: Week 1 completion (BentoML service, ML pipeline, Docker integration, tests)

---

## Overview

Week 2 builds on the Week 1 foundation by adding production-grade capabilities:
- Automated CI/CD pipelines with GitHub Actions
- API security (authentication, rate limiting)
- Performance optimization (caching, batch processing)
- Scheduling automation (Airflow or ZenML)
- Enhanced monitoring and logging

---

## Day 1: GitHub Actions CI/CD - Part 1 (Testing & Quality)

### Objectives
- Set up automated testing workflow
- Add code quality checks (linting, type checking)
- Create coverage reporting
- Set up branch protection rules

### Tasks

#### 1. Create CI/CD Directory Structure
```bash
mkdir -p .github/workflows
mkdir -p .github/scripts
```

#### 2. Testing Workflow (`test.yml`)
Create `.github/workflows/test.yml`:
- Trigger on push to main, pull requests
- Matrix testing: Python 3.13
- Steps:
  - Checkout code
  - Set up Python with caching
  - Install dependencies with uv
  - Run unit tests with pytest
  - Run integration tests
  - Generate coverage report
  - Upload coverage to Codecov (optional)

#### 3. Code Quality Workflow (`quality.yml`)
Create `.github/workflows/quality.yml`:
- Run ruff for linting
- Run black for formatting checks
- Run mypy for type checking
- Fail if any quality check fails

#### 4. Pre-commit Hooks
Create `.pre-commit-config.yaml`:
- Local hooks for black, ruff, mypy
- Ensure code quality before commits

#### 5. GitHub Branch Protection
Document in `docs/ci_cd_guide.md`:
- Require passing CI before merge
- Require at least 1 review
- Require linear history

### Deliverables
- [ ] `.github/workflows/test.yml` - Automated testing workflow
- [ ] `.github/workflows/quality.yml` - Code quality checks
- [ ] `.pre-commit-config.yaml` - Pre-commit hooks
- [ ] `docs/ci_cd_guide.md` - CI/CD setup documentation

### Success Criteria
- ✅ Tests run automatically on every push
- ✅ Code quality checks pass
- ✅ Coverage report generated (target: >80%)
- ✅ Pre-commit hooks prevent bad commits

---

## Day 2: GitHub Actions CI/CD - Part 2 (Build & Deploy)

### Objectives
- Automate Docker image builds
- Set up container registry integration
- Create deployment workflow for Kubernetes
- Implement semantic versioning

### Tasks

#### 1. Docker Build Workflow (`docker-build.yml`)
Create `.github/workflows/docker-build.yml`:
- Trigger on push to main, tags
- Build both FastAPI and BentoML images
- Tag with git SHA and semantic version
- Push to GitHub Container Registry (ghcr.io)
- Cache Docker layers for faster builds
- Multi-platform builds (amd64, arm64)

#### 2. BentoML Build Workflow (`bento-build.yml`)
Create `.github/workflows/bento-build.yml`:
- Build BentoML service on version tags
- Run bento validation tests
- Push to BentoML Cloud or container registry
- Store Bento metadata as artifact

#### 3. Release Workflow (`release.yml`)
Create `.github/workflows/release.yml`:
- Trigger on semantic version tags (v1.0.0, v1.0.1)
- Build all Docker images
- Run full test suite
- Create GitHub release with changelog
- Deploy to staging environment
- Notification on success/failure

#### 4. Versioning Script
Create `.github/scripts/version.sh`:
- Auto-generate semantic versions
- Update version in pyproject.toml
- Create git tags automatically

#### 5. Container Registry Setup
- Configure GitHub Container Registry (ghcr.io)
- Set up image retention policies
- Document registry authentication

### Deliverables
- [ ] `.github/workflows/docker-build.yml` - Docker build automation
- [ ] `.github/workflows/bento-build.yml` - BentoML build automation
- [ ] `.github/workflows/release.yml` - Release automation
- [ ] `.github/scripts/version.sh` - Versioning script
- [ ] `docs/deployment_guide.md` - Deployment documentation

### Success Criteria
- ✅ Docker images built automatically on push
- ✅ Images tagged with version and SHA
- ✅ Images pushed to container registry
- ✅ Release process fully automated

---

## Day 3: API Security & Authentication

### Objectives
- Implement API key authentication
- Add rate limiting per client
- Set up request/response logging
- Create security middleware
- Add CORS configuration

### Tasks

#### 1. Authentication System
Create `src/pokewatch/api/auth.py`:
```python
class APIKeyAuth:
    """API key authentication middleware"""
    def __init__(self, api_keys: list[str]):
        self.api_keys = set(api_keys)

    async def __call__(self, request: Request):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key not in self.api_keys:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return api_key
```

Add to both FastAPI and BentoML services:
- Header-based API key authentication
- Support for multiple API keys
- Key rotation mechanism
- Environment variable configuration

#### 2. Rate Limiting
Create `src/pokewatch/api/rate_limiter.py`:
```python
class RateLimiter:
    """Token bucket rate limiter per API key"""
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.buckets: Dict[str, TokenBucket] = {}

    async def check_rate_limit(self, api_key: str) -> bool:
        # Returns True if allowed, False if rate limited
```

Features:
- Per-API-key rate limiting
- Token bucket algorithm
- Configurable limits (requests/minute)
- Redis backend for distributed rate limiting
- Return rate limit headers (X-RateLimit-Remaining, X-RateLimit-Reset)

#### 3. Security Middleware
Create `src/pokewatch/api/middleware.py`:
- Request ID generation (X-Request-ID)
- Request/response logging with timestamps
- Security headers (X-Content-Type-Options, X-Frame-Options)
- Request size limits
- IP-based blocking (optional)

#### 4. CORS Configuration
Update `src/pokewatch/api/main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://pokewatch.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)
```

#### 5. API Key Management
Create `scripts/manage_api_keys.py`:
- Generate new API keys
- List active keys
- Revoke keys
- Store keys in .env or secret manager

#### 6. Update Configuration
Update `config/settings.yaml`:
```yaml
api:
  auth:
    enabled: true
    require_api_key: true
  rate_limit:
    enabled: true
    requests_per_minute: 60
    burst_size: 10
  security:
    cors_enabled: true
    allowed_origins:
      - https://pokewatch.example.com
```

### Deliverables
- [ ] `src/pokewatch/api/auth.py` - Authentication system
- [ ] `src/pokewatch/api/rate_limiter.py` - Rate limiting implementation
- [ ] `src/pokewatch/api/middleware.py` - Security middleware
- [ ] `scripts/manage_api_keys.py` - API key management tool
- [ ] `tests/integration/test_auth.py` - Authentication tests
- [ ] `tests/integration/test_rate_limiting.py` - Rate limiting tests
- [ ] `docs/security_guide.md` - Security documentation

### Success Criteria
- ✅ All endpoints require valid API key
- ✅ Rate limiting prevents abuse (429 responses)
- ✅ Request/response logging works
- ✅ CORS configured correctly
- ✅ Security headers present

---

## Day 4: Performance Optimization & Caching

### Objectives
- Implement Redis caching for predictions
- Add batch prediction optimization
- Set up connection pooling
- Optimize model loading
- Add performance monitoring

### Tasks

#### 1. Redis Integration
Create `src/pokewatch/cache/__init__.py`:
- Redis client setup with connection pooling
- Cache key generation strategy
- TTL configuration (time-to-live)

Create `src/pokewatch/cache/redis_cache.py`:
```python
class PredictionCache:
    """Redis cache for fair price predictions"""

    async def get(self, card_id: str, date: str) -> Optional[dict]:
        """Get cached prediction"""
        key = f"prediction:{card_id}:{date}"
        return await redis.get(key)

    async def set(self, card_id: str, date: str, prediction: dict, ttl: int = 3600):
        """Cache prediction with TTL"""
        key = f"prediction:{card_id}:{date}"
        await redis.setex(key, ttl, json.dumps(prediction))

    async def invalidate(self, card_id: str):
        """Invalidate all predictions for a card"""
        pattern = f"prediction:{card_id}:*"
        await redis.delete_pattern(pattern)
```

#### 2. Update API Endpoints with Caching
Update `src/pokewatch/api/main.py`:
```python
@app.post("/fair_price")
async def fair_price(request: FairPriceRequest, cache: PredictionCache = Depends()):
    # Check cache first
    cached = await cache.get(request.card_id, str(request.date))
    if cached:
        return FairPriceResponse(**cached)

    # Compute prediction
    result = model.predict(...)

    # Cache result
    await cache.set(request.card_id, str(request.date), result.dict())
    return result
```

Update BentoML service similarly.

#### 3. Batch Prediction Optimization
Create `src/pokewatch/models/batch_predictor.py`:
```python
class BatchPredictor:
    """Optimized batch prediction with caching"""

    async def predict_batch(self, requests: List[PredictionRequest]) -> List[dict]:
        # 1. Check cache for all requests
        # 2. Compute only cache misses
        # 3. Batch compute for efficiency
        # 4. Cache all new results
        # 5. Return combined results
```

Benefits:
- Reduce redundant computations
- Vectorized operations with numpy/pandas
- Parallel processing for independent predictions

#### 4. Model Loading Optimization
Update `src/pokewatch/models/baseline.py`:
```python
class BaselineModel:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, model_dir: str):
        """Singleton pattern for model loading"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls.load(model_dir)
        return cls._instance
```

Features:
- Lazy loading (load on first request)
- Singleton pattern (load once, reuse)
- Warm-up endpoint to preload model

#### 5. Connection Pooling
Update database/API clients:
- HTTP client with connection pooling (httpx.AsyncClient)
- Redis connection pool
- Reuse connections across requests

#### 6. Docker Compose with Redis
Update `docker-compose.yml`:
```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  api:
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379

volumes:
  redis_data:
```

#### 7. Performance Monitoring
Create `src/pokewatch/monitoring/performance.py`:
- Track cache hit rate (Prometheus metrics)
- Track prediction latency (p50, p95, p99)
- Track batch size distribution
- Alert on cache misses > 50%

### Deliverables
- [ ] `src/pokewatch/cache/redis_cache.py` - Redis caching implementation
- [ ] `src/pokewatch/models/batch_predictor.py` - Batch prediction optimizer
- [ ] Updated `src/pokewatch/api/main.py` - Caching in FastAPI
- [ ] Updated `src/pokewatch/serving/service.py` - Caching in BentoML
- [ ] Updated `docker-compose.yml` - Redis service
- [ ] `tests/integration/test_caching.py` - Cache functionality tests
- [ ] `tests/performance/test_benchmarks.py` - Performance benchmarks
- [ ] `docs/performance_guide.md` - Performance optimization guide

### Success Criteria
- ✅ Cache hit rate > 70% for repeated requests
- ✅ Prediction latency reduced by 50%+ (for cached)
- ✅ Batch predictions 3x faster than individual
- ✅ Model loads once and reuses
- ✅ Redis connection pooling works

---

## Day 5: Scheduling & Automation with ZenML

### Objectives
- Set up ZenML server (local or cloud)
- Convert simple pipeline to full ZenML pipeline
- Add pipeline scheduling
- Implement pipeline monitoring
- Create automated retraining workflow

### Tasks

#### 1. ZenML Server Setup
Create `scripts/setup_zenml.sh`:
```bash
#!/bin/bash
# Install ZenML with server
pip install "zenml[server]>=0.55.0"

# Initialize ZenML
zenml init

# Start local ZenML server
zenml up

# Or connect to cloud ZenML
# zenml connect --url https://your-zenml-server.com
```

Configure stack:
```bash
# Register local artifact store
zenml artifact-store register local_store --flavor=local

# Register MLflow experiment tracker (DagsHub)
zenml experiment-tracker register dagshub_mlflow \
  --flavor=mlflow \
  --tracking_uri=$MLFLOW_TRACKING_URI \
  --tracking_username=$MLFLOW_TRACKING_USERNAME \
  --tracking_password=$DAGSHUB_TOKEN

# Register container registry
zenml container-registry register local_registry \
  --flavor=default \
  --uri=localhost:5000

# Create and set stack
zenml stack register local_stack \
  -a local_store \
  -e dagshub_mlflow \
  -c local_registry

zenml stack set local_stack
```

#### 2. Convert Pipeline to ZenML
Update `pipelines/steps.py`:
```python
from zenml import step
from zenml.config import ResourceSettings

@step(enable_cache=True, settings={"resources": ResourceSettings(cpu_count=2, memory="4GB")})
def collect_data_step() -> str:
    """Collect daily card prices from API"""
    logger.info("Starting data collection...")
    # Existing logic
    return str(raw_data_path)

@step(enable_cache=True)
def preprocess_data_step(raw_data_path: str) -> str:
    """Preprocess raw data into features"""
    # Existing logic
    return str(features_path)

@step(enable_cache=False)  # Always retrain
def train_model_step(features_path: str) -> Tuple[str, dict]:
    """Train baseline model"""
    # Existing logic
    return str(model_path), metrics

@step
def validate_model_step(metrics: dict) -> bool:
    """Validate model quality"""
    # Existing logic
    return is_valid

@step(enable_cache=False)
def build_bento_step(model_path: str, is_valid: bool) -> str:
    """Build BentoML service"""
    # Existing logic
    return bento_tag
```

Update `pipelines/ml_pipeline.py`:
```python
from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(
    parent_image="python:3.13-slim",
    requirements=["pandas>=2.0.0", "numpy>=1.24.0", "pydantic>=2.0.0"],
    environment={"MLFLOW_TRACKING_URI": os.getenv("MLFLOW_TRACKING_URI")}
)

@pipeline(enable_cache=True, settings={"docker": docker_settings})
def ml_training_pipeline():
    """ZenML ML training pipeline"""
    raw_data = collect_data_step()
    features = preprocess_data_step(raw_data)
    model_path, metrics = train_model_step(features)
    is_valid = validate_model_step(metrics)
    bento_tag = build_bento_step(model_path, is_valid)
    return bento_tag

if __name__ == "__main__":
    ml_training_pipeline()
```

#### 3. Pipeline Scheduling
Create `pipelines/schedules.py`:
```python
from zenml.config.schedule import Schedule
from pipelines.ml_pipeline import ml_training_pipeline

# Daily retraining schedule (3 AM UTC)
daily_schedule = Schedule(
    name="daily_retraining",
    cron_expression="0 3 * * *",  # 3 AM daily
    catchup=False
)

# Run pipeline with schedule
ml_training_pipeline = ml_training_pipeline.with_options(
    schedule=daily_schedule
)
```

#### 4. Pipeline Monitoring
Create `pipelines/monitoring.py`:
```python
from zenml import get_step_context

def log_step_metrics():
    """Log step-level metrics to MLflow"""
    context = get_step_context()

    # Log step duration
    duration = context.step_run.end_time - context.step_run.start_time
    mlflow.log_metric(f"{context.step_run.name}_duration_seconds", duration.total_seconds())

    # Log step status
    mlflow.log_param(f"{context.step_run.name}_status", context.step_run.status)
```

Add to each step in `steps.py`:
```python
@step
def collect_data_step() -> str:
    start_time = time.time()
    # ... existing logic ...
    duration = time.time() - start_time
    mlflow.log_metric("collect_duration_seconds", duration)
    return raw_data_path
```

#### 5. Automated Retraining Workflow
Create `pipelines/auto_retrain.py`:
```python
from zenml import pipeline
from zenml.integrations.mlflow.steps import mlflow_model_deployer_step

@pipeline
def continuous_training_pipeline():
    """Automated retraining with deployment"""
    # Step 1: Collect latest data
    raw_data = collect_data_step()

    # Step 2: Preprocess
    features = preprocess_data_step(raw_data)

    # Step 3: Train new model
    model_path, metrics = train_model_step(features)

    # Step 4: Validate against production model
    is_better = compare_models_step(metrics)

    # Step 5: Deploy if better
    if is_better:
        bento_tag = build_bento_step(model_path, is_valid=True)
        deploy_to_kubernetes_step(bento_tag)

    return metrics
```

#### 6. ZenML Dashboard & Visualization
- Access ZenML UI at http://localhost:8237
- View pipeline runs, artifacts, metadata
- Compare pipeline runs
- Inspect step outputs
- Monitor pipeline health

### Deliverables
- [ ] `scripts/setup_zenml.sh` - ZenML setup script
- [ ] Updated `pipelines/steps.py` - ZenML step decorators
- [ ] Updated `pipelines/ml_pipeline.py` - ZenML pipeline
- [ ] `pipelines/schedules.py` - Pipeline scheduling configuration
- [ ] `pipelines/monitoring.py` - Pipeline monitoring utilities
- [ ] `pipelines/auto_retrain.py` - Automated retraining workflow
- [ ] `docs/zenml_guide.md` - ZenML setup and usage guide
- [ ] `tests/integration/test_zenml_pipeline.py` - ZenML pipeline tests

### Success Criteria
- ✅ ZenML server running and accessible
- ✅ Pipeline runs successfully with ZenML decorators
- ✅ Daily schedule configured (runs at 3 AM)
- ✅ Pipeline metrics logged to MLflow
- ✅ Artifacts tracked in ZenML
- ✅ Automated retraining workflow functional

---

## Week 2 Summary

### Total Deliverables: 30+ files

**CI/CD (6 files)**:
- `.github/workflows/test.yml`
- `.github/workflows/quality.yml`
- `.github/workflows/docker-build.yml`
- `.github/workflows/bento-build.yml`
- `.github/workflows/release.yml`
- `.github/scripts/version.sh`

**Security (5 files)**:
- `src/pokewatch/api/auth.py`
- `src/pokewatch/api/rate_limiter.py`
- `src/pokewatch/api/middleware.py`
- `scripts/manage_api_keys.py`
- Updated `config/settings.yaml`

**Performance (4 files)**:
- `src/pokewatch/cache/redis_cache.py`
- `src/pokewatch/models/batch_predictor.py`
- `src/pokewatch/monitoring/performance.py`
- Updated `docker-compose.yml`

**Automation (6 files)**:
- `scripts/setup_zenml.sh`
- Updated `pipelines/steps.py`
- Updated `pipelines/ml_pipeline.py`
- `pipelines/schedules.py`
- `pipelines/monitoring.py`
- `pipelines/auto_retrain.py`

**Tests (6 files)**:
- `tests/integration/test_auth.py`
- `tests/integration/test_rate_limiting.py`
- `tests/integration/test_caching.py`
- `tests/performance/test_benchmarks.py`
- `tests/integration/test_zenml_pipeline.py`
- `.pre-commit-config.yaml`

**Documentation (5 files)**:
- `docs/ci_cd_guide.md`
- `docs/deployment_guide.md`
- `docs/security_guide.md`
- `docs/performance_guide.md`
- `docs/zenml_guide.md`

### Key Metrics & Targets

**CI/CD**:
- ✅ 100% automated testing on every push
- ✅ Code coverage > 80%
- ✅ Docker builds < 5 minutes
- ✅ Zero manual deployment steps

**Security**:
- ✅ 100% authenticated requests
- ✅ Rate limiting: 60 req/min per key
- ✅ Request logging for audit trail
- ✅ Security headers on all responses

**Performance**:
- ✅ Cache hit rate > 70%
- ✅ Cached prediction latency < 50ms
- ✅ Batch predictions 3x faster
- ✅ Model load time < 2 seconds

**Automation**:
- ✅ Daily automated retraining at 3 AM
- ✅ Pipeline runs tracked in ZenML
- ✅ Experiments logged to MLflow
- ✅ Automatic deployment on validation

---

## Integration with Week 1

Week 2 builds directly on Week 1's foundation:

| Week 1 Component | Week 2 Enhancement |
|------------------|-------------------|
| BentoML Service | + API auth, rate limiting, caching |
| ML Pipeline | + ZenML decorators, scheduling, monitoring |
| Docker Setup | + Redis, automated builds, multi-platform |
| Integration Tests | + Auth tests, performance tests, CI/CD |
| Documentation | + Security guide, CI/CD guide, ZenML guide |

---

## Migration Strategy

### Parallel Operation Period
- Week 2 Day 1-2: CI/CD setup (non-breaking)
- Week 2 Day 3: Security layer (requires API key migration)
- Week 2 Day 4: Performance layer (transparent to clients)
- Week 2 Day 5: Automation layer (backend only)

### Breaking Changes
Only Day 3 (Security) introduces breaking changes:
- All clients must provide `X-API-Key` header
- Migration plan:
  1. Deploy with `auth.required: false` (warning only)
  2. Notify clients to add API keys (1 week notice)
  3. Enable `auth.required: true`

---

## Testing Strategy

### Day 1-2: CI/CD Testing
```bash
# Trigger workflows
git push origin main
git tag v1.1.0
git push origin v1.1.0

# Verify in GitHub Actions UI
# - test.yml passes
# - quality.yml passes
# - docker-build.yml creates images
# - release.yml creates release
```

### Day 3: Security Testing
```bash
# Test authentication
curl -H "X-API-Key: test_key_123" http://localhost:8000/fair_price

# Test rate limiting
for i in {1..100}; do curl -H "X-API-Key: test_key_123" http://localhost:8000/health; done

# Should see 429 after 60 requests
```

### Day 4: Performance Testing
```bash
# Test cache hit rate
python tests/performance/test_benchmarks.py

# Expected: >70% cache hit rate after warmup
```

### Day 5: Pipeline Testing
```bash
# Run ZenML pipeline
python pipelines/ml_pipeline.py

# Verify in ZenML UI: http://localhost:8237
```

---

## Troubleshooting

### Common Issues

**CI/CD Failures**:
- Check GitHub Actions logs
- Verify secrets configured (GHCR_TOKEN, DOCKERHUB_TOKEN)
- Ensure tests pass locally first

**Authentication Issues**:
- Verify API keys in .env
- Check header name matches (X-API-Key)
- Ensure key loaded in auth middleware

**Rate Limiting False Positives**:
- Check Redis connectivity
- Verify rate limit configuration
- Inspect rate limiter logs

**Cache Misses**:
- Check Redis connectivity
- Verify cache key generation
- Inspect cache TTL settings

**ZenML Pipeline Failures**:
- Check ZenML server status: `zenml status`
- Verify stack configuration: `zenml stack describe`
- Check step logs in ZenML UI

---

## Next Steps (Week 3 Preview)

Week 3 will focus on:
- **Kubernetes deployment** (manifests, HPA, ingress)
- **Prometheus + Grafana monitoring** (custom metrics, dashboards)
- **Advanced ZenML** (custom materializers, step operators)
- **A/B testing infrastructure** (baseline vs. new model comparison)
- **Alerting** (PagerDuty/Slack integration for pipeline failures)

---

## Appendix: Configuration Files

### `.env` Additions for Week 2
```bash
# Week 2: Security
API_KEYS=key1_abc123,key2_def456,key3_ghi789
RATE_LIMIT_ENABLED=true
RATE_LIMIT_RPM=60

# Week 2: Caching
REDIS_URL=redis://localhost:6379
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600

# Week 2: ZenML
ZENML_SERVER_URL=http://localhost:8237
ZENML_STACK_NAME=local_stack

# Week 2: CI/CD
GITHUB_TOKEN=ghp_your_token_here
DOCKER_REGISTRY=ghcr.io/your-username
```

### `config/settings.yaml` Additions
```yaml
# Week 2: API Security
api:
  auth:
    enabled: true
    require_api_key: true
  rate_limit:
    enabled: true
    requests_per_minute: 60
    burst_size: 10
  security:
    cors_enabled: true
    allowed_origins:
      - https://pokewatch.example.com

# Week 2: Caching
cache:
  enabled: true
  backend: redis
  redis_url: ${REDIS_URL}
  ttl_seconds: 3600

# Week 2: Performance
performance:
  batch_size: 50
  model_preload: true
  connection_pool_size: 10

# Week 2: Pipeline Scheduling
pipeline:
  schedule:
    enabled: true
    cron: "0 3 * * *"  # 3 AM daily
  orchestrator: zenml
  retry_on_failure: true
  max_retries: 3
```

---

**End of Week 2 Plan**
