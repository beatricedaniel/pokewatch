"""
ML pipeline for PokeWatch - Week 2, Day 5: ZenML integration.

This pipeline can be run in two modes:
1. With ZenML: Automatic tracking, artifacts, and experiment logging
2. Without ZenML: Simple orchestration (fallback)
"""

import logging

# ZenML imports (Week 2, Day 5)
try:
    from zenml import pipeline

    ZENML_AVAILABLE = True
except ImportError:
    # Fallback if ZenML not installed
    def pipeline(func):
        return func

    ZENML_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pipeline(enable_cache=True)
def pokewatch_training_pipeline():
    """
    Execute the complete ML pipeline with ZenML tracking.

    Steps:
        1. Collect data from API
        2. Preprocess and engineer features
        3. Train baseline model
        4. Validate model quality
        5. Build BentoML service (if valid)

    Returns:
        Bento tag if successful, None otherwise
    """
    # Import steps
    from pipelines.steps import (
        collect_data_step,
        preprocess_data_step,
        train_model_step,
        validate_model_step,
        build_bento_step,
    )

    # Step 1: Collect data
    raw_data_path = collect_data_step()

    # Step 2: Preprocess
    features_path = preprocess_data_step(raw_data_path)

    # Step 3: Train model
    model_path, metrics = train_model_step(features_path)

    # Step 4: Validate
    is_valid = validate_model_step(metrics)

    # Step 5: Build Bento (only if valid)
    bento_tag = build_bento_step(model_path, is_valid)

    return bento_tag


if __name__ == "__main__":
    # Run the pipeline
    result = pokewatch_training_pipeline()

    # Exit with appropriate code
    exit(0 if result else 1)
