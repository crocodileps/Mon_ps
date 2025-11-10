"""Tests d'intégration pour les endpoints /opportunities/"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestOpportunitiesEndpoints:
    
    def test_get_opportunities_success(self, client):
        """Test récupération opportunités"""
        response = client.get("/opportunities/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_detect_arbitrage_success(self, client):
        """Test détection arbitrage"""
        response = client.get("/opportunities/arbitrage")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
