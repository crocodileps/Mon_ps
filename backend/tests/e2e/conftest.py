"""
Fixtures pour E2E Tests (Full Stack)
"""
import pytest
import random
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# ============================================================================
# SEED FIXING
# ============================================================================

@pytest.fixture(autouse=True)
def deterministic_tests():
    """Force determinism"""
    random.seed(42)
    np.random.seed(42)
    yield


# ============================================================================
# FASTAPI TEST CLIENT
# ============================================================================

@pytest.fixture
def test_client():
    """FastAPI TestClient"""
    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as client:
        yield client


# ============================================================================
# CONCURRENCY
# ============================================================================

@pytest.fixture
def concurrent_executor():
    """ThreadPoolExecutor for concurrency tests"""
    with ThreadPoolExecutor(max_workers=10) as executor:
        yield executor


@pytest.fixture
def sample_match_data():
    """Sample match data"""
    return {
        "home_team": "Liverpool",
        "away_team": "Chelsea",
        "match_date": (datetime.now() + timedelta(days=3)).date().isoformat()
    }


@pytest.fixture
def sample_teams_pool():
    """Pool équipes réelles"""
    return [
        "Liverpool", "Manchester City", "Arsenal", "Chelsea",
        "Real Madrid", "Barcelona", "Bayern Munich", "PSG"
    ]
