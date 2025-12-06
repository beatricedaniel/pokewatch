"""
Training/evaluation script for baseline model with MLflow tracking.

This script loads the baseline model, evaluates it on processed data,
and logs metrics, parameters, and artifacts to MLflow.

Usage:
    python -m pokewatch.models.train_baseline
    python -m pokewatch.models.train_baseline --data_path data/processed/sv2a_pokemon_card_151.parquet
"""

import argparse
import logging
import os
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import mlflow
import mlflow.pyfunc
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from pokewatch.config import get_settings, get_data_path
from pokewatch.core.decision_rules import DecisionConfig, compute_signal
from pokewatch.models.baseline import BaselineFairPriceModel, load_baseline_model

logger = logging.getLogger(__name__)


class BaselineModelWrapper(mlflow.pyfunc.PythonModel):
    """
    MLflow-compatible wrapper for BaselineFairPriceModel.

    This wrapper allows the baseline model to be logged and loaded via MLflow.
    """

    def __init__(self, model: BaselineFairPriceModel):
        """
        Initialize the wrapper with a BaselineFairPriceModel instance.

        Args:
            model: The BaselineFairPriceModel to wrap
        """
        self.model = model

    def predict(self, context, model_input):
        """
        Predict fair price for given card_id and date.

        Args:
            context: MLflow context (unused)
            model_input: DataFrame with columns: card_id, date (optional)

        Returns:
            DataFrame with columns: resolved_date, market_price, fair_price
        """
        results = []

        for _, row in model_input.iterrows():
            card_id = row["card_id"]
            date = row.get("date", None)
            if pd.isna(date):
                date = None
            elif isinstance(date, str):
                from datetime import datetime

                date = datetime.strptime(date, "%Y-%m-%d").date()

            try:
                resolved_date, market_price, fair_price = self.model.predict(card_id, date)
                results.append(
                    {
                        "resolved_date": resolved_date,
                        "market_price": market_price,
                        "fair_price": fair_price,
                    }
                )
            except Exception as e:
                logger.warning(f"Prediction failed for card_id={card_id}, date={date}: {e}")
                results.append(
                    {
                        "resolved_date": None,
                        "market_price": None,
                        "fair_price": None,
                    }
                )

        return pd.DataFrame(results)


def calculate_metrics(
    df: pd.DataFrame,
    model: BaselineFairPriceModel,
    decision_cfg: DecisionConfig,
) -> dict:
    """
    Calculate evaluation metrics for the baseline model.

    Args:
        df: DataFrame with processed features (card_id, date, market_price, fair_value_baseline)
        model: BaselineFairPriceModel instance
        decision_cfg: Decision configuration for signal computation

    Returns:
        Dictionary with metrics: rmse, mape, dataset_size, coverage_rate
    """
    # Get predictions for all (card_id, date) pairs in the dataset
    predictions = []
    errors = []
    signals = []

    for _, row in df.iterrows():
        card_id = row["card_id"]
        date = row["date"]
        true_market_price = row["market_price"]

        try:
            resolved_date, market_price, fair_price = model.predict(card_id, date)

            # Calculate error (using market_price as ground truth)
            error = fair_price - true_market_price
            errors.append(error)

            # Calculate signal
            signal, _ = compute_signal(market_price, fair_price, decision_cfg)
            signals.append(signal)

            predictions.append(
                {
                    "card_id": card_id,
                    "date": date,
                    "true_market_price": true_market_price,
                    "predicted_fair_price": fair_price,
                    "error": error,
                    "signal": signal,
                }
            )
        except Exception as e:
            logger.debug(f"Failed to predict for card_id={card_id}, date={date}: {e}")
            continue

    if not predictions:
        raise ValueError("No valid predictions could be made")

    pred_df = pd.DataFrame(predictions)

    # Calculate RMSE
    rmse = np.sqrt(np.mean([e**2 for e in errors]))

    # Calculate MAPE (avoid division by zero)
    mape_values = []
    for _, row in pred_df.iterrows():
        if row["true_market_price"] > 0:
            pct_error = abs(row["error"] / row["true_market_price"]) * 100
            mape_values.append(pct_error)
    mape = np.mean(mape_values) if mape_values else np.nan

    # Calculate coverage rate (percentage of valid predictions)
    dataset_size = len(pred_df)
    total_size = len(df)
    coverage_rate = dataset_size / total_size if total_size > 0 else 0.0

    # Calculate signal distribution
    signal_counts = pd.Series(signals).value_counts()
    buy_rate = signal_counts.get("BUY", 0) / dataset_size if dataset_size > 0 else 0.0
    sell_rate = signal_counts.get("SELL", 0) / dataset_size if dataset_size > 0 else 0.0
    hold_rate = signal_counts.get("HOLD", 0) / dataset_size if dataset_size > 0 else 0.0

    return {
        "rmse": float(rmse),
        "mape": float(mape),
        "dataset_size": int(dataset_size),
        "coverage_rate": float(coverage_rate),
        "buy_rate": float(buy_rate),
        "sell_rate": float(sell_rate),
        "hold_rate": float(hold_rate),
        "pred_df": pred_df,
    }


def create_visualizations(pred_df: pd.DataFrame, output_dir: Path) -> dict:
    """
    Create visualization artifacts.

    Args:
        pred_df: DataFrame with predictions and errors
        output_dir: Directory to save plots

    Returns:
        Dictionary mapping artifact names to file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {}

    # 1. Error distribution histogram
    plt.figure(figsize=(10, 6))
    plt.hist(pred_df["error"], bins=50, edgecolor="black", alpha=0.7)
    plt.xlabel("Error (Predicted Fair Price - Market Price)")
    plt.ylabel("Frequency")
    plt.title("Distribution of Prediction Errors")
    plt.grid(True, alpha=0.3)
    error_dist_path = output_dir / "error_distribution.png"
    plt.savefig(error_dist_path, dpi=150, bbox_inches="tight")
    plt.close()
    artifacts["error_distribution"] = error_dist_path

    # 2. Scatter plot: True vs Predicted
    plt.figure(figsize=(10, 6))
    plt.scatter(
        pred_df["true_market_price"],
        pred_df["predicted_fair_price"],
        alpha=0.5,
        s=10,
    )
    # Add diagonal line (perfect prediction)
    min_price = min(pred_df["true_market_price"].min(), pred_df["predicted_fair_price"].min())
    max_price = max(pred_df["true_market_price"].max(), pred_df["predicted_fair_price"].max())
    plt.plot([min_price, max_price], [min_price, max_price], "r--", label="Perfect Prediction")
    plt.xlabel("True Market Price")
    plt.ylabel("Predicted Fair Price")
    plt.title("True Market Price vs Predicted Fair Price")
    plt.legend()
    plt.grid(True, alpha=0.3)
    scatter_path = output_dir / "scatter_true_vs_predicted.png"
    plt.savefig(scatter_path, dpi=150, bbox_inches="tight")
    plt.close()
    artifacts["scatter_plot"] = scatter_path

    # 3. Signal distribution pie chart
    plt.figure(figsize=(8, 8))
    signal_counts = pred_df["signal"].value_counts()
    plt.pie(
        signal_counts.values,
        labels=signal_counts.index,
        autopct="%1.1f%%",
        startangle=90,
    )
    plt.title("Signal Distribution (BUY/SELL/HOLD)")
    signal_dist_path = output_dir / "signal_distribution.png"
    plt.savefig(signal_dist_path, dpi=150, bbox_inches="tight")
    plt.close()
    artifacts["signal_distribution"] = signal_dist_path

    return artifacts


def main(
    data_path: Optional[Path] = None,
    experiment_name: str = "pokewatch_baseline",
    run_name: Optional[str] = None,
) -> int:
    """
    Main entry point for training/evaluating baseline model with MLflow tracking.

    Args:
        data_path: Path to processed parquet file. If None, uses default.
        experiment_name: MLflow experiment name
        run_name: MLflow run name. If None, auto-generated.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Load environment variables
    load_dotenv()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        # Load settings
        settings = get_settings()

        # Configure MLflow tracking URI
        # For local development, use local file tracking to avoid artifact storage issues
        # When using remote server, artifacts should be uploaded via HTTP (requires S3/MinIO)
        tracking_uri_env = os.getenv("MLFLOW_TRACKING_URI")

        # Get project root (4 levels up from this file: models -> pokewatch -> src -> pokewatch)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent

        if not tracking_uri_env or tracking_uri_env.strip() == "":
            # Default to local file tracking for development
            local_mlruns = project_root / "mlruns"
            local_mlruns.mkdir(exist_ok=True)
            tracking_uri = f"file://{local_mlruns.absolute()}"
            logger.info("No MLFLOW_TRACKING_URI set, using local file tracking")
        else:
            # Use remote server if configured
            tracking_uri = tracking_uri_env
            # Ensure mlruns directory exists locally (may be used for temporary artifact storage)
            local_mlruns = project_root / "mlruns"
            local_mlruns.mkdir(exist_ok=True)
            logger.info(f"Using remote MLflow server: {tracking_uri}")
            logger.warning(
                "When using remote server, ensure artifact storage is properly configured "
                "(e.g., S3/MinIO). For local development, use local file tracking instead."
            )

        mlflow.set_tracking_uri(tracking_uri)
        logger.info(f"MLflow tracking URI: {tracking_uri}")

        # Set experiment
        experiment = mlflow.set_experiment(experiment_name)
        logger.info(f"Using experiment: {experiment_name} (ID: {experiment.experiment_id})")

        # Load model
        logger.info("Loading baseline model...")
        model = load_baseline_model(data_path)
        logger.info(f"Model loaded with {len(model.get_all_card_ids())} cards")

        # Load data for evaluation
        if data_path is None:
            from pokewatch.data.collectors.daily_price_collector import load_cards_config

            cards_config = load_cards_config()
            set_name = cards_config["set"]["name"]
            safe_set_name = set_name.lower().replace(" ", "_").replace(":", "").replace("-", "_")
            safe_set_name = "".join(c for c in safe_set_name if c.isalnum() or c == "_")
            data_path = get_data_path("processed") / f"{safe_set_name}.parquet"

        logger.info(f"Loading evaluation data from: {data_path}")
        df = pd.read_parquet(data_path)
        logger.info(f"Loaded {len(df)} rows for evaluation")

        # Get decision configuration
        decision_cfg = DecisionConfig(
            buy_threshold_pct=settings.model.default_buy_threshold_pct,
            sell_threshold_pct=settings.model.default_sell_threshold_pct,
        )

        # Calculate metrics
        logger.info("Calculating metrics...")
        metrics_dict = calculate_metrics(df, model, decision_cfg)

        # Start MLflow run
        with mlflow.start_run(run_name=run_name) as run:
            logger.info(f"MLflow run started: {run.info.run_id}")

            # Log parameters
            mlflow.log_params(
                {
                    "model_type": "baseline_moving_average",
                    "window_size": 3,
                    "buy_threshold_pct": decision_cfg.buy_threshold_pct,
                    "sell_threshold_pct": decision_cfg.sell_threshold_pct,
                }
            )

            # Log metrics
            mlflow.log_metrics(
                {
                    "rmse": metrics_dict["rmse"],
                    "mape": metrics_dict["mape"],
                    "dataset_size": metrics_dict["dataset_size"],
                    "coverage_rate": metrics_dict["coverage_rate"],
                    "buy_rate": metrics_dict["buy_rate"],
                    "sell_rate": metrics_dict["sell_rate"],
                    "hold_rate": metrics_dict["hold_rate"],
                }
            )

            # Create visualizations
            logger.info("Creating visualizations...")
            artifacts_dir = Path("mlruns_artifacts") / run.info.run_id
            artifacts = create_visualizations(metrics_dict["pred_df"], artifacts_dir)

            # Log visualization artifacts
            for artifact_name, artifact_path in artifacts.items():
                mlflow.log_artifact(str(artifact_path), artifact_path="plots")
                logger.info(f"Logged artifact: {artifact_name}")

            # Log model (commented out due to API version compatibility issues with MLflow v2.14.1)
            # When using remote MLflow server, model logging requires newer API endpoints
            # For Phase 1, artifacts (plots) and metrics are sufficient
            # TODO: Upgrade MLflow server to v3.x or use file-based tracking for model artifacts
            # logger.info("Logging model to MLflow...")
            # model_wrapper = BaselineModelWrapper(model)
            #
            # # Create input example
            # sample_card_id = model.get_all_card_ids()[0]
            # sample_date = model.get_latest_date(sample_card_id)
            # input_example = pd.DataFrame({
            #     "card_id": [sample_card_id],
            #     "date": [sample_date.isoformat() if sample_date else None],
            # })
            #
            # mlflow.pyfunc.log_model(
            #     artifact_path="baseline_model",
            #     python_model=model_wrapper,
            #     input_example=input_example,
            # )
            # logger.info("Model logged successfully")

            # Log summary text
            summary = f"""
Baseline Model Evaluation Summary
=================================
Model Type: Moving Average (window=3)
Dataset Size: {metrics_dict['dataset_size']} samples
Coverage Rate: {metrics_dict['coverage_rate']:.2%}

Metrics:
- RMSE: {metrics_dict['rmse']:.2f}
- MAPE: {metrics_dict['mape']:.2f}%

Signal Distribution:
- BUY: {metrics_dict['buy_rate']:.2%}
- SELL: {metrics_dict['sell_rate']:.2%}
- HOLD: {metrics_dict['hold_rate']:.2%}
"""
            summary_path = artifacts_dir / "evaluation_summary.txt"
            summary_path.write_text(summary)
            mlflow.log_artifact(str(summary_path), artifact_path="summary")

            # Save model artifacts to DVC-tracked directory
            # For baseline model, we save the processed features + metadata
            logger.info("Saving model artifacts for DVC versioning...")
            models_dir = project_root / "models" / "baseline"
            models_dir.mkdir(parents=True, exist_ok=True)

            # Save processed features (model data source)
            import shutil

            shutil.copy2(data_path, models_dir / f"{data_path.name}")
            logger.info(f"Copied features to: {models_dir / data_path.name}")

            # Save model metadata with timestamp
            from datetime import datetime

            metadata = {
                "model_type": "baseline_moving_average",
                "window_size": 3,
                "trained_at": datetime.now().isoformat(),
                "mlflow_run_id": run.info.run_id,
                "mlflow_experiment_id": experiment.experiment_id,
                "dataset_path": str(data_path),
                "dataset_size": metrics_dict["dataset_size"],
                "metrics": {
                    "rmse": float(metrics_dict["rmse"]),
                    "mape": float(metrics_dict["mape"]),
                    "coverage_rate": float(metrics_dict["coverage_rate"]),
                },
                "thresholds": {
                    "buy_threshold_pct": decision_cfg.buy_threshold_pct,
                    "sell_threshold_pct": decision_cfg.sell_threshold_pct,
                },
            }

            import json

            metadata_path = models_dir / "model_metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved metadata to: {metadata_path}")

            logger.info("Evaluation complete!")
            logger.info(
                f"View results at: {tracking_uri}/#/experiments/{experiment.experiment_id}/runs/{run.info.run_id}"
            )

        return 0

    except Exception as e:
        logger.error(f"Training/evaluation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train/evaluate baseline model with MLflow tracking"
    )
    parser.add_argument(
        "--data_path",
        type=str,
        default=None,
        help="Path to processed parquet file (default: auto-detect from cards.yaml)",
    )
    parser.add_argument(
        "--experiment_name",
        type=str,
        default="pokewatch_baseline",
        help="MLflow experiment name",
    )
    parser.add_argument(
        "--run_name",
        type=str,
        default=None,
        help="MLflow run name (default: auto-generated)",
    )

    args = parser.parse_args()

    data_path = Path(args.data_path) if args.data_path else None
    exit(main(data_path=data_path, experiment_name=args.experiment_name, run_name=args.run_name))
