"""
Pytest Fixtures pour Tests Brain API
Anti-Flaky Patterns + Deterministic Tests
"""

import pytest
import sys
import random
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, MagicMock

# ============================================================================
# SEED FIXING - DETERMINISTIC TESTS
# ============================================================================

@pytest.fixture(autouse=True)
def deterministic_tests():
    """Force determinism pour éviter flaky tests"""
    random.seed(42)
    np.random.seed(42)
    # Note: UnifiedBrain devrait aussi accepter seed, TODO dans brain code
    yield
    # Cleanup
    random.seed()  # Reset to random


# ============================================================================
# QUANTUM CORE PATH SETUP
# ============================================================================

@pytest.fixture(scope="session")
def quantum_core_path():
    """Path vers quantum_core MASTER"""
    path = Path("/home/Mon_ps/quantum_core")
    if not path.exists():
        pytest.skip(f"quantum_core not found at {path}")

    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

    return path


# ============================================================================
# REAL UNIFIEDBRAIN FIXTURE (Integration Tests)
# ============================================================================

@pytest.fixture(scope="session")
def real_unified_brain(quantum_core_path):
    """
    Real UnifiedBrain instance (expensive, shared across session)

    Scope: session (créé 1 fois, réutilisé partout)
    """
    from brain.unified_brain import UnifiedBrain

    brain = UnifiedBrain()
    return brain


@pytest.fixture
def brain_repository_real(real_unified_brain):
    """BrainRepository avec VRAI UnifiedBrain (integration tests)"""
    from api.v1.brain.repository import BrainRepository

    repo = BrainRepository()
    # Vérifier qu'on utilise le vrai brain
    assert repo.brain is not None
    assert hasattr(repo.brain, 'analyze_match')

    return repo


# ============================================================================
# MOCK UNIFIEDBRAIN FIXTURE (Unit Tests)
# ============================================================================

@pytest.fixture
def mock_unified_brain():
    """Mock UnifiedBrain pour unit tests rapides"""
    mock = MagicMock()

    # Mock analyze_match response
    mock_prediction = MagicMock()
    mock_prediction.home_team = "Liverpool"
    mock_prediction.away_team = "Chelsea"
    mock_prediction.over_under_25_yes_prob = 0.65
    mock_prediction.btts_yes_prob = 0.58
    mock_prediction.home_win_prob = 0.52

    mock.analyze_match.return_value = mock_prediction
    mock.health_check.return_value = {
        "status": "operational",
        "markets_supported": 93
    }

    return mock


@pytest.fixture
def brain_repository_mock(mock_unified_brain, monkeypatch):
    """BrainRepository avec Mock UnifiedBrain (unit tests)"""
    from api.v1.brain.repository import BrainRepository

    # Monkeypatch UnifiedBrain import
    monkeypatch.setattr(
        "api.v1.brain.repository.UnifiedBrain",
        lambda: mock_unified_brain
    )

    repo = BrainRepository()
    repo.brain = mock_unified_brain

    return repo


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_match_data():
    """Sample match data pour tests"""
    return {
        "home_team": "Liverpool",
        "away_team": "Chelsea",
        "match_date": (datetime.now() + timedelta(days=3)).date().isoformat()
    }


@pytest.fixture
def sample_teams_pool():
    """Pool équipes réelles pour tests variés"""
    return [
        "Liverpool", "Manchester City", "Arsenal", "Chelsea",
        "Real Madrid", "Barcelona", "Bayern Munich", "PSG",
        "Inter Milan", "AC Milan", "Juventus", "Napoli"
    ]


@pytest.fixture
def edge_case_teams():
    """Edge cases équipes pour robustesse"""
    return {
        "special_chars": "Inter Miami",
        "accents": "Atlético Madrid",
        "long_name": "Borussia Mönchengladbach",
        "numbers": "1899 Hoffenheim",
        "lowercase": "liverpool",  # Test normalization
        "unknown": "UnknownTeamXYZ123"
    }


# ============================================================================
# FASTAPI TEST CLIENT
# ============================================================================

@pytest.fixture
def test_client():
    """FastAPI TestClient pour E2E tests"""
    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as client:
        yield client


# ============================================================================
# CONCURRENCY HELPERS
# ============================================================================

@pytest.fixture
def concurrent_executor():
    """ThreadPoolExecutor pour concurrency tests"""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=10) as executor:
        yield executor


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

@pytest.fixture
def performance_monitor():
    """Monitor performance pour benchmarks"""
    import time

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()
            return self.elapsed()

        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return PerformanceMonitor()
