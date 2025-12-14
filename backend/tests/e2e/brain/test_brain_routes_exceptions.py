"""
E2E Tests - Routes Exception Paths
Objectif: Cover exception handling lines in routes.py
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestCalculateEndpointExceptions:
    """Test exception paths for /calculate endpoint"""

    def test_calculate_value_error(self, test_client):
        """Test ValueError handling (400)"""
        with patch('api.v1.brain.routes.brain_service.calculate_predictions') as mock_calc:
            mock_calc.side_effect = ValueError("Invalid team names")

            response = test_client.post(
                "/api/v1/brain/calculate",
                json={
                    "home_team": "Liverpool",
                    "away_team": "Chelsea",
                    "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
                }
            )

            assert response.status_code == 400
            assert "Invalid team names" in response.json()["detail"]

    def test_calculate_runtime_error(self, test_client):
        """Test RuntimeError handling (500)"""
        with patch('api.v1.brain.routes.brain_service.calculate_predictions') as mock_calc:
            mock_calc.side_effect = RuntimeError("UnifiedBrain unavailable")

            response = test_client.post(
                "/api/v1/brain/calculate",
                json={
                    "home_team": "Liverpool",
                    "away_team": "Chelsea",
                    "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
                }
            )

            assert response.status_code == 500
            assert "UnifiedBrain unavailable" in response.json()["detail"]

    def test_calculate_unexpected_exception(self, test_client):
        """Test unexpected Exception handling (500)"""
        with patch('api.v1.brain.routes.brain_service.calculate_predictions') as mock_calc:
            mock_calc.side_effect = Exception("Unexpected error")

            response = test_client.post(
                "/api/v1/brain/calculate",
                json={
                    "home_team": "Liverpool",
                    "away_team": "Chelsea",
                    "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
                }
            )

            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]


class TestGoalscorerEndpointExceptions:
    """Test exception paths for /goalscorer endpoint"""

    def test_goalscorer_value_error(self, test_client):
        """Test ValueError handling (400)"""
        with patch('api.v1.brain.routes.brain_service.calculate_goalscorers') as mock_calc:
            mock_calc.side_effect = ValueError("Invalid request")

            response = test_client.post(
                "/api/v1/brain/goalscorer",
                json={
                    "home_team": "Liverpool",
                    "away_team": "Chelsea",
                    "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
                }
            )

            assert response.status_code == 400

    def test_goalscorer_runtime_error(self, test_client):
        """Test RuntimeError handling (500)"""
        with patch('api.v1.brain.routes.brain_service.calculate_goalscorers') as mock_calc:
            mock_calc.side_effect = RuntimeError("Service unavailable")

            response = test_client.post(
                "/api/v1/brain/goalscorer",
                json={
                    "home_team": "Liverpool",
                    "away_team": "Chelsea",
                    "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
                }
            )

            assert response.status_code == 500

    def test_goalscorer_unexpected_exception(self, test_client):
        """Test unexpected Exception handling (500)"""
        with patch('api.v1.brain.routes.brain_service.calculate_goalscorers') as mock_calc:
            mock_calc.side_effect = Exception("Unexpected")

            response = test_client.post(
                "/api/v1/brain/goalscorer",
                json={
                    "home_team": "Liverpool",
                    "away_team": "Chelsea",
                    "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
                }
            )

            assert response.status_code == 500


class TestHealthEndpointExceptions:
    """Test exception paths for /health endpoint"""

    def test_health_exception(self, test_client):
        """Test Exception handling (500)"""
        with patch('api.v1.brain.routes.brain_service.get_health') as mock_health:
            mock_health.side_effect = Exception("Health check failed")

            response = test_client.get("/api/v1/brain/health")

            assert response.status_code == 500
            assert "Health check failed" in response.json()["detail"]


class TestMarketsEndpointExceptions:
    """Test exception paths for /markets endpoint"""

    def test_markets_exception(self, test_client):
        """Test Exception handling (500)"""
        with patch('api.v1.brain.routes.brain_service.get_markets_list') as mock_markets:
            mock_markets.side_effect = Exception("Markets retrieval failed")

            response = test_client.get("/api/v1/brain/markets")

            assert response.status_code == 500
            assert "Failed to retrieve markets" in response.json()["detail"]
