# Kubernetes Quick Reference

## Essential Verification Commands

```bash
# Navigate to project
cd /Users/beatrice/Documents/data_scientest/projet/pokewatch

# 1. Verify Everything (Automated)
./scripts/verify_k8s.sh

# 2. Check Status
kubectl get all -n pokewatch

# 3. Test API
kubectl port-forward -n pokewatch svc/pokewatch-api 8000:8000 &
curl http://localhost:8000/health
pkill -f "kubectl port-forward"

# 4. Monitor
./scripts/monitor_k8s.sh

# 5. View Logs
kubectl logs -n pokewatch -l app=pokewatch-api --tail=50
```

---

## How Current Deployment Works

### Local Minikube

1. **Build**: Image created inside Minikube
2. **Deploy**: Kubernetes creates 2 pods
3. **Access**: Via port-forward to localhost:8000

```bash
eval $(minikube docker-env)           # Point to Minikube Docker
docker build -t pokewatch-api:latest  # Build image
kubectl apply -f k8s/                 # Deploy
kubectl port-forward svc/... 8000     # Access
```

---

## Deploying to Remote VM

### Quick Steps

1. **Setup VM**:
   ```bash
   ssh user@vm-ip
   curl -sfL https://get.k3s.io | sh -
   ```

2. **Configure kubectl**:
   ```bash
   scp user@vm-ip:/etc/rancher/k3s/k3s.yaml ~/.kube/config-vm
   sed -i '' 's/127.0.0.1/VM-IP/g' ~/.kube/config-vm
   export KUBECONFIG=~/.kube/config-vm
   ```

3. **Build Image** (choose one):
   - **On VM**: `ssh user@vm-ip && cd pokewatch && docker build ...`
   - **Registry**: `docker push <registry>/pokewatch-api:latest`

4. **Deploy**:
   ```bash
   kubectl apply -f k8s/
   ```

5. **Access**:
   ```bash
   curl http://VM-IP:30080/health
   ```

### Key Difference

| Local | Remote |
|-------|--------|
| Build in Minikube | Build on VM or use registry |
| Access: `localhost:8000` (port-forward) | Access: `VM-IP:30080` (direct) |
| `imagePullPolicy: Never` | `imagePullPolicy: Always` (if registry) |

---

## File Structure

```
pokewatch/
├── k8s/
│   ├── namespace.yaml
│   ├── api-deployment.yaml
│   ├── api-service.yaml
│   └── hpa.yaml
├── scripts/
│   ├── deploy_k8s.sh      # Automated deployment
│   ├── monitor_k8s.sh     # Status monitoring
│   ├── verify_k8s.sh      # Verification tests
│   └── k8s_commands.sh    # Commands cheat sheet
└── docs/
    └── kubernetes_guide.md
```

---

## Most Important Commands

```bash
# Deploy
./scripts/deploy_k8s.sh

# Verify
./scripts/verify_k8s.sh

# Monitor
./scripts/monitor_k8s.sh

# Status
kubectl get all -n pokewatch

# Logs
kubectl logs -n pokewatch -l app=pokewatch-api

# Scale
kubectl scale deployment/pokewatch-api --replicas=5 -n pokewatch

# Clean up
kubectl delete namespace pokewatch
```

---

## Documentation Locations

- **Quick Reference**: `QUICK_REFERENCE.md` (this file)
- **Full Verification**: `VERIFICATION_COMMANDS.md`
- **Remote Deployment**: `DEPLOYMENT_GUIDE.md`
- **Complete Guide**: `docs/kubernetes_guide.md`
- **Implementation Details**: `KUBERNETES_COMPLETE.md`
- **Summary**: `KUBERNETES_SUMMARY.md`
