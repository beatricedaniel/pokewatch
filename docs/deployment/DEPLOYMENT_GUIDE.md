# Kubernetes Deployment: Local vs Remote VM

## Current Setup (Local Minikube)

### Architecture
```
Your MacBook
└── Minikube (K8s cluster in Docker)
    ├── Pod 1: pokewatch-api
    └── Pod 2: pokewatch-api
```

### How It Works

1. **Build Image**: Images built inside Minikube's Docker daemon
   ```bash
   eval $(minikube docker-env)
   docker build -t pokewatch-api:latest -f docker/api.Dockerfile .
   ```

2. **Deploy**: Apply Kubernetes manifests
   ```bash
   kubectl apply -f k8s/
   ```

3. **Access**: Via port-forward (creates tunnel)
   ```bash
   kubectl port-forward -n pokewatch svc/pokewatch-api 8000:8000
   curl http://localhost:8000/health
   ```

### Key Configuration
```yaml
# k8s/api-deployment.yaml
containers:
- name: api
  image: pokewatch-api:latest
  imagePullPolicy: Never  # Uses local image, no registry needed
```

---

## Deploying to Remote VM

### Architecture Change
```
Your MacBook                    Remote VM (Cloud)
└── kubectl ──────────────────► K3s/Kubernetes
                                ├── Pod 1: pokewatch-api
                                └── Pod 2: pokewatch-api
```

### Prerequisites

**Remote VM Requirements:**
- OS: Ubuntu 22.04 LTS
- RAM: 8 GB minimum
- CPU: 4 cores
- Disk: 50 GB
- Open ports: 22 (SSH), 6443 (K8s API), 30080 (NodePort)

### Step-by-Step Migration

#### 1. Install K3s on Remote VM

```bash
# SSH to VM
ssh user@<vm-ip>

# Install K3s (lightweight Kubernetes)
curl -sfL https://get.k3s.io | sh -

# Verify
sudo kubectl get nodes
```

#### 2. Configure Local kubectl

```bash
# On your MacBook - get kubeconfig from VM
scp user@<vm-ip>:/etc/rancher/k3s/k3s.yaml ~/.kube/config-vm

# Edit config: replace 127.0.0.1 with VM's public IP
sed -i '' 's/127.0.0.1/<VM-PUBLIC-IP>/g' ~/.kube/config-vm

# Use remote config
export KUBECONFIG=~/.kube/config-vm

# Test connection
kubectl get nodes
```

#### 3. Handle Docker Images

**Option A: Build on VM** (Simplest)
```bash
# Copy code to VM
rsync -avz pokewatch/ user@<vm-ip>:~/pokewatch/

# SSH and build
ssh user@<vm-ip>
cd ~/pokewatch
docker build -t pokewatch-api:latest -f docker/api.Dockerfile .
```

**Option B: Use Docker Registry** (Production)
```bash
# On your MacBook
docker login
docker tag pokewatch-api:latest <dockerhub-user>/pokewatch-api:latest
docker push <dockerhub-user>/pokewatch-api:latest

# Update k8s/api-deployment.yaml:
# image: <dockerhub-user>/pokewatch-api:latest
# imagePullPolicy: Always  # Changed from Never
```

#### 4. Deploy to Remote

```bash
# On your MacBook (with remote kubeconfig)
export KUBECONFIG=~/.kube/config-vm

# Deploy
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml

# Monitor
kubectl get pods -n pokewatch --watch
```

#### 5. Access Remote Deployment

**Direct Access** (VM has public IP):
```bash
# No port-forward needed!
curl http://<vm-ip>:30080/health
```

**With Ingress** (Production):
```bash
# Add domain DNS: pokewatch.example.com → VM-IP
# Deploy ingress
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pokewatch-ingress
  namespace: pokewatch
spec:
  rules:
  - host: pokewatch.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: pokewatch-api
            port:
              number: 8000
EOF

# Access
curl http://pokewatch.example.com/health
```

---

## Key Differences

| Aspect | Local (Minikube) | Remote (VM) |
|--------|------------------|-------------|
| **Location** | Your MacBook | Cloud VM |
| **Build** | `eval $(minikube docker-env)` | Build on VM or use registry |
| **Access** | `kubectl port-forward` + localhost | Direct IP or domain |
| **Image Pull** | `Never` (local only) | `Always` (from registry) |
| **Public** | No | Yes |
| **Cost** | Free | ~$10-50/month |

## Switch Between Environments

```bash
# Use local
export KUBECONFIG=~/.kube/config
kubectl config use-context minikube

# Use remote
export KUBECONFIG=~/.kube/config-vm
kubectl get nodes
```

## Recommended Workflow

1. **Develop Locally**: Use Minikube for fast iteration
2. **Test Locally**: `./scripts/deploy_k8s.sh`
3. **Deploy to VM**: For demos and presentations
4. **Same Commands**: `kubectl apply -f k8s/` works everywhere!

---

## Quick Migration Checklist

- [ ] Provision VM (8GB RAM, 4 CPU)
- [ ] Install K3s on VM
- [ ] Configure kubectl locally
- [ ] Build/push Docker images
- [ ] Update imagePullPolicy if needed
- [ ] Deploy with `kubectl apply -f k8s/`
- [ ] Test with `curl http://vm-ip:30080/health`

---

Last Updated: 2025-12-06
