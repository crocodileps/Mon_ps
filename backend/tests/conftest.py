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
