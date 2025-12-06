#!/bin/bash
# ZenML Setup Script - Week 2, Day 5
# Sets up ZenML with local stack and DagsHub MLflow integration

set -e  # Exit on error

echo "========================================="
echo "PokeWatch ZenML Setup"
echo "========================================="
echo ""

# Check if we're in the pokewatch directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the pokewatch directory"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Error: Virtual environment not activated"
    echo "   Run: source .venv/bin/activate"
    exit 1
fi

echo "Step 1: Installing ZenML..."
uv pip install "zenml[server]>=0.55.0"
echo "✓ ZenML installed"
echo ""

echo "Step 2: Initializing ZenML..."
zenml init
echo "✓ ZenML initialized"
echo ""

echo "Step 3: Registering local artifact store..."
zenml artifact-store register local_store --flavor=local || echo "  (already exists)"
echo "✓ Local artifact store registered"
echo ""

echo "Step 4: Registering local orchestrator..."
zenml orchestrator register local_orchestrator --flavor=local || echo "  (already exists)"
echo "✓ Local orchestrator registered"
echo ""

echo "Step 5: Registering DagsHub MLflow experiment tracker..."
# Check if environment variables are set
if [ -z "$MLFLOW_TRACKING_URI" ]; then
    echo "⚠ Warning: MLFLOW_TRACKING_URI not set"
    echo "   Using default: https://dagshub.com/beatricedaniel/pokewatch.mlflow"
    export MLFLOW_TRACKING_URI="https://dagshub.com/beatricedaniel/pokewatch.mlflow"
fi

if [ -z "$MLFLOW_TRACKING_USERNAME" ]; then
    echo "⚠ Warning: MLFLOW_TRACKING_USERNAME not set"
    echo "   Using default: beatricedaniel"
    export MLFLOW_TRACKING_USERNAME="beatricedaniel"
fi

if [ -z "$DAGSHUB_TOKEN" ]; then
    echo "⚠ Warning: DAGSHUB_TOKEN not set"
    echo "   Please set DAGSHUB_TOKEN environment variable for MLflow tracking"
else
    # Register MLflow experiment tracker with DagsHub
    zenml experiment-tracker register dagshub_mlflow \
      --flavor=mlflow \
      --tracking_uri="$MLFLOW_TRACKING_URI" \
      --tracking_username="$MLFLOW_TRACKING_USERNAME" \
      --tracking_password="$DAGSHUB_TOKEN" 2>/dev/null || echo "  (already exists)"
    echo "✓ DagsHub MLflow experiment tracker registered"
fi
echo ""

echo "Step 6: Creating ZenML stack..."
# Delete existing stack if it exists
zenml stack delete local_stack -y 2>/dev/null || true

# Create new stack
if [ -z "$DAGSHUB_TOKEN" ]; then
    # Stack without experiment tracker
    zenml stack register local_stack \
      -a local_store \
      -o local_orchestrator
else
    # Stack with experiment tracker
    zenml stack register local_stack \
      -a local_store \
      -o local_orchestrator \
      -e dagshub_mlflow
fi

# Set as active stack
zenml stack set local_stack
echo "✓ Stack 'local_stack' created and activated"
echo ""

echo "Step 7: Verifying setup..."
zenml stack describe
echo ""

echo "========================================="
echo "✓ ZenML Setup Complete!"
echo "========================================="
echo ""
echo "Stack Components:"
echo "  - Artifact Store: local (stores pipeline artifacts locally)"
echo "  - Orchestrator: local (runs pipelines locally)"
if [ ! -z "$DAGSHUB_TOKEN" ]; then
    echo "  - Experiment Tracker: dagshub_mlflow (logs to DagsHub)"
fi
echo ""
echo "Next Steps:"
echo "  1. Run pipeline: python pipelines/ml_pipeline.py"
echo "  2. View runs: zenml pipeline runs list"
echo "  3. (Optional) Start ZenML dashboard: zenml up"
echo ""
echo "For help: zenml --help"
echo ""
