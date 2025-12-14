"""Smoke tests for Predictions API routes.

Tests basiques pour valider endpoints fonctionnent.
Tests E2E complets en Session #24.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from quantum_core.api.main import app

client = TestClient(app)


class TestPredictionsRoutesSmoke:
    """Smoke tests - Validation basique endpoints."""

    def test_health_check(self):
        """Test: Health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self):
        """Test: Root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "docs" in data

    def test_brain_health(self):
        """Test: Brain health check."""
        response = client.get("/api/v1/predictions/brain/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert len(data["agents_available"]) == 4

    def test_generate_match_prediction_smoke(self):
        """Smoke test: Generate match prediction."""
        payload = {
            "match_id": "test_match_001",
            "competition": "Test League",
            "match_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        }

        response = client.post("/api/v1/predictions/match", json=payload)

        # Mock service devrait retourner 200
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["match_id"] == "test_match_001"
        assert "ensemble" in data

    def test_generate_prediction_past_date_error(self):
        """Test: Erreur si date passée."""
        payload = {
            "match_id": "test_match_002",
            "competition": "Test League",
            "match_date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        }

        response = client.post("/api/v1/predictions/match", json=payload)

        # Devrait rejeter date passée
        assert response.status_code == 400
        data = response.json()
        assert "past" in data["detail"].lower()

    def test_generate_prediction_missing_field_error(self):
        """Test: Erreur si champ manquant."""
        payload = {
            "match_id": "test_match_003",
            # competition manquant
            # match_date manquant
        }

        response = client.post("/api/v1/predictions/match", json=payload)

        # Validation Pydantic devrait échouer
        assert response.status_code == 422
