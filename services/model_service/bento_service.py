"""
BentoML Model Service for PokeWatch

Wraps the existing baseline model to serve predictions via HTTP.
This service loads the trained model from MLflow and provides a prediction endpoint.
"""
import logging
from typing import Optional

import bentoml
from bentoml.io import JSON

from pokewatch.models.baseline import load_baseline_model

logger = logging.getLogger(__name__)


@bentoml.service(
    name="pokewatch_model_service",
    resources={"cpu": "2"},
    traffic={"timeout": 10}
)
class ModelService:
    """
    BentoML service for serving Pokemon card fair price predictions.

    This service wraps the existing baseline model without requiring
    any changes to the model code itself.
    """

    def __init__(self):
        """Initialize the service by loading the baseline model."""
        logger.info("Loading baseline model...")
        self.model = load_baseline_model()
        logger.info(f"Model loaded with {len(self.model.get_all_card_ids())} cards")

    @bentoml.api
    def predict(self, card_id: str, date: Optional[str] = None) -> dict:
        """
        Predict fair price for a given card.

        Args:
            card_id: Card internal ID (e.g., "charizard_ex_199")
            date: Optional date in YYYY-MM-DD format. If None, uses latest available.

        Returns:
            Dictionary with:
                - card_id: The input card ID
                - date: The resolved date used for prediction
                - market_price: Current market price
                - fair_price: Predicted fair price

        Example:
            >>> service.predict(card_id="charizard_ex_199", date="2025-12-01")
            {
                "card_id": "charizard_ex_199",
                "date": "2025-12-01",
                "market_price": 150.0,
                "fair_price": 145.0
            }
        """
        try:
            # Reuse existing model.predict() method - no changes needed!
            resolved_date, market_price, fair_price = self.model.predict(
                card_id=card_id,
                date=date
            )

            return {
                "card_id": card_id,
                "date": str(resolved_date),
                "market_price": float(market_price),
                "fair_price": float(fair_price)
            }
        except ValueError as e:
            logger.error(f"Prediction error for {card_id}: {e}")
            raise bentoml.exceptions.BadInput(str(e))

    @bentoml.api
    def health(self) -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "model_loaded": True,
            "cards_count": len(self.model.get_all_card_ids())
        }

    @bentoml.api
    def cards(self) -> dict:
        """
        List all available card IDs in the model.

        Returns:
            Dictionary with:
                - cards: List of card IDs
                - count: Number of cards
        """
        card_ids = self.model.get_all_card_ids()
        return {
            "cards": card_ids,
            "count": len(card_ids)
        }

    @bentoml.api
    def reload(self) -> dict:
        """
        Reload the model from MLflow registry.

        Called by Airflow DAG after training a new model.
        """
        try:
            logger.info("Reloading model from MLflow...")
            self.model = load_baseline_model()
            logger.info(f"Model reloaded successfully with {len(self.model.get_all_card_ids())} cards")
            return {
                "status": "reloaded",
                "cards_count": len(self.model.get_all_card_ids())
            }
        except Exception as e:
            logger.error(f"Model reload failed: {e}")
            raise bentoml.exceptions.InternalServerError(f"Reload failed: {str(e)}")
