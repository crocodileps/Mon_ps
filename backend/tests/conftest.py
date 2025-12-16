"""
Test Configuration - Mon_PS Hedge Fund Grade

Provides fixtures and configuration for pytest.
Handles optional dependencies gracefully.
"""

import os
import sys
import pytest

# Add backend to path
sys.path.insert(0, '/home/Mon_ps/backend')

# Environment setup for tests
os.environ.setdefault("TESTING", "true")

# ═══════════════════════════════════════════════════════════════
# OPTIONAL IMPORTS (graceful degradation)
# ═══════════════════════════════════════════════════════════════

# Try to import FastAPI test client (requires httpx)
try:
    from fastapi.testclient import TestClient
    FASTAPI_AVAILABLE = True
except (ImportError, RuntimeError) as e:
    TestClient = None
    FASTAPI_AVAILABLE = False
    print(f"⚠️  FastAPI TestClient not available: {e}")


# ═══════════════════════════════════════════════════════════════
# DATABASE FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def db_settings():
    """Get database settings for tests."""
    from core.config import get_settings
    return get_settings()


@pytest.fixture(scope="function")
def db_session():
    """
    Provide a database session for tests.

    Automatically rolls back after each test to keep DB clean.
    """
    from core.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def async_db_session():
    """
    Provide an async database session for tests.

    Note: Must be used with pytest-asyncio.
    """
    import asyncio
    from core.database import AsyncSessionLocal

    async def get_session():
        async with AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.rollback()

    return get_session


# ═══════════════════════════════════════════════════════════════
# FASTAPI FIXTURES (conditional)
# ═══════════════════════════════════════════════════════════════

if FASTAPI_AVAILABLE:
    @pytest.fixture(scope="module")
    def test_client():
        """
        Provide a FastAPI test client.

        Only available if httpx is installed.
        """
        # Import your FastAPI app here
        # from main import app
        # return TestClient(app)
        pytest.skip("FastAPI app not configured for testing")


# ═══════════════════════════════════════════════════════════════
# UNIT OF WORK FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="function")
def unit_of_work(db_session):
    """Provide a Unit of Work instance for tests."""
    from repositories.unit_of_work import UnitOfWork
    return UnitOfWork(db_session)


# ═══════════════════════════════════════════════════════════════
# MOCK FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_session():
    """Provide a mock database session for unit tests."""
    from unittest.mock import Mock, MagicMock

    session = MagicMock()
    session.execute = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.add = Mock()
    session.flush = Mock()
    session.refresh = Mock()

    return session


# ═══════════════════════════════════════════════════════════════
# LEGACY FIXTURES (Restored for test_settings.py compatibility)
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(autouse=False)
def reset_settings_cache():
    """Reset Settings singleton cache between tests.

    Critical: Prevents state pollution across tests.
    """
    try:
        from infrastructure.config.dependencies import get_settings
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()
    except ImportError:
        yield


@pytest.fixture
def isolated_env(monkeypatch):
    """Provide clean environment for deterministic tests.

    Used by: tests/test_infrastructure/test_settings.py
    """
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
    """Simulate production environment.

    Used by: tests/test_infrastructure/test_settings.py
    """
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("MIN_CONFIDENCE_THRESHOLD", "0.85")

    yield


@pytest.fixture
def test_settings():
    """Test settings (override defaults).

    Provides Settings instance for tests that need it.
    """
    try:
        from infrastructure.config.settings import Settings
        return Settings(
            environment="test",
            debug=True,
            database_url="sqlite:///:memory:",
            cache_enabled=False,
            min_confidence_threshold=0.70,
            max_prediction_days=60,
        )
    except ImportError:
        pytest.skip("Settings not available")


@pytest.fixture
def disable_cache(monkeypatch):
    """Disable SmartCache for tests (always cache miss)."""
    from unittest.mock import MagicMock

    mock_cache = MagicMock()
    mock_cache.get.return_value = (None, False)
    mock_cache.set.return_value = True
    mock_cache.enabled = False

    try:
        monkeypatch.setattr("api.v1.brain.repository.smart_cache", mock_cache)
    except (ImportError, AttributeError):
        pass

    return mock_cache
