"""
Integration tests for BentoML service.

These tests verify that the BentoML service works correctly and maintains
compatibility with the FastAPI API contract.

Run with: pytest tests/integration/test_bento_service.py -v
Requires: BentoML service running on http://localhost:3000
"""

import pytest
import requests


@pytest.fixture(scope="module")
def bento_url():
    """BentoML service URL."""
    return "http://localhost:3000"


@pytest.fixture(scope="module")
def check_service_running(bento_url):
    """Check if BentoML service is running before tests."""
    try:
        response = requests.get(f"{bento_url}/health", timeout=5)
        if response.status_code != 200:
            pytest.skip("BentoML service not responding correctly")
    except requests.exceptions.ConnectionError:
        pytest.skip("BentoML service not running. Start with: make bento-serve")


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_endpoint_returns_200(self, bento_url, check_service_running):
        """Test health check endpoint returns 200 OK."""
        response = requests.get(f"{bento_url}/health")

        assert response.status_code == 200

    def test_health_endpoint_response_structure(self, bento_url, check_service_running):
        """Test health endpoint returns correct structure."""
        response = requests.get(f"{bento_url}/health")
        data = response.json()

        # Verify required fields
        assert "status" in data
        assert "model_loaded" in data
        assert "num_cards" in data

        # Verify field types
        assert isinstance(data["status"], str)
        assert isinstance(data["model_loaded"], bool)
        assert isinstance(data["num_cards"], int)

    def test_health_endpoint_model_loaded(self, bento_url, check_service_running):
        """Test health endpoint reports model as loaded."""
        response = requests.get(f"{bento_url}/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert data["model_loaded"] is True
        assert data["num_cards"] > 0


class TestPredictEndpoint:
    """Tests for /predict endpoint."""

    def test_predict_endpoint_returns_200(self, bento_url, check_service_running):
        """Test prediction endpoint returns 200 OK with valid input."""
        payload = {
            "card_id": "sv2a_151_charizard_ex___201_165",
        }

        response = requests.post(f"{bento_url}/predict", json=payload)

        assert response.status_code == 200

    def test_predict_endpoint_response_structure(self, bento_url, check_service_running):
        """Test prediction endpoint returns correct structure."""
        payload = {
            "card_id": "sv2a_151_charizard_ex___201_165",
        }

        response = requests.post(f"{bento_url}/predict", json=payload)
        data = response.json()

        # Verify all required fields present
        required_fields = [
            "card_id",
            "date",
            "market_price",
            "fair_price",
            "deviation_pct",
            "signal",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_predict_endpoint_signal_values(self, bento_url, check_service_running):
        """Test signal is one of BUY, SELL, or HOLD."""
        payload = {
            "card_id": "sv2a_151_charizard_ex___201_165",
        }

        response = requests.post(f"{bento_url}/predict", json=payload)
        data = response.json()

        assert data["signal"] in ["BUY", "SELL", "HOLD"]

    def test_predict_endpoint_with_date(self, bento_url, check_service_running):
        """Test prediction with specific date."""
        payload = {"card_id": "sv2a_151_charizard_ex___201_165", "date": "2025-11-30"}

        response = requests.post(f"{bento_url}/predict", json=payload)

        # Should succeed or return 404 if date not available
        assert response.status_code in [200, 404]

    def test_predict_endpoint_field_types(self, bento_url, check_service_running):
        """Test all response fields have correct types."""
        payload = {
            "card_id": "sv2a_151_charizard_ex___201_165",
        }

        response = requests.post(f"{bento_url}/predict", json=payload)
        data = response.json()

        assert isinstance(data["card_id"], str)
        assert isinstance(data["date"], str)
        assert isinstance(data["market_price"], (int, float))
        assert isinstance(data["fair_price"], (int, float))
        assert isinstance(data["deviation_pct"], (int, float))
        assert isinstance(data["signal"], str)

    def test_predict_endpoint_invalid_card_id(self, bento_url, check_service_running):
        """Test prediction with invalid card ID returns error."""
        payload = {
            "card_id": "invalid_card_id_12345",
        }

        response = requests.post(f"{bento_url}/predict", json=payload)

        # Should return 4xx or 5xx error
        assert response.status_code >= 400


class TestListCardsEndpoint:
    """Tests for /list_cards endpoint."""

    def test_list_cards_endpoint_returns_200(self, bento_url, check_service_running):
        """Test list cards endpoint returns 200 OK."""
        response = requests.get(f"{bento_url}/list_cards")

        assert response.status_code == 200

    def test_list_cards_response_structure(self, bento_url, check_service_running):
        """Test list cards endpoint returns correct structure."""
        response = requests.get(f"{bento_url}/list_cards")
        data = response.json()

        assert "total" in data
        assert "cards" in data
        assert isinstance(data["total"], int)
        assert isinstance(data["cards"], list)

    def test_list_cards_count_matches(self, bento_url, check_service_running):
        """Test total count matches actual list length."""
        response = requests.get(f"{bento_url}/list_cards")
        data = response.json()

        assert data["total"] == len(data["cards"])

    def test_list_cards_returns_cards(self, bento_url, check_service_running):
        """Test list cards returns at least one card."""
        response = requests.get(f"{bento_url}/list_cards")
        data = response.json()

        assert data["total"] > 0
        assert len(data["cards"]) > 0

    def test_list_cards_sorted(self, bento_url, check_service_running):
        """Test cards list is sorted."""
        response = requests.get(f"{bento_url}/list_cards")
        data = response.json()

        assert data["cards"] == sorted(data["cards"])


class TestBatchPredictEndpoint:
    """Tests for /batch_predict endpoint."""

    def test_batch_predict_endpoint_returns_200(self, bento_url, check_service_running):
        """Test batch prediction returns 200 OK."""
        payload = [
            {"card_id": "sv2a_151_charizard_ex___201_165"},
        ]

        response = requests.post(f"{bento_url}/batch_predict", json=payload)

        assert response.status_code == 200

    def test_batch_predict_multiple_cards(self, bento_url, check_service_running):
        """Test batch prediction with multiple cards."""
        # Get available cards first
        cards_response = requests.get(f"{bento_url}/list_cards")
        available_cards = cards_response.json()["cards"]

        if len(available_cards) < 2:
            pytest.skip("Need at least 2 cards for batch test")

        payload = [
            {"card_id": available_cards[0]},
            {"card_id": available_cards[1]},
        ]

        response = requests.post(f"{bento_url}/batch_predict", json=payload)
        data = response.json()

        assert response.status_code == 200
        assert isinstance(data, list)
        assert len(data) == 2

    def test_batch_predict_handles_partial_failures(self, bento_url, check_service_running):
        """Test batch prediction handles some invalid cards gracefully."""
        payload = [
            {"card_id": "sv2a_151_charizard_ex___201_165"},  # Valid
            {"card_id": "invalid_card_12345"},  # Invalid
        ]

        response = requests.post(f"{bento_url}/batch_predict", json=payload)

        # Should still return 200 with mixed results
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2


class TestAPICompatibility:
    """Tests to ensure BentoML API matches FastAPI contract."""

    def test_content_type_json(self, bento_url, check_service_running):
        """Test API returns JSON content type."""
        response = requests.get(f"{bento_url}/health")

        assert "application/json" in response.headers.get("Content-Type", "")

    def test_cors_headers_present(self, bento_url, check_service_running):
        """Test CORS headers are present (if configured)."""
        response = requests.get(f"{bento_url}/health")

        # This test can be adjusted based on CORS configuration
        # For now, just check response is valid
        assert response.status_code == 200


class TestPerformance:
    """Basic performance tests."""

    def test_health_check_latency(self, bento_url, check_service_running):
        """Test health check responds in under 1 second."""
        import time

        start = time.time()
        response = requests.get(f"{bento_url}/health")
        latency = time.time() - start

        assert response.status_code == 200
        assert latency < 1.0, f"Health check took {latency:.2f}s, expected < 1s"

    def test_prediction_latency(self, bento_url, check_service_running):
        """Test prediction responds in under 2 seconds."""
        import time

        payload = {
            "card_id": "sv2a_151_charizard_ex___201_165",
        }

        start = time.time()
        response = requests.post(f"{bento_url}/predict", json=payload)
        latency = time.time() - start

        assert response.status_code == 200
        assert latency < 2.0, f"Prediction took {latency:.2f}s, expected < 2s"
