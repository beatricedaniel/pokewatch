# Kubernetes Development Plan - Implementation Guide

**Project:** PokeWatch Kubernetes Deployment
**Goal:** Implement container orchestration and scalability with Kubernetes
**Duration:** 3 days (7-9 hours total)
**Approach:** Local Minikube deployment (simple and educational)

---

## Overview

Based on [ARCHITECTURE.md](ARCHITECTURE.md) and [KUBERNETES_SIMPLE_PLAN.md](KUBERNETES_SIMPLE_PLAN.md), this plan implements:

✅ **Kubernetes deployment** (Minikube)
✅ **Multi-pod architecture** (2-5 replicas)
✅ **Load balancing** (Service)
✅ **Auto-scaling** (HPA)
✅ **Health checks** (Liveness/Readiness)
✅ **Management scripts** (Deploy, monitor, verify)
✅ **Complete documentation**

---

## Prerequisites

### What We Already Have ✅

- ✅ Docker image for API (`pokewatch-api:latest`)
- ✅ FastAPI application with health endpoints
- ✅ Security middleware (auth, rate limiting)
- ✅ Performance optimization (caching)
- ✅ CI/CD workflows

### What We Need to Install

```bash
# Kubernetes tools
brew install minikube kubectl

# Optional (for testing)
brew install jq  # JSON parsing
```

---

## Day 1: Minikube Setup & Deployment (3-4 hours)

**Goal:** Deploy PokeWatch API to local Kubernetes cluster

### Task 1.1: Install Kubernetes Tools (15 min)

**Checklist:**
- [ ] Install Minikube
- [ ] Install kubectl
- [ ] Verify installations

**Commands:**
```bash
# Install tools
brew install minikube kubectl

# Verify Minikube
minikube version
# Expected: minikube version: v1.32.0 or higher

# Verify kubectl
kubectl version --client
# Expected: Client Version: v1.28.x or higher
```

**Verification:**
```bash
# Both commands should succeed
minikube version && kubectl version --client
```

**Expected Time:** 15 minutes

---

### Task 1.2: Start Minikube Cluster (10 min)

**Checklist:**
- [ ] Start Minikube with appropriate resources
- [ ] Verify cluster is running
- [ ] Check kubectl can connect

**Commands:**
```bash
# Start Minikube
minikube start --driver=docker --memory=4096 --cpus=2

# Expected output:
# 😄  minikube v1.32.0 on Darwin 14.1
# ✨  Using the docker driver based on user configuration
# 👍  Starting control plane node minikube in cluster minikube
# ...
# 🏄  Done! kubectl is now configured to use "minikube" cluster

# Verify cluster
kubectl cluster-info
# Expected:
# Kubernetes control plane is running at https://127.0.0.1:xxxxx

# Check nodes
kubectl get nodes
# Expected:
# NAME       STATUS   ROLES           AGE   VERSION
# minikube   Ready    control-plane   1m    v1.28.x
```

**Troubleshooting:**
```bash
# If Minikube fails to start
minikube delete
minikube start --driver=docker

# If kubectl can't connect
minikube update-context
```

**Expected Time:** 10 minutes

---

### Task 1.3: Create Kubernetes Namespace (5 min)

**Checklist:**
- [ ] Create `k8s/` directory
- [ ] Create namespace manifest
- [ ] Apply to cluster

**File:** `k8s/namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: pokewatch
  labels:
    name: pokewatch
    project: mlops
    environment: development
```

**Commands:**
```bash
# Create directory
mkdir -p k8s

# Create file (paste content above)
# Or use command:
cat > k8s/namespace.yaml << 'EOF'
apiVersion: v1
kind: Namespace
metadata:
  name: pokewatch
  labels:
    name: pokewatch
    project: mlops
    environment: development
EOF

# Apply to cluster
kubectl apply -f k8s/namespace.yaml

# Expected output:
# namespace/pokewatch created

# Verify
kubectl get namespace pokewatch
# Expected:
# NAME        STATUS   AGE
# pokewatch   Active   5s
```

**Expected Time:** 5 minutes

---

### Task 1.4: Create API Deployment Manifest (30 min)

**Checklist:**
- [ ] Create deployment manifest with 2 replicas
- [ ] Configure resource limits
- [ ] Add health probes
- [ ] Set environment variables

**File:** `k8s/api-deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pokewatch-api
  namespace: pokewatch
  labels:
    app: pokewatch
    component: api
    version: v1
spec:
  replicas: 2  # Start with 2 pods for load balancing
  selector:
    matchLabels:
      app: pokewatch-api
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max 1 extra pod during update
      maxUnavailable: 0  # Keep all pods running during update
  template:
    metadata:
      labels:
        app: pokewatch-api
        version: v1
    spec:
      containers:
      - name: api
        image: pokewatch-api:latest
        imagePullPolicy: Never  # Use local image (Minikube only)
        ports:
        - containerPort: 8000
          name: http
          protocol: TCP

        # Environment variables
        env:
        - name: ENVIRONMENT
          value: "kubernetes"
        - name: API_KEYS
          value: "pk_dev_test123,pk_dev_test456"
        - name: LOG_LEVEL
          value: "INFO"

        # Resource limits (important for K8s scheduling)
        resources:
          requests:
            memory: "256Mi"  # Guaranteed minimum
            cpu: "250m"      # Guaranteed minimum (0.25 cores)
          limits:
            memory: "512Mi"  # Maximum allowed
            cpu: "500m"      # Maximum allowed (0.5 cores)

        # Liveness probe (is container alive?)
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
            scheme: HTTP
          initialDelaySeconds: 30  # Wait 30s after start
          periodSeconds: 10        # Check every 10s
          timeoutSeconds: 5        # Timeout after 5s
          successThreshold: 1      # 1 success = healthy
          failureThreshold: 3      # 3 failures = restart pod

        # Readiness probe (is container ready for traffic?)
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
            scheme: HTTP
          initialDelaySeconds: 10  # Wait 10s after start
          periodSeconds: 5         # Check every 5s
          timeoutSeconds: 3        # Timeout after 3s
          successThreshold: 1      # 1 success = ready
          failureThreshold: 3      # 3 failures = not ready
```

**Key Concepts:**
- **replicas: 2** - Run 2 copies for high availability
- **resources** - CPU/memory limits for scheduling
- **livenessProbe** - Restart unhealthy containers
- **readinessProbe** - Remove unhealthy containers from service
- **imagePullPolicy: Never** - Use local Minikube images

**Expected Time:** 30 minutes

---

### Task 1.5: Create Service Manifest (15 min)

**Checklist:**
- [ ] Create service manifest
- [ ] Configure NodePort for external access
- [ ] Set up load balancing

**File:** `k8s/api-service.yaml`
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
    app: pokewatch-api  # Route to pods with this label
  ports:
  - port: 8000        # Service port (internal)
    targetPort: 8000  # Container port
    nodePort: 30080   # External port (accessible at localhost:30080)
    protocol: TCP
    name: http
  sessionAffinity: None  # Round-robin load balancing
```

**Key Concepts:**
- **selector** - Routes traffic to matching pods
- **NodePort** - Exposes service on every node's IP at static port
- **port** - Port inside the cluster
- **targetPort** - Port on the container
- **nodePort** - External port (30000-32767 range)

**Expected Time:** 15 minutes

---

### Task 1.6: Build Docker Image for Minikube (15 min)

**Checklist:**
- [ ] Point Docker to Minikube's Docker daemon
- [ ] Build image inside Minikube
- [ ] Verify image exists

**Commands:**
```bash
# Point Docker CLI to Minikube's Docker daemon
eval $(minikube docker-env)

# Verify you're using Minikube's Docker
docker ps
# Should show Minikube containers

# Build image (from project root)
cd /Users/beatrice/Documents/data_scientest/projet/pokewatch
docker build -f docker/api.Dockerfile -t pokewatch-api:latest .

# Expected output:
# [+] Building 45.2s (12/12) FINISHED
# ...
# => => naming to docker.io/library/pokewatch-api:latest

# Verify image exists in Minikube
docker images | grep pokewatch-api
# Expected:
# pokewatch-api   latest   abc123def456   2 minutes ago   500MB
```

**Important:** This builds the image inside Minikube's Docker, so Kubernetes can access it without a registry.

**Expected Time:** 15 minutes

---

### Task 1.7: Deploy to Kubernetes (15 min)

**Checklist:**
- [ ] Apply all manifests
- [ ] Wait for pods to be ready
- [ ] Verify deployment

**Commands:**
```bash
# Apply manifests in order
kubectl apply -f k8s/namespace.yaml
# Output: namespace/pokewatch created

kubectl apply -f k8s/api-deployment.yaml
# Output: deployment.apps/pokewatch-api created

kubectl apply -f k8s/api-service.yaml
# Output: service/pokewatch-api created

# Watch pods being created
kubectl get pods -n pokewatch -w
# Press Ctrl+C when all pods are Running

# Expected output:
# NAME                             READY   STATUS    RESTARTS   AGE
# pokewatch-api-xxxxxxxxxx-xxxxx   1/1     Running   0          30s
# pokewatch-api-xxxxxxxxxx-xxxxx   1/1     Running   0          30s

# Check deployment status
kubectl get deployment -n pokewatch
# Expected:
# NAME            READY   UP-TO-DATE   AVAILABLE   AGE
# pokewatch-api   2/2     2            2           1m

# Check service
kubectl get service -n pokewatch
# Expected:
# NAME            TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
# pokewatch-api   NodePort   10.96.xxx.xxx   <none>        8000:30080/TCP   1m
```

**Expected Time:** 15 minutes

---

### Task 1.8: Test Deployment (15 min)

**Checklist:**
- [ ] Get service URL
- [ ] Test health endpoint
- [ ] Test API with authentication
- [ ] Verify load balancing

**Commands:**
```bash
# Get service URL
minikube service pokewatch-api -n pokewatch --url

# Expected output:
# http://127.0.0.1:xxxxx
# (This tunnels to NodePort 30080)

# Save URL
URL=$(minikube service pokewatch-api -n pokewatch --url)

# Test health endpoint
curl $URL/health

# Expected response:
# {"status":"healthy","uptime_seconds":60,"requests_served":1,"timestamp":"..."}

# Test with API key
curl -H "X-API-Key: pk_dev_test123" $URL/health

# Should succeed with same response

# Test prediction endpoint
curl -X POST $URL/fair_price \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pk_dev_test123" \
  -d '{"card_id":"pikachu-vmax-swsh045","date":"2024-11-30"}'

# Expected: JSON response with prediction

# Test load balancing (check logs from different pods)
kubectl logs -l app=pokewatch-api -n pokewatch --tail=5
# Should see logs from both pods
```

**Verification:**
- ✅ Health endpoint responds
- ✅ API authentication works
- ✅ Predictions work
- ✅ Both pods receive traffic

**Expected Time:** 15 minutes

---

### Task 1.9: Create Deployment Script (30 min)

**Checklist:**
- [ ] Create automated deployment script
- [ ] Add error handling
- [ ] Add status checks
- [ ] Make executable

**File:** `scripts/deploy_k8s.sh`
```bash
#!/bin/bash
#
# Deploy PokeWatch to Kubernetes (Minikube)
# Usage: bash scripts/deploy_k8s.sh
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "PokeWatch Kubernetes Deployment"
echo -e "==========================================${NC}"
echo ""

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Check Minikube is running
echo -e "${BLUE}[1/6] Checking Minikube...${NC}"
if ! minikube status | grep -q "Running"; then
    echo -e "${YELLOW}Starting Minikube...${NC}"
    minikube start --driver=docker --memory=4096 --cpus=2
fi
echo -e "${GREEN}✓ Minikube is running${NC}"
echo ""

# Build Docker image
echo -e "${BLUE}[2/6] Building Docker image...${NC}"
eval $(minikube docker-env)
docker build -f docker/api.Dockerfile -t pokewatch-api:latest . --quiet
echo -e "${GREEN}✓ Image built: pokewatch-api:latest${NC}"
echo ""

# Deploy namespace
echo -e "${BLUE}[3/6] Creating namespace...${NC}"
kubectl apply -f k8s/namespace.yaml
echo -e "${GREEN}✓ Namespace applied${NC}"
echo ""

# Deploy application
echo -e "${BLUE}[4/6] Deploying application...${NC}"
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml
echo -e "${GREEN}✓ Manifests applied${NC}"
echo ""

# Wait for pods
echo -e "${BLUE}[5/6] Waiting for pods to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=pokewatch-api -n pokewatch --timeout=120s
echo -e "${GREEN}✓ Pods are ready${NC}"
echo ""

# Show status
echo -e "${BLUE}[6/6] Deployment status:${NC}"
echo "----------------"
kubectl get pods -n pokewatch
echo ""
kubectl get services -n pokewatch
echo ""

# Get service URL
URL=$(minikube service pokewatch-api -n pokewatch --url 2>/dev/null)
echo -e "${BLUE}Access API:${NC}"
echo "------------"
echo "URL: $URL"
echo ""
echo "Test commands:"
echo "  curl $URL/health"
echo "  curl -H \"X-API-Key: pk_dev_test123\" $URL/health"
echo ""

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "Next steps:"
echo "  - View logs: kubectl logs -l app=pokewatch-api -n pokewatch -f"
echo "  - Scale: kubectl scale deployment pokewatch-api -n pokewatch --replicas=3"
echo "  - Monitor: bash scripts/monitor_k8s.sh"
```

**Make executable:**
```bash
chmod +x scripts/deploy_k8s.sh
```

**Test:**
```bash
bash scripts/deploy_k8s.sh
```

**Expected Time:** 30 minutes

---

### Day 1 Summary

**Deliverables:**
- ✅ Minikube running
- ✅ 3 Kubernetes manifests (namespace, deployment, service)
- ✅ Docker image built in Minikube
- ✅ 2 pods running and serving traffic
- ✅ Service accessible at localhost:30080
- ✅ Deployment automation script

**Verification:**
```bash
# All should pass
kubectl get namespace pokewatch
kubectl get deployment -n pokewatch
kubectl get pods -n pokewatch
kubectl get service -n pokewatch
curl $(minikube service pokewatch-api -n pokewatch --url)/health
```

**Time Spent:** ~3-4 hours

---

## Day 2: Scaling & Management (2-3 hours)

**Goal:** Implement scaling, monitoring, and management tools

### Task 2.1: Test Manual Scaling (30 min)

**Checklist:**
- [ ] Scale up to 5 pods
- [ ] Observe pod creation
- [ ] Verify load balancing
- [ ] Scale back down to 2

**Commands:**
```bash
# Check current replicas
kubectl get deployment pokewatch-api -n pokewatch
# READY: 2/2

# Scale up to 5 pods
kubectl scale deployment pokewatch-api -n pokewatch --replicas=5

# Watch pods being created
kubectl get pods -n pokewatch -w
# Press Ctrl+C when all 5 are Running

# Verify all pods ready
kubectl get deployment pokewatch-api -n pokewatch
# READY: 5/5

# Test load balancing (make 10 requests)
URL=$(minikube service pokewatch-api -n pokewatch --url)
for i in {1..10}; do
  echo "Request $i:"
  curl -s $URL/health | jq '.timestamp'
  sleep 0.5
done

# Check logs from all pods (should see distributed requests)
kubectl logs -l app=pokewatch-api -n pokewatch --tail=2

# Scale back down
kubectl scale deployment pokewatch-api -n pokewatch --replicas=2

# Verify
kubectl get pods -n pokewatch
# Should show 2 Running, 3 Terminating
```

**Learning Points:**
- Scaling is instant (seconds)
- Load balancer distributes requests
- No downtime during scaling

**Expected Time:** 30 minutes

---

### Task 2.2: Create HPA (Horizontal Pod Autoscaler) (30 min)

**Checklist:**
- [ ] Enable metrics server in Minikube
- [ ] Create HPA manifest
- [ ] Apply HPA
- [ ] Verify autoscaler

**Enable Metrics:**
```bash
# Enable metrics server (required for HPA)
minikube addons enable metrics-server

# Wait 30 seconds for metrics to be available
sleep 30

# Verify metrics
kubectl top nodes
kubectl top pods -n pokewatch
```

**File:** `k8s/hpa.yaml`
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: pokewatch-api-hpa
  namespace: pokewatch
  labels:
    app: pokewatch
    component: api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: pokewatch-api
  minReplicas: 2   # Minimum pods
  maxReplicas: 5   # Maximum pods
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
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60   # Wait 60s before scaling up
      policies:
      - type: Percent
        value: 50                      # Add 50% more pods
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5min before scaling down
      policies:
      - type: Percent
        value: 10                      # Remove 10% of pods
        periodSeconds: 60
```

**Apply HPA:**
```bash
# Apply HPA
kubectl apply -f k8s/hpa.yaml

# Expected output:
# horizontalpodautoscaler.autoscaling/pokewatch-api-hpa created

# Check HPA status
kubectl get hpa -n pokewatch

# Expected output:
# NAME                 REFERENCE                  TARGETS         MINPODS   MAXPODS   REPLICAS
# pokewatch-api-hpa    Deployment/pokewatch-api   0%/70%, 0%/80%  2         5         2

# Watch HPA (will auto-update)
kubectl get hpa -n pokewatch -w
```

**Expected Time:** 30 minutes

---

### Task 2.3: Create Monitoring Script (30 min)

**File:** `scripts/monitor_k8s.sh`
```bash
#!/bin/bash
#
# Monitor Kubernetes Deployment
# Usage: bash scripts/monitor_k8s.sh
#

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "PokeWatch Kubernetes Status"
echo -e "==========================================${NC}"
echo ""

# Minikube status
echo -e "${BLUE}Minikube:${NC}"
minikube status
echo ""

# Namespace
echo -e "${BLUE}Namespace:${NC}"
kubectl get namespace pokewatch -o wide
echo ""

# Pods
echo -e "${BLUE}Pods:${NC}"
kubectl get pods -n pokewatch -o wide
echo ""

# Deployment
echo -e "${BLUE}Deployment:${NC}"
kubectl get deployment -n pokewatch
echo ""

# Service
echo -e "${BLUE}Service:${NC}"
kubectl get service -n pokewatch
echo ""

# HPA (if exists)
if kubectl get hpa -n pokewatch 2>/dev/null | grep -q pokewatch-api-hpa; then
    echo -e "${BLUE}Horizontal Pod Autoscaler:${NC}"
    kubectl get hpa -n pokewatch
    echo ""
fi

# Resource usage (if metrics available)
if kubectl top pods -n pokewatch 2>/dev/null; then
    echo -e "${BLUE}Resource Usage:${NC}"
    kubectl top pods -n pokewatch
    echo ""
fi

# Recent events
echo -e "${BLUE}Recent Events:${NC}"
kubectl get events -n pokewatch --sort-by='.lastTimestamp' | tail -10
echo ""

# Recent logs
echo -e "${BLUE}Recent Logs (last 5 lines per pod):${NC}"
kubectl logs -l app=pokewatch-api -n pokewatch --tail=5
echo ""

# Service URL
echo -e "${BLUE}Service URL:${NC}"
minikube service pokewatch-api -n pokewatch --url
echo ""

echo -e "${GREEN}✓ Status check complete${NC}"
```

**Make executable and test:**
```bash
chmod +x scripts/monitor_k8s.sh
bash scripts/monitor_k8s.sh
```

**Expected Time:** 30 minutes

---

### Task 2.4: Create kubectl Commands Cheat Sheet (15 min)

**File:** `scripts/k8s_commands.sh`
```bash
#!/bin/bash
#
# Kubernetes Management Commands Cheat Sheet
# Usage: bash scripts/k8s_commands.sh [command]
#

cat << 'EOF'
Kubernetes Commands for PokeWatch
==================================

# View Resources
kubectl get all -n pokewatch                    # All resources
kubectl get pods -n pokewatch                   # Pods
kubectl get pods -n pokewatch -o wide           # Pods (detailed)
kubectl get deployment -n pokewatch             # Deployment
kubectl get service -n pokewatch                # Service
kubectl get hpa -n pokewatch                    # Autoscaler

# Logs
kubectl logs -l app=pokewatch-api -n pokewatch --tail=50    # Last 50 lines
kubectl logs -l app=pokewatch-api -n pokewatch -f           # Follow logs
kubectl logs <pod-name> -n pokewatch                        # Specific pod

# Describe (for debugging)
kubectl describe pod <pod-name> -n pokewatch
kubectl describe deployment pokewatch-api -n pokewatch
kubectl describe service pokewatch-api -n pokewatch

# Execute commands in pod
kubectl exec -it <pod-name> -n pokewatch -- /bin/bash
kubectl exec -it <pod-name> -n pokewatch -- python --version

# Scaling
kubectl scale deployment pokewatch-api -n pokewatch --replicas=3
kubectl scale deployment pokewatch-api -n pokewatch --replicas=5

# Port Forward (for local testing)
kubectl port-forward -n pokewatch svc/pokewatch-api 8000:8000
# Then access: http://localhost:8000

# Restart Deployment
kubectl rollout restart deployment pokewatch-api -n pokewatch
kubectl rollout status deployment pokewatch-api -n pokewatch

# Delete Resources
kubectl delete pod <pod-name> -n pokewatch           # Delete specific pod
kubectl delete deployment pokewatch-api -n pokewatch # Delete deployment
kubectl delete namespace pokewatch                   # Delete everything

# Get Service URL (Minikube)
minikube service pokewatch-api -n pokewatch --url

# Resource Usage
kubectl top nodes                    # Node usage
kubectl top pods -n pokewatch        # Pod usage

# Events
kubectl get events -n pokewatch --sort-by='.lastTimestamp'

EOF
```

**Make executable:**
```bash
chmod +x scripts/k8s_commands.sh
bash scripts/k8s_commands.sh
```

**Expected Time:** 15 minutes

---

### Task 2.5: Test Rolling Updates (30 min)

**Checklist:**
- [ ] Make a small code change
- [ ] Rebuild image with new tag
- [ ] Update deployment
- [ ] Verify zero-downtime update

**Commands:**
```bash
# Make a small change (e.g., update version in health endpoint)
# Edit src/pokewatch/api/main.py and add version field

# Rebuild image with new tag
eval $(minikube docker-env)
docker build -f docker/api.Dockerfile -t pokewatch-api:v2 .

# Update deployment to use new image
kubectl set image deployment/pokewatch-api \
  api=pokewatch-api:v2 \
  -n pokewatch

# Watch rolling update
kubectl rollout status deployment/pokewatch-api -n pokewatch

# Expected output:
# Waiting for deployment "pokewatch-api" rollout to finish: 1 out of 2 new replicas...
# deployment "pokewatch-api" successfully rolled out

# Verify new pods
kubectl get pods -n pokewatch
# Should see new pods with recent AGE

# Test API still works during update
URL=$(minikube service pokewatch-api -n pokewatch --url)
while true; do curl -s $URL/health | jq -r '.status'; sleep 1; done
# Should never fail (zero downtime)

# Rollback if needed
kubectl rollout undo deployment/pokewatch-api -n pokewatch

# Check rollout history
kubectl rollout history deployment/pokewatch-api -n pokewatch
```

**Learning Points:**
- Rolling updates happen pod-by-pod
- No downtime (readiness probes ensure smooth transition)
- Easy rollback

**Expected Time:** 30 minutes

---

### Day 2 Summary

**Deliverables:**
- ✅ Manual scaling tested (2 → 5 → 2 pods)
- ✅ HPA configured (auto-scale 2-5 pods)
- ✅ Monitoring script created
- ✅ kubectl commands cheat sheet
- ✅ Rolling updates tested

**Verification:**
```bash
bash scripts/monitor_k8s.sh
kubectl get hpa -n pokewatch
bash scripts/k8s_commands.sh
```

**Time Spent:** ~2-3 hours

---

## Day 3: Documentation & Verification (2 hours)

**Goal:** Complete documentation and verify everything works

### Task 3.1: Create Kubernetes Guide (1 hour)

**File:** `docs/kubernetes_guide.md`

See [KUBERNETES_SIMPLE_PLAN.md](KUBERNETES_SIMPLE_PLAN.md) Task 3, Day 3 for complete content.

**Checklist:**
- [ ] Quick start section
- [ ] Architecture explanation
- [ ] Common commands
- [ ] Troubleshooting guide
- [ ] Examples

**Expected Time:** 1 hour

---

### Task 3.2: Create Verification Script (30 min)

**File:** `scripts/verify_k8s.sh`

```bash
#!/bin/bash
#
# Verify Kubernetes Deployment
# Usage: bash scripts/verify_k8s.sh
#

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "PokeWatch Kubernetes Verification"
echo -e "==========================================${NC}"
echo ""

FAILED=0

# Check 1: Minikube
echo -n "Checking Minikube... "
if minikube status | grep -q "Running"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    FAILED=1
fi

# Check 2: Namespace
echo -n "Checking namespace... "
if kubectl get namespace pokewatch >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    FAILED=1
fi

# Check 3: Deployment
echo -n "Checking deployment... "
if kubectl get deployment pokewatch-api -n pokewatch >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    FAILED=1
fi

# Check 4: Pods
echo -n "Checking pods... "
READY=$(kubectl get pods -n pokewatch -o json | jq '[.items[] | select(.status.phase=="Running")] | length')
if [ "$READY" -ge 1 ]; then
    echo -e "${GREEN}✓ $READY pods running${NC}"
else
    echo -e "${RED}✗ No pods running${NC}"
    FAILED=1
fi

# Check 5: Service
echo -n "Checking service... "
if kubectl get service pokewatch-api -n pokewatch >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    FAILED=1
fi

# Check 6: HPA
echo -n "Checking HPA... "
if kubectl get hpa pokewatch-api-hpa -n pokewatch >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ Not found (optional)${NC}"
fi

# Check 7: API Health
echo -n "Checking API health... "
URL=$(minikube service pokewatch-api -n pokewatch --url 2>/dev/null)
if HEALTH=$(curl -s "$URL/health" 2>/dev/null | jq -r '.status' 2>/dev/null); then
    if [ "$HEALTH" = "healthy" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠ Not healthy${NC}"
    fi
else
    echo -e "${RED}✗ Not responding${NC}"
    FAILED=1
fi

# Check 8: Load balancing
echo -n "Checking load balancing... "
if [ "$READY" -ge 2 ]; then
    echo -e "${GREEN}✓ $READY pods can distribute load${NC}"
else
    echo -e "${YELLOW}⚠ Only $READY pod${NC}"
fi

echo ""

# Summary
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Deployment Details:"
    echo "  URL: $URL"
    echo "  Pods: $READY"
    echo ""
    echo "Next steps:"
    echo "  - Monitor: bash scripts/monitor_k8s.sh"
    echo "  - Scale: kubectl scale deployment pokewatch-api -n pokewatch --replicas=3"
    echo "  - Logs: kubectl logs -l app=pokewatch-api -n pokewatch -f"
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  - Redeploy: bash scripts/deploy_k8s.sh"
    echo "  - Check pods: kubectl get pods -n pokewatch"
    echo "  - View logs: kubectl logs -l app=pokewatch-api -n pokewatch"
    exit 1
fi
```

**Make executable and test:**
```bash
chmod +x scripts/verify_k8s.sh
bash scripts/verify_k8s.sh
```

**Expected Time:** 30 minutes

---

### Task 3.3: Update README (30 min)

**File:** `README.md`

Add Kubernetes section:

```markdown
## Kubernetes Deployment

PokeWatch can be deployed to Kubernetes for container orchestration and scalability.

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

# Auto-scaling (HPA)
kubectl apply -f k8s/hpa.yaml
kubectl get hpa -n pokewatch
```

### Management

```bash
# View logs
kubectl logs -l app=pokewatch-api -n pokewatch -f

# Access API
minikube service pokewatch-api -n pokewatch --url

# Delete deployment
kubectl delete namespace pokewatch
```

For complete guide, see [docs/kubernetes_guide.md](docs/kubernetes_guide.md)
```

**Expected Time:** 30 minutes

---

### Day 3 Summary

**Deliverables:**
- ✅ Complete Kubernetes guide
- ✅ Verification script
- ✅ README updated
- ✅ All features documented

**Verification:**
```bash
bash scripts/verify_k8s.sh
cat docs/kubernetes_guide.md | head -50
grep -A 10 "Kubernetes" README.md
```

**Time Spent:** ~2 hours

---

## Complete Implementation Checklist

### Day 1: Deployment
- [x] Install Minikube and kubectl
- [x] Start Minikube cluster
- [x] Create namespace.yaml
- [x] Create api-deployment.yaml
- [x] Create api-service.yaml
- [x] Build Docker image in Minikube
- [x] Deploy to Kubernetes
- [x] Create deploy_k8s.sh script

### Day 2: Scaling
- [x] Test manual scaling
- [x] Create HPA manifest
- [x] Create monitoring script
- [x] Create commands cheat sheet
- [x] Test rolling updates

### Day 3: Documentation
- [x] Create Kubernetes guide
- [x] Create verification script
- [x] Update README

---

## Final Deliverables

### Files Created (12 total)

**Kubernetes Manifests (4):**
1. `k8s/namespace.yaml`
2. `k8s/api-deployment.yaml`
3. `k8s/api-service.yaml`
4. `k8s/hpa.yaml`

**Scripts (4):**
5. `scripts/deploy_k8s.sh`
6. `scripts/monitor_k8s.sh`
7. `scripts/verify_k8s.sh`
8. `scripts/k8s_commands.sh`

**Documentation (2):**
9. `docs/kubernetes_guide.md`
10. `ARCHITECTURE.md` (updated)

**Planning (2):**
11. `KUBERNETES_SIMPLE_PLAN.md`
12. `KUBERNETES_DEVELOPMENT_PLAN.md` (this file)

---

## Verification Commands

**Complete verification:**
```bash
# 1. Verify files exist
ls k8s/*.yaml
ls scripts/*.sh
ls docs/kubernetes_guide.md

# 2. Verify deployment
bash scripts/verify_k8s.sh

# 3. Test functionality
bash scripts/deploy_k8s.sh
bash scripts/monitor_k8s.sh

# 4. Test scaling
kubectl scale deployment pokewatch-api -n pokewatch --replicas=5
kubectl get pods -n pokewatch

# 5. Test API
URL=$(minikube service pokewatch-api -n pokewatch --url)
curl $URL/health
```

---

## Success Criteria

Kubernetes deployment is complete when:

- ✅ Minikube running locally
- ✅ 2+ pods deployed and running
- ✅ Service load-balancing traffic
- ✅ Health checks passing
- ✅ Manual scaling works (2 → 5 → 2)
- ✅ HPA configured (optional)
- ✅ Rolling updates tested
- ✅ All scripts working
- ✅ Documentation complete
- ✅ Verification script passes

---

## Time Summary

| Day | Focus | Time |
|-----|-------|------|
| **Day 1** | Deployment | 3-4 hours |
| **Day 2** | Scaling & Management | 2-3 hours |
| **Day 3** | Documentation | 2 hours |
| **Total** | Complete Implementation | **7-9 hours** |

---

## Next Steps

After completing this plan:

1. **Run complete verification**
   ```bash
   bash scripts/verify_k8s.sh
   ```

2. **Test all features**
   ```bash
   bash scripts/deploy_k8s.sh
   bash scripts/monitor_k8s.sh
   kubectl scale deployment pokewatch-api -n pokewatch --replicas=3
   ```

3. **(Optional) Deploy to cloud**
   - Use same manifests with cloud Kubernetes
   - Update service type to LoadBalancer
   - See [KUBERNETES_DEPLOYMENT_OPTIONS.md](KUBERNETES_DEPLOYMENT_OPTIONS.md)

4. **Update Phase 3 status**
   - Mark Kubernetes implementation complete
   - Update PHASE3_PROGRESS.md
   - Create PHASE3_COMPLETE.md

---

**Ready to start?** Begin with Day 1, Task 1.1! 🚀
