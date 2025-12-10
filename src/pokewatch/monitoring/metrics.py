"""Prometheus metrics for PokeWatch API monitoring.

This module defines and exposes Prometheus metrics for monitoring
API performance, request counts, and model information.
"""

from prometheus_client import Counter, Histogram, Info, generate_latest
from prometheus_client.core import CollectorRegistry

# Create a custom registry to avoid conflicts
POKEWATCH_REGISTRY = CollectorRegistry()

# Request metrics
REQUEST_COUNT = Counter(
    "pokewatch_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status_code"],
    registry=POKEWATCH_REGISTRY,
)

REQUEST_LATENCY = Histogram(
    "pokewatch_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=POKEWATCH_REGISTRY,
)

# Prediction metrics
PREDICTION_COUNT = Counter(
    "pokewatch_predictions_total",
    "Total number of fair price predictions",
    ["signal"],  # BUY, SELL, HOLD
    registry=POKEWATCH_REGISTRY,
)

# Model metrics
MODEL_INFO = Info(
    "pokewatch_model",
    "Information about the currently loaded model",
    registry=POKEWATCH_REGISTRY,
)

MODEL_RELOAD_COUNT = Counter(
    "pokewatch_model_reloads_total",
    "Total number of model reloads",
    ["status"],  # success, failure
    registry=POKEWATCH_REGISTRY,
)

# Error metrics
ERROR_COUNT = Counter(
    "pokewatch_errors_total",
    "Total number of errors",
    ["error_type"],
    registry=POKEWATCH_REGISTRY,
)


def get_metrics() -> bytes:
    """Generate Prometheus metrics output.

    Returns:
        bytes: Prometheus-formatted metrics
    """
    return generate_latest(POKEWATCH_REGISTRY)


def record_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
    """Record a request metric.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: Request endpoint path
        status_code: HTTP response status code
        duration: Request duration in seconds
    """
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


def record_prediction(signal: str) -> None:
    """Record a prediction metric.

    Args:
        signal: Trading signal (BUY, SELL, HOLD)
    """
    PREDICTION_COUNT.labels(signal=signal).inc()


def update_model_info(version: str, loaded_at: str) -> None:
    """Update model information.

    Args:
        version: Model version string
        loaded_at: Timestamp when model was loaded
    """
    MODEL_INFO.info({"version": version, "loaded_at": loaded_at})


def record_model_reload(success: bool) -> None:
    """Record a model reload event.

    Args:
        success: Whether the reload was successful
    """
    status = "success" if success else "failure"
    MODEL_RELOAD_COUNT.labels(status=status).inc()


def record_error(error_type: str) -> None:
    """Record an error metric.

    Args:
        error_type: Type of error (validation, prediction, internal, etc.)
    """
    ERROR_COUNT.labels(error_type=error_type).inc()
