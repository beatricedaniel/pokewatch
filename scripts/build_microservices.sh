#!/bin/bash
# Build all microservice Docker images for PokeWatch
#
# This script builds 4 Docker images:
# 1. pokewatch-api:latest - API Gateway
# 2. pokewatch-model:latest - Model Service (BentoML)
# 3. pokewatch-decision:latest - Decision Service
# 4. pokewatch-batch:latest - Batch Pipeline (for Airflow)
#
# Usage:
#   ./scripts/build_microservices.sh [--minikube]
#
# Options:
#   --minikube    Use Minikube's Docker daemon (for local k8s deployment)

set -e

# Parse arguments
USE_MINIKUBE=false
if [ "$1" == "--minikube" ]; then
    USE_MINIKUBE=true
fi

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Building PokeWatch Microservices${NC}"
echo -e "${BLUE}========================================${NC}"

# Switch to Minikube Docker daemon if requested
if [ "$USE_MINIKUBE" = true ]; then
    echo -e "${YELLOW}Configuring Docker to use Minikube...${NC}"
    eval $(minikube docker-env)
    echo -e "${GREEN}✓ Using Minikube Docker daemon${NC}"
fi

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "\n${YELLOW}Project Root: $PROJECT_ROOT${NC}"

# Build 1: API Gateway
echo -e "\n${BLUE}[1/4] Building API Gateway...${NC}"
docker build \
    -t pokewatch-api:latest \
    -f docker/api.Dockerfile \
    .
echo -e "${GREEN}✓ API Gateway built successfully${NC}"

# Build 2: Model Service (BentoML)
echo -e "\n${BLUE}[2/4] Building Model Service...${NC}"
docker build \
    -t pokewatch-model:latest \
    -f docker/model-service.Dockerfile \
    .
echo -e "${GREEN}✓ Model Service built successfully${NC}"

# Build 3: Decision Service
echo -e "\n${BLUE}[3/4] Building Decision Service...${NC}"
docker build \
    -t pokewatch-decision:latest \
    -f docker/decision-service.Dockerfile \
    .
echo -e "${GREEN}✓ Decision Service built successfully${NC}"

# Build 4: Batch Pipeline (for Airflow)
echo -e "\n${BLUE}[4/4] Building Batch Pipeline...${NC}"
docker build \
    -t pokewatch-batch:latest \
    -f docker/batch-pipeline.Dockerfile \
    .
echo -e "${GREEN}✓ Batch Pipeline built successfully${NC}"

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}All images built successfully!${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${YELLOW}Built images:${NC}"
docker images | grep -E "pokewatch-(api|model|decision|batch)" | head -4

echo -e "\n${YELLOW}Next steps:${NC}"
if [ "$USE_MINIKUBE" = true ]; then
    echo "  1. Deploy to Kubernetes: kubectl apply -f k8s/"
    echo "  2. Check deployment: kubectl get pods -n pokewatch"
    echo "  3. Access API: minikube service api-gateway -n pokewatch"
else
    echo "  1. Test locally: docker-compose up"
    echo "  2. Or deploy to k8s: ./scripts/build_microservices.sh --minikube && kubectl apply -f k8s/"
fi
