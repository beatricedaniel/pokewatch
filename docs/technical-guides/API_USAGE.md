# PokeWatch API Usage Guide

This guide explains how to start and use the PokeWatch FastAPI server.

## Starting the API Server

### Option 1: Using uvicorn directly

```bash
cd pokewatch
uv run uvicorn pokewatch.api.main:app --reload
```

The `--reload` flag enables auto-reload on code changes (useful for development).

### Option 2: Using uvicorn with custom host/port

```bash
uv run uvicorn pokewatch.api.main:app --host 0.0.0.0 --port 8080
```

### Option 3: Using Python module

```bash
cd pokewatch
uv run python -m uvicorn pokewatch.api.main:app
```

The API will be available at `http://localhost:8000` by default.

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API is running and if the model is loaded.

**Example with curl:**
```bash
curl http://localhost:8000/health
```

**Example with Python:**
```python
import requests

response = requests.get("http://localhost:8000/health")
print(response.json())
```

**Response:**
```json
{
  "status": "ok",
  "model_loaded": true,
  "cards_count": 10
}
```

---

### 2. List Available Cards

**Endpoint:** `GET /cards`

**Description:** Get a list of all card IDs available in the model.

**Example with curl:**
```bash
curl http://localhost:8000/cards
```

**Example with Python:**
```python
import requests

response = requests.get("http://localhost:8000/cards")
data = response.json()
print(f"Total cards: {data['count']}")
for card_id in data['cards']:
    print(f"  - {card_id}")
```

**Response:**
```json
{
  "cards": [
    "sv2a_151_charizard_ex___201_165",
    "sv2a_151_venusaur_ex___198_165",
    ...
  ],
  "count": 10
}
```

---

### 3. Get Fair Price Prediction

**Endpoint:** `POST /fair_price`

**Description:** Get fair price prediction and trading signal for a specific card.

**Request Body:**
```json
{
  "card_id": "sv2a_151_charizard_ex___201_165",
  "date": "2025-11-24"  // Optional: if omitted, uses latest available date
}
```

**Example with curl:**
```bash
# Using latest available date
curl -X POST http://localhost:8000/fair_price \
  -H "Content-Type: application/json" \
  -d '{"card_id": "sv2a_151_charizard_ex___201_165"}'

# Using specific date
curl -X POST http://localhost:8000/fair_price \
  -H "Content-Type: application/json" \
  -d '{"card_id": "sv2a_151_charizard_ex___201_165", "date": "2025-11-24"}'
```

**Example with Python:**
```python
import requests
from datetime import date

# Using latest date
response = requests.post(
    "http://localhost:8000/fair_price",
    json={"card_id": "sv2a_151_charizard_ex___201_165"}
)
print(response.json())

# Using specific date
response = requests.post(
    "http://localhost:8000/fair_price",
    json={
        "card_id": "sv2a_151_charizard_ex___201_165",
        "date": "2025-11-24"
    }
)
print(response.json())
```

**Response:**
```json
{
  "card_id": "sv2a_151_charizard_ex___201_165",
  "date": "2025-11-24",
  "market_price": 246.34,
  "fair_price": 245.50,
  "deviation_pct": 0.0034,
  "signal": "HOLD"
}
```

**Response Fields:**
- `card_id`: The card identifier
- `date`: The date used for prediction
- `market_price`: Current market price on that date
- `fair_price`: Predicted fair value
- `deviation_pct`: Percentage deviation: `(market_price - fair_price) / fair_price`
- `signal`: Trading signal: `"BUY"`, `"SELL"`, or `"HOLD"`

**Trading Signals:**
- `BUY`: Market price is at least 10% below fair value (undervalued)
- `SELL`: Market price is at least 15% above fair value (overvalued)
- `HOLD`: Market price is within the normal range

**Error Responses:**

- **404 Not Found:** Card ID not found
  ```json
  {
    "detail": "Unknown card_id: invalid_card_id"
  }
  ```

- **404 Not Found:** Date not found for the card
  ```json
  {
    "detail": "No data found for card_id: sv2a_151_charizard_ex___201_165 on date: 2026-01-01"
  }
  ```

- **503 Service Unavailable:** Model not loaded
  ```json
  {
    "detail": "Model not loaded. Please wait for startup to complete."
  }
  ```

---

## Finding Card IDs

Card IDs are based on the `internal_id` field in `config/cards.yaml`. You can:

1. **List all available cards via API:**
   ```bash
   curl http://localhost:8000/cards
   ```

2. **Check the cards.yaml file:**
   ```bash
   cat config/cards.yaml
   ```
   Look for the `internal_id` field in each card entry.

3. **Use the test script:**
   ```bash
   uv run python scripts/test_api.py
   ```

## Interactive API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

You can test all endpoints directly from your browser using these interfaces.

## Example Workflow

1. **Start the server:**
   ```bash
   cd pokewatch
   uv run uvicorn pokewatch.api.main:app --reload
   ```

2. **Check health:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **List available cards:**
   ```bash
   curl http://localhost:8000/cards
   ```

4. **Get fair price for a card:**
   ```bash
   curl -X POST http://localhost:8000/fair_price \
     -H "Content-Type: application/json" \
     -d '{"card_id": "sv2a_151_charizard_ex___201_165"}'
   ```

## Testing Script

A test script is provided to demonstrate all endpoints:

```bash
# Make sure the API server is running first
uv run python scripts/test_api.py
```

This script will:
- Test the health endpoint
- List all available cards
- Test fair price predictions with different scenarios
- Show example error cases
