# PokeWatch Microservices Deployment Guide

This guide explains how to deploy the PokeWatch microservices architecture to Kubernetes.

## Architecture Overview

The PokeWatch platform consists of:

### Always-Running Services (3 microservices)

1. **API Gateway** (`pokewatch-api:latest`)
   - Port: 8000 (external: NodePort 30080)
   - Purpose: External-facing REST API, routes requests to backend services
   - Dependencies: Model Service, Decision Service

2. **Model Service** (`pokewatch-model:latest`)
   - Port: 3000 (ClusterIP)
   - Purpose: ML predictions (fair price estimation)
   - Technology: BentoML
   - Endpoints: `/predict`, `/cards`, `/health`, `/reload`

3. **Decision Service** (`pokewatch-decision:latest`)
   - Port: 8001 (ClusterIP)
   - Purpose: BUY/SELL/HOLD signal generation
   - Technology: FastAPI
   - Endpoints: `/signal`, `/health`

### Batch Processing (Airflow-orchestrated)

4. **Batch Pipeline** (`pokewatch-batch:latest`)
   - Runs inside Airflow workers
   - Tasks:
     - Data collection (daily price data)
     - Preprocessing (feature engineering)
     - Model training (baseline model)
     - Model deployment (trigger Model Service reload)

## Prerequisites

1. **Kubernetes cluster** (Minikube, K3s, or cloud provider)
   ```bash
   # For Minikube
   minikube start --driver=docker --memory=4096 --cpus=4
   ```

2. **kubectl** configured to access your cluster
   ```bash
   kubectl version --client
   ```

3. **Helm 3** (for Airflow installation)
   ```bash
   helm version
   ```

4. **Docker** (for building images)
   ```bash
   docker --version
   ```

## Step-by-Step Deployment

### Step 1: Create Namespaces

```bash
kubectl create namespace pokewatch
kubectl create namespace airflow
```

### Step 2: Create Secrets

Create Kubernetes secrets with your API keys and tokens:

```bash
# Copy the template
cp k8s/ml-secrets.yaml k8s/ml-secrets-live.yaml

# Edit the file and replace placeholders with base64-encoded values
# Example: echo -n "your-api-key" | base64
nano k8s/ml-secrets-live.yaml

# Apply secrets
kubectl apply -f k8s/ml-secrets-live.yaml -n pokewatch
kubectl apply -f k8s/ml-secrets-live.yaml -n airflow
```

**Required secrets:**
- `POKEMON_PRICE_API_KEY`: API key for Pokemon Price Tracker
- `DAGSHUB_USER_TOKEN`: DagsHub authentication token
- `MLFLOW_TRACKING_URI`: MLflow tracking server URL (e.g., https://dagshub.com/user/repo.mlflow)

### Step 3: Build Docker Images

```bash
# Build all 4 images and load into Minikube
./scripts/build_microservices.sh --minikube
```

This creates:
- `pokewatch-api:latest` (API Gateway)
- `pokewatch-model:latest` (Model Service)
- `pokewatch-decision:latest` (Decision Service)
- `pokewatch-batch:latest` (Batch Pipeline)

### Step 4: Deploy PersistentVolumes

```bash
kubectl apply -f k8s/airflow-pv.yaml
```

This creates:
- `airflow-dags-pvc` (5Gi) - For DAG files
- `airflow-logs-pvc` (10Gi) - For Airflow logs
- `ml-data-pvc` (20Gi) - For ML data (shared)

### Step 5: Deploy Microservices

```bash
# Deploy all microservices
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/model-service-deployment.yaml
kubectl apply -f k8s/model-service-service.yaml
kubectl apply -f k8s/model-service-hpa.yaml
kubectl apply -f k8s/decision-service-deployment.yaml
kubectl apply -f k8s/decision-service-service.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=model-service -n pokewatch --timeout=180s
kubectl wait --for=condition=ready pod -l app=decision-service -n pokewatch --timeout=60s
kubectl wait --for=condition=ready pod -l app=api-gateway -n pokewatch --timeout=60s
```

### Step 6: Verify Microservices

```bash
# Check all pods
kubectl get pods -n pokewatch

# Expected output:
# NAME                               READY   STATUS    RESTARTS   AGE
# api-gateway-xxxxxx-xxxxx           1/1     Running   0          2m
# api-gateway-xxxxxx-xxxxx           1/1     Running   0          2m
# decision-service-xxxxxx-xxxxx      1/1     Running   0          2m
# decision-service-xxxxxx-xxxxx      1/1     Running   0          2m
# model-service-xxxxxx-xxxxx         1/1     Running   0          3m
# model-service-xxxxxx-xxxxx         1/1     Running   0          3m

# Check services
kubectl get svc -n pokewatch

# Test health endpoints
kubectl port-forward -n pokewatch svc/api-gateway 8000:8000 &
curl http://localhost:8000/health
```

### Step 7: Install Airflow

```bash
# Add Airflow Helm repository
helm repo add apache-airflow https://airflow.apache.org
helm repo update

# Install Airflow with custom values
helm install airflow apache-airflow/airflow \
    -f k8s/airflow-values.yaml \
    --namespace airflow \
    --create-namespace

# Wait for Airflow to be ready (may take 3-5 minutes)
kubectl wait --for=condition=ready pod -l component=webserver -n airflow --timeout=300s
```

### Step 8: Copy DAGs to Airflow

```bash
# Get Airflow scheduler pod name
SCHEDULER_POD=$(kubectl get pods -n airflow -l component=scheduler -o jsonpath='{.items[0].metadata.name}')

# Copy DAG files
kubectl cp airflow/dags/ml_pipeline.py airflow/$SCHEDULER_POD:/opt/airflow/dags/

# Verify DAG was copied
kubectl exec -n airflow $SCHEDULER_POD -- ls -la /opt/airflow/dags/
```

### Step 9: Access Airflow UI

```bash
# Port-forward to Airflow webserver
kubectl port-forward -n airflow svc/airflow-webserver 8080:8080

# Open browser: http://localhost:8080
# Default credentials: admin / admin
```

### Step 10: Trigger ML Pipeline

1. Open Airflow UI (http://localhost:8080)
2. Find DAG: `pokewatch_ml_pipeline`
3. Toggle "Pause/Unpause DAG" to enable it
4. Click "Trigger DAG" to run manually
5. Monitor progress in Graph or Tree view

**DAG tasks:**
1. `collect_data` - Fetch 7 days of price data
2. `preprocess_data` - Feature engineering
3. `train_model` - Train baseline model, log to MLflow
4. `deploy_model` - Trigger Model Service reload

## Verification

### Test API Gateway

```bash
# Port-forward API Gateway
kubectl port-forward -n pokewatch svc/api-gateway 8000:8000 &

# 1. Health check
curl http://localhost:8000/health

# Expected: {"status":"ok","model_loaded":true,"cards_count":40}

# 2. List cards
curl -X GET http://localhost:8000/cards

# Expected: {"cards":["charizard_ex_199",...], "count":40}

# 3. Fair price prediction
curl -X POST http://localhost:8000/fair_price \
    -H "Content-Type: application/json" \
    -d '{
        "card_id": "charizard_ex_199",
        "date": "2025-12-01"
    }'

# Expected:
# {
#   "card_id": "charizard_ex_199",
#   "date": "2025-12-01",
#   "market_price": 150.0,
#   "fair_price": 145.0,
#   "deviation_pct": 0.034,
#   "signal": "HOLD"
# }
```

### Test Individual Services

```bash
# Test Model Service (internal)
kubectl run test-pod --rm -it --image=curlimages/curl --restart=Never -n pokewatch -- \
    curl http://model-service.pokewatch.svc.cluster.local:3000/health

# Test Decision Service (internal)
kubectl run test-pod --rm -it --image=curlimages/curl --restart=Never -n pokewatch -- \
    curl -X POST http://decision-service.pokewatch.svc.cluster.local:8001/signal \
    -H "Content-Type: application/json" \
    -d '{"market_price":90,"fair_price":100,"buy_threshold_pct":0.1,"sell_threshold_pct":0.15}'
```

### Check Autoscaling

```bash
# View HPA status
kubectl get hpa -n pokewatch

# Expected:
# NAME                  REFERENCE                  TARGETS         MINPODS   MAXPODS   REPLICAS
# model-service-hpa     Deployment/model-service   cpu: 5%/70%     2         5         2
#                                                   memory: 10%/80%

# Simulate load to trigger scaling
kubectl run load-generator --rm -it --image=busybox --restart=Never -n pokewatch -- \
    sh -c "while true; do wget -q -O- http://model-service.pokewatch.svc.cluster.local:3000/health; done"

# Watch pods scale up (in another terminal)
watch kubectl get pods -n pokewatch
```

## Architecture Flow

### Inference Request Flow

```
User → API Gateway (8000)
         ↓
         ├─→ Model Service (3000) → Fair Price Prediction
         └─→ Decision Service (8001) → Trading Signal
         ↓
      Combined Response
```

### Batch Pipeline Flow

```
Airflow Scheduler
    ↓
Airflow Worker (batch-pipeline image)
    ↓
[collect_data] → API → data/raw/*.parquet
    ↓
[preprocess_data] → data/processed/*.parquet
    ↓
[train_model] → MLflow → models/
    ↓
[deploy_model] → POST /reload → Model Service
```

## Monitoring

### View Logs

```bash
# API Gateway logs
kubectl logs -n pokewatch -l app=api-gateway --tail=50 -f

# Model Service logs
kubectl logs -n pokewatch -l app=model-service --tail=50 -f

# Decision Service logs
kubectl logs -n pokewatch -l app=decision-service --tail=50 -f

# Airflow scheduler logs
kubectl logs -n airflow -l component=scheduler --tail=50 -f
```

### View Events

```bash
# All events in pokewatch namespace
kubectl get events -n pokewatch --sort-by='.lastTimestamp'

# All events in airflow namespace
kubectl get events -n airflow --sort-by='.lastTimestamp'
```

### Resource Usage

```bash
# Pod resource usage
kubectl top pods -n pokewatch

# Node resource usage
kubectl top nodes
```

## Troubleshooting

### Pods Not Starting

```bash
# Describe pod to see errors
kubectl describe pod <pod-name> -n pokewatch

# Common issues:
# - ImagePullBackOff: Image not found in Minikube's daemon
#   Solution: Run ./scripts/build_microservices.sh --minikube
# - CrashLoopBackOff: Application errors
#   Solution: Check logs with kubectl logs
```

### Model Service Not Loading Model

```bash
# Check logs
kubectl logs -n pokewatch -l app=model-service

# Common issue: Missing MLflow credentials
# Solution: Verify ml-secrets contains correct values
kubectl get secret ml-secrets -n pokewatch -o yaml
```

### Airflow DAG Not Running

```bash
# Check scheduler logs
kubectl logs -n airflow -l component=scheduler

# Common issues:
# - DAG file not found: Copy DAG file to PVC
# - Secrets missing: Verify ml-secrets in airflow namespace
# - Dependencies missing: Rebuild pokewatch-batch:latest image
```

### Service Communication Errors

```bash
# Test DNS resolution
kubectl run test-dns --rm -it --image=busybox --restart=Never -n pokewatch -- \
    nslookup model-service.pokewatch.svc.cluster.local

# Test connectivity
kubectl run test-conn --rm -it --image=curlimages/curl --restart=Never -n pokewatch -- \
    curl -v http://model-service.pokewatch.svc.cluster.local:3000/health
```

## Cleanup

```bash
# Delete Airflow
helm uninstall airflow -n airflow

# Delete microservices
kubectl delete namespace pokewatch
kubectl delete namespace airflow

# Delete PVs (if needed)
kubectl delete pv airflow-dags-pv airflow-logs-pv ml-data-pv

# Stop Minikube
minikube stop
```

## Scaling

### Manual Scaling

```bash
# Scale Model Service
kubectl scale deployment/model-service --replicas=5 -n pokewatch

# Scale API Gateway
kubectl scale deployment/api-gateway --replicas=3 -n pokewatch
```

### HPA Configuration

The Model Service has HPA enabled:
- **Min replicas**: 2
- **Max replicas**: 5
- **CPU threshold**: 70%
- **Memory threshold**: 80%

To modify HPA:
```bash
kubectl edit hpa model-service-hpa -n pokewatch
```

## Production Considerations

1. **Secrets Management**
   - Use external secret management (Vault, AWS Secrets Manager)
   - Rotate credentials regularly

2. **Persistent Storage**
   - Replace `hostPath` with cloud storage (EBS, GCE PD, Azure Disk)
   - Use managed NFS or object storage (S3, GCS, Azure Blob)

3. **Ingress**
   - Deploy Ingress controller (nginx, Traefik)
   - Configure TLS/SSL certificates
   - Set up domain routing

4. **Monitoring**
   - Deploy Prometheus + Grafana
   - Set up alerts for pod failures, high resource usage
   - Monitor model performance metrics

5. **High Availability**
   - Run multiple replicas of all services
   - Configure pod disruption budgets
   - Use node affinity/anti-affinity

6. **CI/CD**
   - Automate image builds with GitHub Actions
   - Deploy via ArgoCD or Flux
   - Implement blue-green or canary deployments

## Next Steps

- [ ] Set up Prometheus monitoring
- [ ] Configure Ingress with TLS
- [ ] Implement model A/B testing
- [ ] Add drift detection to pipeline
- [ ] Set up alerting for DAG failures
- [ ] Optimize resource limits based on actual usage

---

**Last Updated**: 2025-12-08
**Status**: Production-ready for course demonstration
