#!/bin/bash
# PokeWatch Kubernetes Verification Script

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

NAMESPACE="pokewatch"
FAILED=0

echo -e "${BLUE}=== PokeWatch Kubernetes Verification ===${NC}"
echo ""

# Test function
test_step() {
    local description=$1
    local command=$2

    echo -n "  Testing: $description... "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# 1. Prerequisites
echo -e "${YELLOW}1. Checking Prerequisites${NC}"
test_step "Minikube installed" "which minikube"
test_step "kubectl installed" "which kubectl"
test_step "Docker installed" "which docker"
test_step "Minikube running" "minikube status"
echo ""

# 2. Namespace
echo -e "${YELLOW}2. Checking Namespace${NC}"
test_step "Namespace exists" "kubectl get namespace $NAMESPACE"
echo ""

# 3. Deployments
echo -e "${YELLOW}3. Checking Deployments${NC}"
test_step "Deployment exists" "kubectl get deployment pokewatch-api -n $NAMESPACE"
test_step "Deployment ready" "kubectl get deployment pokewatch-api -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' | grep -q '[0-9]'"
test_step "Min 2 replicas" "[ \$(kubectl get deployment pokewatch-api -n $NAMESPACE -o jsonpath='{.status.readyReplicas}') -ge 2 ]"
echo ""

# 4. Pods
echo -e "${YELLOW}4. Checking Pods${NC}"
test_step "Pods exist" "kubectl get pods -n $NAMESPACE -l app=pokewatch-api"
test_step "All pods running" "kubectl get pods -n $NAMESPACE -l app=pokewatch-api -o jsonpath='{.items[*].status.phase}' | grep -q 'Running'"
test_step "All pods ready" "kubectl get pods -n $NAMESPACE -l app=pokewatch-api -o jsonpath='{.items[*].status.conditions[?(@.type==\"Ready\")].status}' | grep -q 'True'"
echo ""

# 5. Services
echo -e "${YELLOW}5. Checking Services${NC}"
test_step "Service exists" "kubectl get svc pokewatch-api -n $NAMESPACE"
test_step "Service type NodePort" "kubectl get svc pokewatch-api -n $NAMESPACE -o jsonpath='{.spec.type}' | grep -q 'NodePort'"
test_step "Service has endpoints" "kubectl get endpoints pokewatch-api -n $NAMESPACE -o jsonpath='{.subsets[*].addresses[*].ip}' | grep -q '[0-9]'"
echo ""

# 6. ConfigMap
echo -e "${YELLOW}6. Checking ConfigMap${NC}"
test_step "ConfigMap exists" "kubectl get configmap pokewatch-config -n $NAMESPACE"
echo ""

# 7. Docker Image
echo -e "${YELLOW}7. Checking Docker Image${NC}"
eval $(minikube docker-env)
test_step "Docker image exists" "docker images | grep -q 'pokewatch-api'"
echo ""

# 8. Health Check
echo -e "${YELLOW}8. Checking API Health${NC}"
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=pokewatch-api -o jsonpath='{.items[0].metadata.name}')
if [ -n "$POD_NAME" ]; then
    test_step "Pod responds to health check" "kubectl exec -n $NAMESPACE $POD_NAME -- curl -s http://localhost:8000/health | grep -q 'ok'"
else
    echo -e "  ${RED}No pod found to test${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# 9. Resource Limits
echo -e "${YELLOW}9. Checking Resource Configuration${NC}"
test_step "CPU requests set" "kubectl get deployment pokewatch-api -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].resources.requests.cpu}' | grep -q 'm'"
test_step "Memory requests set" "kubectl get deployment pokewatch-api -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].resources.requests.memory}' | grep -q 'Mi'"
test_step "CPU limits set" "kubectl get deployment pokewatch-api -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].resources.limits.cpu}' | grep -q 'm'"
test_step "Memory limits set" "kubectl get deployment pokewatch-api -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}' | grep -q 'Mi'"
echo ""

# 10. Health Probes
echo -e "${YELLOW}10. Checking Health Probes${NC}"
test_step "Liveness probe configured" "kubectl get deployment pokewatch-api -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].livenessProbe}' | grep -q 'health'"
test_step "Readiness probe configured" "kubectl get deployment pokewatch-api -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].readinessProbe}' | grep -q 'health'"
echo ""

# 11. Optional: HPA
echo -e "${YELLOW}11. Checking HPA (Optional)${NC}"
if kubectl get hpa pokewatch-api-hpa -n $NAMESPACE > /dev/null 2>&1; then
    test_step "HPA exists" "kubectl get hpa pokewatch-api-hpa -n $NAMESPACE"
    test_step "HPA targets deployment" "kubectl get hpa pokewatch-api-hpa -n $NAMESPACE -o jsonpath='{.spec.scaleTargetRef.name}' | grep -q 'pokewatch-api'"
else
    echo -e "  ${YELLOW}HPA not configured (optional)${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}=== Verification Summary ===${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Deployment is healthy and ready to use."
    echo ""
    echo "Access the API:"
    echo "  kubectl port-forward -n pokewatch svc/pokewatch-api 8000:8000"
    echo "  curl http://localhost:8000/health"
    exit 0
else
    echo -e "${RED}✗ $FAILED check(s) failed${NC}"
    echo ""
    echo "Run these commands to troubleshoot:"
    echo "  kubectl get all -n $NAMESPACE"
    echo "  kubectl get events -n $NAMESPACE"
    echo "  kubectl logs -l app=pokewatch-api -n $NAMESPACE"
    exit 1
fi
