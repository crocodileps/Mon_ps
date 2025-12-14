"""Tests for UPDATE Endpoint - Production Critical Functionality.

Validates:
- Successful update (happy path)
- Not found error (404)
- Partial updates (only changed fields)

Without these tests, UPDATE endpoint is untested in production.
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from quantum_core.api.main import app
from quantum_core.api.predictions.routes import get_prediction_service
from quantum_core.api.common.exceptions import MonPSException
from tests.factories import create_market_prediction


# ─────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    """FastAPI test client."""
    # Clear dependency overrides before each test
    app.dependency_overrides.clear()
    return TestClient(app)


# ─────────────────────────────────────────────────────────────────────────
# TESTS - UPDATE Endpoint
# ─────────────────────────────────────────────────────────────────────────


class TestUpdatePredictionEndpoint:
    """Tests for PUT /api/v1/predictions/{prediction_id}."""

    def test_update_prediction_success(self, client):
        """Test successful prediction update (happy path).

        Critical: Validates UPDATE endpoint works end-to-end.
        """
        # Mock service with successful update
        # Create mock prediction
        original_prediction = create_market_prediction(
            prediction_id="test_update_123",
            confidence_score=0.75,
        )

        # Updated prediction
        updated_prediction = create_market_prediction(
            prediction_id="test_update_123",
            confidence_score=0.90,  # Changed
            fair_odds=original_prediction.fair_odds,  # Same
        )

        mock_service = AsyncMock()
        mock_service.update_prediction.return_value = updated_prediction

        # Override dependency
        app.dependency_overrides[get_prediction_service] = lambda: mock_service

        # Call UPDATE endpoint
        payload = {"confidence_score": 0.90}
        response = client.put(
            "/api/v1/predictions/test_update_123",
            json=payload,
        )

        # Validate success
        assert response.status_code == 200
        data = response.json()
        # Response is PredictionResponse with nested prediction
        assert data["prediction"]["prediction_id"] == "test_update_123"
        assert data["prediction"]["confidence_score"] == 0.90

        # Verify service was called correctly
        mock_service.update_prediction.assert_called_once()
        # Verify prediction_id and confidence_score were passed (kwargs)
        call_kwargs = mock_service.update_prediction.call_args.kwargs
        assert call_kwargs["prediction_id"] == "test_update_123"
        assert call_kwargs["confidence_score"] == 0.90

        # Cleanup
        app.dependency_overrides.clear()

    def test_update_prediction_not_found(self, client):
        """Test updating non-existent prediction returns 404.

        Critical: Frontend needs 404 to show "prediction not found" error.
        """
        # Mock service with prediction not found
        mock_service = AsyncMock()
        mock_service.update_prediction.side_effect = MonPSException(
            detail="Prediction not found",
            status_code=404,
            error_code="PREDICTION_NOT_FOUND",
        )

        # Override dependency
        app.dependency_overrides[get_prediction_service] = lambda: mock_service

        # Call UPDATE endpoint with non-existent ID
        payload = {"confidence_score": 0.95}
        response = client.put(
            "/api/v1/predictions/non_existent_prediction",
            json=payload,
        )

        # Validate 404
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

        # Cleanup
        app.dependency_overrides.clear()

    def test_update_prediction_partial_update(self, client):
        """Test partial update (only some fields changed).

        Validates that partial updates work (PATCH-like behavior with PUT).
        """
        # Mock service
        updated_prediction = create_market_prediction(
            prediction_id="test_partial_123",
            fair_odds=2.50,  # Updated
            confidence_score=0.80,  # Same
        )

        mock_service = AsyncMock()
        mock_service.update_prediction.return_value = updated_prediction

        # Override dependency
        app.dependency_overrides[get_prediction_service] = lambda: mock_service

        # Partial update (only fair_odds)
        payload = {"fair_odds": 2.50}
        response = client.put(
            "/api/v1/predictions/test_partial_123",
            json=payload,
        )

        # Validate success
        assert response.status_code == 200
        data = response.json()
        # Response is PredictionResponse with nested prediction
        assert data["prediction"]["fair_odds"] == 2.50

        # Cleanup
        app.dependency_overrides.clear()
