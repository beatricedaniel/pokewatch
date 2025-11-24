"""
FastAPI application for PokeWatch API.

Provides endpoints for fair price prediction and trading signals.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from pokewatch.api import dependencies
from pokewatch.api.schemas import FairPriceRequest, FairPriceResponse, HealthResponse
from pokewatch.config import get_settings
from pokewatch.core.decision_rules import DecisionConfig, compute_signal
from pokewatch.models.baseline import BaselineFairPriceModel, load_baseline_model

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging to write to both console and logs/logs.txt file."""
    # Determine log file path
    # Try to use logs directory relative to project root, or current directory
    project_root = Path(__file__).parent.parent.parent.parent
    log_dir = project_root / "logs"
    log_file = log_dir / "logs.txt"
    
    # Create logs directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Get log level from environment or default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Console handler
            logging.StreamHandler(),
            # File handler (append mode)
            logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        ],
    )
    
    logger.info(f"Logging configured. Log file: {log_file}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Loads the baseline model on startup.
    """
    # Setup logging first
    setup_logging()
    
    # Startup
    logger.info("Starting PokeWatch API...")
    try:
        settings = get_settings()

        # Load baseline model
        logger.info("Loading baseline model...")
        model = load_baseline_model()
        dependencies.set_model(model)

        # Load decision configuration
        decision_cfg = DecisionConfig(
            buy_threshold_pct=settings.model.default_buy_threshold_pct,
            sell_threshold_pct=settings.model.default_sell_threshold_pct,
        )
        dependencies.set_decision_config(decision_cfg)

        logger.info(
            f"✓ Model loaded with {len(model.get_all_card_ids())} cards. "
            f"Decision thresholds: BUY <= -{decision_cfg.buy_threshold_pct*100}%, "
            f"SELL >= +{decision_cfg.sell_threshold_pct*100}%"
        )
    except Exception as e:
        logger.error(f"Failed to load model during startup: {e}", exc_info=True)
        # Don't set model, API will return 503 until model is loaded

    yield

    # Shutdown
    logger.info("Shutting down PokeWatch API...")


app = FastAPI(
    title="PokeWatch API",
    description="API for Pokemon card fair price prediction and trading signals",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health():
    """
    Health check endpoint.

    Returns:
        Service status and model information
    """
    model_loaded, cards_count = dependencies.get_model_status()
    status_value = "ok" if model_loaded else "error"

    return HealthResponse(
        status=status_value,
        model_loaded=model_loaded,
        cards_count=cards_count,
    )


@app.post("/fair_price", response_model=FairPriceResponse)
def fair_price(
    payload: FairPriceRequest,
    model: Annotated[BaselineFairPriceModel, Depends(dependencies.get_model)],
    decision_cfg: Annotated[DecisionConfig, Depends(dependencies.get_decision_config)],
):
    """
    Predict fair price and compute trading signal for a card.

    Args:
        payload: Request with card_id and optional date
        model: Baseline model (injected dependency)
        decision_cfg: Decision configuration (injected dependency)

    Returns:
        FairPriceResponse with prediction and signal

    Raises:
        HTTPException: If card_id is unknown or date not found
    """
    try:
        # Predict fair price
        resolved_date, market_price, fair_price = model.predict(
            card_id=payload.card_id,
            date=payload.date,
        )
    except ValueError as e:
        # Handle unknown card_id or missing date
        error_msg = str(e)
        if "Unknown card_id" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown card_id: {payload.card_id}",
            )
        elif "No data found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )

    # Compute trading signal
    try:
        signal, deviation_pct = compute_signal(market_price, fair_price, decision_cfg)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing signal: {str(e)}",
        )

    return FairPriceResponse(
        card_id=payload.card_id,
        date=resolved_date,
        market_price=market_price,
        fair_price=fair_price,
        deviation_pct=deviation_pct,
        signal=signal,
    )


@app.get("/cards")
def list_cards(
    model: Annotated[BaselineFairPriceModel, Depends(dependencies.get_model)],
):
    """
    List all available card IDs.

    Returns:
        List of card IDs in the model
    """
    card_ids = model.get_all_card_ids()
    return {"cards": card_ids, "count": len(card_ids)}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

