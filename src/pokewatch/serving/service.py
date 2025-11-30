"""
BentoML service for PokeWatch fair price predictions.

Replaces the FastAPI application with production-grade serving.
"""

import logging
from typing import Optional, List
from datetime import date, datetime

import bentoml
from pydantic import BaseModel, Field

from pokewatch.models.baseline import BaselineFairPriceModel, load_baseline_model
from pokewatch.core.decision_rules import DecisionConfig, compute_signal
from pokewatch.config import get_settings

logger = logging.getLogger(__name__)


# Request/Response schemas (matching FastAPI schemas)
class PredictionRequest(BaseModel):
    """Request schema for fair price prediction."""
    card_id: str = Field(..., description="Card identifier (e.g., 'sv2a_151_charizard_ex___201_165')")
    date: Optional[str] = Field(None, description="Date for prediction (YYYY-MM-DD). Defaults to latest.")

    class Config:
        json_schema_extra = {
            "example": {
                "card_id": "sv2a_151_charizard_ex___201_165",
                "date": "2025-11-24",
            }
        }


class PredictionResponse(BaseModel):
    """Response schema for fair price prediction."""
    card_id: str
    date: str
    market_price: float
    fair_price: float
    deviation_pct: float
    signal: str  # BUY, SELL, HOLD

    class Config:
        json_schema_extra = {
            "example": {
                "card_id": "sv2a_151_charizard_ex___201_165",
                "date": "2025-11-24",
                "market_price": 246.34,
                "fair_price": 245.50,
                "deviation_pct": 0.0034,
                "signal": "HOLD",
            }
        }


# Create BentoML service
@bentoml.service(
    name="pokewatch_service",
    resources={
        "cpu": "1",
        "memory": "1Gi",
    },
    traffic={
        "timeout": 30,
        "concurrency": 32,  # Max concurrent requests
    },
)
class PokeWatchService:
    """PokeWatch BentoML service for card price predictions."""

    def __init__(self):
        """Initialize service and load model."""
        logger.info("Initializing PokeWatch service...")
        
        # Load settings and decision config (lazy loading - only when service starts)
        # This allows the module to be imported during Docker build without requiring API key
        settings = get_settings()
        self.decision_cfg = DecisionConfig(
            buy_threshold_pct=settings.model.default_buy_threshold_pct,
            sell_threshold_pct=settings.model.default_sell_threshold_pct,
        )
        
        # Load model
        self.model = load_baseline_model()
        logger.info(f"Model loaded with {len(self.model.get_all_card_ids())} cards")

    @bentoml.api
    def health(self) -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy" if self.model is not None else "unhealthy",
            "model_loaded": self.model is not None,
            "num_cards": len(self.model.get_all_card_ids()) if self.model else 0,
        }

    @bentoml.api
    def predict(self, request: PredictionRequest) -> PredictionResponse:
        """
        Predict fair value and trading signal for a card.

        Args:
            request: Prediction request with card_id and optional date

        Returns:
            Prediction response with fair value, market price, and signal

        Raises:
            ValueError: If card_id is unknown or date is invalid
        """
        card_id = request.card_id

        # Parse date
        pred_date = None
        if request.date:
            pred_date = datetime.strptime(request.date, "%Y-%m-%d").date()

        # Get prediction from model
        resolved_date, market_price, fair_value = self.model.predict(
            card_id=card_id,
            date=pred_date
        )

        # Compute signal
        signal, delta_pct = compute_signal(
            market_price=market_price,
            fair_value=fair_value,
            config=self.decision_cfg,
        )

        # Build response
        return PredictionResponse(
            card_id=card_id,
            date=resolved_date.isoformat(),
            market_price=market_price,
            fair_price=fair_value,
            deviation_pct=delta_pct,
            signal=signal,
        )

    @bentoml.api
    def list_cards(self) -> dict:
        """List all tracked cards."""
        card_ids = self.model.get_all_card_ids()

        return {
            "total": len(card_ids),
            "cards": sorted(list(card_ids)),
        }

    @bentoml.api
    async def batch_predict(self, requests: List[PredictionRequest]) -> List[dict]:
        """
        Batch prediction for multiple cards.

        Uses async for better performance with multiple requests.
        """
        results = []
        for req in requests:
            try:
                result = self.predict(req)
                results.append(result.dict())
            except Exception as e:
                logger.error(f"Batch prediction failed for {req.card_id}: {e}")
                # Add error entry
                results.append({
                    "card_id": req.card_id,
                    "error": str(e),
                })

        return results
