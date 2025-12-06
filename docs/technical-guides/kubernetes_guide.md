# PokeWatch Kubernetes Deployment Guide

This guide covers deploying and managing PokeWatch on Kubernetes using Minikube.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Deployment](#deployment)
5. [Scaling](#scaling)
6. [Monitoring](#monitoring)
7. [Rolling Updates](#rolling-updates)
8. [Troubleshooting](#troubleshooting)
9. [Commands Reference](#commands-reference)

---

## Prerequisites

### Required Tools

- **Minikube** v1.25+ ([Installation](https://minikube.sigs.k8s.io/docs/start/))
- **kubectl** v1.22+ ([Installation](https://kubernetes.io/docs/tasks/tools/))
- **Docker** (for Minikube driver)

### Verification

```bash
# Check Minikube
minikube version

# Check kubectl
kubectl version --client

# Check Docker
docker --version
```

---

## Quick Start

### 1. Automated Deployment

The easiest way to deploy:

```bash
cd pokewatch
./scripts/deploy_k8s.sh
```

This script will:
- Start Minikube (if not running)
- Build the Docker image
- Deploy namespace, deployment, and service
- Wait for pods to be ready

### 2. Access the API

```bash
# Method 1: Port-forward
kubectl port-forward -n pokewatch svc/pokewatch-api 8000:8000

# Then access
curl http://localhost:8000/health

# Method 2: Minikube service
minikube service pokewatch-api -n pokewatch
```

---

## Architecture

### Kubernetes Resources

```
pokewatch-namespace
├── Deployment (pokewatch-api)
│   ├── Pod 1 (api container)
│   └── Pod 2 (api container)
├── Service (pokewatch-api)
│   └── NodePort :30080
├── ConfigMap (pokewatch-config)
└── HPA (pokewatch-api-hpa)
    ├── Min replicas: 2
    └── Max replicas: 5
```

### Container Specifications

**API Container:**
- Image: `pokewatch-api:latest`
- Port: 8000
- Resources:
  - Request: 250m CPU, 256Mi Memory
  - Limit: 500m CPU, 512Mi Memory
- Health Probes:
  - Liveness: `/health` (30s delay)
  - Readiness: `/health` (10s delay)

### Network

- **Service Type**: NodePort
- **Internal Port**: 8000
- **External Port**: 30080
- **Access**: Through port-forward or Minikube service

---

## Deployment

### Manual Deployment Steps

#### 1. Start Minikube

```bash
minikube start --driver=docker --memory=4096 --cpus=2
```

#### 2. Build Docker Image

```bash
# Point Docker to Minikube's Docker daemon
eval $(minikube docker-env)

# Build image
docker build -t pokewatch-api:latest -f docker/api.Dockerfile .
```

#### 3. Apply Kubernetes Manifests

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Deploy application
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml

# (Optional) Enable auto-scaling
kubectl apply -f k8s/hpa.yaml
```

#### 4. Verify Deployment

```bash
# Check all resources
kubectl get all -n pokewatch

# Wait for pods to be ready
kubectl wait --for=condition=ready pod \
    -l app=pokewatch-api \
    -n pokewatch \
    --timeout=120s
```

---

## Scaling

### Manual Scaling

Scale the number of pods manually:

```bash
# Scale to 5 pods
kubectl scale deployment/pokewatch-api --replicas=5 -n pokewatch

# Verify
kubectl get pods -n pokewatch
```

### Horizontal Pod Autoscaler (HPA)

The HPA automatically scales pods based on CPU and memory usage.

#### Configuration

- **Min replicas**: 2
- **Max replicas**: 5
- **CPU threshold**: 70% average utilization
- **Memory threshold**: 80% average utilization

#### Enable HPA

```bash
kubectl apply -f k8s/hpa.yaml
```

#### Monitor HPA

```bash
# Current status
kubectl get hpa -n pokewatch

# Watch for changes
kubectl get hpa -n pokewatch --watch
```

#### Example Output

```
NAME                  REFERENCE                  TARGETS   MINPODS   MAXPODS   REPLICAS
pokewatch-api-hpa     Deployment/pokewatch-api   15%/70%   2         5         2
```

#### Disable HPA

```bash
kubectl delete hpa pokewatch-api-hpa -n pokewatch
```

---

## Monitoring

### Using the Monitor Script

```bash
# One-time status
./scripts/monitor_k8s.sh

# Continuous monitoring
./scripts/monitor_k8s.sh --watch
```

### Manual Monitoring Commands

#### Pod Status

```bash
# List all pods
kubectl get pods -n pokewatch

# Detailed pod info
kubectl describe pod <pod-name> -n pokewatch

# Pod resource usage (requires metrics-server)
kubectl top pods -n pokewatch
```

#### Logs

```bash
# View pod logs
kubectl logs <pod-name> -n pokewatch

# Follow logs in real-time
kubectl logs -f <pod-name> -n pokewatch

# Logs from all pods
kubectl logs -l app=pokewatch-api -n pokewatch
```

#### Events

```bash
# Recent events
kubectl get events -n pokewatch --sort-by='.lastTimestamp'
```

#### Service Status

```bash
# List services
kubectl get svc -n pokewatch

# Service details
kubectl describe svc pokewatch-api -n pokewatch
```

---

## Rolling Updates

Rolling updates allow zero-downtime deployments.

### Update to New Version

#### 1. Build New Image

```bash
# Point to Minikube Docker
eval $(minikube docker-env)

# Build with new tag
docker build -t pokewatch-api:v2 -f docker/api.Dockerfile .
```

#### 2. Update Deployment

```bash
# Update image
kubectl set image deployment/pokewatch-api \
    api=pokewatch-api:v2 \
    -n pokewatch

# Watch rollout
kubectl rollout status deployment/pokewatch-api -n pokewatch
```

#### 3. Verify Update

```bash
# Check pod ages (new pods created)
kubectl get pods -n pokewatch

# View rollout history
kubectl rollout history deployment/pokewatch-api -n pokewatch
```

### Rollback

If something goes wrong:

```bash
# Rollback to previous version
kubectl rollout undo deployment/pokewatch-api -n pokewatch

# Rollback to specific revision
kubectl rollout undo deployment/pokewatch-api \
    --to-revision=1 \
    -n pokewatch
```

### Rollout History

```bash
# View all revisions
kubectl rollout history deployment/pokewatch-api -n pokewatch

# View specific revision
kubectl rollout history deployment/pokewatch-api \
    --revision=2 \
    -n pokewatch
```

---

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n pokewatch

# View pod events
kubectl describe pod <pod-name> -n pokewatch

# Check logs
kubectl logs <pod-name> -n pokewatch
```

**Common Issues:**

1. **ImagePullBackOff**: Image not found in Minikube
   ```bash
   # Rebuild image with Minikube Docker
   eval $(minikube docker-env)
   docker build -t pokewatch-api:latest -f docker/api.Dockerfile .
   ```

2. **CrashLoopBackOff**: Application crashing
   ```bash
   # Check logs for errors
   kubectl logs <pod-name> -n pokewatch
   ```

3. **Pending**: Insufficient resources
   ```bash
   # Check node resources
   kubectl top nodes
   ```

### Service Not Accessible

```bash
# Check service
kubectl get svc -n pokewatch

# Verify endpoints
kubectl get endpoints -n pokewatch
```

### HPA Not Working

```bash
# Check HPA status
kubectl get hpa -n pokewatch

# Check metrics-server
kubectl top pods -n pokewatch
```

If metrics not available:
```bash
# Enable metrics-server
minikube addons enable metrics-server
```

### Minikube Issues

```bash
# Check Minikube status
minikube status

# Restart Minikube
minikube stop
minikube start

# Delete and recreate cluster
minikube delete
minikube start --driver=docker --memory=4096 --cpus=2
```

---

## Commands Reference

See the complete commands cheat sheet:

```bash
./scripts/k8s_commands.sh
```

### Essential Commands

```bash
# Deployment
kubectl get all -n pokewatch
kubectl apply -f k8s/
kubectl delete -f k8s/

# Scaling
kubectl scale deployment/pokewatch-api --replicas=<N> -n pokewatch
kubectl get hpa -n pokewatch

# Updates
kubectl set image deployment/pokewatch-api api=pokewatch-api:<tag> -n pokewatch
kubectl rollout undo deployment/pokewatch-api -n pokewatch

# Monitoring
kubectl get pods -n pokewatch
kubectl logs <pod-name> -n pokewatch
kubectl top pods -n pokewatch

# Access
kubectl port-forward -n pokewatch svc/pokewatch-api 8000:8000
minikube service pokewatch-api -n pokewatch

# Cleanup
kubectl delete namespace pokewatch
minikube stop
```

---

## Production Considerations

While this guide uses Minikube for local development, deploying to production requires additional considerations:

1. **Managed Kubernetes**: Use GKE, EKS, or AKS
2. **Ingress**: Replace NodePort with Ingress controller
3. **TLS/SSL**: Add HTTPS certificates
4. **Secrets Management**: Use Kubernetes Secrets or external secret managers
5. **Persistent Storage**: Add PersistentVolumes for data
6. **Monitoring**: Prometheus + Grafana
7. **Logging**: ELK or Loki stack
8. **CI/CD**: Automate builds and deployments
9. **Resource Limits**: Tune based on load testing
10. **High Availability**: Multi-zone deployment

---

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Minikube Documentation](https://minikube.sigs.k8s.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Horizontal Pod Autoscaler](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review pod logs: `kubectl logs <pod-name> -n pokewatch`
3. Check events: `kubectl get events -n pokewatch`
4. Run monitor script: `./scripts/monitor_k8s.sh`
