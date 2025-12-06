# Kubernetes Deployment - Simple Implementation Plan

**Focus:** Implémenter la scalabilité avec Docker/Kubernetes (Only)
**Context:** MLOps course project - demonstrate container orchestration basics
**Time:** 2-3 days maximum
**Approach:** Local Kubernetes (Minikube) - simple and educational

---

## Overview

We already have:
- ✅ Docker images (FastAPI, BentoML)
- ✅ CI/CD (builds Docker images automatically)
- ✅ ZenML pipeline orchestration
- ✅ Security and monitoring ready

Now we add:
- ⏳ Kubernetes deployment (local Minikube)
- ⏳ Container orchestration and scaling

**Goal:** Demonstrate how to deploy and scale containerized ML applications with Kubernetes.

---

## Prerequisites

Already working:
```bash
cd /Users/beatrice/Documents/data_scientest/projet/pokewatch

# Existing Docker images
docker images | grep pokewatch

# Expected:
# pokewatch-api
# pokewatch-bento (optional)
```

---

## Day 1: Minikube Setup & Deployment (3-4 hours)

### Task 1: Install Kubernetes Tools (15 min)

```bash
# Install Minikube (local Kubernetes cluster)
brew install minikube

# Install kubectl (Kubernetes CLI)
brew install kubectl

# Verify installation
minikube version
kubectl version --client
```

### Task 2: Start Minikube (10 min)

```bash
# Start Minikube cluster
minikube start --driver=docker --memory=4096 --cpus=2

# Verify cluster is running
kubectl cluster-info
kubectl get nodes

# Expected output:
# NAME       STATUS   ROLES           AGE   VERSION
# minikube   Ready    control-plane   1m    v1.28.x
```

### Task 3: Create Kubernetes Manifests (1 hour)

Create simple manifests in `k8s/` directory:

#### File 1: `k8s/namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: pokewatch
  labels:
    name: pokewatch
```

#### File 2: `k8s/api-deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pokewatch-api
  namespace: pokewatch
  labels:
    app: pokewatch
    component: api
spec:
  replicas: 2  # Start with 2 pods for load balancing
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
        image: pokewatch-api:latest
        imagePullPolicy: Never  # Use local image (Minikube)
        ports:
        - containerPort: 8000
          name: http
        env:
        # Simple environment variables
        - name: API_KEYS
          value: "pk_dev_test123"
        - name: ENVIRONMENT
          value: "kubernetes"
        # Resource limits (important for K8s)
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        # Health checks
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

#### File 3: `k8s/api-service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: pokewatch-api
  namespace: pokewatch
  labels:
    app: pokewatch
    component: api
spec:
  type: NodePort  # Simple external access (no Ingress needed)
  selector:
    app: pokewatch-api
  ports:
  - port: 8000        # Service port
    targetPort: 8000  # Container port
    nodePort: 30080   # External port (localhost:30080)
    protocol: TCP
    name: http
```

**That's it!** Just 3 simple files - no ConfigMaps, Secrets, or Ingress for now.

### Task 4: Build Image for Minikube (15 min)

```bash
# Point Docker to Minikube's Docker daemon
eval $(minikube docker-env)

# Build image inside Minikube
docker build -f docker/api.Dockerfile -t pokewatch-api:latest .

# Verify image exists in Minikube
docker images | grep pokewatch-api
```

### Task 5: Deploy to Kubernetes (15 min)

```bash
# Apply manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml

# Watch deployment progress
kubectl get pods -n pokewatch -w

# Expected output:
# NAME                             READY   STATUS    RESTARTS   AGE
# pokewatch-api-xxxxxxxxxx-xxxxx   1/1     Running   0          30s
# pokewatch-api-xxxxxxxxxx-xxxxx   1/1     Running   0          30s
```

### Task 6: Test Deployment (15 min)

```bash
# Get service URL
minikube service pokewatch-api -n pokewatch --url

# Expected output:
# http://127.0.0.1:xxxxx (forwarded from localhost:30080)

# Test API
URL=$(minikube service pokewatch-api -n pokewatch --url)
curl $URL/health

# Expected response:
# {"status":"healthy","timestamp":"..."}

# Test with API key
curl -H "X-API-Key: pk_dev_test123" $URL/health
```

### Task 7: Create Deployment Script (30 min)

**File:** `scripts/deploy_k8s.sh`
```bash
#!/bin/bash
#
# Deploy PokeWatch to Kubernetes (Minikube)
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "PokeWatch Kubernetes Deployment"
echo -e "==========================================${NC}"
echo ""

# Check Minikube is running
if ! minikube status | grep -q "Running"; then
    echo -e "${YELLOW}Starting Minikube...${NC}"
    minikube start --driver=docker --memory=4096 --cpus=2
fi

echo -e "${GREEN}✓ Minikube is running${NC}"
echo ""

# Build Docker image
echo -e "${BLUE}Building Docker image...${NC}"
eval $(minikube docker-env)
docker build -f docker/api.Dockerfile -t pokewatch-api:latest . --quiet
echo -e "${GREEN}✓ Image built${NC}"
echo ""

# Deploy to Kubernetes
echo -e "${BLUE}Deploying to Kubernetes...${NC}"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml
echo -e "${GREEN}✓ Manifests applied${NC}"
echo ""

# Wait for pods to be ready
echo -e "${BLUE}Waiting for pods to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=pokewatch-api -n pokewatch --timeout=120s
echo -e "${GREEN}✓ Pods are ready${NC}"
echo ""

# Show deployment info
echo -e "${BLUE}Deployment Info:${NC}"
echo "----------------"
kubectl get pods -n pokewatch
echo ""
kubectl get services -n pokewatch
echo ""

# Get service URL
echo -e "${BLUE}Access API:${NC}"
echo "------------"
URL=$(minikube service pokewatch-api -n pokewatch --url)
echo "URL: $URL"
echo ""
echo "Test:"
echo "  curl $URL/health"
echo "  curl -H \"X-API-Key: pk_dev_test123\" $URL/health"
echo ""

echo -e "${GREEN}✅ Deployment complete!${NC}"
```

```bash
chmod +x scripts/deploy_k8s.sh
```

---

## Day 2: Scaling & Management (2-3 hours)

### Task 1: Test Manual Scaling (30 min)

```bash
# Scale up to 5 pods
kubectl scale deployment pokewatch-api -n pokewatch --replicas=5

# Watch pods being created
kubectl get pods -n pokewatch -w

# Verify all 5 pods are running
kubectl get pods -n pokewatch

# Test load balancing (multiple requests hit different pods)
URL=$(minikube service pokewatch-api -n pokewatch --url)
for i in {1..10}; do
  curl -s $URL/health | jq '.timestamp'
done

# Scale down to 2 pods
kubectl scale deployment pokewatch-api -n pokewatch --replicas=2
```

### Task 2: Add Horizontal Pod Autoscaler (Optional) (30 min)

**File:** `k8s/hpa.yaml`
```yaml
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
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70  # Scale up if CPU > 70%
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80  # Scale up if memory > 80%
```

```bash
# Enable metrics server in Minikube
minikube addons enable metrics-server

# Apply HPA
kubectl apply -f k8s/hpa.yaml

# Check HPA status
kubectl get hpa -n pokewatch

# Expected output:
# NAME                 REFERENCE                  TARGETS   MINPODS   MAXPODS   REPLICAS
# pokewatch-api-hpa    Deployment/pokewatch-api   0%/70%    2         5         2
```

### Task 3: Kubernetes Management Commands (30 min)

Create a cheat sheet script:

**File:** `scripts/k8s_commands.sh`
```bash
#!/bin/bash
#
# Kubernetes Management Commands Cheat Sheet
#

# View all resources
kubectl get all -n pokewatch

# View pods with details
kubectl get pods -n pokewatch -o wide

# View pod logs
kubectl logs -l app=pokewatch-api -n pokewatch --tail=50

# Follow logs in real-time
kubectl logs -l app=pokewatch-api -n pokewatch -f

# Describe pod (for troubleshooting)
kubectl describe pod <pod-name> -n pokewatch

# Execute command in pod
kubectl exec -it <pod-name> -n pokewatch -- /bin/bash

# Port forward (for local testing)
kubectl port-forward -n pokewatch svc/pokewatch-api 8000:8000

# Scale deployment
kubectl scale deployment pokewatch-api -n pokewatch --replicas=3

# Update deployment (after image change)
kubectl rollout restart deployment pokewatch-api -n pokewatch

# Check rollout status
kubectl rollout status deployment pokewatch-api -n pokewatch

# View HPA status
kubectl get hpa -n pokewatch

# Delete everything
kubectl delete namespace pokewatch
```

```bash
chmod +x scripts/k8s_commands.sh
```

### Task 4: Create Monitoring Script (30 min)

**File:** `scripts/monitor_k8s.sh`
```bash
#!/bin/bash
#
# Monitor Kubernetes Deployment
#

echo "PokeWatch Kubernetes Status"
echo "============================"
echo ""

# Check Minikube
echo "Minikube Status:"
minikube status
echo ""

# Check pods
echo "Pods:"
kubectl get pods -n pokewatch
echo ""

# Check services
echo "Services:"
kubectl get services -n pokewatch
echo ""

# Check HPA (if exists)
if kubectl get hpa -n pokewatch 2>/dev/null; then
    echo "Autoscaler:"
    kubectl get hpa -n pokewatch
    echo ""
fi

# Resource usage
echo "Resource Usage:"
kubectl top pods -n pokewatch 2>/dev/null || echo "  (metrics-server not enabled)"
echo ""

# Recent logs
echo "Recent Logs (last 10 lines):"
kubectl logs -l app=pokewatch-api -n pokewatch --tail=10
echo ""

# Service URL
echo "API URL:"
minikube service pokewatch-api -n pokewatch --url
```

```bash
chmod +x scripts/monitor_k8s.sh
```

### Task 5: Test Rolling Updates (30 min)

```bash
# Make a small change to the API (e.g., add a version endpoint)
# Then rebuild and update

# Rebuild image
eval $(minikube docker-env)
docker build -f docker/api.Dockerfile -t pokewatch-api:v2 .

# Update deployment to use new image
kubectl set image deployment/pokewatch-api api=pokewatch-api:v2 -n pokewatch

# Watch rolling update
kubectl rollout status deployment/pokewatch-api -n pokewatch

# Verify pods were replaced one by one (zero downtime)
kubectl get pods -n pokewatch

# Rollback if needed
kubectl rollout undo deployment/pokewatch-api -n pokewatch
```

---

## Day 3: Documentation & Verification (2 hours)

### Task 1: Create Kubernetes Guide (1 hour)

**File:** `docs/kubernetes_guide.md`
```markdown
# Kubernetes Deployment Guide

## Overview

PokeWatch is deployed to Kubernetes for container orchestration and scalability.

**Environment:** Minikube (local Kubernetes cluster)
**Components:** API deployment with 2+ replicas, load-balanced service

---

## Prerequisites

Install required tools:
```bash
brew install minikube kubectl
```

---

## Quick Start

### 1. Deploy to Kubernetes

```bash
# Deploy everything
bash scripts/deploy_k8s.sh
```

### 2. Access API

```bash
# Get service URL
minikube service pokewatch-api -n pokewatch --url

# Test API
curl <url>/health
```

### 3. Monitor

```bash
# Check status
bash scripts/monitor_k8s.sh

# View logs
kubectl logs -l app=pokewatch-api -n pokewatch -f
```

---

## Architecture

```
Minikube Cluster
├── Namespace: pokewatch
│   ├── Deployment: pokewatch-api
│   │   ├── Pod 1 (pokewatch-api:latest)
│   │   └── Pod 2 (pokewatch-api:latest)
│   └── Service: pokewatch-api (NodePort 30080)
│       └── Load balances traffic to pods
```

---

## Scaling

### Manual Scaling

```bash
# Scale to 5 pods
kubectl scale deployment pokewatch-api -n pokewatch --replicas=5

# Check pods
kubectl get pods -n pokewatch
```

### Auto-scaling (Optional)

```bash
# Enable metrics
minikube addons enable metrics-server

# Apply HPA
kubectl apply -f k8s/hpa.yaml

# Check autoscaler
kubectl get hpa -n pokewatch
```

---

## Common Tasks

### View Pods
```bash
kubectl get pods -n pokewatch
```

### View Logs
```bash
# All pods
kubectl logs -l app=pokewatch-api -n pokewatch --tail=50

# Specific pod
kubectl logs <pod-name> -n pokewatch

# Follow logs
kubectl logs -l app=pokewatch-api -n pokewatch -f
```

### Update Deployment
```bash
# After code changes
bash scripts/deploy_k8s.sh
```

### Delete Deployment
```bash
kubectl delete namespace pokewatch
```

---

## Troubleshooting

### Pods not starting

```bash
# Check pod status
kubectl get pods -n pokewatch

# Describe pod for details
kubectl describe pod <pod-name> -n pokewatch

# Check logs
kubectl logs <pod-name> -n pokewatch
```

### Service not accessible

```bash
# Check service
kubectl get svc -n pokewatch

# Check Minikube service list
minikube service list

# Try port forward
kubectl port-forward -n pokewatch svc/pokewatch-api 8000:8000
```

### Image not found

```bash
# Rebuild image in Minikube
eval $(minikube docker-env)
docker build -f docker/api.Dockerfile -t pokewatch-api:latest .

# Verify image
docker images | grep pokewatch-api
```

---

## Cleanup

```bash
# Stop Minikube
minikube stop

# Delete cluster
minikube delete
```

---

## Learning Resources

- **Kubernetes Basics**: https://kubernetes.io/docs/tutorials/kubernetes-basics/
- **Minikube**: https://minikube.sigs.k8s.io/docs/
- **kubectl Cheat Sheet**: https://kubernetes.io/docs/reference/kubectl/cheatsheet/
```

### Task 2: Create Verification Script (30 min)

**File:** `scripts/verify_k8s.sh`
```bash
#!/bin/bash
#
# Verify Kubernetes Deployment
#

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "PokeWatch Kubernetes Verification"
echo "=================================="
echo ""

FAILED=0

# Check 1: Minikube running
echo -n "Checking Minikube... "
if minikube status | grep -q "Running"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Minikube not running${NC}"
    FAILED=1
fi

# Check 2: Namespace exists
echo -n "Checking namespace... "
if kubectl get namespace pokewatch >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Namespace not found${NC}"
    FAILED=1
fi

# Check 3: Deployment exists
echo -n "Checking deployment... "
if kubectl get deployment pokewatch-api -n pokewatch >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Deployment not found${NC}"
    FAILED=1
fi

# Check 4: Pods running
echo -n "Checking pods... "
READY_PODS=$(kubectl get pods -n pokewatch -o json | jq '[.items[] | select(.status.phase=="Running")] | length')
if [ "$READY_PODS" -ge 1 ]; then
    echo -e "${GREEN}✓ $READY_PODS pods running${NC}"
else
    echo -e "${RED}✗ No pods running${NC}"
    FAILED=1
fi

# Check 5: Service exists
echo -n "Checking service... "
if kubectl get service pokewatch-api -n pokewatch >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Service not found${NC}"
    FAILED=1
fi

# Check 6: API responding
echo -n "Checking API health... "
URL=$(minikube service pokewatch-api -n pokewatch --url 2>/dev/null)
if HEALTH=$(curl -s "$URL/health" 2>/dev/null | jq -r '.status' 2>/dev/null); then
    if [ "$HEALTH" = "healthy" ]; then
        echo -e "${GREEN}✓ API is healthy${NC}"
    else
        echo -e "${YELLOW}⚠ API responded but not healthy${NC}"
    fi
else
    echo -e "${RED}✗ API not responding${NC}"
    FAILED=1
fi

echo ""

# Summary
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Service URL: $URL"
    echo ""
    echo "Next steps:"
    echo "  - Test scaling: kubectl scale deployment pokewatch-api -n pokewatch --replicas=3"
    echo "  - View logs: kubectl logs -l app=pokewatch-api -n pokewatch"
    echo "  - Monitor: bash scripts/monitor_k8s.sh"
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  - Check pods: kubectl get pods -n pokewatch"
    echo "  - View logs: kubectl logs -l app=pokewatch-api -n pokewatch"
    echo "  - Redeploy: bash scripts/deploy_k8s.sh"
    exit 1
fi
```

```bash
chmod +x scripts/verify_k8s.sh
```

### Task 3: Update Main README (30 min)

Add Kubernetes section to `README.md`:

```markdown
## Kubernetes Deployment

PokeWatch can be deployed to Kubernetes for scalability and high availability.

### Quick Start

```bash
# Deploy to Minikube
bash scripts/deploy_k8s.sh

# Verify deployment
bash scripts/verify_k8s.sh

# Monitor
bash scripts/monitor_k8s.sh
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment pokewatch-api -n pokewatch --replicas=5

# Auto-scaling (optional)
kubectl apply -f k8s/hpa.yaml
```

For complete guide, see [docs/kubernetes_guide.md](docs/kubernetes_guide.md)
```

---

## Summary

### Deliverables

**Kubernetes Manifests (3 files):**
- `k8s/namespace.yaml` - Namespace for isolation
- `k8s/api-deployment.yaml` - API deployment with 2 replicas
- `k8s/api-service.yaml` - NodePort service for external access
- `k8s/hpa.yaml` - (Optional) Horizontal Pod Autoscaler

**Scripts (4 files):**
- `scripts/deploy_k8s.sh` - Automated deployment
- `scripts/monitor_k8s.sh` - Status monitoring
- `scripts/verify_k8s.sh` - Verification tests
- `scripts/k8s_commands.sh` - Command cheat sheet

**Documentation (1 file):**
- `docs/kubernetes_guide.md` - Complete K8s guide

### Learning Objectives ✅

1. **Container Orchestration** - Deploy multi-pod application
2. **Load Balancing** - Service distributes traffic across pods
3. **Scaling** - Manual and automatic scaling
4. **High Availability** - Multiple replicas for fault tolerance
5. **Resource Management** - CPU/memory limits and requests
6. **Health Checks** - Liveness and readiness probes
7. **Rolling Updates** - Zero-downtime deployments

### Technologies Demonstrated

- ✅ **Kubernetes** - Container orchestration
- ✅ **Minikube** - Local K8s cluster
- ✅ **kubectl** - K8s CLI
- ✅ **Docker** - Containerization
- ✅ **HPA** - Horizontal Pod Autoscaling (optional)

### Time Required

- **Day 1**: 3-4 hours (setup + deploy)
- **Day 2**: 2-3 hours (scaling + management)
- **Day 3**: 2 hours (documentation)
- **Total**: 7-9 hours (≈ 1 week at course pace)

### Verification Checklist

- [ ] Minikube installed and running
- [ ] Kubernetes manifests created (3-4 files)
- [ ] Docker image built in Minikube
- [ ] Deployment applied successfully
- [ ] 2+ pods running
- [ ] Service accessible via NodePort
- [ ] Health checks working
- [ ] Scaling tested (manual)
- [ ] HPA applied (optional)
- [ ] Scripts created (4 files)
- [ ] Documentation complete
- [ ] Verification script passes

---

## Quick Start Commands

```bash
# Day 1: Deploy
brew install minikube kubectl
minikube start
bash scripts/deploy_k8s.sh

# Day 2: Scale
kubectl scale deployment pokewatch-api -n pokewatch --replicas=5
bash scripts/monitor_k8s.sh

# Day 3: Verify
bash scripts/verify_k8s.sh
```

**Total:** 3 commands to deploy a scalable Kubernetes application! 🚀

---

## What's NOT Included (Simplified)

- ❌ Cloud deployment (GKE/EKS/AKS)
- ❌ Ingress controller (Nginx/Traefik)
- ❌ SSL/TLS certificates
- ❌ Persistent volumes (StatefulSets)
- ❌ Helm charts
- ❌ Service mesh (Istio)
- ❌ Full Prometheus/Grafana stack
- ❌ Secrets management (Vault)

**Why?** Keep it simple for educational purposes. Focus on core Kubernetes concepts.

---

**Ready to implement?** Start with: `brew install minikube kubectl` 🎯
