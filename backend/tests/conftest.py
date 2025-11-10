"""Fixtures communes pour tous les tests"""
import pytest
import sys
from pathlib import Path

# Ajouter le parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime
from api.main import app


@pytest.fixture
def client():
    """Client de test FastAPI"""
    return TestClient(app)


@pytest.fixture
def sample_bet():
    """Pari exemple pour les tests"""
    return {
        "match_id": "test_match_123",
        "outcome": "Home",
        "bookmaker": "Bet365",
        "odds_value": 2.50,
        "stake": 10.00,
        "bet_type": "value",
        "notes": "Test bet"
    }


@pytest.fixture(scope="session")
def anyio_backend():
    """Configuration pour pytest-anyio"""
    return "asyncio"
