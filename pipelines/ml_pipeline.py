"""
ML pipeline for PokeWatch - Simple implementation without ZenML dependency.

This can be run directly with Python or integrated with ZenML later.
For now, it's a simple orchestration script that chains the steps together.
"""

import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_ml_pipeline():
    """
    Execute the complete ML pipeline.

    Steps:
        1. Collect data from API
        2. Preprocess and engineer features
        3. Train baseline model
        4. Validate model quality
        5. Build BentoML service (if valid)

    Returns:
        Bento tag if successful, None otherwise
    """
    logger.info("=" * 60)
    logger.info("Starting PokeWatch ML Pipeline")
    logger.info("=" * 60)

    try:
        # Import steps
        from pipelines.steps import (
            collect_data_step,
            preprocess_data_step,
            train_model_step,
            validate_model_step,
            build_bento_step,
        )

        # Step 1: Collect data
        logger.info("\n[Step 1/5] Collecting data...")
        raw_data_path = collect_data_step()
        logger.info(f"✓ Data collected: {raw_data_path}")

        # Step 2: Preprocess
        logger.info("\n[Step 2/5] Preprocessing features...")
        features_path = preprocess_data_step(raw_data_path)
        logger.info(f"✓ Features created: {features_path}")

        # Step 3: Train model
        logger.info("\n[Step 3/5] Training model...")
        model_path, metrics = train_model_step(features_path)
        logger.info(f"✓ Model trained: {model_path}")
        logger.info(f"  Metrics: MAPE={metrics['mape']:.2f}, RMSE={metrics['rmse']:.2f}, Coverage={metrics['coverage_rate']:.2%}")

        # Step 4: Validate
        logger.info("\n[Step 4/5] Validating model...")
        is_valid = validate_model_step(metrics)

        if not is_valid:
            logger.error("✗ Model validation failed!")
            logger.error("  Pipeline stopped. Model not deployed.")
            return None

        logger.info("✓ Model validated successfully")

        # Step 5: Build Bento
        logger.info("\n[Step 5/5] Building BentoML service...")
        bento_tag = build_bento_step(model_path, is_valid)
        logger.info(f"✓ Bento built: {bento_tag}")

        # Success summary
        logger.info("\n" + "=" * 60)
        logger.info("Pipeline completed successfully!")
        logger.info("=" * 60)
        logger.info(f"Bento tag: {bento_tag}")
        logger.info("\nTo serve locally:")
        logger.info(f"  bentoml serve {bento_tag}")
        logger.info("\nTo containerize:")
        logger.info(f"  bentoml containerize {bento_tag}")
        logger.info("=" * 60)

        return bento_tag

    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error("Pipeline failed!")
        logger.error("=" * 60)
        logger.error(f"Error: {e}", exc_info=True)
        logger.error("=" * 60)
        return None


if __name__ == "__main__":
    # Run the pipeline
    result = run_ml_pipeline()

    # Exit with appropriate code
    exit(0 if result else 1)
