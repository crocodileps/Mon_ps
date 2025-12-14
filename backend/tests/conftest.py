"""pytest configuration and fixtures.

Global fixtures available to all tests.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import database dependencies (optional for unit tests like cache)
try:
    from infrastructure.database.base import Base
    from infrastructure.database.models import PredictionORM
    HAS_DATABASE = True
except ModuleNotFoundError as e:
    # quantum_core not available → database tests will skip
    # but unit tests (cache, etc.) can still run
    if "quantum_core" in str(e):
        Base = None
        PredictionORM = None
        HAS_DATABASE = False
    else:
        raise  # Re-raise if it's not a quantum_core issue

from infrastructure.config.settings import Settings
from api.main import app
# from tests.factories import (
#     create_market_prediction,
#     create_ensemble_realistic,
# )


# ─────────────────────────────────────────────────────────────────────────
# FIXTURES - FastAPI Client (legacy)
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture(scope="session")
def anyio_backend():
    """Configuration for pytest-anyio."""
    return "asyncio"


# ─────────────────────────────────────────────────────────────────────────
# FIXTURES - Test Data (ADR #007)
# ─────────────────────────────────────────────────────────────────────────


# @pytest.fixture
# def sample_market_prediction():
#     """Fixture: Sample MarketPrediction."""
#     return create_market_prediction(
#         match_id="psg_om_2024",
#         fair_odds=1.85,
#         confidence_score=0.82,
#     )


# @pytest.fixture
# def sample_ensemble():
#     """Fixture: Sample EnsemblePrediction (realistic)."""
#     return create_ensemble_realistic(
#         match_id="psg_om_2024",
#         base_odds=1.85,
#         variance=0.05,
#     )


# @pytest.fixture
# def sample_ensemble_low_confidence():
#     """Fixture: Ensemble with low confidence (high disagreement)."""
#     return create_ensemble_realistic(
#         match_id="uncertain_match",
#         base_odds=1.85,
#         variance=0.30,  # High variance = low agreement
#     )


# ─────────────────────────────────────────────────────────────────────────
# FIXTURES - Database (in-memory SQLite)
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def db_engine():
    """Create in-memory SQLite engine for tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create tables
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create database session for tests."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()

    yield session

    session.close()


# ─────────────────────────────────────────────────────────────────────────
# FIXTURES - Settings
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def test_settings():
    """Test settings (override defaults)."""
    return Settings(
        environment="test",
        debug=True,
        database_url="sqlite:///:memory:",
        cache_enabled=False,
        min_confidence_threshold=0.70,
        max_prediction_days=60,
    )


# ═══════════════════════════════════════════════════════════════════
# TEST ISOLATION - Hedge Fund Pattern
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Reset Settings singleton cache between tests.

    Critical: Prevents state pollution across tests.
    Pattern: autouse ensures ALL tests benefit from isolation.
    """
    try:
        from backend.infrastructure.config.dependencies import get_settings
        # Clear before test
        get_settings.cache_clear()
        yield
        # Clear after test (defensive)
        get_settings.cache_clear()
    except ImportError:
        # If infrastructure.config doesn't exist, skip
        yield


@pytest.fixture
def isolated_env(monkeypatch):
    """Provide clean environment for deterministic tests."""
    env_vars = [
        "ENVIRONMENT",
        "DEBUG",
        "DATABASE_URL",
        "CACHE_ENABLED",
        "MIN_CONFIDENCE_THRESHOLD",
        "MAX_PREDICTION_DAYS",
        "LOG_LEVEL",
    ]

    for var in env_vars:
        monkeypatch.delenv(var, raising=False)

    yield


@pytest.fixture
def prod_env(monkeypatch):
    """Simulate production environment."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("MIN_CONFIDENCE_THRESHOLD", "0.85")

    yield


# ═══════════════════════════════════════════════════════════════════
# CACHE FIXTURES - SmartCache Integration
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def disable_cache(monkeypatch):
    """Disable SmartCache for tests (always cache miss).

    Use this fixture in tests that should not use cache,
    or to ensure tests are deterministic.

    Example:
        def test_something(disable_cache):
            # Cache is disabled, always computes fresh
            result = repository.calculate_predictions(...)
    """
    from unittest.mock import MagicMock

    mock_cache = MagicMock()
    mock_cache.get.return_value = (None, False)  # Always cache miss
    mock_cache.set.return_value = True
    mock_cache.enabled = False

    monkeypatch.setattr("api.v1.brain.repository.smart_cache", mock_cache)

    return mock_cache
