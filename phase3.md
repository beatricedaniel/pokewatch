# Phase 3: Orchestration & Deployment

**Deadline:** November 10
**Status:** Planning

---

## Overview

Phase 3 transforms PokeWatch from a local development project into a production-ready, scalable MLOps platform with:
- **End-to-end orchestration** (Airflow or ZenML)
- **CI/CD pipeline** for automated testing and deployment
- **Production-grade API** (BentoML)
- **Scalable infrastructure** (Kubernetes)

### Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Orchestration** | Airflow or ZenML | Automate data collection, training, deployment |
| **Model Serving** | BentoML | Production-grade model serving with versioning |
| **Container Orchestration** | Kubernetes (K8s) | Scalable deployment and auto-scaling |
| **CI/CD** | GitHub Actions | Automated testing, building, deployment |
| **Monitoring** | Prometheus + Grafana | Metrics, alerts, dashboards |
| **API Gateway** | Nginx/Traefik (optional) | Load balancing, SSL termination |

---

## Phase 3 Goals

### 1. Finaliser l'orchestration de bout en bout
- Automate the complete ML pipeline (data → training → deployment)
- Schedule daily data collection and periodic retraining
- Handle failures, retries, and alerting
- Track pipeline lineage and dependencies

### 2. Créer un pipeline CI/CD
- Automated testing on every commit
- Automated Docker image building
- Automated deployment to staging/production
- Integration with DagsHub for data/model validation

### 3. Optimiser et sécuriser l'API
- Migrate from FastAPI to BentoML for production serving
- Add authentication and API rate limiting
- Implement request validation and error handling
- Add logging, monitoring, and health checks
- Optimize for low latency and high throughput

### 4. Implémenter la scalabilité avec Docker/Kubernetes
- Deploy all services to Kubernetes cluster
- Implement horizontal pod autoscaling (HPA)
- Set up persistent volumes for data/models
- Configure ingress for external access
- Implement service mesh (optional)

---

## Step-by-Step Development Plan

### **Step 1: Choose Orchestration Framework (Week 1)**

**Options:**

**Option A: Apache Airflow** (Recommended for batch workflows)
- ✅ Industry standard for data pipelines
- ✅ Rich UI for monitoring and debugging
- ✅ Extensive plugin ecosystem
- ✅ Good for scheduled, batch jobs
- ❌ Steeper learning curve
- ❌ More infrastructure overhead

**Option B: ZenML** (Recommended for ML pipelines)
- ✅ Purpose-built for ML workflows
- ✅ Built-in MLflow integration
- ✅ Simpler for ML use cases
- ✅ Better pipeline versioning
- ❌ Less mature than Airflow
- ❌ Smaller community

**Decision Criteria:**
- If PokeWatch needs complex scheduling, dependencies, and monitoring → **Airflow**
- If PokeWatch focuses on ML experimentation and reproducibility → **ZenML**
- Can also use **both**: ZenML for ML pipelines, Airflow for data orchestration

**Recommendation:** Start with **ZenML** for simplicity, migrate to Airflow if needed in Phase 4.

**Tasks:**
1. Install and configure ZenML (or Airflow)
2. Create pipeline for: `collect → preprocess → train → validate → deploy`
3. Integrate with DagsHub for artifact tracking
4. Add scheduling (daily data collection, weekly retraining)
5. Implement alerting (Slack/email on failures)

**Deliverables:**
- `pipelines/zenml_pipeline.py` or `dags/pokewatch_dag.py`
- Configuration files for orchestration
- Documentation in `docs/orchestration.md`

---

### **Step 2: Migrate to BentoML for Model Serving (Week 1-2)**

**Why BentoML?**
- Production-grade model serving framework
- Built-in model versioning and Docker containerization
- Automatic API generation with OpenAPI specs
- Performance optimizations (batching, caching)
- Easy deployment to K8s, AWS, GCP, Azure

**Tasks:**

#### 2.1 Create BentoML Service
```python
# src/pokewatch/serving/bento_service.py

import bentoml
from bentoml.io import JSON
import pandas as pd

@bentoml.service(
    resources={"cpu": "500m", "memory": "512Mi"},
    traffic={"timeout": 10},
)
class PokeWatchService:
    # Load model from DVC/MLflow on service start
    model = bentoml.models.get("pokewatch_baseline:latest")

    @bentoml.api
    def predict_signal(self, input_data: JSON) -> JSON:
        """
        Predict BUY/SELL/HOLD signal for a card.

        Input: {"card_id": "sv2a-pokemon-card-151", "date": "2025-11-30"}
        Output: {"signal": "BUY", "fair_value": 42.50, "confidence": 0.85}
        """
        # Load model and predict
        card_id = input_data["card_id"]
        date = input_data.get("date")

        # Get prediction from baseline model
        result = self.model.predict(card_id, date)

        return {
            "card_id": card_id,
            "signal": result["signal"],
            "fair_value": result["fair_value"],
            "market_price": result["market_price"],
            "delta_pct": result["delta_pct"],
            "confidence": result.get("confidence", None),
        }

    @bentoml.api
    def batch_predict(self, input_data: JSON) -> JSON:
        """Batch prediction for multiple cards."""
        cards = input_data["cards"]
        results = [self.predict_signal(card) for card in cards]
        return {"predictions": results}
```

#### 2.2 Build and Test Bento
```bash
# Build Bento
bentoml build

# Serve locally
bentoml serve pokewatch_service:latest

# Test
curl -X POST http://localhost:3000/predict_signal \
  -H "Content-Type: application/json" \
  -d '{"card_id": "sv2a-pokemon-card-151"}'

# Containerize
bentoml containerize pokewatch_service:latest
```

#### 2.3 Integrate with MLflow/DVC
- Load models from DagsHub MLflow Model Registry
- Version Bentos with DVC
- Track Bento deployments in MLflow

**Deliverables:**
- `src/pokewatch/serving/bento_service.py`
- `bentofile.yaml` (Bento configuration)
- `scripts/build_bento.sh`
- Updated API documentation

---

### **Step 3: Implement CI/CD Pipeline (Week 2)**

**GitHub Actions Workflows:**

#### 3.1 Testing Workflow (`.github/workflows/test.yml`)
```yaml
name: Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev]"

      - name: Run linters
        run: |
          ruff check src/
          black --check src/

      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=src/pokewatch

      - name: Run integration tests
        run: pytest tests/integration/ -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

#### 3.2 Build & Push Docker Images (`.github/workflows/docker.yml`)
```yaml
name: Build Docker Images

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [api, collector, training]
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          file: docker/${{ matrix.service }}.Dockerfile
          push: true
          tags: |
            beatricedaniel/pokewatch-${{ matrix.service }}:latest
            beatricedaniel/pokewatch-${{ matrix.service }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

#### 3.3 Deploy to Kubernetes (`.github/workflows/deploy.yml`)
```yaml
name: Deploy to Kubernetes

on:
  push:
    tags: ['v*']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBECONFIG }}" > kubeconfig.yaml
          export KUBECONFIG=kubeconfig.yaml

      - name: Deploy to K8s
        run: |
          kubectl apply -f k8s/namespace.yaml
          kubectl apply -f k8s/configmap.yaml
          kubectl apply -f k8s/secrets.yaml
          kubectl apply -f k8s/deployments/
          kubectl apply -f k8s/services/
          kubectl apply -f k8s/ingress.yaml

      - name: Verify deployment
        run: |
          kubectl rollout status deployment/pokewatch-api -n pokewatch
          kubectl get pods -n pokewatch
```

**Deliverables:**
- `.github/workflows/test.yml`
- `.github/workflows/docker.yml`
- `.github/workflows/deploy.yml`
- Documentation in `docs/ci_cd.md`

---

### **Step 4: Kubernetes Deployment (Week 3)**

#### 4.1 Kubernetes Manifests Structure
```
k8s/
├── namespace.yaml              # Namespace for PokeWatch
├── configmap.yaml              # Non-sensitive config
├── secrets.yaml                # API keys, tokens (encrypted)
├── deployments/
│   ├── api-deployment.yaml     # BentoML API deployment
│   ├── collector-deployment.yaml
│   └── training-deployment.yaml
├── services/
│   ├── api-service.yaml        # ClusterIP service for API
│   └── collector-service.yaml
├── ingress.yaml                # External access
├── hpa.yaml                    # Horizontal Pod Autoscaler
├── pvc.yaml                    # Persistent Volume Claims for data
└── monitoring/
    ├── prometheus.yaml
    └── grafana.yaml
```

#### 4.2 Example: API Deployment
```yaml
# k8s/deployments/api-deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: pokewatch-api
  namespace: pokewatch
  labels:
    app: pokewatch
    component: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pokewatch
      component: api
  template:
    metadata:
      labels:
        app: pokewatch
        component: api
    spec:
      containers:
      - name: api
        image: beatricedaniel/pokewatch-bento:latest
        ports:
        - containerPort: 3000
          name: http
        env:
        - name: DAGSHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: pokewatch-secrets
              key: dagshub-token
        - name: MLFLOW_TRACKING_URI
          valueFrom:
            configMapKeyRef:
              name: pokewatch-config
              key: mlflow-uri
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: data
          mountPath: /app/data
          readOnly: true
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: pokewatch-data-pvc
```

#### 4.3 Horizontal Pod Autoscaler
```yaml
# k8s/hpa.yaml

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: pokewatch-api-hpa
  namespace: pokewatch
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: pokewatch-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
      - type: Percent
        value: 50
        periodSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

#### 4.4 Ingress with SSL
```yaml
# k8s/ingress.yaml

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pokewatch-ingress
  namespace: pokewatch
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.pokewatch.io
    secretName: pokewatch-tls
  rules:
  - host: api.pokewatch.io
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: pokewatch-api
            port:
              number: 3000
```

**Tasks:**
1. Set up Kubernetes cluster (Minikube local, or cloud: GKE/EKS/AKS)
2. Create all K8s manifests
3. Configure persistent storage for data/models
4. Set up ingress controller (Nginx)
5. Configure SSL certificates (cert-manager + Let's Encrypt)
6. Implement autoscaling policies
7. Test deployment and scaling

**Deliverables:**
- Complete `k8s/` directory with all manifests
- `scripts/deploy_k8s.sh` deployment script
- Documentation in `docs/kubernetes.md`

---

### **Step 5: API Security & Optimization (Week 2-3)**

#### 5.1 Authentication & Authorization
```python
# src/pokewatch/serving/auth.py

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import os

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key from request header."""
    valid_keys = os.getenv("API_KEYS", "").split(",")

    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    return api_key

# In BentoML service
@bentoml.api(
    route="/predict",
    dependencies=[Depends(verify_api_key)]
)
def predict(self, input_data: JSON) -> JSON:
    # Protected endpoint
    pass
```

#### 5.2 Rate Limiting
```python
# Use slowapi for rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@bentoml.api
@limiter.limit("100/minute")
def predict_signal(self, input_data: JSON) -> JSON:
    # Rate limited to 100 requests per minute per IP
    pass
```

#### 5.3 Request Validation with Pydantic
```python
from pydantic import BaseModel, Field, validator
from datetime import date

class PredictionRequest(BaseModel):
    card_id: str = Field(..., regex=r"^[a-z0-9_-]+$")
    date: Optional[date] = None

    @validator("card_id")
    def validate_card_id(cls, v):
        # Check against known cards
        if v not in get_known_cards():
            raise ValueError(f"Unknown card ID: {v}")
        return v

@bentoml.api
def predict_signal(self, input_data: PredictionRequest) -> JSON:
    # Auto-validated input
    pass
```

#### 5.4 Caching for Performance
```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache predictions for 1 hour
@lru_cache(maxsize=1000)
def get_cached_prediction(card_id: str, date: str) -> dict:
    # Expensive prediction logic
    return model.predict(card_id, date)

# Or use Redis for distributed caching
import redis

redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

def get_prediction_with_redis(card_id: str, date: str) -> dict:
    cache_key = f"pred:{card_id}:{date}"

    # Check cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Compute and cache
    result = model.predict(card_id, date)
    redis_client.setex(cache_key, 3600, json.dumps(result))  # 1 hour TTL

    return result
```

**Deliverables:**
- Authentication middleware
- Rate limiting configuration
- Request validation schemas
- Caching implementation
- Performance benchmarks

---

### **Step 6: Monitoring & Observability (Week 3)**

#### 6.1 Prometheus Metrics
```python
# src/pokewatch/serving/metrics.py

from prometheus_client import Counter, Histogram, Gauge
import time

# Define metrics
prediction_counter = Counter(
    "pokewatch_predictions_total",
    "Total number of predictions made",
    ["card_id", "signal"]
)

prediction_latency = Histogram(
    "pokewatch_prediction_latency_seconds",
    "Prediction latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
)

model_accuracy = Gauge(
    "pokewatch_model_accuracy",
    "Current model accuracy (MAPE)"
)

# Use in API
@bentoml.api
def predict_signal(self, input_data: JSON) -> JSON:
    start_time = time.time()

    # Make prediction
    result = self.model.predict(input_data["card_id"])

    # Record metrics
    prediction_counter.labels(
        card_id=input_data["card_id"],
        signal=result["signal"]
    ).inc()

    prediction_latency.observe(time.time() - start_time)

    return result
```

#### 6.2 Grafana Dashboard
Create dashboards for:
- Request rate and latency (p50, p95, p99)
- Error rate and status codes
- Model performance metrics (MAPE, RMSE)
- Signal distribution (BUY/SELL/HOLD ratio)
- Resource usage (CPU, memory, disk)
- Data freshness (time since last collection)

#### 6.3 Alerting Rules
```yaml
# k8s/monitoring/alerts.yaml

groups:
- name: pokewatch
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status="500"}[5m]) > 0.05
    for: 5m
    annotations:
      summary: "High error rate detected"

  - alert: HighLatency
    expr: histogram_quantile(0.95, prediction_latency_seconds) > 2.0
    for: 5m
    annotations:
      summary: "API latency above 2s (p95)"

  - alert: ModelDrift
    expr: pokewatch_model_accuracy > 20.0
    for: 30m
    annotations:
      summary: "Model MAPE above 20%, possible drift"

  - alert: StaleData
    expr: (time() - pokewatch_data_last_updated_timestamp) > 86400
    annotations:
      summary: "Data not updated in 24 hours"
```

**Deliverables:**
- Prometheus metrics exporters
- Grafana dashboards (JSON configs)
- Alert rules and notification channels
- Documentation in `docs/monitoring.md`

---

### **Step 7: Orchestration Implementation (Week 3-4)**

#### Option A: ZenML Pipeline

```python
# pipelines/ml_pipeline.py

from zenml import pipeline, step
from zenml.integrations.mlflow.steps import mlflow_model_deployer_step
from datetime import datetime

@step
def collect_data() -> pd.DataFrame:
    """Collect latest card prices from API."""
    from pokewatch.data.collectors.daily_price_collector import collect_daily_prices

    df = collect_daily_prices()
    return df

@step
def preprocess_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Feature engineering."""
    from pokewatch.data.preprocessing.make_features import make_features

    features_df = make_features(raw_df)
    return features_df

@step
def train_model(features_df: pd.DataFrame) -> BaselineFairPriceModel:
    """Train baseline model."""
    from pokewatch.models.baseline import BaselineFairPriceModel

    model = BaselineFairPriceModel(features_df)
    return model

@step
def evaluate_model(model: BaselineFairPriceModel, test_df: pd.DataFrame) -> dict:
    """Evaluate model and return metrics."""
    from pokewatch.models.train_baseline import calculate_metrics

    metrics = calculate_metrics(test_df, model, decision_cfg)
    return metrics

@step
def validate_model(metrics: dict) -> bool:
    """Validate model meets quality thresholds."""
    mape_threshold = 15.0
    coverage_threshold = 0.90

    if metrics["mape"] > mape_threshold:
        raise ValueError(f"MAPE {metrics['mape']} exceeds threshold {mape_threshold}")

    if metrics["coverage_rate"] < coverage_threshold:
        raise ValueError(f"Coverage {metrics['coverage_rate']} below threshold {coverage_threshold}")

    return True

@step
def deploy_model(model: BaselineFairPriceModel, is_valid: bool):
    """Deploy model to BentoML."""
    if not is_valid:
        raise ValueError("Model validation failed, skipping deployment")

    # Save model to BentoML
    import bentoml

    bentoml.picklable_model.save_model(
        "pokewatch_baseline",
        model,
        metadata={
            "trained_at": datetime.now().isoformat(),
            "framework": "baseline",
        }
    )

    # Build and containerize
    # This will be triggered by CI/CD

@pipeline(enable_cache=True)
def ml_training_pipeline():
    """Complete ML pipeline from data collection to deployment."""
    raw_data = collect_data()
    features = preprocess_data(raw_data)
    model = train_model(features)
    metrics = evaluate_model(model, features)
    is_valid = validate_model(metrics)
    deploy_model(model, is_valid)

# Schedule pipeline
from zenml.integrations.airflow.orchestrators import AirflowOrchestrator

if __name__ == "__main__":
    # Run pipeline
    ml_training_pipeline()

    # Or schedule it
    # ml_training_pipeline.run(schedule="0 2 * * *")  # Daily at 2 AM
```

#### Option B: Airflow DAG

```python
# dags/pokewatch_dag.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

default_args = {
    "owner": "pokewatch",
    "depends_on_past": False,
    "email": ["alerts@pokewatch.io"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "pokewatch_ml_pipeline",
    default_args=default_args,
    description="PokeWatch ML Pipeline - Data Collection, Training, Deployment",
    schedule_interval="0 2 * * *",  # Daily at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=["ml", "pokewatch"],
)

# Task 1: Collect data
collect_data = BashOperator(
    task_id="collect_data",
    bash_command="cd /opt/pokewatch && make collect",
    dag=dag,
)

# Task 2: Preprocess
preprocess_data = BashOperator(
    task_id="preprocess_data",
    bash_command="cd /opt/pokewatch && make preprocess",
    dag=dag,
)

# Task 3: Train model
train_model = BashOperator(
    task_id="train_model",
    bash_command="cd /opt/pokewatch && make train",
    dag=dag,
)

# Task 4: Validate model
def validate_model_metrics(**context):
    """Check if model meets quality thresholds."""
    import mlflow

    # Get latest run
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name("pokewatch_baseline")
    runs = client.search_runs(experiment.experiment_id, order_by=["start_time DESC"], max_results=1)

    if not runs:
        raise ValueError("No runs found")

    latest_run = runs[0]
    mape = latest_run.data.metrics.get("mape")
    coverage = latest_run.data.metrics.get("coverage_rate")

    if mape > 15.0:
        raise ValueError(f"MAPE {mape} exceeds threshold")

    if coverage < 0.90:
        raise ValueError(f"Coverage {coverage} below threshold")

    return True

validate_model = PythonOperator(
    task_id="validate_model",
    python_callable=validate_model_metrics,
    dag=dag,
)

# Task 5: Build Bento
build_bento = BashOperator(
    task_id="build_bento",
    bash_command="cd /opt/pokewatch && ./scripts/build_bento.sh",
    dag=dag,
)

# Task 6: Deploy to K8s
deploy_to_k8s = BashOperator(
    task_id="deploy_to_k8s",
    bash_command="cd /opt/pokewatch && kubectl apply -f k8s/deployments/api-deployment.yaml",
    dag=dag,
)

# Task 7: Push DVC data
push_dvc = BashOperator(
    task_id="push_dvc",
    bash_command="cd /opt/pokewatch && make dvc-push",
    dag=dag,
)

# Task 8: Send notification
def send_success_notification(**context):
    """Send Slack/email notification on success."""
    # Implement notification logic
    print("Pipeline completed successfully!")

notify_success = PythonOperator(
    task_id="notify_success",
    python_callable=send_success_notification,
    dag=dag,
)

# Define task dependencies
collect_data >> preprocess_data >> train_model >> validate_model
validate_model >> build_bento >> deploy_to_k8s
validate_model >> push_dvc
[deploy_to_k8s, push_dvc] >> notify_success
```

**Deliverables:**
- ZenML pipeline (`pipelines/ml_pipeline.py`) or Airflow DAG (`dags/pokewatch_dag.py`)
- Scheduling configuration
- Failure handling and retry logic
- Notification setup (Slack/email)
- Documentation in `docs/orchestration.md`

---

## Phase 3 Timeline

| Week | Focus | Deliverables |
|------|-------|--------------|
| **Week 1** | Orchestration & BentoML | ZenML/Airflow setup, BentoML service |
| **Week 2** | CI/CD & Security | GitHub Actions, authentication, rate limiting |
| **Week 3** | Kubernetes & Monitoring | K8s manifests, Prometheus, Grafana |
| **Week 4** | Integration & Testing | End-to-end testing, documentation |

---

## Success Criteria

Phase 3 is complete when:

- [ ] **Orchestration**: Automated pipeline runs daily without manual intervention
- [ ] **CI/CD**: Every commit triggers tests, successful merges trigger deployments
- [ ] **API**: BentoML API serves predictions with <100ms latency (p95)
- [ ] **Security**: API requires authentication, has rate limiting
- [ ] **Scalability**: K8s autoscaling works (tested with load testing)
- [ ] **Monitoring**: Dashboards show key metrics, alerts fire on anomalies
- [ ] **Documentation**: Complete setup guides for all components
- [ ] **Reliability**: Pipeline has 99% success rate over 1 week

---

## Architecture Diagram (Phase 3)

```
┌──────────────────────────────────────────────────────────────────┐
│                    GitHub Repository                             │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐             │
│  │ Push Code  │→ │ GitHub      │→ │ Build Docker │             │
│  │            │  │ Actions CI  │  │ Images       │             │
│  └────────────┘  └─────────────┘  └──────┬───────┘             │
└─────────────────────────────────────────────┼────────────────────┘
                                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                   Kubernetes Cluster                             │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Orchestration (ZenML/Airflow)                              ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   ││
│  │  │ Collect  │→ │Preprocess│→ │  Train   │→ │ Deploy   │   ││
│  │  │ (CronJob)│  │  (Job)   │  │  (Job)   │  │  (Job)   │   ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ BentoML API  │  │  Collector   │  │   Training   │         │
│  │ (Deployment) │  │ (CronJob)    │  │   (Job)      │         │
│  │ ┌──────────┐ │  │              │  │              │         │
│  │ │ Pod 1    │ │  └──────────────┘  └──────────────┘         │
│  │ │ Pod 2    │ │                                              │
│  │ │ Pod 3    │ │  ┌──────────────┐  ┌──────────────┐         │
│  │ └──────────┘ │  │ Prometheus   │  │   Grafana    │         │
│  │              │  │ (Monitoring) │  │ (Dashboard)  │         │
│  └──────┬───────┘  └──────────────┘  └──────────────┘         │
│         │                                                       │
│  ┌──────▼─────────────────────────┐                           │
│  │  Ingress (Nginx)               │                           │
│  │  - SSL/TLS (Let's Encrypt)     │                           │
│  │  - Rate Limiting               │                           │
│  └────────────────────────────────┘                           │
└──────────────────────────────────────────────────────────────────┘
                       ↕
┌──────────────────────────────────────────────────────────────────┐
│                      External Services                           │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   DagsHub    │  │  Pokémon API │  │    Slack     │         │
│  │ - MLflow     │  │              │  │  (Alerts)    │         │
│  │ - DVC        │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└──────────────────────────────────────────────────────────────────┘
```

---

## Additional Resources

### Learning Resources
- **BentoML**: https://docs.bentoml.com/
- **ZenML**: https://docs.zenml.io/
- **Airflow**: https://airflow.apache.org/docs/
- **Kubernetes**: https://kubernetes.io/docs/home/
- **Prometheus**: https://prometheus.io/docs/
- **Grafana**: https://grafana.com/docs/

### Tools to Install
```bash
# BentoML
pip install bentoml

# ZenML
pip install "zenml[server]"

# Kubernetes CLI
brew install kubectl

# Helm (K8s package manager)
brew install helm

# Minikube (local K8s)
brew install minikube
```

---

## Phase 4 Preview

After completing Phase 3, Phase 4 will focus on:
- **Advanced ML models** (LSTM, Transformers for time-series)
- **A/B testing** framework for model comparison
- **Feature store** (Feast) for feature management
- **Data quality monitoring** (Great Expectations)
- **Drift detection** and automated retraining triggers
- **Multi-region deployment** for global availability
- **Cost optimization** and resource management

---

**Let's build production-ready PokeWatch! 🚀**
