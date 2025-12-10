"""Drift detection module using Evidently.

This module provides functionality to detect data drift and prediction drift
in the PokeWatch price prediction system.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
from evidently.metrics import (
    DatasetDriftMetric,
    DataDriftTable,
    ColumnDriftMetric,
)

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detect data and prediction drift using Evidently.

    This class compares reference data (historical baseline) against
    current data to detect significant distribution changes.
    """

    def __init__(
        self,
        drift_threshold: float = 0.1,
        report_dir: str = "data/drift_reports",
    ):
        """Initialize drift detector.

        Args:
            drift_threshold: Threshold for drift detection (0.0-1.0).
                            Values above this indicate drift.
            report_dir: Directory to save drift reports.
        """
        self.drift_threshold = drift_threshold
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def detect_data_drift(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        numerical_features: Optional[list[str]] = None,
    ) -> dict:
        """Detect drift in input data distributions.

        Args:
            reference_data: Historical baseline data (e.g., last 30 days)
            current_data: Recent data to compare (e.g., last 7 days)
            numerical_features: List of numerical columns to check for drift.
                               If None, uses ['market_price', 'fair_price']

        Returns:
            Dictionary with drift detection results:
            - is_drift: Whether drift was detected
            - drift_score: Overall drift score
            - drifted_columns: List of columns with drift
            - report_path: Path to HTML report
        """
        if numerical_features is None:
            numerical_features = ["market_price", "fair_price"]

        # Ensure columns exist
        available_features = [
            f
            for f in numerical_features
            if f in reference_data.columns and f in current_data.columns
        ]

        if not available_features:
            logger.warning("No valid features found for drift detection")
            return {
                "is_drift": False,
                "drift_score": 0.0,
                "drifted_columns": [],
                "report_path": None,
            }

        # Create column mapping
        column_mapping = ColumnMapping(
            numerical_features=available_features,
        )

        # Create drift report
        report = Report(
            metrics=[
                DatasetDriftMetric(),
                DataDriftTable(),
            ]
        )

        try:
            report.run(
                reference_data=reference_data[available_features],
                current_data=current_data[available_features],
                column_mapping=column_mapping,
            )

            # Extract results
            result = report.as_dict()
            metrics = result.get("metrics", [])

            # Get dataset drift metric
            dataset_drift = None
            drift_by_column = {}

            for metric in metrics:
                metric_id = metric.get("metric", "")
                metric_result = metric.get("result", {})

                if "DatasetDriftMetric" in metric_id:
                    dataset_drift = metric_result
                elif "DataDriftTable" in metric_id:
                    drift_by_column = metric_result.get("drift_by_columns", {})

            # Determine if drift detected
            is_drift = False
            drift_score = 0.0
            drifted_columns = []

            if dataset_drift:
                drift_score = dataset_drift.get("share_of_drifted_columns", 0.0)
                is_drift = drift_score > self.drift_threshold

            for col, col_data in drift_by_column.items():
                if col_data.get("drift_detected", False):
                    drifted_columns.append(col)

            # Save HTML report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.report_dir / f"data_drift_{timestamp}.html"
            report.save_html(str(report_path))

            logger.info(
                f"Data drift detection complete. "
                f"Drift detected: {is_drift}, Score: {drift_score:.2%}, "
                f"Drifted columns: {drifted_columns}"
            )

            return {
                "is_drift": is_drift,
                "drift_score": drift_score,
                "drifted_columns": drifted_columns,
                "report_path": str(report_path),
            }

        except Exception as e:
            logger.error(f"Error during drift detection: {e}", exc_info=True)
            return {
                "is_drift": False,
                "drift_score": 0.0,
                "drifted_columns": [],
                "report_path": None,
                "error": str(e),
            }

    def detect_prediction_drift(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        prediction_column: str = "fair_price",
    ) -> dict:
        """Detect drift in model predictions.

        Args:
            reference_data: Historical predictions
            current_data: Recent predictions
            prediction_column: Column name for predictions

        Returns:
            Dictionary with drift detection results
        """
        if prediction_column not in reference_data.columns:
            logger.warning(f"Column {prediction_column} not found in reference data")
            return {
                "is_drift": False,
                "drift_score": 0.0,
                "report_path": None,
            }

        if prediction_column not in current_data.columns:
            logger.warning(f"Column {prediction_column} not found in current data")
            return {
                "is_drift": False,
                "drift_score": 0.0,
                "report_path": None,
            }

        # Create column mapping for prediction drift
        column_mapping = ColumnMapping(
            prediction=prediction_column,
        )

        # Create prediction drift report
        report = Report(
            metrics=[
                ColumnDriftMetric(column_name=prediction_column),
            ]
        )

        try:
            report.run(
                reference_data=reference_data[[prediction_column]],
                current_data=current_data[[prediction_column]],
                column_mapping=column_mapping,
            )

            # Extract results
            result = report.as_dict()
            metrics = result.get("metrics", [])

            is_drift = False
            drift_score = 0.0

            for metric in metrics:
                metric_result = metric.get("result", {})
                is_drift = metric_result.get("drift_detected", False)
                drift_score = metric_result.get("drift_score", 0.0)

            # Save HTML report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.report_dir / f"prediction_drift_{timestamp}.html"
            report.save_html(str(report_path))

            logger.info(
                f"Prediction drift detection complete. "
                f"Drift detected: {is_drift}, Score: {drift_score:.4f}"
            )

            return {
                "is_drift": is_drift,
                "drift_score": drift_score,
                "report_path": str(report_path),
            }

        except Exception as e:
            logger.error(f"Error during prediction drift detection: {e}", exc_info=True)
            return {
                "is_drift": False,
                "drift_score": 0.0,
                "report_path": None,
                "error": str(e),
            }

    def generate_full_report(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        numerical_features: Optional[list[str]] = None,
    ) -> dict:
        """Generate a comprehensive drift report.

        Args:
            reference_data: Historical baseline data
            current_data: Recent data to compare
            numerical_features: Numerical columns to analyze

        Returns:
            Dictionary with full drift analysis results
        """
        if numerical_features is None:
            numerical_features = ["market_price", "fair_price"]

        available_features = [
            f
            for f in numerical_features
            if f in reference_data.columns and f in current_data.columns
        ]

        if not available_features:
            logger.warning("No valid features for full report")
            return {"error": "No valid features found"}

        column_mapping = ColumnMapping(
            numerical_features=available_features,
        )

        # Create comprehensive report with presets
        report = Report(
            metrics=[
                DataDriftPreset(),
            ]
        )

        try:
            report.run(
                reference_data=reference_data[available_features],
                current_data=current_data[available_features],
                column_mapping=column_mapping,
            )

            # Save HTML report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.report_dir / f"full_drift_report_{timestamp}.html"
            report.save_html(str(report_path))

            # Get JSON results
            result = report.as_dict()

            logger.info(f"Full drift report saved to {report_path}")

            return {
                "report_path": str(report_path),
                "metrics": result.get("metrics", []),
                "timestamp": timestamp,
            }

        except Exception as e:
            logger.error(f"Error generating full report: {e}", exc_info=True)
            return {"error": str(e)}


def run_drift_detection(
    reference_path: str,
    current_path: str,
    drift_threshold: float = 0.1,
    report_dir: str = "data/drift_reports",
) -> dict:
    """Run drift detection from file paths.

    Convenience function to run drift detection on parquet files.

    Args:
        reference_path: Path to reference data parquet file
        current_path: Path to current data parquet file
        drift_threshold: Threshold for drift detection
        report_dir: Directory for reports

    Returns:
        Combined drift detection results
    """
    try:
        reference_data = pd.read_parquet(reference_path)
        current_data = pd.read_parquet(current_path)
    except Exception as e:
        logger.error(f"Error loading data files: {e}")
        return {"error": f"Failed to load data: {e}"}

    detector = DriftDetector(
        drift_threshold=drift_threshold,
        report_dir=report_dir,
    )

    # Run both drift detection types
    data_drift = detector.detect_data_drift(reference_data, current_data)
    prediction_drift = detector.detect_prediction_drift(reference_data, current_data)

    return {
        "data_drift": data_drift,
        "prediction_drift": prediction_drift,
        "overall_drift_detected": data_drift["is_drift"] or prediction_drift["is_drift"],
    }


if __name__ == "__main__":
    # Example usage
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) >= 3:
        reference_path = sys.argv[1]
        current_path = sys.argv[2]
        results = run_drift_detection(reference_path, current_path)
        print("\nDrift Detection Results:")
        print(f"  Data drift detected: {results['data_drift']['is_drift']}")
        print(f"  Prediction drift detected: {results['prediction_drift']['is_drift']}")
        print(f"  Overall drift: {results['overall_drift_detected']}")
    else:
        print("Usage: python drift_detector.py <reference.parquet> <current.parquet>")
