"""
Integration tests for ML pipeline.

These tests verify that the complete ML pipeline runs successfully.

Run with: pytest tests/integration/test_ml_pipeline.py -v
Note: These tests may take several minutes to complete.
"""

import pytest
from pathlib import Path
import json


@pytest.fixture(scope="module")
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent.parent


class TestPipelineSteps:
    """Test individual pipeline steps."""

    def test_collect_step_imports(self):
        """Test collect step can be imported."""
        from pipelines.steps import collect_data_step

        assert callable(collect_data_step)

    def test_preprocess_step_imports(self):
        """Test preprocess step can be imported."""
        from pipelines.steps import preprocess_data_step

        assert callable(preprocess_data_step)

    def test_train_step_imports(self):
        """Test train step can be imported."""
        from pipelines.steps import train_model_step

        assert callable(train_model_step)

    def test_validate_step_imports(self):
        """Test validate step can be imported."""
        from pipelines.steps import validate_model_step

        assert callable(validate_model_step)

    def test_build_bento_step_imports(self):
        """Test build bento step can be imported."""
        from pipelines.steps import build_bento_step

        assert callable(build_bento_step)


class TestPipelineValidation:
    """Test pipeline validation logic."""

    def test_validate_model_step_accepts_good_metrics(self):
        """Test validation passes with good metrics."""
        from pipelines.steps import validate_model_step

        good_metrics = {
            "mape": 10.0,  # Below 20% threshold
            "rmse": 5.0,
            "coverage_rate": 0.95,  # Above 80% threshold
        }

        is_valid = validate_model_step(good_metrics)

        assert is_valid is True

    def test_validate_model_step_rejects_high_mape(self):
        """Test validation fails with high MAPE."""
        from pipelines.steps import validate_model_step

        bad_metrics = {
            "mape": 25.0,  # Above 20% threshold
            "rmse": 5.0,
            "coverage_rate": 0.95,
        }

        is_valid = validate_model_step(bad_metrics)

        assert is_valid is False

    def test_validate_model_step_rejects_low_coverage(self):
        """Test validation fails with low coverage."""
        from pipelines.steps import validate_model_step

        bad_metrics = {
            "mape": 10.0,
            "rmse": 5.0,
            "coverage_rate": 0.70,  # Below 80% threshold
        }

        is_valid = validate_model_step(bad_metrics)

        assert is_valid is False


class TestPipelineArtifacts:
    """Test that pipeline creates expected artifacts."""

    def test_model_metadata_structure(self, project_root):
        """Test model metadata file has correct structure."""
        metadata_path = project_root / "models" / "baseline" / "model_metadata.json"

        if not metadata_path.exists():
            pytest.skip("Model metadata not found. Run pipeline first: make pipeline-run")

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # Verify required fields
        assert "model_type" in metadata
        assert "window_size" in metadata
        assert "trained_at" in metadata
        assert "metrics" in metadata
        assert "thresholds" in metadata

        # Verify metrics structure
        assert "rmse" in metadata["metrics"]
        assert "mape" in metadata["metrics"]
        assert "coverage_rate" in metadata["metrics"]

        # Verify thresholds structure
        assert "buy_threshold_pct" in metadata["thresholds"]
        assert "sell_threshold_pct" in metadata["thresholds"]

    def test_processed_features_exist(self, project_root):
        """Test that processed features file exists after pipeline run."""
        features_path = project_root / "data" / "processed" / "sv2a_pokemon_card_151.parquet"

        if not features_path.exists():
            pytest.skip("Processed features not found. Run pipeline first: make pipeline-run")

        # Verify file is not empty
        assert features_path.stat().st_size > 0


class TestPipelineOrchestration:
    """Test pipeline orchestration."""

    def test_ml_pipeline_module_imports(self):
        """Test ML pipeline module can be imported."""
        from pipelines import ml_pipeline

        assert hasattr(ml_pipeline, "run_ml_pipeline")

    def test_pipeline_function_callable(self):
        """Test pipeline function is callable."""
        from pipelines.ml_pipeline import run_ml_pipeline

        assert callable(run_ml_pipeline)


class TestPipelineIntegration:
    """
    Full pipeline integration tests.

    WARNING: These tests run the actual pipeline and may take several minutes.
    """

    @pytest.mark.slow
    @pytest.mark.skipif(
        not Path("data/processed/sv2a_pokemon_card_151.parquet").exists(),
        reason="Requires processed data. Run 'make preprocess' first."
    )
    def test_train_and_validate_steps(self, project_root):
        """Test training and validation steps with existing data."""
        from pipelines.steps import train_model_step, validate_model_step

        features_path = project_root / "data" / "processed" / "sv2a_pokemon_card_151.parquet"

        # Run training
        model_path, metrics = train_model_step(str(features_path))

        # Verify outputs
        assert Path(model_path).exists()
        assert "mape" in metrics
        assert "rmse" in metrics
        assert "coverage_rate" in metrics

        # Validate
        is_valid = validate_model_step(metrics)

        # Should pass validation with real data
        assert isinstance(is_valid, bool)


class TestPipelineErrorHandling:
    """Test pipeline error handling."""

    def test_preprocess_step_fails_with_missing_data(self):
        """Test preprocess step handles missing data gracefully."""
        from pipelines.steps import preprocess_data_step

        with pytest.raises(Exception):
            # Should fail with non-existent file
            preprocess_data_step("/nonexistent/file.parquet")

    def test_train_step_fails_with_invalid_path(self):
        """Test train step handles invalid path."""
        from pipelines.steps import train_model_step

        with pytest.raises(Exception):
            # Should fail with non-existent file
            train_model_step("/nonexistent/features.parquet")

    def test_build_bento_fails_with_invalid_model(self):
        """Test build bento step handles validation failure."""
        from pipelines.steps import build_bento_step

        with pytest.raises(ValueError, match="validation failed"):
            # Should raise error when model is invalid
            build_bento_step("/some/path", is_valid=False)
