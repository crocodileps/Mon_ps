"""
Fixtures pour Integration Tests (Real Dependencies)
Fix: Docker-first path (aligned with api/v1/brain/repository.py)
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
# QUANTUM CORE PATH (Docker-first, aligned with repository.py)
# ============================================================================

@pytest.fixture(scope="session")
def quantum_core_path():
    """
    Path vers quantum_core MASTER

    Logic aligned with api/v1/brain/repository.py:
    - Priority 1: Docker volume (/quantum_core)
    - Priority 2: Local development (/home/Mon_ps/quantum_core)
    """
    # Priority 1: Docker volume (production)
    docker_path = Path("/quantum_core")

    # Priority 2: Local development
    local_path = Path("/home/Mon_ps/quantum_core")

    if docker_path.exists():
        path = docker_path
    elif local_path.exists():
        path = local_path
    else:
        pytest.skip(
            f"quantum_core not found. Checked:\n"
            f"  - Docker: {docker_path}\n"
            f"  - Local:  {local_path}\n"
            f"Integration tests require quantum_core."
        )

    # Add BOTH paths to sys.path for complete compatibility
    # 1. Parent directory (/) allows "from quantum_core.adapters..." (UnifiedBrain internal imports)
    # 2. quantum_core itself allows "from brain.unified_brain..." (our imports)
    parent_path = str(path.parent)
    if parent_path not in sys.path:
        sys.path.insert(0, parent_path)

    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

    return path


# ============================================================================
# REAL UNIFIEDBRAIN
# ============================================================================

@pytest.fixture(scope="session")
def real_unified_brain(quantum_core_path):
    """Real UnifiedBrain instance (expensive, shared)"""
    try:
        from brain.unified_brain import UnifiedBrain
        brain = UnifiedBrain()
        return brain
    except Exception as e:
        pytest.skip(f"Failed to import UnifiedBrain: {e}")


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
        "Real Madrid", "Barcelona", "Bayern Munich", "PSG",
        "Inter Milan", "AC Milan", "Juventus", "Napoli"
    ]


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
