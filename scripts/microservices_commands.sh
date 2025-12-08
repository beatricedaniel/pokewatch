#!/bin/bash
# PokeWatch Microservices - Quick Reference Commands
#
# This script provides a menu-driven interface for common operations
# Usage: ./scripts/microservices_commands.sh

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

function show_menu() {
    clear
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}PokeWatch Microservices - Quick Commands${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "1.  Build all images (Minikube)"
    echo "2.  Deploy all services"
    echo "3.  Check deployment status"
    echo "4.  View logs (API Gateway)"
    echo "5.  View logs (Model Service)"
    echo "6.  View logs (Decision Service)"
    echo "7.  View logs (Airflow Scheduler)"
    echo "8.  Port-forward API Gateway"
    echo "9.  Port-forward Airflow UI"
    echo "10. Test API health"
    echo "11. Test fair price prediction"
    echo "12. Scale Model Service"
    echo "13. Trigger Airflow DAG"
    echo "14. View HPA status"
    echo "15. Copy DAG to Airflow"
    echo "16. Restart services"
    echo "17. Delete all resources"
    echo "0.  Exit"
    echo ""
    echo -n "Select option: "
}

function build_images() {
    echo -e "${YELLOW}Building all Docker images...${NC}"
    ./scripts/build_microservices.sh --minikube
}

function deploy_services() {
    echo -e "${YELLOW}Deploying all services...${NC}"
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/model-service-deployment.yaml
    kubectl apply -f k8s/model-service-service.yaml
    kubectl apply -f k8s/model-service-hpa.yaml
    kubectl apply -f k8s/decision-service-deployment.yaml
    kubectl apply -f k8s/decision-service-service.yaml
    kubectl apply -f k8s/api-deployment.yaml
    kubectl apply -f k8s/api-service.yaml
    echo -e "${GREEN}✓ Deployment submitted${NC}"
    echo -e "${YELLOW}Waiting for pods to be ready...${NC}"
    kubectl wait --for=condition=ready pod -l app=model-service -n pokewatch --timeout=180s || true
    kubectl wait --for=condition=ready pod -l app=decision-service -n pokewatch --timeout=60s || true
    kubectl wait --for=condition=ready pod -l app=api-gateway -n pokewatch --timeout=60s || true
}

function check_status() {
    echo -e "${YELLOW}Checking deployment status...${NC}"
    echo ""
    echo -e "${BLUE}=== Pods ===${NC}"
    kubectl get pods -n pokewatch
    echo ""
    echo -e "${BLUE}=== Services ===${NC}"
    kubectl get svc -n pokewatch
    echo ""
    echo -e "${BLUE}=== HPA ===${NC}"
    kubectl get hpa -n pokewatch
}

function view_api_logs() {
    echo -e "${YELLOW}Viewing API Gateway logs (Ctrl+C to exit)...${NC}"
    kubectl logs -n pokewatch -l app=api-gateway --tail=50 -f
}

function view_model_logs() {
    echo -e "${YELLOW}Viewing Model Service logs (Ctrl+C to exit)...${NC}"
    kubectl logs -n pokewatch -l app=model-service --tail=50 -f
}

function view_decision_logs() {
    echo -e "${YELLOW}Viewing Decision Service logs (Ctrl+C to exit)...${NC}"
    kubectl logs -n pokewatch -l app=decision-service --tail=50 -f
}

function view_airflow_logs() {
    echo -e "${YELLOW}Viewing Airflow Scheduler logs (Ctrl+C to exit)...${NC}"
    kubectl logs -n airflow -l component=scheduler --tail=50 -f
}

function portforward_api() {
    echo -e "${YELLOW}Port-forwarding API Gateway to localhost:8000${NC}"
    echo -e "${GREEN}API will be available at: http://localhost:8000${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    kubectl port-forward -n pokewatch svc/api-gateway 8000:8000
}

function portforward_airflow() {
    echo -e "${YELLOW}Port-forwarding Airflow UI to localhost:8080${NC}"
    echo -e "${GREEN}Airflow UI will be available at: http://localhost:8080${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    kubectl port-forward -n airflow svc/airflow-webserver 8080:8080
}

function test_health() {
    echo -e "${YELLOW}Testing API health...${NC}"
    kubectl run test-health --rm -it --image=curlimages/curl --restart=Never -n pokewatch -- \
        curl -s http://api-gateway.pokewatch.svc.cluster.local:8000/health | jq .
}

function test_prediction() {
    echo -e "${YELLOW}Testing fair price prediction...${NC}"
    kubectl run test-predict --rm -it --image=curlimages/curl --restart=Never -n pokewatch -- \
        curl -s -X POST http://api-gateway.pokewatch.svc.cluster.local:8000/fair_price \
        -H "Content-Type: application/json" \
        -d '{"card_id":"charizard_ex_199","date":"2025-12-01"}' | jq .
}

function scale_model() {
    echo -n "Enter number of replicas (2-5): "
    read replicas
    echo -e "${YELLOW}Scaling Model Service to $replicas replicas...${NC}"
    kubectl scale deployment/model-service --replicas=$replicas -n pokewatch
    echo -e "${GREEN}✓ Scaling initiated${NC}"
    sleep 2
    kubectl get pods -n pokewatch -l app=model-service
}

function trigger_dag() {
    echo -e "${YELLOW}Triggering Airflow DAG 'pokewatch_ml_pipeline'...${NC}"
    WEBSERVER_POD=$(kubectl get pods -n airflow -l component=webserver -o jsonpath='{.items[0].metadata.name}')
    kubectl exec -n airflow $WEBSERVER_POD -- airflow dags trigger pokewatch_ml_pipeline
    echo -e "${GREEN}✓ DAG triggered${NC}"
    echo -e "${YELLOW}View progress in Airflow UI: http://localhost:8080${NC}"
}

function view_hpa() {
    echo -e "${YELLOW}Viewing HPA status...${NC}"
    kubectl get hpa -n pokewatch
    echo ""
    echo -e "${YELLOW}Detailed HPA info:${NC}"
    kubectl describe hpa model-service-hpa -n pokewatch
}

function copy_dag() {
    echo -e "${YELLOW}Copying DAG to Airflow...${NC}"
    SCHEDULER_POD=$(kubectl get pods -n airflow -l component=scheduler -o jsonpath='{.items[0].metadata.name}')
    kubectl cp airflow/dags/ml_pipeline.py airflow/$SCHEDULER_POD:/opt/airflow/dags/
    echo -e "${GREEN}✓ DAG copied${NC}"
    echo -e "${YELLOW}Verifying...${NC}"
    kubectl exec -n airflow $SCHEDULER_POD -- ls -la /opt/airflow/dags/
}

function restart_services() {
    echo -e "${YELLOW}Restarting all services...${NC}"
    kubectl rollout restart deployment/api-gateway -n pokewatch
    kubectl rollout restart deployment/model-service -n pokewatch
    kubectl rollout restart deployment/decision-service -n pokewatch
    echo -e "${GREEN}✓ Restart initiated${NC}"
    echo -e "${YELLOW}Waiting for rollout to complete...${NC}"
    kubectl rollout status deployment/api-gateway -n pokewatch
    kubectl rollout status deployment/model-service -n pokewatch
    kubectl rollout status deployment/decision-service -n pokewatch
}

function delete_all() {
    echo -e "${RED}WARNING: This will delete all PokeWatch resources!${NC}"
    echo -n "Are you sure? (yes/no): "
    read confirm
    if [ "$confirm" == "yes" ]; then
        echo -e "${YELLOW}Deleting all resources...${NC}"
        kubectl delete namespace pokewatch
        kubectl delete namespace airflow
        echo -e "${GREEN}✓ Resources deleted${NC}"
    else
        echo -e "${YELLOW}Cancelled${NC}"
    fi
}

# Main loop
while true; do
    show_menu
    read choice
    case $choice in
        1) build_images ;;
        2) deploy_services ;;
        3) check_status ;;
        4) view_api_logs ;;
        5) view_model_logs ;;
        6) view_decision_logs ;;
        7) view_airflow_logs ;;
        8) portforward_api ;;
        9) portforward_airflow ;;
        10) test_health ;;
        11) test_prediction ;;
        12) scale_model ;;
        13) trigger_dag ;;
        14) view_hpa ;;
        15) copy_dag ;;
        16) restart_services ;;
        17) delete_all ;;
        0) echo -e "${GREEN}Goodbye!${NC}"; exit 0 ;;
        *) echo -e "${RED}Invalid option${NC}" ;;
    esac
    echo ""
    echo -n "Press Enter to continue..."
    read
done
