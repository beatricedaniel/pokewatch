# PokeWatch Unified Dockerfile
# Single image with multiple entry points for API and Pipeline tasks
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src
COPY config ./config

# Create necessary directories
RUN mkdir -p /app/data/raw /app/data/processed /app/data/interim /app/logs /app/models

# Set Python path
ENV PYTHONPATH=/app/src

# Expose port for API
EXPOSE 8000

# Default: run API
# Override with different commands for pipeline tasks:
#   - python -m pokewatch.data.collectors.daily_price_collector
#   - python -m pokewatch.data.preprocessing.make_features
#   - python -m pokewatch.models.train_baseline
CMD ["uvicorn", "pokewatch.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
