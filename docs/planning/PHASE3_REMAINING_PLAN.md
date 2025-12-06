# Phase 3 Remaining Plan - Simplified for MLOps Learning

**Context:** Educational MLOps project for Data Scientest course
**Goal:** Demonstrate key MLOps concepts while keeping implementation simple
**Status:** Week 1-2 complete (BentoML, CI/CD, Security, ZenML) | Week 3-4 remaining

---

## What's Done ✅ (Week 1-2)

- ✅ **BentoML**: Production model serving
- ✅ **ZenML**: ML pipeline orchestration with MLflow tracking
- ✅ **CI/CD**: 5 GitHub Actions workflows (test, quality, docker, bento, release)
- ✅ **Security**: API key auth, rate limiting, OWASP headers
- ✅ **Performance**: Caching (10-50x speedup)
- ✅ **Docker**: Containerized services (API, collector, training)
- ✅ **Documentation**: 5,500+ lines of comprehensive guides

---

## What's Remaining ⏳ (Week 3-4)

From [phase3.md](phase3.md) success criteria:

| Criteria | Status | Need |
|----------|--------|------|
| Orchestration (daily pipeline) | ✅ Done | - |
| CI/CD automation | ✅ Done | - |
| API performance (<100ms) | ✅ Done | - |
| Security (auth + rate limit) | ✅ Done | - |
| **Kubernetes deployment** | ❌ Missing | **Simple K8s** |
| **Monitoring dashboards** | ❌ Missing | **Basic metrics** |
| Documentation | ✅ Done | Final runbook |
| **Reliability testing** | ❌ Missing | **Simple tests** |

**Focus:** Kubernetes + Monitoring (simplified for learning)

---

## Simplified Week 3-4 Plan

### Key Principles for MLOps Course Project

1. **Keep it simple** - Focus on concepts, not complexity
2. **Local first** - Use Minikube, not cloud (free + easy)
3. **Essential only** - Skip advanced features (SSL, multi-region, etc.)
4. **Learning focused** - Demonstrate MLOps patterns, not production scale
5. **Time-boxed** - 2 weeks max, realistic for course timeline

---

## Week 3: Kubernetes Basics (Simplified)

**Goal:** Deploy PokeWatch to local Kubernetes (Minikube) to demonstrate container orchestration

**Time:** 2-3 days (not full week)

### Day 1: Minikube Setup & Basic Deployment (3-4 hours)

**Learning Objectives:**
- Understand Kubernetes concepts (Pods, Deployments, Services)
- Deploy containerized application to K8s
- Use kubectl to manage applications

**Tasks:**

#### Task 1: Install Minikube & kubectl (30 min)
```bash
# Install Minikube (local Kubernetes)
brew install minikube kubectl

# Start Minikube
minikube start --driver=docker

# Verify
kubectl cluster-info
kubectl get nodes
```

#### Task 2: Create Simple K8s Manifests (1.5 hours)

**Keep it minimal** - Just 3 files to start:

**File 1:** `k8s/namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: pokewatch
```

**File 2:** `k8s/api-deployment.yaml` (simplified)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pokewatch-api
  namespace: pokewatch
spec:
  replicas: 2  # Simple scaling
  selector:
    matchLabels:
      app: pokewatch-api
  template:
    metadata:
      labels:
        app: pokewatch-api
    spec:
      containers:
      - name: api
        image: pokewatch-api:latest  # Use local image
        imagePullPolicy: Never  # Don't pull from registry
        ports:
        - containerPort: 8000
        env:
        - name: API_KEYS
          value: "pk_dev_test123"  # Simple for demo
```

**File 3:** `k8s/api-service.yaml` (simplified)
```yaml
apiVersion: v1
kind: Service
metadata:
  name: pokewatch-api
  namespace: pokewatch
spec:
  type: NodePort  # Simple external access
  selector:
    app: pokewatch-api
  ports:
  - port: 8000
    targetPort: 8000
    nodePort: 30080  # Access at localhost:30080
```

**That's it!** No ConfigMaps, Secrets, Ingress, HPA for now - keep it simple.

#### Task 3: Deploy to Minikube (1 hour)

```bash
# Build Docker image for Minikube
eval $(minikube docker-env)  # Use Minikube's Docker
docker build -f docker/api.Dockerfile -t pokewatch-api:latest .

# Deploy to Kubernetes
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml

# Verify deployment
kubectl get pods -n pokewatch
kubectl get services -n pokewatch

# Test API
minikube service pokewatch-api -n pokewatch --url
# Use URL to test: curl <url>/health
```

#### Task 4: Create Deployment Script (30 min)

**File:** `scripts/deploy_k8s.sh`
```bash
#!/bin/bash
set -e

echo "Building Docker image for Minikube..."
eval $(minikube docker-env)
docker build -f docker/api.Dockerfile -t pokewatch-api:latest .

echo "Deploying to Kubernetes..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml

echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=pokewatch-api -n pokewatch --timeout=60s

echo "✓ Deployment complete!"
echo ""
echo "Get service URL:"
echo "  minikube service pokewatch-api -n pokewatch --url"
```

**Deliverables (Day 1):**
- ✅ Minikube running locally
- ✅ 3 simple K8s manifests (namespace, deployment, service)
- ✅ API running in Kubernetes (2 replicas)
- ✅ Deployment script
- ✅ Basic kubectl commands learned

**Learning Demonstrated:**
- ✅ Container orchestration basics
- ✅ Kubernetes deployment workflow
- ✅ Service discovery and load balancing

---

### Day 2: Basic Monitoring (Simplified) (3-4 hours)

**Goal:** Add simple metrics to demonstrate observability (not full Prometheus/Grafana stack)

**Learning Objectives:**
- Understand application metrics
- Expose health/readiness endpoints
- Basic logging practices

**Tasks:**

#### Task 1: Add Health Endpoints (1 hour)

Update `src/pokewatch/api/main.py`:

```python
from datetime import datetime

# Simple health tracking
start_time = datetime.now()
request_count = 0

@app.get("/health")
async def health():
    """Basic health check"""
    global request_count
    request_count += 1

    return {
        "status": "healthy",
        "uptime_seconds": (datetime.now() - start_time).total_seconds(),
        "requests_served": request_count,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
async def metrics():
    """Simple metrics endpoint (Prometheus-compatible format)"""
    uptime = (datetime.now() - start_time).total_seconds()

    # Simple Prometheus format
    return f"""# HELP pokewatch_uptime_seconds Application uptime
# TYPE pokewatch_uptime_seconds gauge
pokewatch_uptime_seconds {uptime}

# HELP pokewatch_requests_total Total requests served
# TYPE pokewatch_requests_total counter
pokewatch_requests_total {request_count}
"""
```

#### Task 2: Add Kubernetes Health Probes (30 min)

Update `k8s/api-deployment.yaml`:

```yaml
spec:
  containers:
  - name: api
    # ... existing config ...

    # Liveness probe (is app alive?)
    livenessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 10

    # Readiness probe (is app ready for traffic?)
    readinessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 5
```

#### Task 3: Simple Logging (1 hour)

Add structured logging:

```python
# src/pokewatch/api/main.py
import logging
from pythonjsonlogger import jsonlogger

# Configure JSON logging (K8s friendly)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

@app.post("/fair_price")
async def fair_price(...):
    logger.info("prediction_request", extra={
        "card_id": payload.card_id,
        "endpoint": "fair_price"
    })

    # ... prediction logic ...

    logger.info("prediction_complete", extra={
        "card_id": payload.card_id,
        "signal": result["signal"],
        "latency_ms": latency
    })
```

#### Task 4: View Logs in Kubernetes (30 min)

```bash
# View logs from all pods
kubectl logs -l app=pokewatch-api -n pokewatch --tail=50

# Follow logs in real-time
kubectl logs -l app=pokewatch-api -n pokewatch -f

# View logs from specific pod
kubectl logs <pod-name> -n pokewatch
```

#### Task 5: Simple Monitoring Script (1 hour)

**File:** `scripts/monitor_k8s.sh`
```bash
#!/bin/bash

echo "PokeWatch Kubernetes Monitoring"
echo "================================"
echo ""

# Pod status
echo "Pods:"
kubectl get pods -n pokewatch

echo ""
echo "Services:"
kubectl get services -n pokewatch

echo ""
echo "Recent logs (last 20 lines):"
kubectl logs -l app=pokewatch-api -n pokewatch --tail=20

echo ""
echo "Metrics from API:"
URL=$(minikube service pokewatch-api -n pokewatch --url)
curl -s "$URL/metrics"
```

**Deliverables (Day 2):**
- ✅ Health and metrics endpoints
- ✅ Kubernetes health probes
- ✅ JSON logging
- ✅ Log viewing with kubectl
- ✅ Simple monitoring script

**Learning Demonstrated:**
- ✅ Application observability
- ✅ Health checks and probes
- ✅ Structured logging
- ✅ Basic metrics exposure

---

### Day 3: Documentation & Testing (2-3 hours)

**Goal:** Document K8s setup and verify it works

**Tasks:**

#### Task 1: Create Kubernetes Guide (1.5 hours)

**File:** `docs/kubernetes_guide.md`

```markdown
# Kubernetes Deployment Guide (Simplified)

## Prerequisites
- Docker installed
- Minikube installed
- kubectl installed

## Quick Start

1. Start Minikube:
   ```bash
   minikube start
   ```

2. Deploy PokeWatch:
   ```bash
   bash scripts/deploy_k8s.sh
   ```

3. Access API:
   ```bash
   minikube service pokewatch-api -n pokewatch --url
   ```

## Common Commands

- View pods: `kubectl get pods -n pokewatch`
- View logs: `kubectl logs -l app=pokewatch-api -n pokewatch`
- Delete deployment: `kubectl delete namespace pokewatch`

## Monitoring

- Health: `curl <url>/health`
- Metrics: `curl <url>/metrics`
- Logs: `bash scripts/monitor_k8s.sh`
```

#### Task 2: Create Verification Script (1 hour)

**File:** `scripts/verify_k8s.sh`
```bash
#!/bin/bash
set -e

echo "Verifying Kubernetes deployment..."

# Check Minikube running
minikube status || { echo "✗ Minikube not running"; exit 1; }
echo "✓ Minikube running"

# Check namespace
kubectl get namespace pokewatch || { echo "✗ Namespace not found"; exit 1; }
echo "✓ Namespace exists"

# Check pods
POD_COUNT=$(kubectl get pods -n pokewatch -o json | jq '.items | length')
if [ "$POD_COUNT" -lt 1 ]; then
    echo "✗ No pods running"
    exit 1
fi
echo "✓ $POD_COUNT pods running"

# Check service
kubectl get service pokewatch-api -n pokewatch || { echo "✗ Service not found"; exit 1; }
echo "✓ Service exists"

# Test API
URL=$(minikube service pokewatch-api -n pokewatch --url)
HEALTH=$(curl -s "$URL/health" | jq -r '.status')
if [ "$HEALTH" = "healthy" ]; then
    echo "✓ API is healthy"
else
    echo "✗ API not healthy"
    exit 1
fi

echo ""
echo "✅ All Kubernetes checks passed!"
```

**Deliverables (Day 3):**
- ✅ Kubernetes guide documentation
- ✅ Verification script
- ✅ All features tested and working

---

## Week 4: Final Integration & Documentation (Simplified)

**Goal:** Polish the project and create final documentation

**Time:** 2-3 days (not full week)

### Day 1: Simple Load Testing (2-3 hours)

**Goal:** Demonstrate the system can handle basic load

#### Task 1: Create Simple Load Test Script (1.5 hours)

**File:** `tests/load/simple_load_test.py`
```python
#!/usr/bin/env python3
"""Simple load test for PokeWatch API"""

import time
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor

API_URL = "http://localhost:30080"  # Minikube NodePort
API_KEY = "pk_dev_test123"

def make_request():
    """Single API request"""
    start = time.time()
    try:
        response = requests.post(
            f"{API_URL}/fair_price",
            json={"card_id": "pikachu-vmax-swsh045"},
            headers={"X-API-Key": API_KEY},
            timeout=5
        )
        latency = (time.time() - start) * 1000  # ms
        return {
            "success": response.status_code == 200,
            "latency": latency
        }
    except Exception as e:
        return {"success": False, "latency": None}

def run_load_test(num_requests=100, concurrency=10):
    """Run simple load test"""
    print(f"Running load test: {num_requests} requests, {concurrency} concurrent")
    print("-" * 60)

    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request) for _ in range(num_requests)]
        for future in futures:
            results.append(future.result())

    # Calculate stats
    successes = [r for r in results if r["success"]]
    latencies = [r["latency"] for r in successes if r["latency"]]

    print(f"\nResults:")
    print(f"  Total requests: {num_requests}")
    print(f"  Successful: {len(successes)} ({len(successes)/num_requests*100:.1f}%)")
    print(f"  Failed: {num_requests - len(successes)}")

    if latencies:
        print(f"\nLatency:")
        print(f"  Mean: {statistics.mean(latencies):.1f}ms")
        print(f"  Median: {statistics.median(latencies):.1f}ms")
        print(f"  p95: {sorted(latencies)[int(len(latencies)*0.95)]:.1f}ms")
        print(f"  p99: {sorted(latencies)[int(len(latencies)*0.99)]:.1f}ms")

    print("\n✓ Load test complete")

if __name__ == "__main__":
    run_load_test()
```

#### Task 2: Run Load Test (30 min)

```bash
# Install requests if needed
python -m uv pip install requests

# Run test
python tests/load/simple_load_test.py
```

**Expected output:**
```
Running load test: 100 requests, 10 concurrent
------------------------------------------------------------

Results:
  Total requests: 100
  Successful: 98 (98.0%)
  Failed: 2

Latency:
  Mean: 45.2ms
  Median: 42.1ms
  p95: 78.5ms
  p99: 95.3ms

✓ Load test complete
```

#### Task 3: Test Kubernetes Scaling (30 min)

```bash
# Scale up pods
kubectl scale deployment pokewatch-api -n pokewatch --replicas=3

# Run load test again
python tests/load/simple_load_test.py

# Scale down
kubectl scale deployment pokewatch-api -n pokewatch --replicas=2
```

**Deliverables (Day 1):**
- ✅ Simple load test script
- ✅ Performance baseline documented
- ✅ Scaling tested

**Learning Demonstrated:**
- ✅ Performance testing basics
- ✅ Kubernetes scaling
- ✅ Load balancing verification

---

### Day 2: Final Documentation (3-4 hours)

**Goal:** Create complete project documentation

#### Task 1: Operations Runbook (2 hours)

**File:** `RUNBOOK.md`
```markdown
# PokeWatch Operations Runbook

## Quick Start

1. Start local environment:
   ```bash
   minikube start
   bash scripts/deploy_k8s.sh
   ```

2. Verify deployment:
   ```bash
   bash scripts/verify_k8s.sh
   ```

3. Access API:
   ```bash
   minikube service pokewatch-api -n pokewatch
   ```

## Daily Operations

### Run ML Pipeline
```bash
python -m pipelines.ml_pipeline
```

### View Logs
```bash
kubectl logs -l app=pokewatch-api -n pokewatch -f
```

### Check Health
```bash
kubectl get pods -n pokewatch
```

## Troubleshooting

### Pods not starting
```bash
kubectl describe pod <pod-name> -n pokewatch
kubectl logs <pod-name> -n pokewatch
```

### API not responding
```bash
kubectl get svc -n pokewatch
minikube service list
```

## Cleanup
```bash
kubectl delete namespace pokewatch
minikube stop
```
```

#### Task 2: Phase 3 Completion Report (1.5 hours)

**File:** `PHASE3_COMPLETE.md`
```markdown
# Phase 3 Complete - MLOps Implementation

## Summary

PokeWatch Phase 3 demonstrates complete MLOps workflow:

### Week 1-2: Foundation ✅
- BentoML for model serving
- ZenML for pipeline orchestration
- CI/CD with GitHub Actions
- Security (auth, rate limiting)
- Performance optimization (caching)

### Week 3-4: Deployment ✅
- Kubernetes deployment (Minikube)
- Container orchestration
- Health monitoring
- Load testing
- Complete documentation

## Architecture

[Diagram]

## Key Learning Outcomes

1. **ML Pipeline Orchestration** - ZenML with MLflow tracking
2. **Model Serving** - BentoML production deployment
3. **CI/CD** - Automated testing and deployment
4. **Security** - Authentication and rate limiting
5. **Container Orchestration** - Kubernetes basics
6. **Monitoring** - Health checks and logging
7. **Performance** - Caching and load testing

## Technologies Demonstrated

- Python, FastAPI, Pydantic
- BentoML, ZenML, MLflow
- Docker, Kubernetes, Minikube
- GitHub Actions, pre-commit
- DVC, DagsHub
- pytest, coverage

## Verification

All features verified with automated scripts:
- `scripts/verify_week2.sh` - Weeks 1-2
- `scripts/verify_k8s.sh` - Weeks 3-4
- `tests/load/simple_load_test.py` - Performance

## Next Steps (Phase 4)

- Advanced ML models
- Drift detection
- A/B testing
- Feature store
```

**Deliverables (Day 2):**
- ✅ Operations runbook
- ✅ Phase 3 completion report
- ✅ Architecture documentation updated

---

### Day 3: Final Testing & Cleanup (2 hours)

#### Task 1: End-to-End Test (1 hour)

```bash
# Complete workflow test
bash scripts/verify_week2.sh        # Week 1-2 features
bash scripts/deploy_k8s.sh          # Deploy to K8s
bash scripts/verify_k8s.sh          # Verify K8s
python tests/load/simple_load_test.py  # Load test
```

#### Task 2: Code Cleanup (30 min)

```bash
# Run code quality
pre-commit run --all-files

# Run all tests
pytest tests/ -v

# Update documentation
```

#### Task 3: Final Review (30 min)

Create checklist in `PHASE3_COMPLETE.md`:

```markdown
## Phase 3 Checklist

- [x] BentoML service working
- [x] ZenML pipeline running
- [x] CI/CD workflows active
- [x] Security implemented
- [x] Kubernetes deployment working
- [x] Monitoring in place
- [x] Load testing complete
- [x] Documentation complete
- [x] All tests passing
```

---

## Summary: Simplified Week 3-4 Plan

### What We're Doing (Simple)

**Week 3 (2-3 days):**
1. Deploy to Minikube (local Kubernetes)
2. Add health checks and basic metrics
3. Document everything

**Week 4 (2-3 days):**
1. Simple load testing
2. Final documentation (runbook)
3. Verification and cleanup

### What We're NOT Doing (Too Complex for Course)

- ❌ Cloud Kubernetes (GKE/EKS/AKS)
- ❌ Full Prometheus/Grafana stack
- ❌ SSL/TLS certificates
- ❌ Advanced autoscaling (HPA)
- ❌ Helm charts
- ❌ Ingress controllers
- ❌ Service mesh
- ❌ Multi-region deployment

### Key Learning Objectives

1. **Container Orchestration** - Deploy to Kubernetes
2. **Observability** - Health checks, logging, metrics
3. **Performance** - Load testing and scaling
4. **Operations** - Deployment automation, monitoring
5. **Documentation** - Runbook for operations

### Deliverables

**Code:**
- 3 Kubernetes manifests (simple)
- 2 deployment scripts
- 1 monitoring script
- 1 load test script
- Health/metrics endpoints

**Documentation:**
- Kubernetes guide
- Operations runbook
- Phase 3 completion report
- Verification scripts

**Total Time:** 4-6 days (not 2 weeks)

---

## Success Criteria (Simplified)

Phase 3 complete when:

- ✅ API running in Kubernetes (Minikube)
- ✅ 2+ pods serving traffic
- ✅ Health checks working
- ✅ Basic metrics exposed
- ✅ Load test passes (100 req/s)
- ✅ Deployment automated
- ✅ Documentation complete
- ✅ All tests passing

---

## Tools & Technologies to Demonstrate

From course requirements:

| Tool | Usage | Demonstrated |
|------|-------|--------------|
| **ZenML** | Pipeline orchestration | ✅ Week 2 |
| **BentoML** | Model serving | ✅ Week 1 |
| **Kubernetes** | Container orchestration | ⏳ Week 3 (simple) |
| **Docker** | Containerization | ✅ Week 1-2 |
| **CI/CD** | GitHub Actions | ✅ Week 2 |
| **Monitoring** | Health + logs | ⏳ Week 3 (simple) |
| **MLflow** | Experiment tracking | ✅ Week 2 (via ZenML) |

**All key MLOps concepts covered!** 🎯

---

## Next Steps

1. **Review this plan** - Ensure alignment with course goals
2. **Start Week 3 Day 1** - Minikube setup
3. **Keep it simple** - Focus on learning, not complexity
4. **Document everything** - Learning artifact for course

**Ready to implement?** Start with: `brew install minikube kubectl` 🚀
