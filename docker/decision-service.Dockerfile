FROM python:3.13-slim

# Install system dependencies (including build tools for C extensions)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    pydantic \
    pydantic-settings

# Install project in editable mode (for pokewatch.core.decision_rules)
RUN pip install -e .

# Expose FastAPI default port
EXPOSE 8001

# Run FastAPI service
CMD ["uvicorn", "services.decision_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
