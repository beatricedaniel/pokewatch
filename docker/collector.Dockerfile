# Collector Dockerfile for PokeWatch data collection
#
# This Dockerfile creates an environment for running daily price collection
# from the Pokemon Price Tracker API.
#
# Build: docker build -f docker/collector.Dockerfile -t pokewatch-collector .
# Run: docker-compose run --rm collector

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
RUN python -m uv pip install --system --no-cache -e .

# Copy source code and configuration
COPY src/ src/
COPY config/ config/

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Default command: run daily price collector
CMD ["python", "-m", "pokewatch.data.collectors.daily_price_collector"]
