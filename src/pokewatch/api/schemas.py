"""
Pydantic schemas for API request/response models.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Literal, Optional

from pydantic import BaseModel, Field


class FairPriceRequest(BaseModel):
    """Request model for /fair_price endpoint."""

    card_id: str = Field(..., description="Unique card identifier")
    date: Optional[date_type] = Field(
        default=None,
        description="Date for prediction. If None, uses latest available date for the card.",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "card_id": "sv2a_151_charizard_ex___201_165",
                "date": "2025-11-24",
            }
        }


class FairPriceResponse(BaseModel):
    """Response model for /fair_price endpoint."""

    card_id: str = Field(..., description="Unique card identifier")
    date: date_type = Field(..., description="Date used for prediction")
    market_price: float = Field(..., description="Market price on the given date")
    fair_price: float = Field(..., description="Predicted fair value")
    deviation_pct: float = Field(
        ...,
        description="Percentage deviation: (market_price - fair_price) / fair_price",
    )
    signal: Literal["BUY", "SELL", "HOLD"] = Field(
        ..., description="Trading signal: BUY, SELL, or HOLD"
    )

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


class HealthResponse(BaseModel):
    """Response model for /health endpoint."""

    status: Literal["ok", "error"] = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Whether the baseline model is loaded")
    cards_count: Optional[int] = Field(
        default=None, description="Number of cards in the model (if loaded)"
    )
