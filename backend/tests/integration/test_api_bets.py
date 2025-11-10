"""Tests d'intégration pour les endpoints /bets/"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_bet():
    return {
        "match_id": "test_123",
        "outcome": "Home",
        "bookmaker": "Bet365",
        "odds_value": 2.50,
        "stake": 10.00,
        "bet_type": "value"
    }


class TestBetsEndpoints:
    
    def test_create_bet_success(self, client, sample_bet):
        """Test création pari"""
        response = client.post("/bets/", json=sample_bet)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["match_id"] == sample_bet["match_id"]

    def test_get_bets_list(self, client):
        """Test récupération paris"""
        response = client.get("/bets/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
