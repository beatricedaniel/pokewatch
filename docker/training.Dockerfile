# Training Dockerfile for PokeWatch baseline model training
#
# This Dockerfile creates an environment for running model training
# that connects to the MLflow tracking server for experiment tracking.
#
# Build: docker build -f docker/training.Dockerfile -t pokewatch-training .
# Run: docker-compose run --rm training python -m pokewatch.models.train_baseline

FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml .
COPY README.md .

# Install Python dependencies
RUN python -m uv pip install --system --no-cache -e . && \
    python -m uv pip install --system --no-cache boto3

# Copy source code
COPY src/ src/
COPY config/ config/

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden)
CMD ["python", "-m", "pokewatch.models.train_baseline"]
