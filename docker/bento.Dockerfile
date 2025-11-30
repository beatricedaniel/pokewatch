# BentoML Dockerfile for PokeWatch
# This Dockerfile creates a production-ready BentoML service

FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency files and application code (needed for installation)
COPY pyproject.toml .
COPY README.md .
COPY src/ src/
COPY config/ config/

# Install Python dependencies (installs pokewatch package)
RUN python -m uv pip install --system --no-cache -e .

# Copy bentofile and data/models
COPY bentofile.yaml .
COPY data/processed/ data/processed/
COPY models/baseline/ models/baseline/

# Set PYTHONPATH to ensure imports work
ENV PYTHONPATH=/app

# Build Bento (creates standalone service)
# Provide dummy API key during build (only needed for module import validation)
# The actual API key will be provided at runtime via docker-compose environment
RUN POKEMON_PRICE_API_KEY=dummy_build_key bentoml build

# Expose BentoML port
EXPOSE 3000

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Run BentoML service
CMD ["bentoml", "serve", "pokewatch_service:latest", "--host", "0.0.0.0", "--port", "3000"]
