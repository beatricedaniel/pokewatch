"""
Decision Service for PokeWatch

Provides BUY/SELL/HOLD trading signals based on price deviation.
This service wraps the existing decision_rules.py logic without modification.
"""
import logging
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from pokewatch.core.decision_rules import compute_signal, DecisionConfig

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="PokeWatch Decision Service",
    description="Trading signal generation service",
    version="1.0.0"
)


class SignalRequest(BaseModel):
    """Request model for signal generation."""
    market_price: float = Field(..., description="Current market price", gt=0)
    fair_price: float = Field(..., description="Predicted fair value", gt=0)
    buy_threshold_pct: float = Field(
        0.10,
        description="Buy threshold percentage (e.g., 0.10 for -10%)",
        ge=0,
        le=1
    )
    sell_threshold_pct: float = Field(
        0.15,
        description="Sell threshold percentage (e.g., 0.15 for +15%)",
        ge=0,
        le=1
    )

    class Config:
        json_schema_extra = {
            "example": {
                "market_price": 90.0,
                "fair_price": 100.0,
                "buy_threshold_pct": 0.10,
                "sell_threshold_pct": 0.15
            }
        }


class SignalResponse(BaseModel):
    """Response model for signal generation."""
    signal: Literal["BUY", "SELL", "HOLD"]
    deviation_pct: float = Field(..., description="Price deviation percentage")
    market_price: float
    fair_price: float

    class Config:
        json_schema_extra = {
            "example": {
                "signal": "BUY",
                "deviation_pct": -0.1,
                "market_price": 90.0,
                "fair_price": 100.0
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str


@app.post("/signal", response_model=SignalResponse)
def get_signal(request: SignalRequest) -> SignalResponse:
    """
    Generate trading signal based on price deviation.

    Logic:
    - deviation_pct = (market_price - fair_price) / fair_price
    - If deviation_pct <= -buy_threshold_pct → BUY (undervalued)
    - If deviation_pct >= sell_threshold_pct → SELL (overvalued)
    - Otherwise → HOLD

    Args:
        request: SignalRequest with market_price, fair_price, and thresholds

    Returns:
        SignalResponse with signal and deviation percentage

    Example:
        Request: {"market_price": 90.0, "fair_price": 100.0}
        Response: {"signal": "BUY", "deviation_pct": -0.1, ...}
    """
    try:
        # Create decision configuration
        cfg = DecisionConfig(
            buy_threshold_pct=request.buy_threshold_pct,
            sell_threshold_pct=request.sell_threshold_pct
        )

        # Reuse existing decision_rules.compute_signal() - no changes needed!
        signal, deviation_pct = compute_signal(
            market_price=request.market_price,
            fair_price=request.fair_price,
            cfg=cfg
        )

        return SignalResponse(
            signal=signal,
            deviation_pct=deviation_pct,
            market_price=request.market_price,
            fair_price=request.fair_price
        )

    except ValueError as e:
        logger.error(f"Signal computation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="decision_service"
    )


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger.info("Decision Service initialized")
