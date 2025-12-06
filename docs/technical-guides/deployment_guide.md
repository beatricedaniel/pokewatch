# Deployment Guide - PokeWatch

Complete guide for deploying PokeWatch services to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Deployment](#local-deployment)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [CI/CD Deployment](#cicd-deployment)
6. [Environment Configuration](#environment-configuration)
7. [Monitoring & Health Checks](#monitoring--health-checks)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools
- Docker >= 24.0
- Docker Compose >= 2.20
- Python 3.13+
- uv package manager
- kubectl (for Kubernetes)
- GitHub account with container registry access

### Required Secrets
```bash
POKEMON_PRICE_API_KEY=your_api_key
DAGSHUB_TOKEN=your_dagshub_token
MLFLOW_TRACKING_URI=https://dagshub.com/...
API_KEYS=key1,key2,key3
```

## Local Deployment

### 1. Development Server

```bash
cd pokewatch

# Install dependencies
python -m uv venv
source .venv/bin/activate
python -m uv pip install -e ".[dev]"

# Run FastAPI
uvicorn src.pokewatch.api.main:app --reload --port 8000

# Or run BentoML
bentoml serve src.pokewatch.serving.service:PokeWatchService --port 3000
```

### 2. Local Testing

```bash
# Test FastAPI endpoint
curl http://localhost:8000/health

# Test BentoML endpoint
curl http://localhost:3000/health

# Test prediction
curl -X POST http://localhost:8000/fair_price \
  -H "Content-Type: application/json" \
  -d '{"card_id": "sv4pt5-001", "date": "2024-01-15"}'
```

## Docker Deployment

### 1. Build Images

```bash
cd pokewatch

# Build FastAPI image
docker build -f docker/api.Dockerfile -t pokewatch-api:latest .

# Build BentoML image
docker build -f docker/bento.Dockerfile -t pokewatch-bento:latest .
```

### 2. Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose --profile bento up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Docker Compose Configuration

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  api:
    build:
      context: .
      dockerfile: docker/api.Dockerfile
    ports:
      - "8000:8000"
    environment:
      - POKEMON_PRICE_API_KEY=${POKEMON_PRICE_API_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  bento-api:
    build:
      context: .
      dockerfile: docker/bento.Dockerfile
    ports:
      - "3000:3000"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    profiles:
      - bento

volumes:
  redis_data:
```

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace pokewatch
```

### 2. Create Secrets

```bash
kubectl create secret generic pokewatch-secrets \
  --from-literal=api-key=$POKEMON_PRICE_API_KEY \
  --from-literal=dagshub-token=$DAGSHUB_TOKEN \
  -n pokewatch
```

### 3. Deploy Redis

Create `k8s/redis-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: pokewatch
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: pokewatch
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

### 4. Deploy API Service

Create `k8s/api-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pokewatch-api
  namespace: pokewatch
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pokewatch-api
  template:
    metadata:
      labels:
        app: pokewatch-api
        version: v1
    spec:
      containers:
      - name: api
        image: ghcr.io/your-username/pokewatch-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: POKEMON_PRICE_API_KEY
          valueFrom:
            secretKeyRef:
              name: pokewatch-secrets
              key: api-key
        - name: REDIS_URL
          value: "redis://redis:6379"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
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
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: pokewatch-api
  namespace: pokewatch
spec:
  type: LoadBalancer
  selector:
    app: pokewatch-api
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
```

### 5. Deploy BentoML Service

Create `k8s/bento-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pokewatch-bento
  namespace: pokewatch
spec:
  replicas: 2
  selector:
    matchLabels:
      app: pokewatch-bento
  template:
    metadata:
      labels:
        app: pokewatch-bento
        version: v1
    spec:
      containers:
      - name: bento
        image: ghcr.io/your-username/pokewatch-bento:latest
        ports:
        - containerPort: 3000
        env:
        - name: REDIS_URL
          value: "redis://redis:6379"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 60
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: pokewatch-bento
  namespace: pokewatch
spec:
  type: LoadBalancer
  selector:
    app: pokewatch-bento
  ports:
  - port: 80
    targetPort: 3000
    protocol: TCP
```

### 6. Horizontal Pod Autoscaler

Create `k8s/hpa.yaml`:

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
```

### 7. Deploy to Kubernetes

```bash
# Deploy all resources
kubectl apply -f k8s/

# Check deployments
kubectl get deployments -n pokewatch

# Check pods
kubectl get pods -n pokewatch

# Check services
kubectl get services -n pokewatch

# View logs
kubectl logs -f deployment/pokewatch-api -n pokewatch
```

## CI/CD Deployment

### 1. Automated Deployment with GitHub Actions

Deployment happens automatically when:
- Version tag pushed (e.g., `v1.2.3`)
- Release workflow succeeds
- All tests pass

### 2. Manual Deployment

```bash
# Trigger deployment manually
gh workflow run release.yml

# Or use BentoML build workflow
gh workflow run bento-build.yml -f version=1.2.3
```

### 3. Deployment Flow

```
1. Push version tag → v1.2.3
2. GitHub Actions triggered
3. Run tests
4. Build Docker images
5. Push to ghcr.io
6. Deploy to staging
7. Run smoke tests
8. Manual approval (optional)
9. Deploy to production
```

## Environment Configuration

### Production Environment Variables

Create `.env.production`:

```bash
# API Configuration
POKEMON_PRICE_API_KEY=your_production_key
API_KEYS=prod_key1,prod_key2,prod_key3

# Redis Configuration
REDIS_URL=redis://redis:6379
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600

# Security
RATE_LIMIT_ENABLED=true
RATE_LIMIT_RPM=60
AUTH_ENABLED=true

# MLflow
MLFLOW_TRACKING_URI=https://dagshub.com/username/pokewatch.mlflow
DAGSHUB_TOKEN=your_dagshub_token

# Performance
MODEL_PRELOAD=true
BATCH_SIZE=50
CONNECTION_POOL_SIZE=10

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Staging Environment

Create `.env.staging`:

```bash
# Similar to production but with:
POKEMON_PRICE_API_KEY=your_staging_key
API_KEYS=staging_key1,staging_key2
LOG_LEVEL=DEBUG
RATE_LIMIT_RPM=120  # Higher for testing
```

## Monitoring & Health Checks

### Health Check Endpoints

```bash
# FastAPI
curl http://api.pokewatch.com/health
# Response: {"status": "healthy", "version": "1.2.3"}

# BentoML
curl http://bento.pokewatch.com/health
# Response: {"status": "healthy", "model_loaded": true}
```

### Readiness Probes

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3
```

### Liveness Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 5
```

### Metrics Endpoints

```bash
# Prometheus metrics (Future: Week 3)
curl http://api.pokewatch.com/metrics
```

## Rollback Procedures

### Docker Rollback

```bash
# Rollback to previous version
docker-compose down
docker pull ghcr.io/username/pokewatch-api:v1.1.0
docker-compose up -d
```

### Kubernetes Rollback

```bash
# Check rollout history
kubectl rollout history deployment/pokewatch-api -n pokewatch

# Rollback to previous version
kubectl rollout undo deployment/pokewatch-api -n pokewatch

# Rollback to specific revision
kubectl rollout undo deployment/pokewatch-api --to-revision=2 -n pokewatch

# Check rollout status
kubectl rollout status deployment/pokewatch-api -n pokewatch
```

## Troubleshooting

### Common Issues

**1. Container Fails to Start**

```bash
# Check logs
docker logs <container-id>

# Check events
kubectl describe pod <pod-name> -n pokewatch

# Common causes:
# - Missing environment variables
# - Model files not found
# - Redis connection failed
```

**2. Health Check Failing**

```bash
# Test health endpoint directly
kubectl port-forward pod/<pod-name> 8000:8000 -n pokewatch
curl http://localhost:8000/health

# Check pod logs
kubectl logs <pod-name> -n pokewatch
```

**3. High Memory Usage**

```bash
# Check resource usage
kubectl top pods -n pokewatch

# Increase memory limits
kubectl edit deployment pokewatch-api -n pokewatch

# Or scale down replicas temporarily
kubectl scale deployment pokewatch-api --replicas=1 -n pokewatch
```

**4. Redis Connection Issues**

```bash
# Test Redis connectivity
kubectl exec -it <api-pod> -n pokewatch -- sh
redis-cli -h redis ping

# Check Redis logs
kubectl logs deployment/redis -n pokewatch
```

### Debug Mode

Enable debug logging:

```bash
# Set environment variable
kubectl set env deployment/pokewatch-api LOG_LEVEL=DEBUG -n pokewatch

# View detailed logs
kubectl logs -f deployment/pokewatch-api -n pokewatch
```

## Performance Tuning

### Resource Optimization

```yaml
resources:
  requests:
    memory: "512Mi"  # Minimum required
    cpu: "250m"
  limits:
    memory: "1Gi"    # Maximum allowed
    cpu: "500m"
```

### Scaling Configuration

```bash
# Manual scaling
kubectl scale deployment pokewatch-api --replicas=5 -n pokewatch

# Auto-scaling based on CPU
kubectl autoscale deployment pokewatch-api \
  --min=2 --max=10 --cpu-percent=70 -n pokewatch
```

### Connection Pooling

Configure in application:

```python
# Redis pool
redis_pool = redis.ConnectionPool(
    host='redis',
    port=6379,
    max_connections=50,
    decode_responses=True
)
```

## Security Best Practices

### 1. Use Secrets Management

```bash
# Never commit secrets to git
# Use Kubernetes secrets or external secret manager

# Create secret from file
kubectl create secret generic api-secrets \
  --from-env-file=.env.production \
  -n pokewatch
```

### 2. Network Policies

Create `k8s/network-policy.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: pokewatch-network-policy
  namespace: pokewatch
spec:
  podSelector:
    matchLabels:
      app: pokewatch-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx-ingress
    ports:
    - protocol: TCP
      port: 8000
```

### 3. RBAC Configuration

```bash
# Create service account
kubectl create serviceaccount pokewatch-sa -n pokewatch

# Bind to role
kubectl create rolebinding pokewatch-binding \
  --clusterrole=view \
  --serviceaccount=pokewatch:pokewatch-sa \
  -n pokewatch
```

## Backup & Recovery

### Database Backup (if applicable)

```bash
# Backup Redis data
kubectl exec -it redis-0 -n pokewatch -- redis-cli BGSAVE

# Copy backup file
kubectl cp pokewatch/redis-0:/data/dump.rdb ./backup/
```

### Model Artifacts Backup

```bash
# DVC handles model versioning
dvc push

# Manually backup model directory
tar -czf models-backup.tar.gz pokewatch/models/
```

## Monitoring Dashboard

### Kubernetes Dashboard

```bash
# Install dashboard
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

# Create admin user
kubectl create serviceaccount dashboard-admin -n kubernetes-dashboard
kubectl create clusterrolebinding dashboard-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=kubernetes-dashboard:dashboard-admin

# Get token
kubectl -n kubernetes-dashboard create token dashboard-admin

# Access dashboard
kubectl proxy
# Navigate to: http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/
```

## Production Checklist

Before deploying to production:

- [ ] All tests passing in CI/CD
- [ ] Environment variables configured
- [ ] Secrets created in Kubernetes
- [ ] Resource limits set appropriately
- [ ] Health checks configured
- [ ] Monitoring enabled
- [ ] Backup strategy in place
- [ ] Rollback procedure tested
- [ ] Load testing completed
- [ ] Security scan passed
- [ ] Documentation updated
- [ ] Team notified of deployment

---

**Last Updated:** Week 2, Day 2 - Phase 3 Implementation
