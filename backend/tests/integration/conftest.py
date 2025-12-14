"""
Fixtures pour Integration Tests (Real Dependencies)
"""
import pytest
import sys
import random
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

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
# QUANTUM CORE PATH
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
# REAL UNIFIEDBRAIN
# ============================================================================

@pytest.fixture(scope="session")
def real_unified_brain(quantum_core_path):
    """Real UnifiedBrain instance (expensive, shared)"""
    from brain.unified_brain import UnifiedBrain

    brain = UnifiedBrain()
    return brain


@pytest.fixture
def brain_repository_real(real_unified_brain):
    """BrainRepository avec VRAI UnifiedBrain"""
    from api.v1.brain.repository import BrainRepository

    repo = BrainRepository()
    assert repo.brain is not None

    return repo


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
