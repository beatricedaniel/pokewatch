#!/bin/bash
# PokeWatch Docker Setup Script
# Builds Docker images and runs docker-compose services

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo -e "${GREEN}=== PokeWatch Docker Setup ===${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker daemon is not running.${NC}"
    echo -e "${YELLOW}Please start Docker Desktop or the Docker daemon.${NC}"
    echo ""
    echo "On macOS:"
    echo "  1. Open Docker Desktop application"
    echo "  2. Wait for it to fully start (whale icon in menu bar)"
    echo "  3. Run this script again"
    echo ""
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed. Please install docker-compose first.${NC}"
    exit 1
fi

# Use 'docker compose' if available, otherwise 'docker-compose'
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"
touch "$PROJECT_ROOT/logs/logs.txt"

# Function to build images
build_images() {
    echo -e "${YELLOW}Building Docker images...${NC}"
    cd "$PROJECT_ROOT"
    
    # Build API image
    echo -e "${YELLOW}Building API image...${NC}"
    docker build -f docker/api.Dockerfile -t pokewatch-api:latest .
    
    echo -e "${GREEN}✓ Images built successfully${NC}"
    echo ""
}

# Function to run API
run_api() {
    echo -e "${YELLOW}Starting API service...${NC}"
    cd "$PROJECT_ROOT"
    
    $DOCKER_COMPOSE up -d api
    
    echo -e "${GREEN}✓ API service started${NC}"
    echo -e "${YELLOW}API available at: http://localhost:8000${NC}"
    echo -e "${YELLOW}API docs at: http://localhost:8000/docs${NC}"
    echo ""
    echo "To view logs: docker-compose logs -f api"
    echo "To stop: docker-compose down"
}

# Function to run tests
run_tests() {
    echo -e "${YELLOW}Running tests...${NC}"
    cd "$PROJECT_ROOT"
    
    # Start API first (required for integration tests)
    echo -e "${YELLOW}Starting API service for tests...${NC}"
    $DOCKER_COMPOSE up -d api
    
    # Wait for API to be ready
    echo -e "${YELLOW}Waiting for API to be ready...${NC}"
    timeout=60
    counter=0
    while ! curl -f http://localhost:8000/health &> /dev/null; do
        if [ $counter -ge $timeout ]; then
            echo -e "${RED}Error: API did not become ready in time${NC}"
            exit 1
        fi
        sleep 2
        counter=$((counter + 2))
        echo -n "."
    done
    echo ""
    echo -e "${GREEN}✓ API is ready${NC}"
    
    # Run tests
    echo -e "${YELLOW}Running test suite...${NC}"
    $DOCKER_COMPOSE --profile test run --rm tests 2>&1 | tee "$PROJECT_ROOT/logs/logs.txt"
    
    test_exit_code=${PIPESTATUS[0]}
    
    if [ $test_exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed${NC}"
    else
        echo -e "${RED}✗ Some tests failed (exit code: $test_exit_code)${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}Test logs saved to: logs/logs.txt${NC}"
    
    return $test_exit_code
}

# Function to stop services
stop_services() {
    echo -e "${YELLOW}Stopping services...${NC}"
    cd "$PROJECT_ROOT"
    $DOCKER_COMPOSE down
    echo -e "${GREEN}✓ Services stopped${NC}"
}

# Function to show logs
show_logs() {
    cd "$PROJECT_ROOT"
    $DOCKER_COMPOSE logs -f api
}

# Function to clean up
cleanup() {
    echo -e "${YELLOW}Cleaning up Docker resources...${NC}"
    cd "$PROJECT_ROOT"
    $DOCKER_COMPOSE down -v
    docker rmi pokewatch-api:latest 2>/dev/null || true
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

# Main menu
show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build       Build Docker images"
    echo "  up          Build and start API service"
    echo "  down        Stop all services"
    echo "  test        Run all tests"
    echo "  logs        Show API logs"
    echo "  cleanup     Remove all containers and images"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build    # Build images only"
    echo "  $0 up       # Start API"
    echo "  $0 test     # Run tests"
    echo ""
}

# Parse command
case "${1:-help}" in
    build)
        build_images
        ;;
    up)
        build_images
        run_api
        ;;
    down)
        stop_services
        ;;
    test)
        build_images
        run_tests
        ;;
    logs)
        show_logs
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac

