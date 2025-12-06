# PokeWatch Kubernetes Verification Commands

Complete guide with all commands to verify the Kubernetes implementation.

## Quick Verification

```bash
# Automated verification (recommended)
./scripts/verify_k8s.sh
```

## Manual Step-by-Step Verification

### 1. Check Prerequisites
```bash
minikube version
kubectl version --client
docker --version
minikube status
```

### 2. Verify Files Exist
```bash
ls k8s/*.yaml
ls scripts/*k8s*.sh
ls docs/kubernetes_guide.md
```

### 3. Check Kubernetes Resources
```bash
kubectl get all -n pokewatch
kubectl get namespace pokewatch
kubectl get deployment -n pokewatch
kubectl get pods -n pokewatch
kubectl get svc -n pokewatch
```

### 4. Verify Pods Are Running
```bash
kubectl get pods -n pokewatch
# Expected: 2 pods with STATUS=Running, READY=1/1

kubectl describe pod -n pokewatch -l app=pokewatch-api
kubectl logs -n pokewatch -l app=pokewatch-api --tail=20
```

### 5. Test API Health
```bash
kubectl port-forward -n pokewatch svc/pokewatch-api 8000:8000 &
sleep 3
curl http://localhost:8000/health
pkill -f "kubectl port-forward"
```

### 6. Test Scaling
```bash
kubectl scale deployment/pokewatch-api --replicas=5 -n pokewatch
sleep 10
kubectl get pods -n pokewatch
kubectl scale deployment/pokewatch-api --replicas=2 -n pokewatch
```

### 7. Test Scripts
```bash
./scripts/monitor_k8s.sh
./scripts/k8s_commands.sh
./scripts/verify_k8s.sh
```

## Complete Checklist

- [ ] Minikube running
- [ ] 2 pods running
- [ ] Service accessible
- [ ] Health endpoint returns OK
- [ ] Scaling works
- [ ] All scripts execute
- [ ] Documentation exists
