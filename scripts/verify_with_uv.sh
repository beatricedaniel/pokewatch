#!/bin/bash
#
# Week 2 Verification Script - UV Compatible
# Verifies all Week 2 features using uv package manager
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "Week 2 Verification (UV Compatible)"
echo -e "==========================================${NC}"
echo ""

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Check UV is available
if ! command -v uv &> /dev/null && ! python -m uv --version &> /dev/null; then
    echo -e "${YELLOW}Warning: uv not found. Install with: pip install uv${NC}"
    exit 1
fi

echo -e "${GREEN}✓ UV found: $(python -m uv --version)${NC}"
echo ""

# Ensure virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${YELLOW}Virtual environment not activated!${NC}"
    echo "Run: source .venv/bin/activate"
    exit 1
fi

echo -e "${GREEN}✓ Virtual environment activated: $VIRTUAL_ENV${NC}"
echo ""

# Install/verify dependencies
echo -e "${BLUE}[Step 1/6] Installing dependencies with UV${NC}"
echo "--------------------------------------------"
python -m uv pip install -e ".[dev]" > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Verify file structure
echo -e "${BLUE}[Step 2/6] Verifying file structure${NC}"
echo "------------------------------------"
bash scripts/verify_week2.sh
echo ""

# Run security tests
echo -e "${BLUE}[Step 3/6] Running security tests${NC}"
echo "----------------------------------"
pytest tests/integration/test_auth.py tests/integration/test_rate_limiting.py -v --tb=short
echo ""

# Run performance tests
echo -e "${BLUE}[Step 4/6] Running performance tests${NC}"
echo "-------------------------------------"
python scripts/test_performance.py
echo ""

# Verify ZenML installation
echo -e "${BLUE}[Step 5/6] Verifying ZenML${NC}"
echo "----------------------------"
if python -c "import zenml; print(f'ZenML version: {zenml.__version__}')" 2>/dev/null; then
    echo -e "${GREEN}✓ ZenML installed and importable${NC}"
else
    echo -e "${YELLOW}⚠ ZenML not available (optional)${NC}"
fi
echo ""

# Verify BentoML installation
echo -e "${BLUE}[Step 6/6] Verifying BentoML${NC}"
echo "-----------------------------"
if python -c "import bentoml; print(f'BentoML version: {bentoml.__version__}')" 2>/dev/null; then
    echo -e "${GREEN}✓ BentoML installed and importable${NC}"
else
    echo -e "${YELLOW}⚠ BentoML not available${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}=========================================="
echo "Summary"
echo -e "==========================================${NC}"
echo ""
echo -e "${GREEN}✅ Week 2 verification complete with UV!${NC}"
echo ""
echo "Next steps:"
echo "  1. Setup ZenML: bash scripts/setup_zenml.sh"
echo "  2. Run pipeline: python -m pipelines.ml_pipeline"
echo "  3. Test API: uvicorn src.pokewatch.api.main:app --reload"
echo ""
echo "Documentation:"
echo "  - Quick Start: QUICK_START.md"
echo "  - Verification Guide: VERIFICATION_GUIDE.md"
echo "  - Week 2 Report: PHASE3_WEEK2_IMPLEMENTATION_REPORT.md"
