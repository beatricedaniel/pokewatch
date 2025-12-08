# PokeWatch Microservices Architecture

## Overview

PokeWatch has been transitioned from a monolithic architecture to a hybrid microservices architecture consisting of:

- **3 always-running microservices** (Model, Decision, API Gateway)
- **3 batch jobs** orchestrated by Apache Airflow (Data collection, Preprocessing, Training)

This architecture provides:
- ✅ **Separation of Concerns**: Each service has a single responsibility
- ✅ **Independent Scaling**: Scale services based on individual load patterns
- ✅ **Technology Flexibility**: Each service can use optimal technology stack
- ✅ **Fault Isolation**: Service failures don't cascade to entire system
- ✅ **Code Reuse**: ~95% of existing code reused without modification

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         External User                            │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP/REST
                                ▼
                    ┌───────────────────────┐
                    │    API Gateway        │ NodePort 30080
                    │  (pokewatch-api)      │ 2 replicas
                    │  FastAPI              │
                    └───────────┬───────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
      ┌─────────────┐  ┌──────────────┐  (future services)
      │   Model     │  │  Decision    │
      │  Service    │  │   Service    │
      │ (BentoML)   │  │  (FastAPI)   │
      │ ClusterIP   │  │  ClusterIP   │
      │ 2-5 replicas│  │  2 replicas  │
      │ Port 3000   │  │  Port 8001   │
      └──────┬──────┘  └──────────────┘
             │
             │ reload trigger
             │
    ┌────────┴──────────────────────────────────────┐
    │          Apache Airflow Scheduler             │
    │          (airflow namespace)                  │
    │                                               │
    │  DAG: pokewatch_ml_pipeline (daily @ 2 AM)   │
    │  ┌──────────────────────────────────────┐    │
    │  │  1. collect_data (BashOperator)      │    │
    │  │     → data/raw/*.parquet             │    │
    │  │  2. preprocess_data (BashOperator)   │    │
    │  │     → data/processed/*.parquet       │    │
    │  │  3. train_model (BashOperator)       │    │
    │  │     → MLflow → models/               │    │
    │  │  4. deploy_model (BashOperator)      │    │
    │  │     → POST /reload → Model Service   │    │
    │  └──────────────────────────────────────┘    │
    │                                               │
    │  Worker Image: pokewatch-batch:latest        │
    │  (all dependencies included)                 │
    └───────────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────┐
    │   MLflow +      │
    │   DagsHub       │
    │   (external)    │
    └─────────────────┘
```

## Service Specifications

### 1. Model Service (BentoML)

**Technology**: BentoML (ML model serving framework)
**Image**: `pokewatch-model:latest`
**Port**: 3000 (ClusterIP)
**Replicas**: 2-5 (HPA enabled)

**Endpoints**:
- `POST /predict` - Fair price prediction
  ```json
  Request: {"card_id": "charizard_ex_199", "date": "2025-12-01"}
  Response: {"card_id": "...", "date": "...", "market_price": 150.0, "fair_price": 145.0}
  ```
- `GET /cards` - List all tracked card IDs
  ```json
  Response: {"cards": ["charizard_ex_199", ...], "count": 40}
  ```
- `GET /health` - Health check
  ```json
  Response: {"status": "healthy", "model_loaded": true, "cards_count": 40}
  ```
- `POST /reload` - Reload model from MLflow (triggered by Airflow)
  ```json
  Response: {"status": "reloaded", "cards_count": 40}
  ```

**Code Reuse**:
- Wraps `pokewatch.models.baseline.BaselineFairPriceModel`
- No changes to model code - 100% reuse

**Autoscaling**:
- Min: 2 replicas, Max: 5 replicas
- CPU threshold: 70%
- Memory threshold: 80%

**Resource Limits**:
- Requests: 500m CPU, 512Mi Memory
- Limits: 2000m CPU, 2Gi Memory

---

### 2. Decision Service (FastAPI)

**Technology**: FastAPI
**Image**: `pokewatch-decision:latest`
**Port**: 8001 (ClusterIP)
**Replicas**: 2 (fixed)

**Endpoints**:
- `POST /signal` - Generate BUY/SELL/HOLD signal
  ```json
  Request: {
      "market_price": 90.0,
      "fair_price": 100.0,
      "buy_threshold_pct": 0.10,
      "sell_threshold_pct": 0.15
  }
  Response: {
      "signal": "BUY",
      "deviation_pct": -0.1,
      "market_price": 90.0,
      "fair_price": 100.0
  }
  ```
- `GET /health` - Health check
  ```json
  Response: {"status": "healthy", "service": "decision_service"}
  ```

**Code Reuse**:
- Wraps `pokewatch.core.decision_rules.compute_signal()`
- No changes to business logic - 100% reuse

**Resource Limits**:
- Requests: 100m CPU, 128Mi Memory
- Limits: 500m CPU, 256Mi Memory

---

### 3. API Gateway (FastAPI)

**Technology**: FastAPI
**Image**: `pokewatch-api:latest` (same as before, but modified code)
**Port**: 8000 (NodePort 30080 for external access)
**Replicas**: 2 (fixed)

**Purpose**: External-facing REST API that orchestrates calls to backend services

**Endpoints**:
- `GET /health` - Health check (checks downstream services)
- `POST /fair_price` - Fair price prediction + trading signal
  - Calls Model Service → `/predict`
  - Calls Decision Service → `/signal`
  - Combines responses
- `GET /cards` - List all cards (proxies to Model Service)

**Code Changes**:
- Removed direct model loading
- Added `httpx` for service-to-service communication
- Orchestrates downstream service calls
- ~50 lines modified, rest unchanged

**Resource Limits**:
- Requests: 100m CPU, 128Mi Memory
- Limits: 500m CPU, 256Mi Memory

---

### 4. Batch Pipeline (Airflow Workers)

**Technology**: Python + Airflow BashOperator
**Image**: `pokewatch-batch:latest`
**Execution**: Inside Airflow worker pods (LocalExecutor)

**Tasks** (sequential pipeline):

1. **collect_data** (BashOperator)
   - Command: `python -m pokewatch.data.collectors.daily_price_collector --days 7`
   - Output: `data/raw/*.parquet`
   - Dependencies: Pokemon Price Tracker API key

2. **preprocess_data** (BashOperator)
   - Command: `python -m pokewatch.data.preprocessing.make_features`
   - Input: `data/raw/*.parquet`
   - Output: `data/processed/*.parquet`

3. **train_model** (BashOperator)
   - Command: `python -m pokewatch.models.train_baseline`
   - Input: `data/processed/*.parquet`
   - Output: MLflow artifact (logged to DagsHub)
   - Dependencies: MLflow tracking URI, DagsHub token

4. **deploy_model** (BashOperator)
   - Command: `curl -X POST http://model-service:3000/reload`
   - Triggers Model Service to reload latest model from MLflow
   - Graceful fallback: If reload fails, model reloads on next request

**Schedule**: Daily at 2 AM UTC (`0 2 * * *`)

**Code Reuse**: 100% - All existing scripts reused without modification

---

## Deployment Architecture

### Kubernetes Resources

**Namespaces**:
- `pokewatch` - Microservices (Model, Decision, API Gateway)
- `airflow` - Airflow components (Scheduler, Webserver, Workers, PostgreSQL)

**Services**:
- `api-gateway` (NodePort 30080) - External access
- `model-service` (ClusterIP) - Internal only
- `decision-service` (ClusterIP) - Internal only
- `airflow-webserver` (NodePort 30081) - Airflow UI

**Secrets**:
- `ml-secrets` (both namespaces) - Contains:
  - `POKEMON_PRICE_API_KEY`
  - `DAGSHUB_USER_TOKEN`
  - `MLFLOW_TRACKING_URI`

**PersistentVolumes**:
- `airflow-dags-pvc` (5Gi) - DAG files
- `airflow-logs-pvc` (10Gi) - Airflow logs
- `ml-data-pvc` (20Gi) - ML data (shared)

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Gateway | FastAPI | REST API, request routing |
| Model Service | BentoML | ML model serving |
| Decision Service | FastAPI | Business logic service |
| Orchestration | Apache Airflow | Batch job scheduling |
| Experiment Tracking | MLflow + DagsHub | Model versioning |
| Data Versioning | DVC + DagsHub | Data pipeline tracking |
| Container Orchestration | Kubernetes | Deployment, scaling, HA |
| Database | PostgreSQL | Airflow metadata |

---

## Request Flow Examples

### Fair Price Prediction (Synchronous)

```
1. User → API Gateway: POST /fair_price
   {"card_id": "charizard_ex_199", "date": "2025-12-01"}

2. API Gateway → Model Service: POST /predict
   {"card_id": "charizard_ex_199", "date": "2025-12-01"}

3. Model Service → API Gateway: 200 OK
   {"card_id": "...", "date": "...", "market_price": 150.0, "fair_price": 145.0}

4. API Gateway → Decision Service: POST /signal
   {"market_price": 150.0, "fair_price": 145.0, "buy_threshold_pct": 0.1, "sell_threshold_pct": 0.15}

5. Decision Service → API Gateway: 200 OK
   {"signal": "HOLD", "deviation_pct": 0.034}

6. API Gateway → User: 200 OK
   {
       "card_id": "charizard_ex_199",
       "date": "2025-12-01",
       "market_price": 150.0,
       "fair_price": 145.0,
       "deviation_pct": 0.034,
       "signal": "HOLD"
   }

Total latency: ~200-500ms (depending on model complexity)
```

### ML Pipeline Execution (Asynchronous)

```
1. Airflow Scheduler: Triggers DAG at 2 AM UTC

2. Airflow Worker (collect_data task):
   - Fetches 7 days of price data from API
   - Saves to data/raw/*.parquet
   - Duration: ~1-2 minutes (depends on API)

3. Airflow Worker (preprocess_data task):
   - Reads data/raw/*.parquet
   - Applies feature engineering
   - Saves to data/processed/*.parquet
   - Duration: ~10-30 seconds

4. Airflow Worker (train_model task):
   - Reads data/processed/*.parquet
   - Trains baseline model
   - Logs to MLflow (DagsHub)
   - Duration: ~30 seconds

5. Airflow Worker (deploy_model task):
   - Sends POST /reload to Model Service
   - Model Service fetches latest model from MLflow
   - Duration: ~5-10 seconds

Total pipeline duration: ~2-3 minutes
```

---

## Scaling Characteristics

### Model Service (CPU-intensive)
- **Autoscaling**: Enabled (2-5 replicas)
- **Trigger**: CPU > 70% or Memory > 80%
- **Reasoning**: ML predictions are CPU-bound
- **Scale-up**: Aggressive (100% increase every 30s)
- **Scale-down**: Conservative (50% decrease every 5min)

### Decision Service (Lightweight)
- **Autoscaling**: Not needed (fixed 2 replicas)
- **Reasoning**: Simple arithmetic logic, minimal resource usage
- **Resource usage**: <100m CPU per pod

### API Gateway (I/O-bound)
- **Autoscaling**: Not configured (can be added if needed)
- **Reasoning**: Orchestration layer, minimal processing
- **Bottleneck**: Downstream services, not gateway itself

---

## Fault Tolerance

### Service Failures
- **Model Service down**: API returns 503 Service Unavailable
- **Decision Service down**: API returns 503 Service Unavailable
- **API Gateway down**: NodePort still routes to healthy replicas (2 pods)

### Model Reload Failures
- **Soft failure**: Airflow logs warning, pipeline continues
- **Fallback**: Model Service keeps using current model
- **Next attempt**: Model reloads on next prediction request (lazy loading)

### Airflow Worker Failures
- **Task retry**: 2 retries with 5-minute delay
- **Persistent failure**: DAG marked as failed, alert sent
- **Manual intervention**: Investigate logs, fix issue, re-run DAG

---

## Monitoring & Observability

### Health Checks
- All services expose `/health` endpoints
- Kubernetes liveness and readiness probes
- API Gateway checks downstream service health

### Logs
```bash
# Service logs
kubectl logs -n pokewatch -l app=model-service -f
kubectl logs -n pokewatch -l app=decision-service -f
kubectl logs -n pokewatch -l app=api-gateway -f

# Airflow logs
kubectl logs -n airflow -l component=scheduler -f
```

### Metrics
- Kubernetes metrics: `kubectl top pods -n pokewatch`
- Airflow UI: Task duration, success rate, failure patterns
- MLflow: Model performance metrics, training time

---

## Cost Optimization

### Resource Efficiency
- **Total CPU**: ~4-8 cores (2-5 Model Service + 2 Decision + 2 Gateway)
- **Total Memory**: ~4-10 GB
- **Storage**: ~35 GB (DAGs 5GB + Logs 10GB + Data 20GB)

### BashOperator vs KubernetesPodOperator
- **Chosen**: BashOperator (runs inside worker pod)
- **Alternative**: KubernetesPodOperator (spawns new pods per task)
- **Savings**: ~75% fewer pod creations
- **Tradeoff**: Less isolation, shared resources

### Minikube vs Cloud
- **Minikube**: $0 (runs on local machine)
- **Cloud (estimated)**:
  - 3-node cluster: ~$150-300/month
  - Load balancer: ~$20/month
  - Storage: ~$10/month
  - **Total**: ~$180-330/month

---

## Future Enhancements

### Short-term
- [ ] Add Redis for caching predictions (reduce Model Service load)
- [ ] Implement circuit breakers (prevent cascade failures)
- [ ] Add Prometheus + Grafana (metrics dashboard)

### Medium-term
- [ ] Model A/B testing service
- [ ] Real-time drift detection service
- [ ] Notification service (alerts for BUY/SELL signals)

### Long-term
- [ ] ML feature store (centralized feature management)
- [ ] Advanced model serving (TensorFlow Serving, Triton)
- [ ] Distributed training (Kubeflow, Ray)

---

## Files Created/Modified

### New Files (13)
1. `services/model_service/bento_service.py` - BentoML service
2. `services/decision_service/main.py` - Decision service
3. `docker/model-service.Dockerfile` - Model service container
4. `docker/decision-service.Dockerfile` - Decision service container
5. `docker/batch-pipeline.Dockerfile` - Batch pipeline container
6. `airflow/dags/ml_pipeline.py` - Complete ML pipeline DAG
7. `k8s/ml-secrets.yaml` - Secrets template
8. `k8s/model-service-*.yaml` - Model service manifests (3 files)
9. `k8s/decision-service-*.yaml` - Decision service manifests (2 files)
10. `k8s/airflow-pv.yaml` - PersistentVolume manifests
11. `k8s/airflow-values.yaml` - Airflow Helm values
12. `scripts/build_microservices.sh` - Build script
13. `scripts/microservices_commands.sh` - Operations menu

### Modified Files (4)
1. `src/pokewatch/api/main.py` - Converted to API Gateway (~50 lines)
2. `k8s/api-deployment.yaml` - Updated for Gateway role
3. `k8s/api-service.yaml` - Renamed to api-gateway

### Unchanged (95% of codebase)
- All model code (`models/baseline.py`)
- All business logic (`core/decision_rules.py`)
- All data collection (`data/collectors/`)
- All preprocessing (`data/preprocessing/`)
- All configuration (`config/`)

---

**Last Updated**: 2025-12-08
**Implementation Status**: Complete
**Production Ready**: Yes (for course demonstration)
