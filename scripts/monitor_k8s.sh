#!/bin/bash
# PokeWatch Kubernetes Monitoring Script

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

NAMESPACE="pokewatch"

echo -e "${BLUE}=== PokeWatch Kubernetes Monitor ===${NC}"
echo ""

# Function to print section header
section() {
    echo -e "${YELLOW}$1${NC}"
}

# Function to check if namespace exists
if ! kubectl get namespace "$NAMESPACE" > /dev/null 2>&1; then
    echo -e "${RED}Namespace '$NAMESPACE' not found!${NC}"
    echo "Run: kubectl apply -f k8s/namespace.yaml"
    exit 1
fi

# 1. Deployment Status
section "📦 DEPLOYMENT STATUS"
kubectl get deployments -n "$NAMESPACE"
echo ""

# 2. Pods Status
section "🚀 PODS STATUS"
kubectl get pods -n "$NAMESPACE" -o wide
echo ""

# 3. Pod Resources
section "💾 POD RESOURCES (if metrics-server enabled)"
if kubectl top pods -n "$NAMESPACE" > /dev/null 2>&1; then
    kubectl top pods -n "$NAMESPACE"
else
    echo "  Metrics not available (install metrics-server)"
fi
echo ""

# 4. Services
section "🌐 SERVICES"
kubectl get svc -n "$NAMESPACE"
echo ""

# 5. HPA Status
section "📈 HORIZONTAL POD AUTOSCALER"
if kubectl get hpa -n "$NAMESPACE" > /dev/null 2>&1; then
    kubectl get hpa -n "$NAMESPACE"
else
    echo "  No HPA configured"
    echo "  Apply with: kubectl apply -f k8s/hpa.yaml"
fi
echo ""

# 6. Recent Events
section "📋 RECENT EVENTS (last 10)"
kubectl get events -n "$NAMESPACE" \
    --sort-by='.lastTimestamp' \
    --output custom-columns='TIME:.lastTimestamp,TYPE:.type,REASON:.reason,MESSAGE:.message' \
    | tail -10
echo ""

# 7. Pod Health Summary
section "💚 HEALTH SUMMARY"
TOTAL_PODS=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l | tr -d ' ')
RUNNING_PODS=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | grep -c "Running" || echo 0)
READY_PODS=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | awk '{print $2}' | grep -c "1/1" || echo 0)

echo "  Total Pods:   $TOTAL_PODS"
echo "  Running:      $RUNNING_PODS"
echo "  Ready:        $READY_PODS"

if [ "$READY_PODS" == "$TOTAL_PODS" ] && [ "$TOTAL_PODS" -gt 0 ]; then
    echo -e "  ${GREEN}✓ All pods healthy${NC}"
else
    echo -e "  ${RED}⚠ Some pods not ready${NC}"
fi
echo ""

# 8. Quick Health Check
section "🔍 QUICK HEALTH CHECK"
SERVICE_URL="http://127.0.0.1:8000/health"
echo "  Testing API health endpoint..."
echo "  (Run: kubectl port-forward -n pokewatch svc/pokewatch-api 8000:8000)"
echo ""

# Optional: Continuous monitoring
if [ "$1" == "--watch" ] || [ "$1" == "-w" ]; then
    echo -e "${YELLOW}=== Watching pods (Ctrl+C to exit) ===${NC}"
    kubectl get pods -n "$NAMESPACE" --watch
fi
