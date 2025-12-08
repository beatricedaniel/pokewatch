#!/bin/bash
# Diagnostic script for troubleshooting pod issues

NAMESPACE="${1:-pokewatch}"
APP_LABEL="${2:-model-service}"

echo "=== Diagnosing Pods: $APP_LABEL in namespace: $NAMESPACE ==="
echo ""

# 1. Pod Status
echo "📦 POD STATUS:"
kubectl get pods -n "$NAMESPACE" -l app="$APP_LABEL" -o wide
echo ""

# 2. Pod Details (first pod)
FIRST_POD=$(kubectl get pods -n "$NAMESPACE" -l app="$APP_LABEL" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$FIRST_POD" ]; then
    echo "🔍 POD DETAILS ($FIRST_POD):"
    kubectl describe pod "$FIRST_POD" -n "$NAMESPACE" | head -80
    echo ""

    # 3. Pod Logs
    echo "📋 POD LOGS ($FIRST_POD):"
    kubectl logs "$FIRST_POD" -n "$NAMESPACE" --tail=50 2>&1 || echo "  (No logs available)"
    echo ""

    # 4. Previous container logs (if crashed)
    echo "📋 PREVIOUS CONTAINER LOGS (if crashed):"
    kubectl logs "$FIRST_POD" -n "$NAMESPACE" --previous --tail=50 2>&1 || echo "  (No previous logs)"
    echo ""
fi

# 5. Recent Events
echo "📅 RECENT EVENTS:"
kubectl get events -n "$NAMESPACE" \
    --field-selector involvedObject.kind=Pod \
    --sort-by='.lastTimestamp' \
    | grep "$APP_LABEL" | tail -10
echo ""

# 6. Check if image exists (for Minikube)
if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    echo "🐳 CHECKING IMAGE IN MINIKUBE:"
    eval $(minikube docker-env)
    if docker images | grep -q "pokewatch-$APP_LABEL"; then
        echo "  ✓ Image pokewatch-$APP_LABEL:latest found"
        docker images | grep "pokewatch-$APP_LABEL"
    else
        echo "  ✗ Image pokewatch-$APP_LABEL:latest NOT found"
        echo "  Run: ./scripts/build_microservices.sh --minikube"
    fi
    echo ""
fi

# 7. Check secrets
echo "🔐 CHECKING SECRETS:"
if kubectl get secret ml-secrets -n "$NAMESPACE" &> /dev/null; then
    echo "  ✓ Secret ml-secrets exists"
    echo "  Keys in secret:"
    kubectl get secret ml-secrets -n "$NAMESPACE" -o jsonpath='{.data}' | jq -r 'keys[]' 2>/dev/null || echo "    (install jq for better output)"
else
    echo "  ✗ Secret ml-secrets NOT found in namespace $NAMESPACE"
    echo "  Run: kubectl apply -f k8s/ml-secrets-live.yaml -n $NAMESPACE"
fi
echo ""

# 8. Deployment status
echo "🚀 DEPLOYMENT STATUS:"
kubectl get deployment "$APP_LABEL" -n "$NAMESPACE" -o wide 2>/dev/null || echo "  Deployment not found"
echo ""

echo "=== Diagnosis Complete ==="
echo ""
echo "Common issues and fixes:"
echo "  - ImagePullBackOff: Image not found → Run: ./scripts/build_microservices.sh --minikube"
echo "  - CrashLoopBackOff: Check logs above for application errors"
echo "  - Secret errors: Ensure ml-secrets exists with correct keys"
echo "  - Health check failures: Service may need more time to start"
