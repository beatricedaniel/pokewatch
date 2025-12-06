# PokeWatch API Contract - BentoML Migration

**Version:** 1.0
**Last Updated:** 2025-11-30

This document defines the API contract for the BentoML migration, ensuring compatibility with the existing FastAPI implementation.

---

## Current FastAPI Endpoints

### 1. Health Check
- **Endpoint:** `GET /health`
- **Response:** `{"status": "ok", "model_loaded": true, "cards_count": 10}`

### 2. Fair Price Prediction
- **Endpoint:** `POST /fair_price`
- **Request:** `{"card_id": "string", "date": "YYYY-MM-DD"}`
- **Response:** `{"card_id": "string", "date": "YYYY-MM-DD", "market_price": float, "fair_price": float, "deviation_pct": float, "signal": "BUY|SELL|HOLD"}`

---

## BentoML Target Endpoints

### 1. Health Check (unchanged)
- **Endpoint:** `GET /health`
- **Port:** 3000 (BentoML) vs 8000 (FastAPI)

### 2. Prediction (versioned endpoint)
- **Endpoint:** `POST /api/v1/predict`
- **Matches:** FastAPI `/fair_price` schema exactly

### 3. List Cards (new)
- **Endpoint:** `GET /api/v1/cards`
- **Returns:** List of all tracked card IDs

### 4. Batch Prediction (new)
- **Endpoint:** `POST /api/v1/batch_predict`
- **Request:** Array of prediction requests

---

## Migration Strategy

1. **Week 1:** Implement BentoML with matching schemas
2. **Week 2:** Run both services in parallel (FastAPI:8000, BentoML:3000)
3. **Week 3:** Cutover to BentoML in Kubernetes

**Status:** ✅ Contract Documented
