# PokeWatch API Dockerfile
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src
COPY config ./config

# Create data/processed directory
RUN mkdir -p /app/data/processed

# Copy processed data (if directory exists, it will be copied; if not, this will fail)
# Note: The processed data should exist for the API to work properly
COPY data/processed/ ./data/processed/

# Set Python path
ENV PYTHONPATH=/app/src

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "pokewatch.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

