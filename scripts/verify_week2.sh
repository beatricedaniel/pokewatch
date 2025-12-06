#!/bin/bash
#
# Verify Week 2 Implementation
# Quick health check for all Week 2 features
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Week 2 Implementation Verification"
echo "=========================================="
echo ""

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Track results
PASSED=0
FAILED=0

check_file() {
    local file=$1
    local description=$2

    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $description (missing: $file)"
        ((FAILED++))
    fi
}

check_executable() {
    local file=$1
    local description=$2

    if [ -x "$file" ]; then
        echo -e "${GREEN}✓${NC} $description"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $description (not executable: $file)"
        ((FAILED++))
    fi
}

check_command() {
    local cmd=$1
    local description=$2

    if command -v $cmd &> /dev/null; then
        echo -e "${GREEN}✓${NC} $description"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} $description (optional: $cmd not installed)"
    fi
}

# ==========================================
# Day 1-2: CI/CD
# ==========================================
echo "Day 1-2: CI/CD Automation"
echo "----------------------------------------"
check_file ".github/workflows/test.yml" "Test workflow"
check_file ".github/workflows/quality.yml" "Quality workflow"
check_file ".github/workflows/docker-build.yml" "Docker build workflow"
check_file ".github/workflows/bento-build.yml" "Bento build workflow"
check_file ".github/workflows/release.yml" "Release workflow"
check_executable ".github/scripts/version.sh" "Version management script"
check_file ".pre-commit-config.yaml" "Pre-commit config"
check_file "docs/ci_cd_guide.md" "CI/CD documentation"
echo ""

# ==========================================
# Day 3: Security
# ==========================================
echo "Day 3: Security"
echo "----------------------------------------"
check_file "src/pokewatch/api/auth.py" "API key authentication"
check_file "src/pokewatch/api/rate_limiter.py" "Rate limiting"
check_file "src/pokewatch/api/middleware.py" "Security middleware"
check_executable "scripts/manage_api_keys.py" "API key management CLI"
check_file "tests/integration/test_auth.py" "Authentication tests"
check_file "tests/integration/test_rate_limiting.py" "Rate limiting tests"
check_file "docs/security_guide.md" "Security documentation"
echo ""

# ==========================================
# Day 4: Performance
# ==========================================
echo "Day 4: Performance"
echo "----------------------------------------"
check_file "src/pokewatch/models/baseline.py" "Baseline model with cache"
check_executable "scripts/test_performance.py" "Performance test script"

# Check if baseline.py has cache methods
if grep -q "get_cache_stats" "src/pokewatch/models/baseline.py"; then
    echo -e "${GREEN}✓${NC} Cache implementation in baseline model"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Cache implementation missing"
    ((FAILED++))
fi

# Check docker-compose for redis
if grep -q "redis:" "docker-compose.yml"; then
    echo -e "${GREEN}✓${NC} Redis service in docker-compose"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Redis service missing"
    ((FAILED++))
fi
echo ""

# ==========================================
# Day 5: ZenML
# ==========================================
echo "Day 5: ZenML Orchestration"
echo "----------------------------------------"
check_executable "scripts/setup_zenml.sh" "ZenML setup script"
check_executable "scripts/schedule_pipeline.sh" "Pipeline scheduling script"
check_file "pipelines/steps.py" "Pipeline steps"
check_file "pipelines/ml_pipeline.py" "Pipeline definition"
check_file "docs/zenml_guide.md" "ZenML documentation"

# Check if steps have @step decorators
if grep -q "@step" "pipelines/steps.py"; then
    echo -e "${GREEN}✓${NC} ZenML @step decorators"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} ZenML @step decorators missing"
    ((FAILED++))
fi

# Check if pipeline has @pipeline decorator
if grep -q "@pipeline" "pipelines/ml_pipeline.py"; then
    echo -e "${GREEN}✓${NC} ZenML @pipeline decorator"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} ZenML @pipeline decorator missing"
    ((FAILED++))
fi
echo ""

# ==========================================
# Documentation
# ==========================================
echo "Documentation"
echo "----------------------------------------"
check_file "WEEK2_COMPLETE.md" "Week 2 summary"
check_file "WEEK2_FINAL_PLAN.md" "Week 2 final plan"

# Check README for ZenML section
if grep -q "Pipeline Orchestration (ZenML)" "README.md"; then
    echo -e "${GREEN}✓${NC} README updated with ZenML"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} README missing ZenML section"
    ((FAILED++))
fi
echo ""

# ==========================================
# Optional Tools Check
# ==========================================
echo "Optional Tools (not required)"
echo "----------------------------------------"
check_command "pytest" "pytest"
check_command "ruff" "ruff"
check_command "black" "black"
check_command "mypy" "mypy"
check_command "pre-commit" "pre-commit"
check_command "zenml" "zenml"
check_command "docker" "docker"
check_command "docker-compose" "docker-compose"
echo ""

# ==========================================
# Summary
# ==========================================
echo "=========================================="
echo "Summary"
echo "=========================================="
TOTAL=$((PASSED + FAILED))
PERCENTAGE=$((PASSED * 100 / TOTAL))

echo "Passed: $PASSED / $TOTAL ($PERCENTAGE%)"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All Week 2 features verified!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Setup ZenML: bash scripts/setup_zenml.sh"
    echo "  2. Run pipeline: python -m pipelines.ml_pipeline"
    echo "  3. Schedule: bash scripts/schedule_pipeline.sh install"
    echo "  4. View docs: cat docs/zenml_guide.md"
    exit 0
else
    echo -e "${RED}✗ Some features missing ($FAILED failures)${NC}"
    echo ""
    echo "Please check the failures above and ensure all files are present."
    exit 1
fi
