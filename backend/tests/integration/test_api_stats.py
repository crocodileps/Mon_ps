"""Tests d'intégration pour les endpoints /stats/"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestStatsEndpoints:
    
    def test_global_stats_success(self, client):
        """Test statistiques globales"""
        response = client.get("/stats/global")
        assert response.status_code == 200
        data = response.json()
        assert "total_odds" in data
        assert "total_matches" in data

    def test_bankroll_summary_success(self, client):
        """Test résumé bankroll"""
        response = client.get("/stats/bankroll")
        assert response.status_code == 200
        data = response.json()
        assert "current_balance" in data
        assert "nb_bets" in data
