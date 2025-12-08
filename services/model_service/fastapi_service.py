"""
FastAPI Model Service for PokeWatch (simpler alternative to BentoML)

Wraps the existing baseline model to serve predictions via HTTP.
"""
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from pokewatch.models.baseline import load_baseline_model

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="PokeWatch Model Service",
    description="ML model serving for Pokemon card fair price predictions",
    version="1.0.0"
)

# Load model at startup
model = None

@app.on_event("startup")
async def startup_event():
    """Load the baseline model on startup."""
    global model
    logger.info("Loading baseline model...")
    try:
        model = load_baseline_model()
        logger.info(f"Model loaded with {len(model.get_all_card_ids())} cards")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


class PredictRequest(BaseModel):
    """Request model for predictions."""
    card_id: str = Field(..., description="Card internal ID")
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")


class PredictResponse(BaseModel):
    """Response model for predictions."""
    card_id: str
    date: str
    market_price: float
    fair_price: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool
    cards_count: int


class CardsResponse(BaseModel):
    """Cards list response."""
    cards: list[str]
    count: int


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    """
    Predict fair price for a given card.

    Args:
        request: Prediction request with card_id and optional date

    Returns:
        Prediction response with market and fair prices
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        resolved_date, market_price, fair_price = model.predict(
            card_id=request.card_id,
            date=request.date
        )

        return PredictResponse(
            card_id=request.card_id,
            date=str(resolved_date),
            market_price=float(market_price),
            fair_price=float(fair_price)
        )
    except ValueError as e:
        logger.error(f"Prediction error for {request.card_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if model is not None else "unhealthy",
        model_loaded=model is not None,
        cards_count=len(model.get_all_card_ids()) if model else 0
    )


@app.get("/cards", response_model=CardsResponse)
def list_cards() -> CardsResponse:
    """List all available card IDs."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    card_ids = model.get_all_card_ids()
    return CardsResponse(
        cards=card_ids,
        count=len(card_ids)
    )


@app.post("/reload")
def reload_model():
    """Reload the model from MLflow registry."""
    global model
    try:
        logger.info("Reloading model from MLflow...")
        model = load_baseline_model()
        logger.info(f"Model reloaded successfully with {len(model.get_all_card_ids())} cards")
        return {
            "status": "reloaded",
            "cards_count": len(model.get_all_card_ids())
        }
    except Exception as e:
        logger.error(f"Model reload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reload failed: {str(e)}")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger.info("Model Service initialized")
