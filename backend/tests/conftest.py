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

from quantum_core.database.base import Base
from quantum_core.database.models import PredictionORM
from quantum_core.config.settings import Settings
from quantum_core.api.main import app
from tests.factories import (
    create_market_prediction,
    create_ensemble_realistic,
)


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


@pytest.fixture
def sample_market_prediction():
    """Fixture: Sample MarketPrediction."""
    return create_market_prediction(
        match_id="psg_om_2024",
        fair_odds=1.85,
        confidence_score=0.82,
    )


@pytest.fixture
def sample_ensemble():
    """Fixture: Sample EnsemblePrediction (realistic)."""
    return create_ensemble_realistic(
        match_id="psg_om_2024",
        base_odds=1.85,
        variance=0.05,
    )


@pytest.fixture
def sample_ensemble_low_confidence():
    """Fixture: Ensemble with low confidence (high disagreement)."""
    return create_ensemble_realistic(
        match_id="uncertain_match",
        base_odds=1.85,
        variance=0.30,  # High variance = low agreement
    )


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
    from quantum_core.config.dependencies import get_settings

    # Clear before test
    get_settings.cache_clear()

    yield

    # Clear after test (defensive)
    get_settings.cache_clear()


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
