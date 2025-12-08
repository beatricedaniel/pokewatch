# Microservices Transition Plan

**Project**: PokeWatch
**Current Architecture**: Monolithic
**Target Architecture**: Microservices with Airflow Orchestration
**Strategy**: Minimal Code Changes, Maximum Reuse
**Orchestration**: Apache Airflow (Helm Chart) with BashOperator
**Date**: 2025-12-08 (Updated with BashOperator approach)

---

## 🚀 Key Decision: BashOperator Instead of KubernetesPodOperator

**Why this change?**
- ✅ **Simpler**: No Kubernetes API permissions or RBAC configuration needed
- ✅ **Fewer pods**: Batch tasks run inside Airflow worker (no pod spawning)
- ✅ **Faster**: Reduced implementation time from ~28h to ~23.5h
- ✅ **More reliable**: Avoids KubernetesPodOperator issues in Minikube
- ✅ **Still follows best practices**: Uses Airflow for orchestration, maintains task separation

**What we're using**:
- **1 Docker image**: `pokewatch-batch:latest` (all ML dependencies)
- **BashOperator**: Runs `python -m` commands inside worker pod
- **Sequential tasks**: `collect_data >> preprocess_data >> train_model >> deploy_model`
- **Full MLOps integration**: DVC, MLflow, model versioning

**Trade-off**: Batch tasks share the worker pod instead of isolated pods. This is acceptable for our use case (single daily pipeline, low concurrency).

---

## Executive Summary

This plan outlines the transition from the current monolithic PokeWatch application to a microservices architecture while **minimizing code changes**. The strategy focuses on:

1. **Reusing existing code** - No rewrites, just restructuring
2. **Gradual migration** - Can run monolith and microservices simultaneously
3. **Leveraging existing MLOps tools** - MLflow, DVC, DagsHub, BentoML
4. **Apache Airflow orchestration** - Using official Helm chart to orchestrate ML pipeline
5. **Minimal new infrastructure** - Using existing Kubernetes setup + Airflow namespace

---

## Current Architecture Analysis

### Monolithic Structure (Current)

```
pokewatch-api (Single Container)
├── Data Collection (daily_price_collector.py)
├── Preprocessing (make_features.py)
├── Model (baseline.py)
├── Decision Logic (decision_rules.py)
└── API Endpoints (api/main.py)
```

**Deployment**: Single Kubernetes deployment with 2-5 replicas

**Issues**:
- All components scale together (inefficient)
- Data collection runs manually, not as a service
- Cannot independently deploy model updates
- Single point of failure

---

## Target Microservices Architecture

### Architecture Type: Hybrid (Microservices + Batch Jobs)

**Microservices Layer** (Always-running, user-facing services):

```
1. API Gateway Service (Microservice)
   ├── Handles user API requests
   ├── Authentication/Rate limiting
   ├── Routes to Model + Decision services
   └── Scaling: 2-5 replicas

2. Model Service (Microservice, BentoML)
   ├── Serves ML predictions via HTTP
   ├── Loads model from MLflow
   ├── Independently scalable
   └── Scaling: 2-10 replicas (HPA)

3. Decision Service (Microservice)
   ├── Applies BUY/SELL/HOLD rules via HTTP
   ├── Stateless, fast computation
   ├── Independently scalable
   └── Scaling: 2-5 replicas
```

**Batch Jobs Layer** (Scheduled, Airflow-orchestrated tasks):

```
4. Data Collection Job (Airflow Task)
   ├── Runs daily via Airflow DAG
   ├── Short-lived Kubernetes pod
   ├── Fetches card prices from API
   └── Outputs: Raw data → DVC

5. Preprocessing Job (Airflow Task)
   ├── Triggered after data collection
   ├── Short-lived Kubernetes pod
   ├── Feature engineering
   └── Outputs: Processed features → DVC

6. Model Training Job (Airflow Task)
   ├── Triggered after preprocessing
   ├── Short-lived Kubernetes pod
   ├── Trains baseline model
   └── Outputs: Model artifact → MLflow
```

**Key Distinction**:
- **Microservices** = Always running, serve HTTP requests, scale horizontally
- **Batch Jobs** = Run on schedule, execute and terminate, orchestrated by Airflow

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    DagsHub (Central Hub)                    │
│        Git (Code) | DVC (Data) | MLflow (Models)            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│          Apache Airflow (Helm Chart Deployment)             │
│  Namespace: airflow                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ DAG: ml_pipeline (Scheduled daily)                  │   │
│  │                                                     │   │
│  │  Task 1: collect_data (KubernetesPodOperator)      │   │
│  │          ↓                                          │   │
│  │  Task 2: preprocess_data (KubernetesPodOperator)   │   │
│  │          ↓                                          │   │
│  │  Task 3: train_model (KubernetesPodOperator)       │   │
│  │          ↓                                          │   │
│  │  Task 4: deploy_model (Triggers Model Service)     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Components:                                                │
│  • Webserver (UI)    • Scheduler   • Workers               │
│  • PostgreSQL (Metadata) • Redis (Message Queue)           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────┐
│ Data Collector Service (Airflow Task → K8s Pod)           │
│ • Triggered by: Airflow DAG                               │
│ • Runs: docker image with daily_price_collector.py        │
│ • Outputs: dvc push to DagsHub                            │
│ • Volume: PVC for shared data                             │
└───────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────┐
│ Preprocessing Service (Airflow Task → K8s Pod)            │
│ • Triggered by: Airflow DAG (after data collection)       │
│ • Runs: docker image with make_features.py                │
│ • Inputs: Raw data from PVC                               │
│ • Outputs: Processed features → dvc push                  │
└───────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────┐
│ Model Training Service (Airflow Task → K8s Pod)           │
│ • Triggered by: Airflow DAG (after preprocessing)         │
│ • Runs: docker image with train_baseline.py               │
│ • Logs to: MLflow on DagsHub                              │
│ • Outputs: Model artifact → MLflow registry               │
└───────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────┐
│ Model Service (K8s Deployment, BentoML)                   │
│ • Runs: BentoML serving baseline.py                       │
│ • Loads: MLflow model from DagsHub                        │
│ • Reloaded by: Airflow DAG after training                 │
│ • API: POST /predict {"card_id": "...", "date": "..."}   │
│ • Scaling: 2-10 replicas (HPA)                            │
└───────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────┐
│ Decision Service (K8s Deployment)                         │
│ • Runs: FastAPI service wrapping decision_rules.py        │
│ • API: POST /signal {"market_price": X, "fair_price": Y} │
│ • Scaling: 2-5 replicas                                   │
└───────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────────────────────────────────────────┐
│ API Gateway Service (K8s Deployment)                      │
│ • Runs: Modified api/main.py (orchestration only)         │
│ • Auth: Existing API key authentication                   │
│ • Rate Limiting: Existing rate limiter                    │
│ • Routes: Calls Model Service + Decision Service          │
│ • Scaling: 2-5 replicas                                   │
└───────────────────────────────────────────────────────────┘
```

---

## Architecture Clarification

### Is This a Microservices Architecture?

**Answer**: **Yes, it's a hybrid microservices architecture** with two distinct layers:

#### **Layer 1: Microservices (User-Facing)**

These are **true microservices** - always-running, independently scalable HTTP services:

| Service | Type | Purpose | Replicas | Communication |
|---------|------|---------|----------|---------------|
| API Gateway | Microservice | Handle user requests | 2-5 | HTTP (external) |
| Model Service | Microservice | Serve ML predictions | 2-10 | HTTP (internal) |
| Decision Service | Microservice | Apply trading rules | 2-5 | HTTP (internal) |

**Characteristics**:
- ✅ Always running (24/7)
- ✅ Scale independently based on load
- ✅ Communicate via HTTP/REST
- ✅ Can be deployed independently
- ✅ Classic microservices pattern

#### **Layer 2: Batch Jobs (ML Pipeline)**

These are **NOT microservices** - they are event-driven batch processing tasks:

| Job | Type | Purpose | Frequency | Orchestration |
|-----|------|---------|-----------|---------------|
| Data Collection | Batch Job | Fetch card prices | Daily | Airflow DAG |
| Preprocessing | Batch Job | Feature engineering | After collection | Airflow DAG |
| Model Training | Batch Job | Train ML model | After preprocessing | Airflow DAG |

**Characteristics**:
- ⏰ Run on schedule (not always-on)
- 🔄 Short-lived (create pod → execute → terminate)
- 📊 Process data in batches
- 🎯 Orchestrated by Airflow
- ❌ NOT microservices (batch processing pattern)

### Industry Comparison

This hybrid pattern is **very common** in production ML systems:

- **Netflix**: Microservices (streaming API) + Batch Jobs (recommendation training)
- **Uber**: Microservices (ride requests) + Batch Jobs (pricing models)
- **Spotify**: Microservices (music playback) + Batch Jobs (playlist generation)
- **Amazon**: Microservices (product API) + Batch Jobs (recommendation updates)

### Why This Matters

Understanding the distinction helps you:
- **Scale appropriately**: Microservices scale based on traffic, batch jobs run on schedule
- **Monitor correctly**: Different metrics for API latency vs job completion time
- **Design properly**: Synchronous APIs vs asynchronous batch processing
- **Communicate clearly**: "We have 3 microservices + 3 scheduled ML jobs"

---

## Containerization & Minikube Architecture

### Docker Images Inventory

This microservices architecture requires **6 Docker images** built in Minikube's Docker daemon:

#### Microservices Layer (3 Images - Always Running)

| Image Name | Purpose | Base Image | Key Dependencies | Replicas |
|------------|---------|------------|------------------|----------|
| `pokewatch-api-gateway:latest` | API Gateway - User requests | `python:3.13-slim` | FastAPI, httpx, uvicorn | 2-5 |
| `pokewatch-model-service:latest` | Model predictions | `python:3.13-slim` | BentoML, pandas, pyarrow | 2-10 (HPA) |
| `pokewatch-decision-service:latest` | Trading signals | `python:3.13-slim` | FastAPI, uvicorn | 2-5 |

#### Batch Jobs Layer (1 Image - All ML Pipeline Steps)

| Image Name | Purpose | Base Image | Key Dependencies | Frequency |
|------------|---------|------------|------------------|-----------|
| `pokewatch-batch:latest` | Complete ML pipeline (collection + preprocessing + training) | `python:3.13-slim` | All project dependencies | Daily (2 AM) |

**Total Docker Images**: 4 separate images (3 microservices + 1 batch pipeline)

### Minikube Configuration

#### Resource Requirements

**Minimum Configuration**:
```bash
minikube start --driver=docker --memory=8192 --cpus=4
```

**Recommended Configuration** (for smooth operation):
```bash
minikube start --driver=docker --memory=12288 --cpus=6
```

**Breakdown**:
- **Airflow Infrastructure**: ~3-4GB RAM, ~1.5 CPUs (6 pods)
- **Microservices**: ~2-3GB RAM, ~1.5 CPUs (7-20 pods total)
- **Batch Pipeline** (during execution): ~2GB RAM, ~1 CPU (runs on Airflow worker)
- **Kubernetes System**: ~1GB RAM, ~0.5 CPUs
- **Total**: ~8-10GB RAM, ~4-5 CPUs

#### Docker Daemon Setup (No Docker Hub Required!)

**Step 1: Configure shell to use Minikube's Docker**
```bash
# Configure current shell session
eval $(minikube docker-env)

# Verify you're using Minikube's Docker
docker info | grep -i "name:"
# Output: Name: minikube

# List images in Minikube
docker images
```

**Step 2: Build images directly in Minikube**
```bash
# Navigate to project root
cd /path/to/pokewatch

# Build microservices images
docker build -t pokewatch-api-gateway:latest -f docker/api.Dockerfile .
docker build -t pokewatch-model-service:latest -f docker/model-service.Dockerfile .
docker build -t pokewatch-decision-service:latest -f docker/decision-service.Dockerfile .

# Build batch pipeline image (single image for all ML tasks)
docker build -t pokewatch-batch:latest -f docker/batch-pipeline.Dockerfile .

# Verify all images are built
docker images | grep pokewatch
```

**Step 3: Use images in Kubernetes manifests**
```yaml
# Example: k8s/api-deployment.yaml
spec:
  containers:
  - name: api-gateway
    image: pokewatch-api-gateway:latest
    imagePullPolicy: Never  # ← CRITICAL: Use local image, don't pull from registry
```

**Benefits of Minikube Docker Daemon**:
- ✅ **No Docker Hub account** required
- ✅ **No image push/pull** needed (saves time and bandwidth)
- ✅ **Works offline** (no internet needed after initial setup)
- ✅ **Faster builds** (no network latency)
- ✅ **Free** (no registry costs)
- ✅ **Private** (images stay on your machine)

**Important Notes**:
- ⚠️ Run `eval $(minikube docker-env)` in **every new terminal session**
- ⚠️ If you delete Minikube (`minikube delete`), **all images are lost** - rebuild required
- ⚠️ To revert to host Docker: `eval $(minikube docker-env -u)`

### Pod Count Estimates

#### Normal Operation (Outside Batch Execution Window)

| Component | Pod Count | Notes |
|-----------|-----------|-------|
| **Airflow Infrastructure** | | |
| - Webserver | 1 | Airflow UI |
| - Scheduler | 1 | DAG scheduling |
| - Worker | 1 | Task execution (Celery) |
| - Triggerer | 1 | Event-based triggers |
| - PostgreSQL | 1 | Airflow metadata DB |
| - Redis | 1 | Message queue |
| **Microservices (PokeWatch)** | | |
| - API Gateway | 2-5 | User-facing, scales with traffic |
| - Model Service | 2-10 | Scales with prediction load (HPA) |
| - Decision Service | 2-5 | Stateless, lightweight |
| **Total (Normal)** | **12-24 pods** | Airflow (6) + Microservices (6-18) |

#### During Batch Execution (Daily at 2 AM)

| Component | Pod Count | Duration | Notes |
|-----------|-----------|----------|-------|
| **Airflow + Microservices** | 12-24 | Always running | See above |
| **Batch Pipeline (runs on Airflow worker)** | | | |
| - All ML tasks run sequentially in worker pod | 0 | ~20-30 min total | No additional pods created |
| **Total (During Batch)** | **12-24 pods** | Same as normal | Batch runs inside existing Airflow worker |

**Key Points**:
- Batch pipeline runs **inside Airflow worker pod** (no new pods created)
- Total pipeline duration: ~20-30 minutes (collect → preprocess → train → deploy)
- Tasks run **sequentially** using BashOperator
- No KubernetesPodOperator = **no Kubernetes API permissions needed**
- Pod count stays constant at **12-24 pods**

#### Resource Distribution

```
┌─────────────────────────────────────────────────────────────┐
│ Minikube Cluster (8GB RAM, 4 CPUs)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Airflow Namespace (3-4GB RAM, 1.5 CPUs)                   │
│  ┌───────────────────────────────────────────────────┐     │
│  │ ✓ Webserver       (512MB RAM, 0.25 CPU)          │     │
│  │ ✓ Scheduler       (512MB RAM, 0.25 CPU)          │     │
│  │ ✓ Worker          (1GB RAM, 0.5 CPU)             │     │
│  │ ✓ Triggerer       (256MB RAM, 0.1 CPU)           │     │
│  │ ✓ PostgreSQL      (1GB RAM, 0.25 CPU)            │     │
│  │ ✓ Redis           (256MB RAM, 0.1 CPU)           │     │
│  │                                                   │     │
│  │ Batch Pipeline (during 2 AM window):             │     │
│  │ • Runs inside Worker pod (no extra pods)         │     │
│  │ • Sequential: collect → preprocess → train       │     │
│  │ • Total duration: ~20-30 minutes                 │     │
│  └───────────────────────────────────────────────────┘     │
│                                                             │
│  PokeWatch Namespace (2-3GB RAM, 1.5 CPUs)                 │
│  ┌───────────────────────────────────────────────────┐     │
│  │ ✓ API Gateway      (2-5 pods, 256MB each)        │     │
│  │ ✓ Model Service    (2-10 pods, 512MB each)       │     │
│  │ ✓ Decision Service (2-5 pods, 128MB each)        │     │
│  └───────────────────────────────────────────────────┘     │
│                                                             │
│  Kubernetes System (1GB RAM, 0.5 CPUs)                     │
│  ┌───────────────────────────────────────────────────┐     │
│  │ • kube-apiserver  • kube-scheduler                │     │
│  │ • kube-controller • etcd                          │     │
│  │ • CoreDNS         • kube-proxy                    │     │
│  └───────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Service Exposure & Communication

#### External Access (From Outside Cluster)

| Service | Type | Port | Access URL | Purpose |
|---------|------|------|------------|---------|
| API Gateway | NodePort / LoadBalancer | 30080 | `http://<minikube-ip>:30080` | User API requests |
| Airflow Webserver | Port-forward | 8080 | `http://localhost:8080` | Airflow UI (admin only) |

**Access Airflow UI**:
```bash
kubectl port-forward svc/airflow-webserver --address 0.0.0.0 8080:8080 -n airflow
# Then open: http://localhost:8080 (or http://VM-IP:8080 if remote)
```

**Access API**:
```bash
# Get Minikube IP
minikube ip
# Example output: 192.168.49.2

# Access API
curl http://192.168.49.2:30080/health
```

#### Internal Communication (Within Cluster)

| Source Service | Target Service | Protocol | URL | Purpose |
|----------------|----------------|----------|-----|---------|
| API Gateway | Model Service | HTTP | `http://model-service.pokewatch:3000` | Get predictions |
| API Gateway | Decision Service | HTTP | `http://decision-service.pokewatch:8001` | Get trading signals |
| Airflow Worker | DagsHub | HTTPS | DVC/MLflow APIs | Push data/models (from batch tasks) |
| Airflow Worker | Model Service | HTTP | `http://model-service.pokewatch:3000/reload` | Trigger model reload after training |

**Service Types Breakdown**:

```yaml
# API Gateway - External access (users)
kind: Service
metadata:
  name: pokewatch-api
  namespace: pokewatch
spec:
  type: NodePort  # or LoadBalancer in cloud
  ports:
  - port: 8000
    targetPort: 8000
    nodePort: 30080  # External access

---
# Model Service - Internal only (ClusterIP)
kind: Service
metadata:
  name: model-service
  namespace: pokewatch
spec:
  type: ClusterIP  # Internal only!
  ports:
  - port: 3000
    targetPort: 3000

---
# Decision Service - Internal only (ClusterIP)
kind: Service
metadata:
  name: decision-service
  namespace: pokewatch
spec:
  type: ClusterIP  # Internal only!
  ports:
  - port: 8001
    targetPort: 8001
```

**Why ClusterIP for Model and Decision Services?**
- ✅ **Security**: Not exposed to external network
- ✅ **Performance**: Internal DNS resolution (faster)
- ✅ **Simplicity**: No need for authentication on internal services
- ✅ **Best Practice**: Only API Gateway should be public

### Image Build Summary

**One-time setup per Minikube instance**:
```bash
# 1. Point to Minikube Docker
eval $(minikube docker-env)

# 2. Build all 4 images (run from pokewatch/ directory)
docker build -t pokewatch-api-gateway:latest -f docker/api.Dockerfile .
docker build -t pokewatch-model-service:latest -f docker/model-service.Dockerfile .
docker build -t pokewatch-decision-service:latest -f docker/decision-service.Dockerfile .
docker build -t pokewatch-batch:latest -f docker/batch-pipeline.Dockerfile .

# 3. Verify
docker images | grep pokewatch
# Should show 4 images with "latest" tag

# 4. Deploy to Kubernetes
kubectl apply -f k8s/

# 5. Configure Airflow to use pokewatch-batch image for workers
```

**When to rebuild**:
- ❌ After `minikube delete` (all images lost)
- ❌ After code changes to any service
- ✅ Use `docker build` again to update images
- ✅ Then restart pods: `kubectl rollout restart deployment/<service> -n pokewatch`

---

## Implementation Plan (7 Phases)

### **Phase 1: Prepare Shared Infrastructure** (Week 1, Day 1)

**Goal**: Set up centralized MLOps tools + Apache Airflow

**Status**: Partially implemented (need to add Airflow!)

✅ **Already Complete**:
- DagsHub account with MLflow + DVC
- DVC remote configured
- MLflow tracking URI configured
- Kubernetes cluster (Minikube) running

🆕 **NEW: Install Apache Airflow via Helm** (3 hours)

#### 1.1 Add Airflow Helm Repository (5 min)

```bash
# Add official Airflow chart repository
helm repo add apache-airflow https://airflow.apache.org
helm repo update

# Verify
helm repo list
```

#### 1.2 Create Airflow Namespace (2 min)

```bash
kubectl create namespace airflow
kubectl config set-context --current --namespace=airflow
```

#### 1.3 Download and Configure Values (30 min)

```bash
# Download default values
helm show values apache-airflow/airflow > airflow-values.yaml
```

**Create custom values file**: `airflow-my-values.yaml`

```yaml
# Executor: Use CeleryExecutor (simpler than CeleryKubernetesExecutor)
executor: CeleryExecutor

# User credentials
webserver:
  defaultUser:
    username: admin
    password: admin  # Change in production!

# Use custom batch pipeline image for workers
images:
  airflow:
    repository: pokewatch-batch  # Custom image with all dependencies
    tag: latest
    pullPolicy: Never  # Use local Minikube image

# DAG folder configuration
dags:
  persistence:
    enabled: true
    existingClaim: airflow-dags-pvc

# Logs folder configuration
logs:
  persistence:
    enabled: true
    existingClaim: airflow-logs-pvc

# User/group IDs for permissions
uid: 1000
gid: 1000

# Scheduler configuration
scheduler:
  env:
  - name: AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL
    value: "30"  # Scan for new DAGs every 30 seconds

# Worker configuration
workers:
  replicas: 1  # Start with 1 worker
  resources:
    requests:
      memory: "2Gi"
      cpu: "1"
    limits:
      memory: "4Gi"
      cpu: "2"
```

#### 1.4 Create PersistentVolumes for DAGs and Logs (30 min)

**File**: `k8s/airflow-dags-pv.yaml` (NEW)

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: airflow-dags-folder
  namespace: airflow
spec:
  storageClassName: local-path
  capacity:
    storage: 2Gi
  accessModes:
    - ReadWriteOnce
  claimRef:
    namespace: airflow
    name: airflow-dags-pvc
  hostPath:
    path: "/home/ubuntu/kubernetes/airflow/dags"
```

**File**: `k8s/airflow-dags-pvc.yaml` (NEW)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: airflow-dags-pvc
  namespace: airflow
spec:
  storageClassName: local-path
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 2Gi
```

Repeat for logs (`airflow-logs-pv.yaml`, `airflow-logs-pvc.yaml`)

```bash
# Create folders
mkdir -p ~/kubernetes/airflow/dags
mkdir -p ~/kubernetes/airflow/logs

# Deploy PVs and PVCs
kubectl create -f k8s/airflow-dags-pv.yaml
kubectl create -f k8s/airflow-dags-pvc.yaml
kubectl create -f k8s/airflow-logs-pv.yaml
kubectl create -f k8s/airflow-logs-pvc.yaml
```

#### 1.5 Install Airflow (15 min)

```bash
# Install Airflow with custom values
helm upgrade --install airflow apache-airflow/airflow \
  --namespace airflow \
  --create-namespace \
  -f airflow-my-values.yaml

# Wait for pods to be ready (takes 3-5 minutes)
kubectl get pods -n airflow -w
```

**Expected pods**:
- `airflow-webserver-*` - UI
- `airflow-scheduler-*` - DAG scheduler
- `airflow-worker-*` - Task executor
- `airflow-triggerer-*` - Event triggers
- `airflow-postgresql-*` - Metadata database
- `airflow-redis-*` - Message queue

#### 1.6 Access Airflow UI (10 min)

```bash
# Port-forward to access UI
kubectl port-forward svc/airflow-webserver --address 0.0.0.0 8080:8080 -n airflow

# Access at: http://<VM-IP>:8080
# Username: admin
# Password: admin
```

#### 1.7 Create Data PVC for ML Pipeline (30 min)

ML tasks will share data via PersistentVolumes:

**File**: `k8s/ml-data-pv.yaml` (NEW)

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: ml-data-folder
  namespace: airflow
spec:
  storageClassName: local-path
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  claimRef:
    namespace: airflow
    name: ml-data-pvc
  hostPath:
    path: "/home/ubuntu/kubernetes/pokewatch/data"
```

**File**: `k8s/ml-data-pvc.yaml` (NEW)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-data-pvc
  namespace: airflow
spec:
  storageClassName: local-path
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

```bash
kubectl create -f k8s/ml-data-pv.yaml
kubectl create -f k8s/ml-data-pvc.yaml
```

**Total Time**: ~3 hours
**Existing Code Modified**: 0 files
**New Files Created**: 7 files (PVs, PVCs, values file)

---

### **Phase 2: Extract Model Service** (Week 1)

**Goal**: Create standalone Model Service using BentoML

#### 2.1 Create BentoML Service (2 hours)

**File**: `pokewatch/services/model_service/bento_service.py` (NEW)

```python
# Wraps existing baseline.py - NO CHANGES to baseline.py needed!
import bentoml
from bentoml.io import JSON
from pokewatch.models.baseline import load_baseline_model

@bentoml.service(
    resources={"cpu": "2"},
    traffic={"timeout": 10}
)
class ModelService:
    def __init__(self):
        self.model = load_baseline_model()  # Reuses existing code!

    @bentoml.api
    def predict(self, card_id: str, date: str = None) -> dict:
        resolved_date, market_price, fair_price = self.model.predict(
            card_id=card_id,
            date=date
        )
        return {
            "card_id": card_id,
            "date": str(resolved_date),
            "market_price": market_price,
            "fair_price": fair_price
        }
```

**Code Changes**: ZERO changes to existing `baseline.py`

#### 2.2 Create Dockerfile (15 min)

**File**: `pokewatch/services/model_service/Dockerfile` (NEW)

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install bentoml pandas pyarrow pyyaml
CMD ["bentoml", "serve", "bento_service:ModelService", "--host", "0.0.0.0"]
```

#### 2.3 Create Kubernetes Manifests (30 min)

**Files**:
- `k8s/model-service-deployment.yaml` (NEW)
- `k8s/model-service-service.yaml` (NEW)
- `k8s/model-service-hpa.yaml` (NEW)

**Code Changes**: None to existing files

#### 2.4 Test Model Service (1 hour)

```bash
# Build and deploy
bentoml build services/model_service/bento_service.py
kubectl apply -f k8s/model-service-*.yaml

# Test
curl -X POST http://model-service:3000/predict \
  -d '{"card_id": "charizard_ex_199", "date": "2025-12-01"}'
```

**Total Time**: ~4 hours
**Existing Code Modified**: 0 files
**New Files Created**: 4 files

---

### **Phase 3: Extract Decision Service** (Week 1)

**Goal**: Standalone service for BUY/SELL/HOLD logic

#### 3.1 Create Decision Service API (1 hour)

**File**: `pokewatch/services/decision_service/main.py` (NEW)

```python
# Wraps existing decision_rules.py - NO CHANGES to decision_rules.py!
from fastapi import FastAPI
from pydantic import BaseModel
from pokewatch.core.decision_rules import compute_signal, DecisionConfig

app = FastAPI(title="Decision Service")

class SignalRequest(BaseModel):
    market_price: float
    fair_price: float
    buy_threshold_pct: float = 0.10
    sell_threshold_pct: float = 0.15

@app.post("/signal")
def get_signal(req: SignalRequest):
    cfg = DecisionConfig(
        buy_threshold_pct=req.buy_threshold_pct,
        sell_threshold_pct=req.sell_threshold_pct
    )
    signal, deviation_pct = compute_signal(
        market_price=req.market_price,
        fair_price=req.fair_price,
        cfg=cfg
    )  # Reuses existing function!
    return {
        "signal": signal,
        "deviation_pct": deviation_pct
    }

@app.get("/health")
def health():
    return {"status": "ok"}
```

**Code Changes**: ZERO changes to existing `decision_rules.py`

#### 3.2 Create Dockerfile (15 min)

**File**: `pokewatch/services/decision_service/Dockerfile` (NEW)

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install fastapi uvicorn
CMD ["uvicorn", "services.decision_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

#### 3.3 Create Kubernetes Manifests (30 min)

**Files**:
- `k8s/decision-service-deployment.yaml` (NEW)
- `k8s/decision-service-service.yaml` (NEW)

#### 3.4 Test Decision Service (30 min)

```bash
curl -X POST http://decision-service:8001/signal \
  -d '{"market_price": 90, "fair_price": 100}'
# Expected: {"signal": "BUY", "deviation_pct": -0.1}
```

**Total Time**: ~2.5 hours
**Existing Code Modified**: 0 files
**New Files Created**: 4 files

---

### **Phase 4: Convert API to Gateway** (Week 1)

**Goal**: Modify existing API to orchestrate services instead of doing everything

#### 4.1 Modify API Endpoints (2 hours)

**File**: `pokewatch/src/pokewatch/api/main.py` (MODIFIED)

**Changes**: Replace inline logic with service calls

**Before** (lines 188-214):
```python
# Predict fair price (inline)
resolved_date, market_price, fair_price = model.predict(
    card_id=payload.card_id,
    date=payload.date,
)

# Compute trading signal (inline)
signal, deviation_pct = compute_signal(market_price, fair_price, decision_cfg)
```

**After**:
```python
# Call Model Service
import httpx
model_response = httpx.post(
    "http://model-service:3000/predict",
    json={"card_id": payload.card_id, "date": payload.date}
).json()

# Call Decision Service
decision_response = httpx.post(
    "http://decision-service:8001/signal",
    json={
        "market_price": model_response["market_price"],
        "fair_price": model_response["fair_price"]
    }
).json()

# Combine responses
return FairPriceResponse(
    card_id=payload.card_id,
    date=model_response["date"],
    market_price=model_response["market_price"],
    fair_price=model_response["fair_price"],
    deviation_pct=decision_response["deviation_pct"],
    signal=decision_response["signal"],
)
```

**Lines Modified**: ~30 lines in `api/main.py`
**Other Files**: Update `requirements.txt` to add `httpx`

#### 4.2 Update Kubernetes Manifests (30 min)

**File**: `k8s/api-deployment.yaml` (MODIFIED)

Add environment variables for service URLs:
```yaml
env:
  - name: MODEL_SERVICE_URL
    value: "http://model-service:3000"
  - name: DECISION_SERVICE_URL
    value: "http://decision-service:8001"
```

#### 4.3 Test API Gateway (1 hour)

```bash
# Deploy all services
kubectl apply -f k8s/

# Test end-to-end
curl -X POST http://localhost:8000/fair_price \
  -H "X-API-Key: your-key" \
  -d '{"card_id": "charizard_ex_199"}'

# Should return same result as before, but now calls 2 services internally
```

**Total Time**: ~3.5 hours
**Existing Code Modified**: 1 file (`api/main.py` - ~30 lines)
**New Files Created**: 0 files

---

### **Phase 5: Extract Data Collector Service** (Week 2)

**Goal**: Convert manual script to scheduled Kubernetes CronJob

#### 5.1 Create Kubernetes CronJob (1 hour)

**File**: `k8s/data-collector-cronjob.yaml` (MODIFIED - already exists!)

**Good news**: This file already exists at `k8s/cron-collector.yaml`!

**Actions**:
1. Review existing CronJob manifest
2. Update schedule if needed (currently daily)
3. Ensure it pushes to DVC after collection

**Additions to daily_price_collector.py** (~20 lines):
```python
# At end of collect_daily_prices() function
def collect_daily_prices(...):
    # ... existing code ...

    # NEW: Push to DVC after collection
    import subprocess
    logger.info("Pushing data to DVC remote...")
    subprocess.run(["dvc", "add", str(output_file)])
    subprocess.run(["dvc", "push"])
    logger.info("Data pushed to DVC successfully")

    return output_file
```

**Code Changes**: ~20 lines added to `daily_price_collector.py`

#### 5.2 Test CronJob (30 min)

```bash
# Trigger manual run
kubectl create job --from=cronjob/data-collector manual-run-1 -n pokewatch

# Check logs
kubectl logs job/manual-run-1 -n pokewatch

# Verify data in DagsHub
```

**Total Time**: ~1.5 hours
**Existing Code Modified**: 1 file (`daily_price_collector.py` - ~20 lines)
**New Files Created**: 0 files (CronJob already exists!)

---

### **Phase 6: Create Airflow DAGs for ML Orchestration** (Week 2)

**Goal**: Orchestrate the full ML pipeline using Airflow DAGs with BashOperator

#### 6.1 Build Batch Pipeline Docker Image (1 hour)

Create a single Docker image with all dependencies for the ML pipeline.

**IMPORTANT**: We'll use **Minikube's Docker daemon** (no Docker Hub required!)

**File**: `docker/batch-pipeline.Dockerfile` (NEW)

```dockerfile
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install all Python dependencies (data collection, preprocessing, training, MLflow, DVC)
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    pyarrow \
    pyyaml \
    requests \
    httpx \
    scikit-learn \
    mlflow \
    dvc \
    dvc-s3 \
    python-dotenv \
    pydantic \
    pydantic-settings

# Install project in editable mode
RUN pip install -e .

# Default command (will be overridden by Airflow tasks)
CMD ["python", "--version"]
```

**Build the image**:

```bash
# Point to Minikube's Docker daemon
eval $(minikube docker-env)

# Build batch pipeline image
cd /path/to/pokewatch
docker build -t pokewatch-batch:latest -f docker/batch-pipeline.Dockerfile .

# Verify
docker images | grep pokewatch-batch
```

**Benefits of this approach**:
- ✅ No Docker Hub account needed
- ✅ No push/pull time (faster builds)
- ✅ Works offline
- ✅ Single image for all ML tasks
- ✅ No KubernetesPodOperator = No K8s API permissions needed
- ✅ Free!

#### 6.2 Create Kubernetes Secrets for Credentials (30 min)

Airflow tasks need access to API keys and DagsHub credentials.

**File**: `k8s/ml-secrets.yaml` (NEW)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ml-secrets
  namespace: airflow
type: Opaque
stringData:
  # Plain text values (kubectl will base64 encode them)
  POKEMON_PRICE_API_KEY: "your-pokemon-api-key-here"
  DAGSHUB_USER_TOKEN: "your-dagshub-token-here"
  DAGSHUB_USER_NAME: "your-dagshub-username"
  MLFLOW_TRACKING_URI: "https://dagshub.com/your-username/pokewatch.mlflow"
```

```bash
# Create secrets
kubectl apply -f k8s/ml-secrets.yaml -n airflow

# Verify
kubectl get secrets -n airflow | grep ml-secrets
```

#### 6.3 Create Airflow DAG: ml_pipeline.py (2 hours)

**File**: `~/kubernetes/airflow/dags/ml_pipeline.py` (NEW)

```python
"""
ML Pipeline DAG for PokeWatch
Orchestrates: Data Collection → Preprocessing → Training → Model Deployment
Uses BashOperator to run tasks inside Airflow worker pod
"""
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

# Default arguments for all tasks
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Define DAG
with DAG(
    dag_id='ml_pipeline',
    description='PokeWatch ML Pipeline: Collect → Preprocess → Train → Deploy',
    tags=['pokewatch', 'ml', 'batch'],
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=days_ago(1),
    catchup=False,
    default_args=default_args,
) as dag:

    # Task 1: Data Collection
    collect_data = BashOperator(
        task_id='collect_data',
        bash_command='''
        set -e
        echo "Starting data collection..."
        cd /app

        # Run data collector
        python -m pokewatch.data.collectors.daily_price_collector \
            --days 7 \
            --format parquet

        # Push to DVC
        echo "Pushing data to DVC..."
        dvc add data/raw/*.parquet
        dvc push

        echo "Data collection completed successfully"
        ''',
        env={
            'POKEMON_PRICE_API_KEY': '{{ var.value.POKEMON_PRICE_API_KEY }}',
            'DAGSHUB_USER_TOKEN': '{{ var.value.DAGSHUB_USER_TOKEN }}',
        },
    )

    # Task 2: Preprocessing
    preprocess_data = BashOperator(
        task_id='preprocess_data',
        bash_command='''
        set -e
        echo "Starting preprocessing..."
        cd /app

        # Pull latest data from DVC
        dvc pull data/raw

        # Run preprocessing
        python -m pokewatch.data.preprocessing.make_features

        # Push processed data to DVC
        echo "Pushing processed data to DVC..."
        dvc add data/processed/*.parquet
        dvc push

        echo "Preprocessing completed successfully"
        ''',
        env={
            'DAGSHUB_USER_TOKEN': '{{ var.value.DAGSHUB_USER_TOKEN }}',
        },
    )

    # Task 3: Model Training
    train_model = BashOperator(
        task_id='train_model',
        bash_command='''
        set -e
        echo "Starting model training..."
        cd /app

        # Pull latest processed data from DVC
        dvc pull data/processed

        # Run training (logs to MLflow automatically)
        python -m pokewatch.models.train_baseline

        echo "Model training completed successfully"
        echo "Model logged to MLflow registry"
        ''',
        env={
            'MLFLOW_TRACKING_URI': '{{ var.value.MLFLOW_TRACKING_URI }}',
            'DAGSHUB_USER_TOKEN': '{{ var.value.DAGSHUB_USER_TOKEN }}',
        },
    )

    # Task 4: Deploy Model (trigger Model Service reload)
    deploy_model = BashOperator(
        task_id='deploy_model',
        bash_command='''
        set -e
        echo "Triggering model service reload..."

        # Send reload signal to Model Service
        curl -X POST \
            -H "Content-Type: application/json" \
            http://model-service.pokewatch.svc.cluster.local:3000/reload \
            || echo "Warning: Model service reload failed, will reload on next request"

        echo "Model deployment completed"
        ''',
    )

    # Define task dependencies (sequential execution)
    collect_data >> preprocess_data >> train_model >> deploy_model
```

**Key Features**:
- ✅ **BashOperator**: Runs commands inside Airflow worker pod (no new pods created)
- ✅ **No Kubernetes API calls**: Simpler, no RBAC issues
- ✅ **Sequential execution**: Tasks run one after another
- ✅ **Retry logic**: Each task retries up to 2 times on failure
- ✅ **DVC integration**: Automatic data versioning
- ✅ **MLflow integration**: Automatic experiment tracking
- ✅ **Error handling**: `set -e` exits on first error

#### 6.4 Create Init DAG for Setup (1 hour)

**File**: `~/kubernetes/airflow/dags/init_ml.py` (NEW)

```python
"""
Init DAG - Run once to set up ML infrastructure
Creates necessary directories, connections, etc.
"""
from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.bash import BashOperator

with DAG(
    dag_id='init_ml',
    description='Initialize ML infrastructure (run once)',
    tags=['pokewatch', 'setup'],
    schedule_interval=None,  # Manual trigger only
    start_date=days_ago(1),
    catchup=False
) as dag:

    create_directories = BashOperator(
        task_id='create_directories',
        bash_command='''
        mkdir -p /app/data/raw
        mkdir -p /app/data/interim
        mkdir -p /app/data/processed
        mkdir -p /app/models/baseline
        echo "Directories created successfully"
        '''
    )

    verify_dvc = BashOperator(
        task_id='verify_dvc',
        bash_command='dvc version && echo "DVC is installed"'
    )

    create_directories >> verify_dvc
```

#### 6.4 Configure Airflow Variables (15 min)

Set up environment variables for Airflow tasks.

```bash
# Access Airflow UI
kubectl port-forward svc/airflow-webserver 8080:8080 -n airflow

# Open browser: http://localhost:8080
# Login: admin / admin

# Navigate to: Admin → Variables

# Add these variables:
# Key: POKEMON_PRICE_API_KEY, Value: <your-api-key>
# Key: DAGSHUB_USER_TOKEN, Value: <your-dagshub-token>
# Key: MLFLOW_TRACKING_URI, Value: https://dagshub.com/<username>/pokewatch.mlflow
```

#### 6.5 Test Airflow DAGs (2 hours)

```bash
# Copy DAGs to Airflow folder
cp dags/ml_pipeline.py ~/kubernetes/airflow/dags/
cp dags/init_ml.py ~/kubernetes/airflow/dags/

# Wait for Airflow to detect DAGs (30 seconds with our config)
# Check in Airflow UI: http://localhost:8080

# Trigger init_ml DAG first (one-time setup)
# Then trigger ml_pipeline DAG manually to test

# Monitor logs in Airflow UI → DAGs → ml_pipeline → Graph View
```

**Verification**:
1. ✅ Check Airflow UI shows both DAGs
2. ✅ Trigger `init_ml` DAG manually
3. ✅ Verify all tasks complete successfully (green in UI)
4. ✅ Trigger `ml_pipeline` DAG manually
5. ✅ Monitor worker pod logs: `kubectl logs -f -n airflow <worker-pod-name>`
6. ✅ Check task logs in Airflow UI (click on task → View Log)
7. ✅ Verify data in DagsHub DVC (check commits)
8. ✅ Verify model in MLflow registry (check experiments)

**Total Time**: ~4 hours (reduced from 8.5 hours - no KubernetesPodOperator complexity!)
**Existing Code Modified**: 0 files
**New Files Created**: 3 files (Dockerfile, DAG, secrets)

---

### **Phase 7: Monitoring & Validation** (Week 2)

**Goal**: Ensure all services are healthy and communicating

#### 7.1 Add Service Health Checks (1 hour)

Add `/health` endpoints to all services (already done for most!)

#### 7.2 Create Verification Script (2 hours)

**File**: `scripts/verify_microservices.sh` (NEW)

```bash
#!/bin/bash
# Verify all microservices are running

echo "1. Checking Data Collector CronJob..."
kubectl get cronjob data-collector -n pokewatch

echo "2. Checking Model Service..."
curl http://model-service:3000/health

echo "3. Checking Decision Service..."
curl http://decision-service:8001/health

echo "4. Checking API Gateway..."
curl http://localhost:8000/health

echo "5. Testing end-to-end flow..."
curl -X POST http://localhost:8000/fair_price \
  -H "X-API-Key: $API_KEY" \
  -d '{"card_id": "charizard_ex_199"}'
```

#### 7.3 Performance Testing (2 hours)

Compare monolith vs microservices:
- Latency (expect slight increase due to network calls)
- Throughput (should be similar)
- Resource usage (should be more efficient with independent scaling)

**Total Time**: ~5 hours
**Existing Code Modified**: 0 files
**New Files Created**: 1 file

---

## Summary of Changes

### Total Implementation Time

| Phase | Time | Code Modified | New Files |
|-------|------|---------------|-----------|
| Phase 1: Airflow + Infrastructure | 3h | 0 files | 7 |
| Phase 2: Model Service | 4h | 0 files | 4 |
| Phase 3: Decision Service | 2.5h | 0 files | 4 |
| Phase 4: API Gateway | 3.5h | 1 file (30 lines) | 0 |
| Phase 5: Data Collector | 1.5h | 1 file (20 lines) | 0 |
| Phase 6: Airflow DAGs (BashOperator) | 4h | 0 files | 3 |
| Phase 7: Monitoring | 5h | 0 files | 1 |
| **TOTAL** | **~23.5 hours** | **2 files** | **19 files** |

### Files Modified (Minimal Changes!)

1. **`pokewatch/src/pokewatch/api/main.py`** - ~30 lines
   - Replace inline model/decision calls with HTTP calls to services

2. **`pokewatch/data/collectors/daily_price_collector.py`** - ~20 lines
   - Add DVC push after data collection

### New Files Created

**Phase 1: Airflow Infrastructure (7 files)**
1. `k8s/airflow-dags-pv.yaml` - PV for DAGs
2. `k8s/airflow-dags-pvc.yaml` - PVC for DAGs
3. `k8s/airflow-logs-pv.yaml` - PV for logs
4. `k8s/airflow-logs-pvc.yaml` - PVC for logs
5. `k8s/ml-data-pv.yaml` - PV for ML data
6. `k8s/ml-data-pvc.yaml` - PVC for ML data
7. `airflow-my-values.yaml` - Airflow Helm values

**Phase 2: Model Service (4 files)**
8. `services/model_service/bento_service.py` - BentoML wrapper
9. `services/model_service/Dockerfile` - Container for Model Service
10. `k8s/model-service-deployment.yaml` - K8s deployment
11. `k8s/model-service-service.yaml` - K8s service

**Phase 3: Decision Service (4 files)**
12. `services/decision_service/main.py` - FastAPI wrapper for decisions
13. `services/decision_service/Dockerfile` - Container for Decision Service
14. `k8s/decision-service-deployment.yaml` - K8s deployment
15. `k8s/decision-service-service.yaml` - K8s service

**Phase 6: Airflow DAGs (3 files)**
16. `docker/batch-pipeline.Dockerfile` - Single image for all ML tasks
17. `k8s/ml-secrets.yaml` - Secrets for ML tasks
18. `~/kubernetes/airflow/dags/ml_pipeline.py` - Main ML pipeline DAG (BashOperator)

**Phase 7: Monitoring (1 file)**
19. `scripts/verify_microservices.sh` - Verification script

---

## Migration Strategy (Gradual Rollout)

### Strategy: Strangler Fig Pattern

Run **both** architectures simultaneously and gradually shift traffic:

```
Week 1:
├── Monolith (100% traffic) ✅
└── Microservices (deployed, 0% traffic) 🆕

Week 2:
├── Monolith (50% traffic)
└── Microservices (50% traffic) 🔄

Week 3:
├── Monolith (0% traffic, standby)
└── Microservices (100% traffic) ✅

Week 4:
└── Microservices only (retire monolith) 🎉
```

### Deployment Order

1. **Deploy all microservices** (keep monolith running)
2. **Test microservices independently** (no user traffic yet)
3. **Route 10% traffic** to microservices via load balancer
4. **Monitor metrics** (latency, errors, resource usage)
5. **Gradually increase** to 50%, then 100%
6. **Retire monolith** when confident

---

## Rollback Plan

### If Issues Arise

**Immediate Rollback** (5 minutes):
```bash
# Route all traffic back to monolith
kubectl scale deployment/model-service --replicas=0 -n pokewatch
kubectl scale deployment/decision-service --replicas=0 -n pokewatch
# Monolith still running, immediately takes all traffic
```

**No Data Loss**: DVC/MLflow/DagsHub are shared, so no data is lost

---

## Benefits vs Costs

### Benefits

✅ **Independent Scaling**
- Model Service can scale 2-10 replicas based on prediction load
- API Gateway stays at 2-5 replicas for routing
- Data Collector runs once daily (CronJob)

✅ **Faster Deployments**
- Update model without redeploying entire API
- Update decision rules without affecting data collection
- Update API gateway without touching ML code

✅ **Better Resource Usage**
- Model Service gets more CPU/memory for predictions
- Decision Service is lightweight, needs less resources
- No wasted resources on idle components

✅ **Clearer Ownership**
- Data team owns Data Collector
- ML team owns Model Service
- Product team owns API Gateway & Decision Service

✅ **MLOps Integration**
- **Airflow** orchestrates entire ML pipeline (data → preprocessing → training → deployment)
- **BentoML** handles model serving optimizations
- **MLflow/DVC/DagsHub** work seamlessly across services
- **KubernetesPodOperator** provides isolated task execution

### Costs

⚠️ **Slight Latency Increase**
- Monolith: 1 internal function call
- Microservices: 2 HTTP calls (Model + Decision)
- Estimated increase: +20-50ms per request
- Mitigation: Use in-cluster networking (fast), add caching

⚠️ **More Operational Complexity**
- 4 services to monitor instead of 1
- Mitigation: Use existing K8s monitoring, verification scripts

⚠️ **Network Overhead**
- HTTP calls between services
- Mitigation: Deploy in same namespace, use ClusterIP services (not NodePort)

⚠️ **Development Effort**
- ~23.5 hours of implementation time (reduced from 28h with BashOperator approach)
- Mitigation: Most code is reused, minimal changes

⚠️ **Additional Infrastructure**
- Airflow requires 6 additional pods (webserver, scheduler, worker, triggerer, PostgreSQL, Redis)
- Estimated +2-3GB RAM, +1-2 CPU cores
- **Benefit**: No extra pods for batch jobs (runs inside worker)
- Mitigation: Increase Minikube resources or use cloud K8s

---

## Success Criteria

### Functional Requirements

- ✅ API returns same results as monolith
- ✅ All endpoints respond within 200ms (p95)
- ✅ Data collection runs daily automatically via Airflow
- ✅ Model training pipeline completes successfully via Airflow DAG
- ✅ Model updates don't require API restart
- ✅ Airflow UI accessible and shows all DAGs
- ✅ All health checks pass

### Non-Functional Requirements

- ✅ Model Service scales independently based on load
- ✅ Can deploy new model version without downtime
- ✅ Can rollback to monolith in <5 minutes
- ✅ Total resource usage ≤ 110% of monolith (slight overhead acceptable)
- ✅ Error rate ≤ 0.1%

---

## Questions for Validation

Before proceeding with implementation, please confirm:

### 1. **Architecture Confirmation**
- ❓ Is the hybrid architecture clear? (3 microservices + 3 batch jobs)
  - **Microservices**: API Gateway, Model Service, Decision Service (always running)
  - **Batch Jobs**: Data Collection, Preprocessing, Training (Airflow-scheduled)
- ❓ Acceptable that batch jobs are NOT microservices but scheduled tasks?

### 2. **Timeline Confirmation**
- ❓ Is 3-4 weeks acceptable for full migration (includes Airflow learning curve)?
- ❓ Should we do this all at once or phase by phase?

### 3. **Resource Confirmation**
- ❓ Can Minikube handle 4 microservices + 6 Airflow pods? (Total ~10 pods)
  - **Recommendation**: Increase Minikube to 8GB RAM, 4 CPUs minimum
  - Command: `minikube start --memory=8192 --cpus=4`
- ❓ Should we plan for cloud deployment (GKE/EKS) eventually?

### 4. **Orchestration Confirmation**
- ❓ Proceed with **Airflow Helm chart** for orchestration? (as per your lesson)
- ❓ Use **CeleryKubernetesExecutor** for flexibility? (small tasks on workers, large tasks on K8s pods)
- ❓ Proceed with **BentoML** for Model Service? (vs plain FastAPI)

### 5. **Image Registry Confirmation** ✅ RESOLVED
- ✅ **No Docker Hub needed!** Using Minikube's Docker daemon
- ✅ Images built locally with `eval $(minikube docker-env)`
- ✅ `imagePullPolicy='Never'` in Airflow DAGs
- ❓ This approach acceptable for local development?

### 6. **Risk Acceptance**
- ❓ Acceptable to have +20-50ms latency increase?
- ❓ Acceptable to increase operational complexity (Airflow adds 6 pods)?
- ❓ Acceptable to require Minikube resource increase?

---

## Next Steps After Approval

1. **You approve this plan** ✅
2. **Increase Minikube resources** (8GB RAM, 4 CPUs)
3. **Start with Phase 1** (Install Airflow via Helm)
4. **Continue with Phase 2-7** (Extract microservices, create DAGs)
5. **Test each phase thoroughly** before moving to next
6. **Document as we go** (update architecture diagrams, API docs)
7. **Deploy first Airflow DAG** and verify end-to-end pipeline

---

## Conclusion

This plan provides a **pragmatic, low-risk path** to microservices by:

- **Reusing 95% of existing code** (only 50 lines modified!)
- **Leveraging existing MLOps stack** (MLflow, DVC, DagsHub, BentoML)
- **Using Apache Airflow** for production-grade orchestration (official Helm chart)
- **Following DataScientest best practices** (KubernetesPodOperator, CeleryKubernetesExecutor)
- **Using existing Kubernetes infrastructure** (Minikube with increased resources)
- **Allowing gradual rollout** (can run both architectures simultaneously)
- **Providing quick rollback** (5 minutes to revert)

## Key Airflow Features Implemented

Based on your DataScientest lesson and practical considerations, this plan implements:

✅ **Airflow Helm Chart Installation** (Phase 1)
- Official Apache Airflow chart from https://airflow.apache.org
- Custom values configuration with `pokewatch-batch` image
- PersistentVolumes for DAGs and logs

✅ **BashOperator for ML Pipeline** (Phase 6) - **UPDATED APPROACH**
- Runs tasks inside Airflow worker pod (no new pods created)
- Uses custom `pokewatch-batch:latest` image with all dependencies
- Simpler than KubernetesPodOperator (no K8s API permissions needed)
- Sequential execution: collect → preprocess → train → deploy

✅ **CeleryExecutor** (Phase 1)
- Worker pods execute batch tasks
- Uses custom Docker image with all ML dependencies
- Simpler than CeleryKubernetesExecutor (no pod spawning)

✅ **Secrets Management** (Phase 6.2)
- Kubernetes Secrets for API keys and credentials
- Airflow Variables for runtime configuration
- Environment variables passed to BashOperator tasks

✅ **DAG Scheduling** (Phase 6.3)
- Daily schedule for ML pipeline (`0 2 * * *`)
- Task dependencies: `collect_data >> preprocess_data >> train_model >> deploy_model`
- Automatic retries (2 retries with 5-minute delay)

✅ **MLOps Integration**
- DVC push/pull integrated into tasks
- MLflow tracking automatic in training task
- Model reload signal to microservices after training

**Ready to proceed?** Please review and let me know if you'd like to:
- ✅ Approve as-is and start implementation
- 🔄 Modify specific phases
- ❓ Discuss any concerns or questions

---

**Author**: Claude Code
**Reviewers**: [Your Name]
**Status**: Awaiting Approval (Updated with Airflow Orchestration)
