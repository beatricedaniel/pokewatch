# UV Setup & Verification Guide

Complete guide for setting up and verifying Week 2 implementations using `uv` (fast Python package manager).

---

## Prerequisites

### Check UV Installation

```bash
# Check if uv is installed
uv --version

# Or (if aliased)
python -m uv --version

# Expected: uv 0.9.11 or higher
```

### Install UV (if needed)

```bash
# Install uv
pip install uv

# Or via curl
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Quick Setup with UV (3 minutes)

```bash
cd /Users/beatrice/Documents/data_scientest/projet/pokewatch

# 1. Create virtual environment with uv
python -m uv venv

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install all dependencies with uv
python -m uv pip install -e ".[dev]"

# 4. Verify installation
bash scripts/verify_with_uv.sh
```

That's it! ✅

---

## Detailed UV Commands

### Install Dependencies

```bash
# Install all project dependencies
python -m uv pip install -e .

# Install with dev dependencies (ruff, black, mypy)
python -m uv pip install -e ".[dev]"

# Install specific packages
python -m uv pip install pytest pytest-cov
python -m uv pip install "zenml[server]>=0.55.0"
python -m uv pip install "bentoml>=1.2.0"
```

### Update Dependencies

```bash
# Update all packages
python -m uv pip install --upgrade -e ".[dev]"

# Update specific package
python -m uv pip install --upgrade zenml
```

### List Dependencies

```bash
# List installed packages
python -m uv pip list

# Show dependency tree
python -m uv pip show zenml
```

---

## Week 2 Verification with UV

### Option 1: Automated (Recommended)

```bash
cd /Users/beatrice/Documents/data_scientest/projet/pokewatch
source .venv/bin/activate

# Run UV-compatible verification
bash scripts/verify_with_uv.sh
```

**Expected output:**
```
==========================================
Week 2 Verification (UV Compatible)
==========================================

✓ UV found: uv 0.9.11
✓ Virtual environment activated

[Step 1/6] Installing dependencies with UV
✓ Dependencies installed

[Step 2/6] Verifying file structure
✓ All files present

[Step 3/6] Running security tests
✓ 55+ tests passed

[Step 4/6] Running performance tests
✓ Performance tests passed

[Step 5/6] Verifying ZenML
✓ ZenML installed

[Step 6/6] Verifying BentoML
✓ BentoML installed

✅ Week 2 verification complete with UV!
```

### Option 2: Manual Steps

```bash
# 1. Ensure dependencies installed
python -m uv pip install -e ".[dev]"

# 2. File structure check
bash scripts/verify_week2.sh

# 3. Security tests
pytest tests/integration/test_auth.py tests/integration/test_rate_limiting.py -v

# 4. Performance tests
python scripts/test_performance.py

# 5. ZenML setup
bash scripts/setup_zenml.sh

# 6. Run pipeline
python -m pipelines.ml_pipeline
```

---

## UV-Specific Features

### Faster Installation

UV is 10-100x faster than pip:

```bash
# Traditional pip (slow)
pip install -e ".[dev]"
# Takes: 30-60 seconds

# With UV (fast)
python -m uv pip install -e ".[dev]"
# Takes: 3-5 seconds
```

### Better Dependency Resolution

UV has superior dependency resolution:

```bash
# UV automatically resolves conflicts
python -m uv pip install zenml bentoml mlflow

# Shows clear resolution steps
# No silent downgrades
```

### Virtual Environment Management

```bash
# Create venv with UV (faster)
python -m uv venv

# Create with specific Python version
python -m uv venv --python 3.13

# Remove and recreate
rm -rf .venv
python -m uv venv
python -m uv pip install -e ".[dev]"
```

---

## Troubleshooting with UV

### Issue: "uv not found"

```bash
# Install uv
pip install uv

# Or use module form
python -m pip install uv

# Verify
python -m uv --version
```

### Issue: Dependencies not installing

```bash
# Clear cache and reinstall
python -m uv cache clean

# Reinstall from scratch
python -m uv pip install --reinstall -e ".[dev]"
```

### Issue: Import errors after installation

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Verify package is installed
python -m uv pip list | grep zenml
python -m uv pip list | grep bentoml

# Try importing
python -c "import zenml; import bentoml; print('✓ All imports work')"
```

### Issue: Conflicting dependencies

```bash
# UV shows clear dependency conflicts
python -m uv pip install -e ".[dev]" --verbose

# Force reinstall specific version
python -m uv pip install --force-reinstall "zenml==0.55.0"
```

---

## UV vs Traditional Pip

### Speed Comparison

| Task | pip | uv | Speedup |
|------|-----|-----|---------|
| Install all deps | 45s | 4s | 11x faster |
| Install single package | 8s | 1s | 8x faster |
| Dependency resolution | 20s | 2s | 10x faster |
| Virtual env creation | 5s | 0.5s | 10x faster |

### Commands Comparison

| Task | pip | uv |
|------|-----|-----|
| Install | `pip install package` | `uv pip install package` |
| Install editable | `pip install -e .` | `uv pip install -e .` |
| List packages | `pip list` | `uv pip list` |
| Show package | `pip show package` | `uv pip show package` |
| Upgrade | `pip install --upgrade` | `uv pip install --upgrade` |
| Create venv | `python -m venv .venv` | `uv venv` |

---

## Complete Setup from Scratch with UV

```bash
# 1. Navigate to project
cd /Users/beatrice/Documents/data_scientest/projet/pokewatch

# 2. Remove old venv (if exists)
rm -rf .venv

# 3. Create new venv with UV
python -m uv venv

# 4. Activate venv
source .venv/bin/activate

# 5. Install all dependencies with UV (fast!)
python -m uv pip install -e ".[dev]"

# 6. Verify installation
python -c "import pokewatch; import zenml; import bentoml; print('✓ All packages installed')"

# 7. Run verification
bash scripts/verify_with_uv.sh

# 8. Setup ZenML
bash scripts/setup_zenml.sh

# 9. Run tests
pytest tests/integration/ -v

# 10. Run performance tests
python scripts/test_performance.py

# Done! ✅
```

---

## UV in CI/CD

Week 2 GitHub Actions workflows are UV-compatible:

```yaml
# .github/workflows/test.yml

- name: Install dependencies with UV
  run: |
    pip install uv
    uv pip install -e ".[dev]"

- name: Run tests
  run: pytest tests/ -v
```

**Benefits:**
- ✅ Faster CI/CD runs (30s → 3s for deps)
- ✅ More reliable dependency resolution
- ✅ Better caching

---

## UV Best Practices

### 1. Always Use Virtual Environments

```bash
# Create venv
python -m uv venv

# Activate
source .venv/bin/activate

# Install
python -m uv pip install -e ".[dev]"
```

### 2. Keep UV Updated

```bash
# Update UV itself
pip install --upgrade uv

# Verify
python -m uv --version
```

### 3. Use pyproject.toml for Dependencies

UV reads from `pyproject.toml` (already configured):

```toml
[project]
dependencies = [
    "fastapi",
    "zenml[server]>=0.55.0",
    "bentoml>=1.2.0",
]

[project.optional-dependencies]
dev = [
    "ruff",
    "black",
    "mypy",
]
```

### 4. Clear Cache When Needed

```bash
# Clear UV cache
python -m uv cache clean

# Check cache size
python -m uv cache dir
```

---

## Verification Checklist with UV

- [ ] UV installed and working (`python -m uv --version`)
- [ ] Virtual environment created (`python -m uv venv`)
- [ ] Virtual environment activated (`source .venv/bin/activate`)
- [ ] Dependencies installed (`python -m uv pip install -e ".[dev]"`)
- [ ] All imports work (`python -c "import zenml; import bentoml"`)
- [ ] File verification passes (`bash scripts/verify_week2.sh`)
- [ ] Security tests pass (`pytest tests/integration/test_auth.py -v`)
- [ ] Performance tests pass (`python scripts/test_performance.py`)
- [ ] ZenML setup complete (`bash scripts/setup_zenml.sh`)
- [ ] Pipeline runs (`python -m pipelines.ml_pipeline`)

---

## Common UV Commands Reference

```bash
# Installation
python -m uv pip install package
python -m uv pip install -e .              # Editable install
python -m uv pip install -e ".[dev]"       # With dev deps

# Upgrade
python -m uv pip install --upgrade package
python -m uv pip install --upgrade -e .

# Uninstall
python -m uv pip uninstall package

# List & Show
python -m uv pip list
python -m uv pip show package
python -m uv pip freeze > requirements.txt

# Virtual Environment
python -m uv venv                          # Create venv
python -m uv venv --python 3.13           # Specific Python
python -m uv venv .venv --seed            # With pip/setuptools

# Cache
python -m uv cache clean
python -m uv cache dir

# Other
python -m uv pip check                     # Check dependencies
python -m uv pip compile pyproject.toml    # Generate requirements
```

---

## Performance Tips

### 1. Use UV for All Package Operations

```bash
# Instead of:
pip install package

# Use:
python -m uv pip install package
```

### 2. Batch Install Dependencies

```bash
# Install all at once (faster)
python -m uv pip install -e ".[dev]"

# Instead of one-by-one (slower)
pip install zenml
pip install bentoml
pip install pytest
```

### 3. Leverage UV Cache

UV caches packages automatically:

```bash
# First install: downloads packages
python -m uv pip install zenml  # 5s

# Second install (different venv): uses cache
python -m uv pip install zenml  # 0.5s
```

---

## Resources

- **UV Documentation**: https://github.com/astral-sh/uv
- **UV vs pip**: https://astral.sh/blog/uv
- **PokeWatch Setup**: [README.md](README.md)
- **Week 2 Verification**: [VERIFICATION_GUIDE.md](VERIFICATION_GUIDE.md)

---

## Summary

**Week 2 is 100% UV-compatible:**

✅ All dependencies in `pyproject.toml`
✅ Virtual environment with `python -m uv venv`
✅ Fast installation with `python -m uv pip install`
✅ All scripts work with UV
✅ Dedicated verification script: `verify_with_uv.sh`

**To verify with UV:**
```bash
cd /Users/beatrice/Documents/data_scientest/projet/pokewatch
source .venv/bin/activate
bash scripts/verify_with_uv.sh
```

**Benefits of using UV:**
- ⚡ 10-100x faster than pip
- 🎯 Better dependency resolution
- 💾 Automatic caching
- 🔒 More reliable builds

---

**UV is fully supported and recommended for PokeWatch!** 🚀
