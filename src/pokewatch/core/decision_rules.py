"""
Decision rules for BUY/SELL/HOLD signals.

Computes trading signals based on deviation between market price and fair value.
"""

from dataclasses import dataclass
from typing import Literal

logger = __name__


@dataclass
class DecisionConfig:
    """Configuration for decision rules."""

    buy_threshold_pct: float = 0.10  # -10% (market price is 10% below fair value)
    sell_threshold_pct: float = 0.15  # +15% (market price is 15% above fair value)


def compute_signal(
    market_price: float,
    fair_price: float,
    cfg: DecisionConfig,
) -> tuple[Literal["BUY", "SELL", "HOLD"], float]:
    """
    Compute trading signal based on price deviation.

    Logic:
    - deviation_pct = (market_price - fair_price) / fair_price
    - If deviation_pct <= -buy_threshold_pct → "BUY" (undervalued)
    - If deviation_pct >= sell_threshold_pct → "SELL" (overvalued)
    - Otherwise → "HOLD"

    Args:
        market_price: Current market price
        fair_price: Predicted fair value
        cfg: Decision configuration with thresholds

    Returns:
        Tuple of (signal, deviation_pct)
        - signal: "BUY", "SELL", or "HOLD"
        - deviation_pct: Percentage deviation from fair value
            (positive = overvalued, negative = undervalued)

    Example:
        >>> cfg = DecisionConfig(buy_threshold_pct=0.10, sell_threshold_pct=0.15)
        >>> signal, deviation = compute_signal(90.0, 100.0, cfg)
        >>> signal
        'BUY'
        >>> deviation
        -0.1
    """
    if fair_price <= 0:
        raise ValueError(f"Fair price must be positive, got: {fair_price}")

    # Calculate deviation percentage
    deviation_pct = (market_price - fair_price) / fair_price

    # Determine signal
    if deviation_pct <= -cfg.buy_threshold_pct:
        signal: Literal["BUY", "SELL", "HOLD"] = "BUY"
    elif deviation_pct >= cfg.sell_threshold_pct:
        signal = "SELL"
    else:
        signal = "HOLD"

    return (signal, deviation_pct)
