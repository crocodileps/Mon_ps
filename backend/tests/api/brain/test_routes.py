"""Tests FastAPI routes"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from datetime import date, timedelta


class TestBrainRoutes:
    """Test Brain API routes"""

    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        from backend.main import app
        return TestClient(app)

    def test_health_endpoint(self, client):
        """GET /health returns 200"""
        with patch('backend.api.v1.brain.routes.brain_service') as mock_service:
            mock_service.get_health.return_value = Mock(
                status="operational",
                version="2.8.0",
                markets_count=99
            )

            response = client.get("/api/v1/brain/health")
            assert response.status_code == 200

    def test_calculate_endpoint_valid(self, client):
        """POST /calculate with valid data returns 200"""
        with patch('backend.api.v1.brain.routes.brain_service') as mock_service:
            mock_service.calculate_predictions.return_value = Mock(
                prediction_id="uuid-123",
                home_team="Liverpool",
                calculation_time=3.2
            )

            future_date = (date.today() + timedelta(days=7)).isoformat()
            response = client.post("/api/v1/brain/calculate", json={
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "match_date": future_date
            })
            assert response.status_code == 200
