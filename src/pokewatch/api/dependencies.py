"""
FastAPI dependencies for PokeWatch API.

Provides dependency injection for model and configuration.
"""

from fastapi import HTTPException, status

from pokewatch.config import get_settings
from pokewatch.core.decision_rules import DecisionConfig
from pokewatch.models.baseline import BaselineFairPriceModel

# Global model instance (set during startup)
_baseline_model: BaselineFairPriceModel | None = None
_decision_cfg: DecisionConfig | None = None


def set_model(model: BaselineFairPriceModel) -> None:
    """Set the global baseline model instance."""
    global _baseline_model
    _baseline_model = model


def set_decision_config(cfg: DecisionConfig) -> None:
    """Set the global decision configuration."""
    global _decision_cfg
    _decision_cfg = cfg


def get_model() -> BaselineFairPriceModel:
    """
    Dependency to get the baseline model.

    Raises:
        HTTPException: If model is not loaded
    """
    if _baseline_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Please wait for startup to complete.",
        )
    return _baseline_model


def get_decision_config() -> DecisionConfig:
    """
    Dependency to get the decision configuration.

    Returns:
        DecisionConfig instance
    """
    if _decision_cfg is None:
        # Fallback to default if not set
        settings = get_settings()
        return DecisionConfig(
            buy_threshold_pct=settings.model.default_buy_threshold_pct,
            sell_threshold_pct=settings.model.default_sell_threshold_pct,
        )
    return _decision_cfg


def get_model_status() -> tuple[bool, int | None]:
    """
    Get model status information.

    Returns:
        Tuple of (is_loaded, cards_count)
    """
    if _baseline_model is None:
        return (False, None)
    return (True, len(_baseline_model.get_all_card_ids()))
