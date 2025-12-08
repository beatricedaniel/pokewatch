FROM python:3.13-slim

# Install system dependencies (including build tools for psutil and other C extensions)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create airflow user and group (UID/GID 50000 to match Airflow Helm chart)
RUN groupadd -r -g 50000 airflow && \
    useradd -r -u 50000 -g airflow -m -d /home/airflow -s /bin/bash airflow

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install all Python dependencies for ML pipeline
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    pyarrow \
    pyyaml \
    requests \
    httpx \
    scikit-learn \
    mlflow \
    dvc \
    dvc-s3 \
    python-dotenv \
    pydantic \
    pydantic-settings \
    apache-airflow

# Install project in editable mode
RUN pip install -e .

# Configure git for DVC (required for DVC operations) for airflow user
RUN su - airflow -c "git config --global user.email 'airflow@pokewatch.local'" && \
    su - airflow -c "git config --global user.name 'Airflow Worker'"

# Change ownership of /app to airflow user
RUN chown -R airflow:airflow /app

# Switch to airflow user
USER airflow

# Default command (will be overridden by Airflow)
CMD ["python", "--version"]
