#!/bin/bash
# Deploy Prometheus and Grafana monitoring stack to Kubernetes
# Usage: ./scripts/deploy_monitoring.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
K8S_DIR="$PROJECT_ROOT/k8s"

echo "========================================"
echo "  PokeWatch Monitoring Stack Deployment"
echo "========================================"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl not found. Please install kubectl first."
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace pokewatch &> /dev/null; then
    echo "Creating pokewatch namespace..."
    kubectl apply -f "$K8S_DIR/namespace.yaml"
fi

echo ""
echo "Step 1: Deploying Prometheus..."
echo "--------------------------------"
kubectl apply -f "$K8S_DIR/prometheus-configmap.yaml"
kubectl apply -f "$K8S_DIR/prometheus-deployment.yaml"

echo ""
echo "Step 2: Deploying Grafana..."
echo "----------------------------"
kubectl apply -f "$K8S_DIR/grafana-configmap.yaml"
kubectl apply -f "$K8S_DIR/grafana-deployment.yaml"

echo ""
echo "Step 3: Waiting for pods to be ready..."
echo "----------------------------------------"
kubectl wait --for=condition=ready pod -l app=prometheus -n pokewatch --timeout=120s || true
kubectl wait --for=condition=ready pod -l app=grafana -n pokewatch --timeout=120s || true

echo ""
echo "Step 4: Checking deployment status..."
echo "--------------------------------------"
kubectl get pods -n pokewatch -l 'app in (prometheus, grafana)'
kubectl get svc -n pokewatch -l 'app in (prometheus, grafana)'

echo ""
echo "========================================"
echo "  Deployment Complete!"
echo "========================================"
echo ""
echo "Access URLs (using Minikube):"
echo "  Prometheus: http://\$(minikube ip):30090"
echo "  Grafana:    http://\$(minikube ip):30300"
echo ""
echo "Or use port-forward:"
echo "  kubectl port-forward -n pokewatch svc/prometheus 9090:9090"
echo "  kubectl port-forward -n pokewatch svc/grafana 3000:3000"
echo ""
echo "Grafana credentials:"
echo "  Username: admin"
echo "  Password: admin"
echo ""
echo "Dashboard: Dashboards -> Browse -> PokeWatch Dashboard"
echo ""
