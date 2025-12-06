"""
Unit tests for decision rules.
"""

import pytest

from pokewatch.core.decision_rules import DecisionConfig, compute_signal


class TestDecisionConfig:
    """Test DecisionConfig dataclass."""

    def test_default_values(self):
        """Test default threshold values."""
        cfg = DecisionConfig()
        assert cfg.buy_threshold_pct == 0.10
        assert cfg.sell_threshold_pct == 0.15

    def test_custom_values(self):
        """Test custom threshold values."""
        cfg = DecisionConfig(buy_threshold_pct=0.15, sell_threshold_pct=0.20)
        assert cfg.buy_threshold_pct == 0.15
        assert cfg.sell_threshold_pct == 0.20


class TestComputeSignal:
    """Test signal computation logic."""

    def test_buy_signal_negative_deviation(self):
        """Test BUY signal when deviation is negative and large enough."""
        cfg = DecisionConfig(buy_threshold_pct=0.10, sell_threshold_pct=0.15)

        # Market price is 10% below fair value (exactly at threshold)
        market_price = 90.0
        fair_price = 100.0

        signal, deviation = compute_signal(market_price, fair_price, cfg)

        assert signal == "BUY"
        assert deviation == pytest.approx(-0.10, abs=0.001)

    def test_buy_signal_below_threshold(self):
        """Test BUY signal when deviation is below buy threshold."""
        cfg = DecisionConfig(buy_threshold_pct=0.10, sell_threshold_pct=0.15)

        # Market price is 15% below fair value (more than threshold)
        market_price = 85.0
        fair_price = 100.0

        signal, deviation = compute_signal(market_price, fair_price, cfg)

        assert signal == "BUY"
        assert deviation == pytest.approx(-0.15, abs=0.001)

    def test_sell_signal_positive_deviation(self):
        """Test SELL signal when deviation is positive and large enough."""
        cfg = DecisionConfig(buy_threshold_pct=0.10, sell_threshold_pct=0.15)

        # Market price is 15% above fair value (exactly at threshold)
        market_price = 115.0
        fair_price = 100.0

        signal, deviation = compute_signal(market_price, fair_price, cfg)

        assert signal == "SELL"
        assert deviation == pytest.approx(0.15, abs=0.001)

    def test_sell_signal_above_threshold(self):
        """Test SELL signal when deviation is above sell threshold."""
        cfg = DecisionConfig(buy_threshold_pct=0.10, sell_threshold_pct=0.15)

        # Market price is 20% above fair value (more than threshold)
        market_price = 120.0
        fair_price = 100.0

        signal, deviation = compute_signal(market_price, fair_price, cfg)

        assert signal == "SELL"
        assert deviation == pytest.approx(0.20, abs=0.001)

    def test_hold_signal_small_negative_deviation(self):
        """Test HOLD signal when deviation is negative but small."""
        cfg = DecisionConfig(buy_threshold_pct=0.10, sell_threshold_pct=0.15)

        # Market price is 5% below fair value (less than buy threshold)
        market_price = 95.0
        fair_price = 100.0

        signal, deviation = compute_signal(market_price, fair_price, cfg)

        assert signal == "HOLD"
        assert deviation == pytest.approx(-0.05, abs=0.001)

    def test_hold_signal_small_positive_deviation(self):
        """Test HOLD signal when deviation is positive but small."""
        cfg = DecisionConfig(buy_threshold_pct=0.10, sell_threshold_pct=0.15)

        # Market price is 5% above fair value (less than sell threshold)
        market_price = 105.0
        fair_price = 100.0

        signal, deviation = compute_signal(market_price, fair_price, cfg)

        assert signal == "HOLD"
        assert deviation == pytest.approx(0.05, abs=0.001)

    def test_hold_signal_equal_prices(self):
        """Test HOLD signal when market price equals fair price."""
        cfg = DecisionConfig(buy_threshold_pct=0.10, sell_threshold_pct=0.15)

        market_price = 100.0
        fair_price = 100.0

        signal, deviation = compute_signal(market_price, fair_price, cfg)

        assert signal == "HOLD"
        assert deviation == pytest.approx(0.0, abs=0.001)

    def test_buy_signal_at_exact_threshold(self):
        """Test BUY signal at exact buy threshold boundary."""
        cfg = DecisionConfig(buy_threshold_pct=0.10, sell_threshold_pct=0.15)

        # Market price is exactly 10% below (at threshold)
        market_price = 90.0
        fair_price = 100.0

        signal, deviation = compute_signal(market_price, fair_price, cfg)

        assert signal == "BUY"
        assert deviation == pytest.approx(-0.10, abs=0.001)

    def test_sell_signal_at_exact_threshold(self):
        """Test SELL signal at exact sell threshold boundary."""
        cfg = DecisionConfig(buy_threshold_pct=0.10, sell_threshold_pct=0.15)

        # Market price is exactly 15% above (at threshold)
        market_price = 115.0
        fair_price = 100.0

        signal, deviation = compute_signal(market_price, fair_price, cfg)

        assert signal == "SELL"
        assert deviation == pytest.approx(0.15, abs=0.001)

    def test_hold_signal_between_thresholds(self):
        """Test HOLD signal when deviation is between thresholds."""
        cfg = DecisionConfig(buy_threshold_pct=0.10, sell_threshold_pct=0.15)

        # Market price is 12% above (between buy and sell thresholds)
        market_price = 112.0
        fair_price = 100.0

        signal, deviation = compute_signal(market_price, fair_price, cfg)

        assert signal == "HOLD"
        assert deviation == pytest.approx(0.12, abs=0.001)

    def test_error_on_zero_fair_price(self):
        """Test that error is raised when fair price is zero."""
        cfg = DecisionConfig()

        with pytest.raises(ValueError, match="Fair price must be positive"):
            compute_signal(100.0, 0.0, cfg)

    def test_error_on_negative_fair_price(self):
        """Test that error is raised when fair price is negative."""
        cfg = DecisionConfig()

        with pytest.raises(ValueError, match="Fair price must be positive"):
            compute_signal(100.0, -10.0, cfg)

    def test_custom_thresholds(self):
        """Test with custom threshold values."""
        cfg = DecisionConfig(buy_threshold_pct=0.05, sell_threshold_pct=0.10)

        # Market price is 6% below (above custom buy threshold of 5%)
        market_price = 94.0
        fair_price = 100.0

        signal, deviation = compute_signal(market_price, fair_price, cfg)

        assert signal == "BUY"
        assert deviation == pytest.approx(-0.06, abs=0.001)
