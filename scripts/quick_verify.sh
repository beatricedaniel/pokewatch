#!/bin/bash
#
# Quick Verification Script for Week 2 Features
# Runs the most important checks to verify all implementations
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

echo -e "${BLUE}=========================================="
echo "Week 2 Quick Verification"
echo -e "==========================================${NC}"
echo ""

# Function to run a test
run_test() {
    local test_name=$1
    local test_command=$2

    ((TOTAL_TESTS++))
    echo -n "Testing: $test_name ... "

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED_TESTS++))
    fi
}

# ==========================================
# 1. File Structure Check
# ==========================================
echo -e "${BLUE}[1/5] File Structure${NC}"
echo "--------------------"

run_test "CI/CD workflows exist" "[ -d .github/workflows ] && [ $(ls .github/workflows/*.yml | wc -l) -ge 5 ]"
run_test "Security modules exist" "[ -f src/pokewatch/api/auth.py ] && [ -f src/pokewatch/api/rate_limiter.py ]"
run_test "Performance scripts exist" "[ -f scripts/test_performance.py ]"
run_test "ZenML scripts exist" "[ -f scripts/setup_zenml.sh ] && [ -f scripts/schedule_pipeline.sh ]"
run_test "Pipeline files exist" "[ -f pipelines/steps.py ] && [ -f pipelines/ml_pipeline.py ]"
run_test "Documentation exists" "[ -f docs/ci_cd_guide.md ] && [ -f docs/security_guide.md ] && [ -f docs/zenml_guide.md ]"

echo ""

# ==========================================
# 2. Code Quality Check
# ==========================================
echo -e "${BLUE}[2/5] Code Quality${NC}"
echo "-------------------"

# Check if pre-commit is available
if command -v pre-commit &> /dev/null; then
    run_test "Pre-commit hooks validate" "pre-commit run --all-files"
else
    echo -e "${YELLOW}⚠ Pre-commit not installed (optional)${NC}"
fi

# Check Python syntax
run_test "Python syntax valid" "python -m py_compile src/pokewatch/api/auth.py src/pokewatch/api/rate_limiter.py"
run_test "Pipeline syntax valid" "python -m py_compile pipelines/steps.py pipelines/ml_pipeline.py"

echo ""

# ==========================================
# 3. Security Implementation Check
# ==========================================
echo -e "${BLUE}[3/5] Security Features${NC}"
echo "-----------------------"

# Check API key management
run_test "API key generator works" "python scripts/manage_api_keys.py generate"
run_test "Auth module imports" "python -c 'from pokewatch.api.auth import APIKeyAuth'"
run_test "Rate limiter imports" "python -c 'from pokewatch.api.rate_limiter import RateLimiter'"
run_test "Middleware imports" "python -c 'from pokewatch.api.middleware import setup_middleware'"

# Check security tests exist and are valid
run_test "Auth tests valid" "python -m pytest tests/integration/test_auth.py --collect-only"
run_test "Rate limit tests valid" "python -m pytest tests/integration/test_rate_limiting.py --collect-only"

echo ""

# ==========================================
# 4. Performance Implementation Check
# ==========================================
echo -e "${BLUE}[4/5] Performance Features${NC}"
echo "--------------------------"

# Check cache implementation
run_test "Cache methods exist" "grep -q 'get_cache_stats' src/pokewatch/models/baseline.py"
run_test "Cache implementation found" "grep -q '_prediction_cache' src/pokewatch/models/baseline.py"
run_test "Performance test script valid" "python -m py_compile scripts/test_performance.py"
run_test "Redis in docker-compose" "grep -q 'redis:' docker-compose.yml"

echo ""

# ==========================================
# 5. ZenML Pipeline Check
# ==========================================
echo -e "${BLUE}[5/5] ZenML Pipeline${NC}"
echo "--------------------"

# Check ZenML decorators
run_test "Pipeline steps have @step" "grep -q '@step' pipelines/steps.py"
run_test "Pipeline has @pipeline" "grep -q '@pipeline' pipelines/ml_pipeline.py"
run_test "Pipeline imports valid" "python -c 'from pipelines.steps import collect_data_step, train_model_step'"
run_test "Setup script executable" "[ -x scripts/setup_zenml.sh ]"
run_test "Schedule script executable" "[ -x scripts/schedule_pipeline.sh ]"

echo ""

# ==========================================
# Summary
# ==========================================
echo -e "${BLUE}=========================================="
echo "Summary"
echo -e "==========================================${NC}"

PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))

echo "Tests Run: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo "Pass Rate: $PASS_RATE%"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Next steps to verify features work:"
    echo "  1. Run security tests: pytest tests/integration/test_auth.py -v"
    echo "  2. Run performance test: python scripts/test_performance.py"
    echo "  3. Setup ZenML: bash scripts/setup_zenml.sh"
    echo "  4. Run pipeline: python -m pipelines.ml_pipeline"
    echo ""
    echo "For detailed verification, see: VERIFICATION_GUIDE.md"
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    echo ""
    echo "Please review the failures above."
    echo "For troubleshooting, see: VERIFICATION_GUIDE.md"
    exit 1
fi
