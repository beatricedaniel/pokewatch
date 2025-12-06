#!/usr/bin/env python3
"""
Simple performance test script for PokeWatch baseline model.

Tests prediction latency and cache effectiveness (Week 2, Day 4).
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pokewatch.models.baseline import load_baseline_model


def test_performance():
    """Test prediction performance and cache hit rate."""
    print("=" * 60)
    print("PokeWatch Performance Test")
    print("=" * 60)
    print()

    # Load model
    print("Loading baseline model...")
    try:
        model = load_baseline_model()
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        print("\nMake sure you have:")
        print("  1. Collected data: python -m pokewatch.data.collectors.daily_price_collector")
        print("  2. Created features: python -m pokewatch.data.preprocessing.make_features")
        return

    card_ids = model.get_all_card_ids()
    if not card_ids:
        print("❌ No cards found in model")
        return

    print(f"✓ Model loaded with {len(card_ids)} cards")
    print()

    # Test card (use first available card)
    test_card = card_ids[0]
    print(f"Test card: {test_card}")
    print()

    # ===================================================================
    # Test 1: Cold cache (first request)
    # ===================================================================
    print("Test 1: Cold Cache Performance")
    print("-" * 60)

    start = time.time()
    try:
        result = model.predict(test_card)
        cold_latency = time.time() - start
        print(f"✓ First prediction (cold): {cold_latency * 1000:.2f}ms")
        print(f"  Result: market_price={result[1]:.2f}, fair_price={result[2]:.2f}")
    except Exception as e:
        print(f"❌ Prediction failed: {e}")
        return

    print()

    # ===================================================================
    # Test 2: Warm cache (repeated requests)
    # ===================================================================
    print("Test 2: Warm Cache Performance")
    print("-" * 60)

    start = time.time()
    model.predict(test_card)
    warm_latency = time.time() - start
    print(f"✓ Second prediction (warm): {warm_latency * 1000:.2f}ms")
    print(f"  Speedup: {cold_latency / warm_latency:.1f}x faster")
    print()

    # ===================================================================
    # Test 3: Bulk performance test
    # ===================================================================
    print("Test 3: Bulk Performance Test (100 requests)")
    print("-" * 60)

    num_requests = 100
    times = []

    for i in range(num_requests):
        # Alternate between same card (cache hits) and different dates/cards
        if i % 2 == 0:
            # Same card - should hit cache
            card_id = test_card
        else:
            # Different card - might miss cache
            card_id = card_ids[i % min(10, len(card_ids))]

        start = time.time()
        try:
            model.predict(card_id)
            times.append(time.time() - start)
        except Exception:
            pass  # Skip failed predictions

    if times:
        avg_ms = sum(times) / len(times) * 1000
        min_ms = min(times) * 1000
        max_ms = max(times) * 1000
        p50_ms = sorted(times)[len(times) // 2] * 1000
        p95_ms = sorted(times)[int(len(times) * 0.95)] * 1000

        print(f"Completed {len(times)} predictions")
        print(f"  Average:  {avg_ms:.2f}ms")
        print(f"  Median (p50): {p50_ms:.2f}ms")
        print(f"  p95:      {p95_ms:.2f}ms")
        print(f"  Min:      {min_ms:.2f}ms")
        print(f"  Max:      {max_ms:.2f}ms")
        print()

    # ===================================================================
    # Test 4: Cache Statistics
    # ===================================================================
    print("Test 4: Cache Statistics")
    print("-" * 60)

    stats = model.get_cache_stats()
    print(f"Cache Hits:    {stats['cache_hits']}")
    print(f"Cache Misses:  {stats['cache_misses']}")
    print(f"Cache Size:    {stats['cache_size']} / {stats['cache_max_size']}")
    print(f"Hit Rate:      {stats['hit_rate'] * 100:.1f}%")
    print(f"Total Requests: {stats['total_requests']}")
    print()

    # ===================================================================
    # Summary
    # ===================================================================
    print("=" * 60)
    print("Performance Summary")
    print("=" * 60)

    if stats['hit_rate'] > 0.5:
        cache_status = "✓ Good"
    elif stats['hit_rate'] > 0.2:
        cache_status = "⚠ Moderate"
    else:
        cache_status = "❌ Poor"

    print(f"Cache Effectiveness: {cache_status} ({stats['hit_rate'] * 100:.1f}% hit rate)")

    if avg_ms < 1.0:
        latency_status = "✓ Excellent"
    elif avg_ms < 10.0:
        latency_status = "✓ Good"
    elif avg_ms < 50.0:
        latency_status = "⚠ Acceptable"
    else:
        latency_status = "❌ Slow"

    print(f"Average Latency: {latency_status} ({avg_ms:.2f}ms)")
    print()

    print("Performance test complete! 🚀")
    print()


if __name__ == "__main__":
    test_performance()
