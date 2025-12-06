#!/bin/bash
set -e

echo "=== PokeWatch Kubernetes Deployment Script ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Minikube is running
echo -e "${YELLOW}1. Checking Minikube status...${NC}"
if ! minikube status > /dev/null 2>&1; then
    echo -e "${RED}Minikube is not running. Starting Minikube...${NC}"
    minikube start --driver=docker --memory=4096 --cpus=2
else
    echo -e "${GREEN}✓ Minikube is running${NC}"
fi
echo ""

# Build Docker image in Minikube
echo -e "${YELLOW}2. Building Docker image...${NC}"
eval $(minikube docker-env)
docker build -t pokewatch-api:latest -f docker/api.Dockerfile .
echo -e "${GREEN}✓ Docker image built${NC}"
echo ""

# Apply Kubernetes manifests
echo -e "${YELLOW}3. Deploying to Kubernetes...${NC}"

# Create namespace
echo "  - Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# Apply deployment and service
echo "  - Deploying API..."
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml

echo -e "${GREEN}✓ Kubernetes resources deployed${NC}"
echo ""

# Wait for pods to be ready
echo -e "${YELLOW}4. Waiting for pods to be ready...${NC}"
kubectl wait --for=condition=ready pod \
    -l app=pokewatch-api \
    -n pokewatch \
    --timeout=120s

echo -e "${GREEN}✓ Pods are ready${NC}"
echo ""

# Display deployment status
echo -e "${YELLOW}5. Deployment Status:${NC}"
echo ""
kubectl get all -n pokewatch
echo ""

# Get service URL
echo -e "${YELLOW}6. Access Information:${NC}"
echo ""
echo "Service URL (requires port-forward):"
echo "  kubectl port-forward -n pokewatch svc/pokewatch-api 8000:8000"
echo "  Then access: http://localhost:8000"
echo ""
echo "Or use Minikube service:"
echo "  minikube service pokewatch-api -n pokewatch"
echo ""

echo -e "${GREEN}=== Deployment Complete! ===${NC}"
