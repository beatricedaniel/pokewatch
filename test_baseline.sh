#!/bin/bash
# Script to test baseline model and decision rules

echo "=========================================="
echo "Testing Baseline Model and Decision Rules"
echo "=========================================="
echo ""

echo "1. Running baseline model tests..."
uv run python -m pytest tests/unit/test_baseline.py -v
echo ""

echo "2. Running decision rules tests..."
uv run python -m pytest tests/unit/test_decision_rules.py -v
echo ""

echo "3. Testing baseline model with real data..."
uv run python -c "
from pokewatch.models.baseline import load_baseline_model
from pokewatch.core.decision_rules import DecisionConfig, compute_signal
from pokewatch.config import get_settings

model = load_baseline_model()
settings = get_settings()
cfg = DecisionConfig(
    buy_threshold_pct=settings.model.default_buy_threshold_pct,
    sell_threshold_pct=settings.model.default_sell_threshold_pct
)

print(f'✓ Model loaded with {len(model.get_all_card_ids())} cards')
print('')
print('Sample predictions:')
print('-' * 80)

for card_id in model.get_all_card_ids()[:3]:
    date, market, fair = model.predict(card_id)
    signal, dev = compute_signal(market, fair, cfg)
    print(f'{card_id[:50]:50s}')
    print(f'  Date: {date} | Market: \${market:.2f} | Fair: \${fair:.2f} | Signal: {signal} ({dev*100:+.2f}%)')
    print('')
"

echo "=========================================="
echo "All tests complete!"
echo "=========================================="
