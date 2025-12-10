"""Monitoring module for PokeWatch.

Provides Prometheus metrics and drift detection functionality.
"""

from pokewatch.monitoring.metrics import (
    get_metrics,
    record_request,
    record_prediction,
    record_error,
    record_model_reload,
    update_model_info,
)

from pokewatch.monitoring.drift_detector import (
    DriftDetector,
    run_drift_detection,
)

__all__ = [
    "get_metrics",
    "record_request",
    "record_prediction",
    "record_error",
    "record_model_reload",
    "update_model_info",
    "DriftDetector",
    "run_drift_detection",
]
