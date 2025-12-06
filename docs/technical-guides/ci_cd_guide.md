# CI/CD Guide - PokeWatch

## Overview

This guide covers the Continuous Integration and Continuous Deployment (CI/CD) setup for PokeWatch using GitHub Actions.

## Architecture

```
.github/
├── workflows/
│   ├── test.yml          # Automated testing
│   ├── quality.yml       # Code quality checks
│   ├── docker-build.yml  # Docker image builds
│   ├── bento-build.yml   # BentoML builds
│   └── release.yml       # Release automation
└── scripts/
    └── version.sh        # Version management
```

## Workflows

### 1. Test Workflow (`test.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**Steps:**
1. Checkout code
2. Set up Python 3.13 with caching
3. Install uv and dependencies
4. Run unit tests with coverage
5. Run integration tests with coverage
6. Upload coverage to Codecov
7. Verify coverage threshold (70%)
8. Archive test results

**Configuration:**
```yaml
python-version: ["3.13"]
coverage-threshold: 70%
```

**Usage:**
```bash
# Runs automatically on push/PR
git push origin main

# View results in GitHub Actions tab
```

### 2. Quality Workflow (`quality.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**Steps:**
1. Checkout code
2. Set up Python 3.13
3. Install dependencies
4. Run ruff linting
5. Run black formatting check
6. Run mypy type checking
7. Check import order
8. Security check with bandit

**Usage:**
```bash
# Fix linting issues locally
cd pokewatch
ruff check src/ tests/ pipelines/ --fix

# Format code
black src/ tests/ pipelines/

# Type check
mypy src/pokewatch --ignore-missing-imports
```

### 3. Docker Build Workflow (`docker-build.yml`)

**Triggers:**
- Push to `main` branch
- Version tags (`v*.*.*`)

**Steps:**
1. Build FastAPI Docker image
2. Build BentoML Docker image
3. Tag with git SHA and version
4. Push to GitHub Container Registry (ghcr.io)
5. Multi-platform builds (amd64, arm64)

**Configuration:**
```yaml
registry: ghcr.io
platforms:
  - linux/amd64
  - linux/arm64
```

**Usage:**
```bash
# Trigger build with version tag
git tag v1.2.0
git push origin v1.2.0

# Images pushed to:
# ghcr.io/your-username/pokewatch-api:v1.2.0
# ghcr.io/your-username/pokewatch-bento:v1.2.0
```

### 4. BentoML Build Workflow (`bento-build.yml`)

**Triggers:**
- Version tags (`v*.*.*`)

**Steps:**
1. Build BentoML service
2. Run validation tests
3. Push to container registry
4. Store Bento metadata

**Usage:**
```bash
# Trigger BentoML build
git tag v1.2.0
git push origin v1.2.0

# Bento tag: pokewatch_service:v1.2.0
```

### 5. Release Workflow (`release.yml`)

**Triggers:**
- Semantic version tags (`v*.*.*`)

**Steps:**
1. Build all Docker images
2. Run full test suite
3. Create GitHub release
4. Generate changelog
5. Deploy to staging
6. Send notifications

**Usage:**
```bash
# Create release
git tag v1.2.0
git push origin v1.2.0

# Creates GitHub release with:
# - Changelog
# - Docker images
# - Release notes
```

## Pre-commit Hooks

Install pre-commit hooks to run checks locally before committing:

```bash
cd pokewatch

# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

**Hooks configured:**
- Trailing whitespace removal
- End-of-file fixer
- YAML/JSON/TOML validation
- Large file check (max 1MB)
- Merge conflict detection
- Private key detection
- Black formatting
- Ruff linting
- Mypy type checking
- Pytest unit tests (pre-push)

## Branch Protection Rules

Recommended branch protection settings for `main` branch:

### Required Status Checks
- ✅ `test` workflow must pass
- ✅ `quality` workflow must pass
- ✅ Coverage threshold ≥ 70%

### Required Reviews
- Require at least 1 approval
- Dismiss stale reviews on new commits
- Require review from code owners

### Additional Settings
- Require linear history (no merge commits)
- Require branches to be up to date
- Require conversation resolution before merging
- Do not allow force pushes
- Do not allow deletions

### Setup in GitHub:
1. Go to `Settings` → `Branches`
2. Add rule for `main` branch
3. Enable all protection settings above

## Secrets Configuration

Required secrets in GitHub repository settings:

```bash
# API Keys
POKEMON_PRICE_API_KEY=your_api_key_here

# Container Registry
GHCR_TOKEN=your_github_token_here

# Optional: Codecov
CODECOV_TOKEN=your_codecov_token_here

# Optional: Deployment
DAGSHUB_TOKEN=your_dagshub_token_here
MLFLOW_TRACKING_URI=https://dagshub.com/...
```

**Setup:**
1. Go to `Settings` → `Secrets and variables` → `Actions`
2. Add each secret with `New repository secret`

## Environment Variables

Workflow environment variables:

```yaml
env:
  PYTHON_VERSION: "3.13"
  COVERAGE_THRESHOLD: 70
  DOCKER_REGISTRY: ghcr.io
  IMAGE_NAME: pokewatch
```

## Caching Strategy

### Python Dependencies
```yaml
- uses: actions/setup-python@v5
  with:
    cache: 'pip'
```

### Docker Layers
```yaml
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

## Artifacts

Workflows produce the following artifacts:

### Test Workflow
- `test-results`: Coverage reports and test results
- Retention: 30 days

### Docker Build Workflow
- Docker images pushed to ghcr.io
- Tags: `latest`, `v1.2.3`, `sha-abc123`

### BentoML Build Workflow
- `bento-metadata`: Bento service metadata
- Retention: 90 days

## Notifications

Configure notifications for workflow failures:

### Slack Integration (Optional)
```yaml
- name: Notify Slack
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK }}
    payload: |
      {
        "text": "CI/CD Failed: ${{ github.workflow }}"
      }
```

### Email Notifications
GitHub automatically sends emails for workflow failures to repository admins.

## Debugging Failed Workflows

### View Logs
1. Go to `Actions` tab in GitHub
2. Click on failed workflow run
3. Expand failed step to view logs

### Re-run Failed Jobs
1. Click `Re-run failed jobs` button
2. Or re-run all jobs with `Re-run all jobs`

### Debug with SSH (Advanced)
```yaml
- name: Setup tmate session
  if: failure()
  uses: mxschmitt/action-tmate@v3
```

## Local Testing

Test workflows locally with `act`:

```bash
# Install act
brew install act

# Run test workflow
act -j test

# Run with secrets
act -j test --secret-file .env.secrets
```

## Performance Optimization

### Parallel Jobs
```yaml
jobs:
  test:
    strategy:
      matrix:
        python-version: ["3.13"]
        os: [ubuntu-latest]
      fail-fast: false
```

### Conditional Execution
```yaml
- name: Run integration tests
  if: github.event_name == 'push'
```

### Job Dependencies
```yaml
jobs:
  test:
    runs-on: ubuntu-latest

  deploy:
    needs: test
    runs-on: ubuntu-latest
```

## Monitoring

### Workflow Status Badges

Add to `README.md`:

```markdown
![Tests](https://github.com/your-username/pokewatch/workflows/Tests/badge.svg)
![Quality](https://github.com/your-username/pokewatch/workflows/Code%20Quality/badge.svg)
![Coverage](https://codecov.io/gh/your-username/pokewatch/branch/main/graph/badge.svg)
```

### Metrics to Track
- ✅ Test pass rate (target: 100%)
- ✅ Code coverage (target: ≥70%)
- ✅ Workflow duration (target: <10 minutes)
- ✅ Docker build time (target: <5 minutes)
- ✅ Deployment success rate (target: ≥95%)

## Troubleshooting

### Common Issues

**1. Coverage Below Threshold**
```bash
# Check coverage locally
cd pokewatch
pytest --cov=src/pokewatch --cov-report=html tests/

# Open coverage report
open htmlcov/index.html
```

**2. Docker Build Fails**
```bash
# Test build locally
cd pokewatch
docker build -f docker/api.Dockerfile -t pokewatch-api .

# Check logs
docker logs <container-id>
```

**3. Import Errors in Tests**
```bash
# Ensure package installed in editable mode
cd pokewatch
python -m uv pip install -e .
```

**4. Pre-commit Hook Fails**
```bash
# Skip hook temporarily (not recommended)
git commit --no-verify

# Fix issues and retry
pre-commit run --all-files
git add .
git commit
```

## Best Practices

### 1. Commit Messages
```bash
# Good commit messages
git commit -m "feat: add API key authentication"
git commit -m "fix: resolve rate limiting edge case"
git commit -m "docs: update CI/CD guide"

# Follow conventional commits
# Types: feat, fix, docs, test, refactor, chore
```

### 2. Version Tagging
```bash
# Semantic versioning: MAJOR.MINOR.PATCH
git tag v1.0.0  # Initial release
git tag v1.1.0  # New feature
git tag v1.1.1  # Bug fix
git tag v2.0.0  # Breaking change
```

### 3. Pull Request Workflow
1. Create feature branch: `git checkout -b feature/api-auth`
2. Make changes and commit
3. Push to GitHub: `git push origin feature/api-auth`
4. Create Pull Request
5. Wait for CI/CD checks to pass
6. Request review
7. Merge to main

### 4. Testing Before Push
```bash
# Always test locally first
cd pokewatch
pytest tests/
ruff check src/ tests/
black --check src/ tests/
```

## Migration from Manual to Automated

### Phase 1: CI Setup (Week 2, Day 1-2)
- ✅ Set up test automation
- ✅ Add quality checks
- ✅ Configure pre-commit hooks

### Phase 2: CD Setup (Week 2, Day 2)
- ⏳ Automate Docker builds
- ⏳ Set up release workflow
- ⏳ Configure deployment

### Phase 3: Monitoring (Week 3)
- ⏳ Add status badges
- ⏳ Set up alerts
- ⏳ Track metrics

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pre-commit Hooks](https://pre-commit.com/)
- [Docker Build Action](https://github.com/docker/build-push-action)
- [Codecov Integration](https://about.codecov.io/language/python/)
- [Semantic Versioning](https://semver.org/)

## Support

For issues with CI/CD:
1. Check workflow logs in GitHub Actions
2. Review this guide
3. Check GitHub Actions status: https://www.githubstatus.com/
4. Open issue in repository

---

**Last Updated:** Week 2, Day 1 - Phase 3 Implementation
