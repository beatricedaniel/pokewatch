FROM python:3.13-slim

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files (includes data/processed and config)
COPY . .

# Install dependencies (FastAPI instead of BentoML for simplicity)
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    pandas \
    numpy \
    pyarrow \
    pyyaml \
    mlflow \
    python-dotenv \
    pydantic \
    pydantic-settings

# Install project in editable mode (needs gcc for psutil)
RUN pip install -e .

# Verify data files exist
RUN ls -la /app/data/processed/ && \
    ls -la /app/config/

# Expose port
EXPOSE 3000

# Run FastAPI service with uvicorn
CMD ["uvicorn", "services.model_service.fastapi_service:app", "--host", "0.0.0.0", "--port", "3000"]
