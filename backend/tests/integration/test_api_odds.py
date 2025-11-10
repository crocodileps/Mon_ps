"""Tests d'intégration pour les endpoints /odds/"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestOddsEndpoints:
    
    def test_get_odds_success(self, client):
        """Test récupération liste cotes"""
        response = client.get("/odds/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_odds_with_limit(self, client):
        """Test récupération cotes avec limite"""
        response = client.get("/odds/?limit=10")
        assert response.status_code == 200
        assert len(response.json()) <= 10

    def test_get_matches_success(self, client):
        """Test récupération liste matchs"""
        response = client.get("/odds/matches")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_health_check(self, client):
        """Test endpoint santé"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_root_endpoint(self, client):
        """Test endpoint racine"""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
