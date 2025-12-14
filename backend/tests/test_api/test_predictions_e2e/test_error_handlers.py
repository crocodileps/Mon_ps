"""Tests for API Error Handlers - Production UX Critical.

Validates that business errors return correct HTTP status codes:
- InvalidDateError → 400 Bad Request
- LowConfidenceError → 422 Unprocessable Entity
- Unexpected errors → 500 Internal Server Error

Without these tests, all errors would return 500 (bad UX + monitoring).
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta

from quantum_core.api.main import app
from quantum_core.api.predictions.routes import get_prediction_service
from quantum_core.api.common.exceptions import (
    InvalidDateError,
    LowConfidenceError,
    UnifiedBrainError,
)


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
# TESTS - Error Handler Semantics
# ─────────────────────────────────────────────────────────────────────────


class TestErrorHandlerSemantics:
    """Validate that error handlers return correct HTTP status codes."""

    def test_invalid_date_error_returns_400(self, client):
        """Test that InvalidDateError is caught and returns 400 Bad Request.

        Critical for UX: Frontend needs to distinguish business validation errors
        (400) from server errors (500).
        """
        # Mock service to raise InvalidDateError
        mock_service = AsyncMock()
        mock_service.generate_match_prediction.side_effect = InvalidDateError(
            "Match date is in the past"
        )

        # Override dependency
        app.dependency_overrides[get_prediction_service] = lambda: mock_service

        # Request with valid payload (service will raise error)
        payload = {
            "match_id": "test_match",
            "competition": "Test League",
            "match_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }

        response = client.post("/api/v1/predictions/match", json=payload)

        # Validate error semantics
        assert response.status_code == 400  # Bad Request, not 500
        data = response.json()
        assert "detail" in data
        assert "past" in data["detail"].lower()

        # Cleanup
        app.dependency_overrides.clear()

    def test_low_confidence_error_returns_422(self, client):
        """Test that LowConfidenceError is caught and returns 422 Unprocessable Entity.

        Critical for business logic: Distinguishes data quality issues (422)
        from validation errors (400) and server errors (500).
        """
        # Mock service to raise LowConfidenceError
        mock_service = AsyncMock()
        mock_service.generate_match_prediction.side_effect = LowConfidenceError(
            "Model agreement too low (0.45 < 0.70 threshold)"
        )

        # Override dependency
        app.dependency_overrides[get_prediction_service] = lambda: mock_service

        # Request with valid payload
        payload = {
            "match_id": "low_confidence_match",
            "competition": "Test League",
            "match_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }

        response = client.post("/api/v1/predictions/match", json=payload)

        # Validate error semantics
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data
        assert (
            "agreement" in data["detail"].lower()
            or "confidence" in data["detail"].lower()
        )

        # Cleanup
        app.dependency_overrides.clear()

    def test_unexpected_error_returns_500(self, client):
        """Test that UnifiedBrainError returns 500 Internal Server Error.

        Critical for monitoring: Brain failures should trigger alerts,
        not be confused with user errors (400/422).
        """
        # Mock service to raise UnifiedBrainError
        mock_service = AsyncMock()
        mock_service.generate_match_prediction.side_effect = UnifiedBrainError(
            "ML model processing failed"
        )

        # Override dependency
        app.dependency_overrides[get_prediction_service] = lambda: mock_service

        # Request with valid payload
        payload = {
            "match_id": "test_match",
            "competition": "Test League",
            "match_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }

        response = client.post("/api/v1/predictions/match", json=payload)

        # Validate error semantics
        assert response.status_code == 500  # Internal Server Error
        data = response.json()
        assert "detail" in data
        # Note: Real error message may be sanitized in production

        # Cleanup
        app.dependency_overrides.clear()
