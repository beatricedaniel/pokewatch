"""
ZenML pipeline steps for PokeWatch ML workflow.

These steps can be orchestrated with ZenML or used independently.
Week 2, Day 5: Added ZenML @step decorators for pipeline orchestration.
"""

import logging
from typing import Tuple
from pathlib import Path

import pandas as pd

# ZenML imports (Week 2, Day 5)
try:
    from zenml import step

    ZENML_AVAILABLE = True
except ImportError:
    # Fallback if ZenML not installed
    def step(func):
        return func

    ZENML_AVAILABLE = False

logger = logging.getLogger(__name__)


@step
def collect_data_step() -> str:
    """
    Collect latest card prices from Pokémon Price Tracker API.

    Returns:
        Path to collected data file
    """
    logger.info("Collecting data from API...")

    # Run data collection via subprocess to use existing code
    import subprocess

    result = subprocess.run(
        ["python", "-m", "pokewatch.data.collectors.daily_price_collector"],
        capture_output=True,
        text=True,
        check=True,
    )

    logger.info("Data collection output:")
    logger.info(result.stdout)

    # Find latest parquet file
    from pokewatch.config import get_data_path

    raw_dir = get_data_path("raw")

    parquet_files = list(raw_dir.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError("No data collected")

    latest_file = max(parquet_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Data collected: {latest_file}")

    return str(latest_file)


@step
def preprocess_data_step(raw_data_path: str) -> str:
    """
    Transform raw data into features for modeling.

    Args:
        raw_data_path: Path to raw data file

    Returns:
        Path to processed features file
    """
    logger.info(f"Preprocessing data from: {raw_data_path}")

    # Run preprocessing
    import subprocess

    result = subprocess.run(
        ["python", "-m", "pokewatch.data.preprocessing.make_features"],
        capture_output=True,
        text=True,
        check=True,
    )

    logger.info("Preprocessing output:")
    logger.info(result.stdout)

    # Get processed file path
    from pokewatch.config import get_data_path
    from pokewatch.data.collectors.daily_price_collector import load_cards_config

    cards_config = load_cards_config()
    set_name = cards_config["set"]["name"]
    safe_set_name = set_name.lower().replace(" ", "_").replace(":", "").replace("-", "_")
    safe_set_name = "".join(c for c in safe_set_name if c.isalnum() or c == "_")

    processed_file = get_data_path("processed") / f"{safe_set_name}.parquet"

    if not processed_file.exists():
        raise FileNotFoundError(f"Processed data not found: {processed_file}")

    logger.info(f"Features processed: {processed_file}")

    return str(processed_file)


@step
def train_model_step(features_path: str) -> Tuple[str, dict]:
    """
    Train baseline model on features.

    Args:
        features_path: Path to features file

    Returns:
        Tuple of (model_path, metrics_dict)
    """
    logger.info(f"Training model on: {features_path}")

    # Load features
    features_df = pd.read_parquet(features_path)

    from pokewatch.models.baseline import BaselineFairPriceModel

    model = BaselineFairPriceModel(features_df)

    logger.info(f"Model trained with {len(model.get_all_card_ids())} cards")

    # Calculate metrics
    from pokewatch.models.train_baseline import calculate_metrics
    from pokewatch.core.decision_rules import DecisionConfig
    from pokewatch.config import get_settings

    settings = get_settings()
    decision_cfg = DecisionConfig(
        buy_threshold_pct=settings.model.default_buy_threshold_pct,
        sell_threshold_pct=settings.model.default_sell_threshold_pct,
    )

    metrics = calculate_metrics(features_df, model, decision_cfg)

    logger.info(
        f"Model metrics: MAPE={metrics['mape']:.2f}, Coverage={metrics['coverage_rate']:.2%}"
    )

    # Save model artifacts
    project_root = Path(__file__).parent.parent
    models_dir = project_root / "models" / "baseline"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Save metadata
    from datetime import datetime
    import json
    import shutil

    shutil.copy2(features_path, models_dir / Path(features_path).name)

    metadata = {
        "model_type": "baseline_moving_average",
        "window_size": 3,
        "trained_at": datetime.now().isoformat(),
        "metrics": {
            "rmse": float(metrics["rmse"]),
            "mape": float(metrics["mape"]),
            "coverage_rate": float(metrics["coverage_rate"]),
        },
        "thresholds": {
            "buy_threshold_pct": decision_cfg.buy_threshold_pct,
            "sell_threshold_pct": decision_cfg.sell_threshold_pct,
        },
    }

    metadata_path = models_dir / "model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Model saved to: {models_dir}")

    return str(models_dir), metrics


@step
def validate_model_step(metrics: dict) -> bool:
    """
    Validate model meets quality thresholds.

    Args:
        metrics: Model evaluation metrics

    Returns:
        True if model is valid, False otherwise
    """
    logger.info("Validating model...")

    MAPE_THRESHOLD = 20.0  # Relaxed for baseline model
    COVERAGE_THRESHOLD = 0.80

    is_valid = metrics["mape"] <= MAPE_THRESHOLD and metrics["coverage_rate"] >= COVERAGE_THRESHOLD

    if is_valid:
        logger.info(
            f"✓ Model valid: MAPE={metrics['mape']:.2f} ≤ {MAPE_THRESHOLD}, Coverage={metrics['coverage_rate']:.2%} ≥ {COVERAGE_THRESHOLD:.0%}"
        )
    else:
        logger.warning(
            f"✗ Model invalid: MAPE={metrics['mape']:.2f} > {MAPE_THRESHOLD} or Coverage={metrics['coverage_rate']:.2%} < {COVERAGE_THRESHOLD:.0%}"
        )

    return is_valid


@step
def build_bento_step(model_path: str, is_valid: bool) -> str:
    """
    Build BentoML service with the trained model.

    Args:
        model_path: Path to model artifacts
        is_valid: Whether model passed validation

    Returns:
        Bento tag (name:version)
    """
    if not is_valid:
        raise ValueError("Model validation failed, skipping Bento build")

    logger.info("Building BentoML service...")

    import subprocess

    # Run build script
    result = subprocess.run(
        ["./scripts/build_bento.sh"],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(Path(__file__).parent.parent),
    )

    logger.info(result.stdout)

    # Try to extract tag from build output first (most reliable)
    import re

    tag_match = re.search(r"pokewatch_service:([a-zA-Z0-9_-]+)", result.stdout)
    if tag_match:
        bento_tag = f"pokewatch_service:{tag_match.group(1)}"
        logger.info(f"✓ Built Bento (from output): {bento_tag}")
        return bento_tag

    # Fallback: Use BentoML Python API to get latest Bento
    try:
        import bentoml

        bentos = bentoml.list()
        if bentos:
            # Get the most recent Bento
            latest_bento = bentos[0]
            # BentoML API returns Bento objects with .tag property
            bento_tag = str(latest_bento.tag)
            logger.info(f"✓ Built Bento (from API): {bento_tag}")
            return bento_tag
    except Exception as e:
        logger.warning(f"Failed to get Bento from Python API: {e}")

    # Last resort: try CLI list command and parse output
    import shutil

    if shutil.which("uv"):
        result = subprocess.run(
            ["uv", "run", "bentoml", "list"], capture_output=True, text=True, check=False
        )
    else:
        result = subprocess.run(["bentoml", "list"], capture_output=True, text=True, check=False)

    if result.returncode == 0 and result.stdout:
        # Parse tag from table output (format: "pokewatch_service:xxxxx")
        tag_match = re.search(r"pokewatch_service:([a-zA-Z0-9_-]+)", result.stdout)
        if tag_match:
            bento_tag = f"pokewatch_service:{tag_match.group(1)}"
            logger.info(f"✓ Built Bento (from CLI): {bento_tag}")
            return bento_tag

    # If all else fails, use default latest tag
    logger.warning("Could not determine Bento tag from build output, using 'latest'")
    return "pokewatch_service:latest"
