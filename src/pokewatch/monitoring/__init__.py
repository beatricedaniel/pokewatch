"""Monitoring module for PokeWatch.

Provides Prometheus metrics and drift detection functionality.

Note: Drift detection (evidently) is imported lazily to avoid
startup issues with Python 3.13 compatibility. Import directly:
    from pokewatch.monitoring.drift_detector import DriftDetector
"""

from pokewatch.monitoring.metrics import (
    get_metrics,
    record_request,
    record_prediction,
    record_error,
    record_model_reload,
    update_model_info,
)

# Don't import drift_detector here - evidently has Python 3.13 issues
# Import it directly when needed:
#   from pokewatch.monitoring.drift_detector import DriftDetector, run_drift_detection

__all__ = [
    "get_metrics",
    "record_request",
    "record_prediction",
    "record_error",
    "record_model_reload",
    "update_model_info",
]
