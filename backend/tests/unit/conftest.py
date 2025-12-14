"""
Fixtures pour Unit Tests (Mocks Only)
"""
import pytest
import random
import numpy as np
from unittest.mock import Mock, MagicMock

# ============================================================================
# SEED FIXING - DETERMINISTIC
# ============================================================================

@pytest.fixture(autouse=True)
def deterministic_tests():
    """Force determinism"""
    random.seed(42)
    np.random.seed(42)
    yield


# ============================================================================
# MOCK UNIFIEDBRAIN
# ============================================================================

@pytest.fixture
def mock_unified_brain():
    """Mock UnifiedBrain pour unit tests"""
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
def sample_match_data():
    """Sample match data"""
    from datetime import datetime, timedelta
    return {
        "home_team": "Liverpool",
        "away_team": "Chelsea",
        "match_date": (datetime.now() + timedelta(days=3)).date().isoformat()
    }
