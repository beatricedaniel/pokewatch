# BentoML Service Guide - PokeWatch

**Version:** 1.0
**Last Updated:** 2025-11-30

This guide covers the BentoML service implementation for PokeWatch, which provides production-grade model serving for card price predictions.

---

## Overview

PokeWatch uses BentoML to serve the baseline model with the following benefits:
- **Production-ready**: Built-in health checks, logging, metrics
- **Auto-scaling**: Ready for Kubernetes HPA
- **Versioning**: Model and service versioning out-of-the-box
- **Performance**: Request batching and caching support
- **Compatibility**: Maintains FastAPI API contract

---

## Architecture

```
┌─────────────────────────────────────────┐
│          BentoML Service                │
│  ┌───────────────────────────────────┐  │
│  │   PokeWatchService                │  │
│  │                                   │  │
│  │   - load_baseline_model()         │  │
│  │   - health()                      │  │
│  │   - predict()                     │  │
│  │   - list_cards()                  │  │
│  │   - batch_predict()               │  │
│  └───────────────────────────────────┘  │
│                  ↓                       │
│  ┌───────────────────────────────────┐  │
│  │   BaselineFairPriceModel          │  │
│  │   (models/baseline/)              │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## Quick Start

### 1. Prerequisites

```bash
# Ensure dependencies installed
cd pokewatch
python -m uv pip install -e .

# Verify BentoML installed
bentoml --version
```

### 2. Build the Bento

```bash
# Using Makefile (recommended)
make bento-build

# OR manually
./scripts/build_bento.sh

# Verify build
bentoml list
```

Expected output:
```
 Tag                                        Size       Creation Time
 pokewatch_service:xxxxx                   123 MiB    2025-11-30 12:34:56
```

### 3. Serve Locally

```bash
# Serve with hot-reload (development)
make bento-serve

# OR manually
bentoml serve pokewatch_service:latest --reload

# Service starts on http://localhost:3000
```

### 4. Test the Service

```bash
# Health check
curl http://localhost:3000/health

# Prediction
curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"card_id": "sv2a_151_charizard_ex___201_165"}'

# List all cards
curl http://localhost:3000/list_cards
```

---

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check service health and model status

**Request:** None

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "num_cards": 10
}
```

**Example:**
```bash
curl http://localhost:3000/health
```

---

### 2. Single Prediction

**Endpoint:** `POST /predict`

**Description:** Predict fair value and trading signal for a card

**Request Body:**
```json
{
  "card_id": "sv2a_151_charizard_ex___201_165",
  "date": "2025-11-30"  // Optional, defaults to latest
}
```

**Response:**
```json
{
  "card_id": "sv2a_151_charizard_ex___201_165",
  "date": "2025-11-30",
  "market_price": 246.34,
  "fair_price": 245.50,
  "deviation_pct": 0.0034,
  "signal": "HOLD"
}
```

**Example:**
```bash
curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "card_id": "sv2a_151_charizard_ex___201_165"
  }'
```

**Python Client:**
```python
import requests

response = requests.post(
    "http://localhost:3000/predict",
    json={"card_id": "sv2a_151_charizard_ex___201_165"}
)

prediction = response.json()
print(f"Signal: {prediction['signal']}")
print(f"Fair Value: ${prediction['fair_price']:.2f}")
```

---

### 3. List Cards

**Endpoint:** `GET /list_cards`

**Description:** Get all tracked cards

**Request:** None

**Response:**
```json
{
  "total": 10,
  "cards": [
    "sv2a_151_alakazam_ex___185_165",
    "sv2a_151_blastoise_ex___188_165",
    "sv2a_151_charizard_ex___201_165",
    "..."
  ]
}
```

**Example:**
```bash
curl http://localhost:3000/list_cards
```

---

### 4. Batch Prediction

**Endpoint:** `POST /batch_predict`

**Description:** Predict for multiple cards in one request

**Request Body:**
```json
[
  {"card_id": "sv2a_151_charizard_ex___201_165"},
  {"card_id": "sv2a_151_blastoise_ex___188_165", "date": "2025-11-30"}
]
```

**Response:**
```json
[
  {
    "card_id": "sv2a_151_charizard_ex___201_165",
    "date": "2025-11-30",
    "market_price": 246.34,
    "fair_price": 245.50,
    "deviation_pct": 0.0034,
    "signal": "HOLD"
  },
  {
    "card_id": "sv2a_151_blastoise_ex___188_165",
    "date": "2025-11-30",
    "market_price": 180.00,
    "fair_price": 200.00,
    "deviation_pct": -0.10,
    "signal": "BUY"
  }
]
```

**Example:**
```bash
curl -X POST http://localhost:3000/batch_predict \
  -H "Content-Type: application/json" \
  -d '[
    {"card_id": "sv2a_151_charizard_ex___201_165"},
    {"card_id": "sv2a_151_blastoise_ex___188_165"}
  ]'
```

---

## Docker Deployment

### Build Docker Image

```bash
# Using Makefile
make bento-containerize

# OR manually
bentoml containerize pokewatch_service:latest -t pokewatch-bento:latest

# Verify image
docker images | grep pokewatch-bento
```

### Run with Docker Compose

```bash
# Start service
docker-compose up bento-api

# OR with profile
docker-compose --profile bento up

# Service available at http://localhost:3000
```

### Run Standalone Container

```bash
# Run container
docker run -d \
  -p 3000:3000 \
  -v $(pwd)/data/processed:/app/data/processed:ro \
  -v $(pwd)/models/baseline:/app/models/baseline:ro \
  --name pokewatch-bento \
  pokewatch-bento:latest

# Check logs
docker logs -f pokewatch-bento

# Stop container
docker stop pokewatch-bento
docker rm pokewatch-bento
```

---

## Configuration

### Environment Variables

The service respects these environment variables:

```bash
# API Key (for data collection, not serving)
POKEMON_PRICE_API_KEY=your_api_key

# MLflow tracking (for logging, optional)
MLFLOW_TRACKING_URI=https://dagshub.com/beatricedaniel/pokewatch.mlflow
DAGSHUB_TOKEN=your_token

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Python path
PYTHONPATH=/app
```

### Resource Configuration

Edit `bentofile.yaml` to adjust resources:

```yaml
docker:
  python_version: "3.13"
  resources:
    cpu: "2"        # CPU cores
    memory: "2Gi"   # RAM
  traffic:
    timeout: 30       # Request timeout (seconds)
    concurrency: 32   # Max concurrent requests
```

---

## Monitoring & Health Checks

### Health Checks

**Liveness Probe:**
```bash
curl -f http://localhost:3000/health || exit 1
```

**Readiness Probe:**
```bash
# Check if service is ready to accept traffic
curl -f http://localhost:3000/health && \
  test "$(curl -s http://localhost:3000/health | jq -r '.model_loaded')" = "true"
```

**Kubernetes Health Check:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 3000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 3000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Logging

Logs are written to:
- **Console**: `stdout` (captured by Docker/K8s)
- **File**: `logs/logs.txt` (if volume mounted)

**View logs:**
```bash
# Docker Compose
docker-compose logs -f bento-api

# Standalone container
docker logs -f pokewatch-bento

# Local development
# Logs appear in terminal
```

---

## Updating the Model

### 1. Train New Model

```bash
# Run training pipeline
make pipeline-run

# Or train individually
make train
```

### 2. Rebuild Bento

```bash
# Rebuild with new model
make bento-build

# New Bento version created
bentoml list
```

### 3. Deploy Update

```bash
# Restart service with new Bento
docker-compose restart bento-api

# Or rebuild and restart
docker-compose build bento-api
docker-compose up -d bento-api
```

---

## Troubleshooting

### Service Won't Start

**Problem:** Service fails to start with "Model not loaded"

**Solution:**
```bash
# Check if processed data exists
ls -lah data/processed/sv2a_pokemon_card_151.parquet

# If missing, run preprocessing
make preprocess

# Rebuild Bento
make bento-build
```

---

### Health Check Fails

**Problem:** `/health` returns unhealthy status

**Solution:**
```bash
# Check logs
docker-compose logs bento-api

# Verify model files exist
ls -lah models/baseline/

# Check data files
ls -lah data/processed/
```

---

### Prediction Errors

**Problem:** Predictions return 500 errors

**Solution:**
```bash
# Test with valid card ID
curl http://localhost:3000/list_cards

# Use card ID from list
curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"card_id": "CARD_ID_FROM_LIST"}'
```

---

### Port Already in Use

**Problem:** Port 3000 already in use

**Solution:**
```bash
# Change port in docker-compose.yml
ports:
  - "3001:3000"  # Host:Container

# Or stop conflicting service
docker ps
docker stop <container_id>
```

---

## Performance Optimization

### Request Batching

For high-throughput scenarios:

```python
# Use batch endpoint
import requests

cards = [
    {"card_id": f"card_{i}"}
    for i in range(100)
]

# Single request for 100 predictions
response = requests.post(
    "http://localhost:3000/batch_predict",
    json=cards
)
```

### Caching

Future enhancement (Week 2):
- Add Redis for prediction caching
- Cache results for 1 hour
- Reduce load on model

---

## Migration from FastAPI

### Side-by-Side Comparison

| Feature | FastAPI (port 8000) | BentoML (port 3000) |
|---------|---------------------|---------------------|
| Health Check | ✅ `/health` | ✅ `/health` |
| Prediction | ✅ `/fair_price` | ✅ `/predict` |
| List Cards | ❌ Not implemented | ✅ `/list_cards` |
| Batch | ❌ Not implemented | ✅ `/batch_predict` |
| Auto-scaling | ⚠️ Manual | ✅ Built-in |
| Versioning | ⚠️ Manual | ✅ Automatic |

### Migration Steps

1. **Run both services in parallel**
   ```bash
   make api          # FastAPI on :8000
   make bento-serve  # BentoML on :3000
   ```

2. **Update client code** to point to `:3000`
3. **Test thoroughly** with integration tests
4. **Deprecate FastAPI** after validation period

---

## Next Steps

- **Week 2**: Add authentication and rate limiting
- **Week 3**: Deploy to Kubernetes with autoscaling
- **Week 4**: Add monitoring with Prometheus/Grafana

---

## Resources

- **BentoML Docs**: https://docs.bentoml.com/
- **API Contract**: `docs/api_contract_bentoml.md`
- **Integration Tests**: `tests/integration/test_bento_service.py`
- **Source Code**: `src/pokewatch/serving/service.py`

---

**Status:** ✅ Production Ready
**Port:** 3000
**Health Check:** http://localhost:3000/health
