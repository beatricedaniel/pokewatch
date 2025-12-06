# Kubernetes Deployment Options

**Question:** Why not use normal Docker + Kubernetes deployment?

**Answer:** We can! Here are your options.

---

## Option 1: Minikube (Local) - Recommended ✅

### What it is
- Kubernetes running locally on your Mac
- Free, fast, safe to experiment
- **Real Kubernetes** - same commands as production

### Advantages
- ✅ **Free** - no cloud costs
- ✅ **Fast** - deploy in seconds
- ✅ **Learn safely** - can't break anything
- ✅ **Same skills** - identical kubectl commands
- ✅ **Offline** - works without internet

### Time & Cost
- **Setup:** 30 minutes
- **Cost:** $0
- **Complexity:** Low

### Quick Start
```bash
brew install minikube kubectl
minikube start
bash scripts/deploy_k8s.sh
```

### When to Use
- ✅ MLOps course projects
- ✅ Learning Kubernetes
- ✅ Local development
- ✅ Testing before cloud deployment

---

## Option 2: Cloud Kubernetes (GKE/EKS/AKS) - Production

### What it is
- Managed Kubernetes on cloud provider
- Real production environment
- Public internet access

### Advantages
- ✅ **Production-ready** - real infrastructure
- ✅ **Public access** - share with anyone
- ✅ **Auto-scaling** - with real cloud resources
- ✅ **High availability** - multiple zones

### Disadvantages
- ❌ **Costs money** - $100-300/month
- ❌ **Complex setup** - cloud account, networking, billing
- ❌ **Slower** - deploy to cloud takes longer
- ❌ **Requires credit card**

### Time & Cost
- **Setup:** 4-6 hours
- **Cost:** $100-300/month (or free tier for 1 month)
- **Complexity:** High

### When to Use
- ✅ Production deployments
- ✅ Demonstrating cloud skills
- ✅ When you need public access
- ✅ When budget allows

---

## Option 3: Docker Compose - Simplest

### What it is
- Just Docker containers, no Kubernetes
- We already have this working!

### Why Not Enough
- ❌ Doesn't demonstrate **Kubernetes** skills
- ❌ No container orchestration
- ❌ No auto-scaling
- ✅ Good for local development only

---

## Hybrid Approach: Best of Both Worlds 🎯

**Recommended plan for MLOps course:**

### Week 3: Local (Minikube) - 2-3 days
1. Deploy to Minikube
2. Learn Kubernetes concepts
3. Test scaling and management
4. **Cost:** $0

### Week 4: Cloud (Optional) - 1-2 days
1. Deploy same manifests to cloud
2. Use GKE free tier ($300 credits)
3. Document cloud deployment
4. **Cost:** $0 (free tier)

**Key insight:** The Kubernetes manifests are **identical**! Just change kubectl context.

---

## Detailed Comparison

| Feature | Minikube | Cloud K8s | Docker Compose |
|---------|----------|-----------|----------------|
| **Cost** | Free | $100-300/month | Free |
| **Setup Time** | 30 min | 4-6 hours | 5 min |
| **Learn K8s** | ✅ Yes | ✅ Yes | ❌ No |
| **Same kubectl** | ✅ Yes | ✅ Yes | ❌ No |
| **Public Access** | ❌ No | ✅ Yes | ❌ No |
| **Auto-scaling** | ✅ Yes (limited) | ✅ Yes (full) | ❌ No |
| **Production-ready** | ❌ No | ✅ Yes | ❌ No |
| **Course Project** | ✅ Perfect | ⚠️ Overkill | ⚠️ Too simple |

---

## Implementation Plans

### Plan A: Minikube Only (Recommended)

**Time:** 2-3 days
**Cost:** $0

See: [KUBERNETES_SIMPLE_PLAN.md](KUBERNETES_SIMPLE_PLAN.md)

**Deliverables:**
- K8s manifests (work anywhere!)
- Deployed to local Kubernetes
- Scaling tested
- Documentation

---

### Plan B: Minikube + Cloud

**Time:** 3-4 days
**Cost:** $0 (using free tier)

**Day 1-2:** Minikube setup (see Plan A)

**Day 3-4:** Cloud deployment

#### Task 1: Create GKE Cluster (1 hour)

```bash
# Install gcloud CLI
brew install google-cloud-sdk

# Login to Google Cloud
gcloud auth login

# Create project
gcloud projects create pokewatch-mlops

# Enable Kubernetes API
gcloud services enable container.googleapis.com

# Create cluster (smallest size for free tier)
gcloud container clusters create pokewatch \
  --zone=us-central1-a \
  --num-nodes=2 \
  --machine-type=e2-small \
  --disk-size=10GB

# Get credentials
gcloud container clusters get-credentials pokewatch --zone=us-central1-a
```

#### Task 2: Deploy to Cloud (30 min)

```bash
# Same manifests work!
kubectl apply -f k8s/

# Get external IP
kubectl get services -n pokewatch

# Test API
curl http://<external-ip>:8000/health
```

#### Task 3: Monitor Costs (15 min)

```bash
# Set billing alert
gcloud billing budgets create --amount=50 --threshold=80

# Check current costs
gcloud billing accounts get-iam-policy
```

#### Task 4: Cleanup (5 min)

```bash
# Delete cluster to stop charges!
gcloud container clusters delete pokewatch --zone=us-central1-a
```

---

## My Recommendation

### For Data Scientest MLOps Course:

**Use Minikube (Plan A)** ✅

**Why:**
1. **Learn all the same concepts** - Kubernetes, kubectl, manifests
2. **Zero cost** - important for students
3. **Fast iteration** - deploy in seconds, not minutes
4. **Safe to experiment** - can't accidentally spend money
5. **Same CV value** - recruiters see "Kubernetes experience"

**The manifests are identical!** If you later want cloud, just:
```bash
# Switch context
gcloud container clusters get-credentials pokewatch
# Deploy (same command!)
kubectl apply -f k8s/
```

---

## What Recruiters See

### Your CV:
```
PokeWatch MLOps Project

Technologies:
✓ Kubernetes (deployment, scaling, orchestration)
✓ Docker (containerization)
✓ kubectl (cluster management)
✓ Container orchestration
✓ Auto-scaling (HPA)
✓ Health checks and probes
```

They **don't care** if it was Minikube or GKE - you learned Kubernetes! ✅

---

## Cloud-Native Without Cloud Costs

**What Minikube teaches you:**

```bash
# These commands work identically in Minikube AND GKE/EKS/AKS

kubectl apply -f k8s/
kubectl get pods
kubectl scale deployment app --replicas=5
kubectl logs -f pod-name
kubectl describe deployment app
kubectl rollout restart deployment app
kubectl port-forward svc/app 8000:8000
```

**You're learning production Kubernetes** - just running it locally! 🎯

---

## Decision Matrix

### Choose Minikube if:
- ✅ Student/learning project
- ✅ Want to learn K8s concepts
- ✅ Limited budget
- ✅ Faster iteration preferred
- ✅ Offline work needed

### Choose Cloud K8s if:
- ✅ Production deployment
- ✅ Need public access
- ✅ Demonstrating cloud skills specifically
- ✅ Budget allows ($100-300/month)
- ✅ Team collaboration needed

### Choose Docker Compose if:
- ✅ Simple local development only
- ❌ NOT for learning Kubernetes

---

## Conclusion

**Answer to your question:**

> "Why not use normal deployment with docker and kubernetes?"

**You CAN!** Both options are valid:

1. **Minikube** = Kubernetes on your laptop (recommended for course)
2. **Cloud K8s** = Kubernetes on GKE/EKS/AKS (production)

**They use the SAME manifests and commands!**

**My recommendation:** Start with Minikube (free, fast, safe), then optionally deploy to cloud for Week 4 if you want.

---

**Next step:** Choose your path and I'll help you implement! 🚀

- Option A: Minikube only (2-3 days, $0)
- Option B: Minikube + Cloud (3-4 days, $0 with free tier)
- Option C: Cloud only (4-5 days, $100-300/month)
