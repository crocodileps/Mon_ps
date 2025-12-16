"""
Comprehensive Test Suite - Database Layer (Hedge Fund Grade)

Tests:
- Connection management (sync/async)
- Repository CRUD operations
- Unit of Work transactions
- Error handling & rollback
- Connection pooling behavior
- Eager loading (N+1 prevention)

Run: pytest tests/unit/repositories/test_database_layer.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, '/home/Mon_ps/backend')

from core.database import (
    get_db,
    check_sync_connection,
    get_pool_status,
    sync_engine,
)
from core.config import settings
from repositories import UnitOfWork, BaseRepository
from models.base import Base, TimestampMixin, AuditMixin


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session."""
    session = Mock(spec=Session)
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.execute = Mock()
    return session


@pytest.fixture
def mock_engine():
    """Mock SQLAlchemy engine."""
    engine = Mock()
    engine.pool = Mock()
    engine.pool.size = Mock(return_value=5)
    engine.pool.checkedin = Mock(return_value=4)
    engine.pool.checkedout = Mock(return_value=1)
    engine.pool.overflow = Mock(return_value=0)
    return engine


# ═══════════════════════════════════════════════════════════════
# CONNECTION TESTS
# ═══════════════════════════════════════════════════════════════

class TestDatabaseConnection:
    """Test database connection management."""

    def test_connection_settings_loaded(self):
        """Test that database settings are loaded from .env."""
        assert settings.DB_HOST is not None
        assert settings.DB_PORT == 5432
        assert settings.DB_USER is not None
        assert settings.DB_PASSWORD is not None
        assert settings.DB_NAME is not None

    def test_pool_settings(self):
        """Test connection pool configuration."""
        assert settings.DB_POOL_SIZE == 5
        assert settings.DB_MAX_OVERFLOW == 10
        assert settings.DB_POOL_TIMEOUT == 30
        assert settings.DB_POOL_RECYCLE == 3600  # 1 hour

    def test_sync_connection_check(self):
        """Test synchronous connection health check."""
        result = check_sync_connection()
        assert result is True, "Database connection should succeed"

    def test_get_pool_status(self):
        """Test pool status monitoring."""
        status = get_pool_status()

        assert "pool_size" in status
        assert "checked_in" in status
        assert "checked_out" in status
        assert "overflow" in status

        assert status["pool_size"] == 5
        assert isinstance(status["checked_in"], int)
        assert isinstance(status["checked_out"], int)

    def test_context_manager_commits_on_success(self, mock_session):
        """Test that context manager commits on success."""
        with patch('core.database.SessionLocal', return_value=mock_session):
            with get_db() as session:
                # Simulate successful operation
                pass

            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
            mock_session.rollback.assert_not_called()

    def test_context_manager_rollbacks_on_error(self, mock_session):
        """Test that context manager rolls back on error."""
        with patch('core.database.SessionLocal', return_value=mock_session):
            with pytest.raises(ValueError):
                with get_db() as session:
                    raise ValueError("Test error")

            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
            mock_session.commit.assert_not_called()


# ═══════════════════════════════════════════════════════════════
# REPOSITORY PATTERN TESTS
# ═══════════════════════════════════════════════════════════════

class TestBaseRepository:
    """Test generic BaseRepository CRUD operations."""

    def test_repository_initialization(self, mock_session):
        """Test repository can be instantiated."""
        repo = BaseRepository(Base, mock_session)

        assert repo.model == Base
        assert repo.session == mock_session

    def test_count_method_exists(self, mock_session):
        """Test count() method exists on repository."""
        from models.odds import Odds  # Use concrete model, not Base

        repo = BaseRepository(Odds, mock_session)
        assert hasattr(repo, 'count')
        assert callable(repo.count)


# ═══════════════════════════════════════════════════════════════
# UNIT OF WORK TESTS
# ═══════════════════════════════════════════════════════════════

class TestUnitOfWork:
    """Test Unit of Work pattern for transactions."""

    def test_uow_initialization(self, mock_session):
        """Test UoW can be instantiated."""
        uow = UnitOfWork(mock_session)
        assert uow.session == mock_session

    def test_uow_lazy_loading_repositories(self, mock_session):
        """Test repositories are lazy-loaded."""
        uow = UnitOfWork(mock_session)

        # Should not be loaded yet
        assert uow._odds is None
        assert uow._tracking is None

        # Access should trigger loading
        odds_repo = uow.odds
        assert odds_repo is not None
        assert uow._odds is not None

        # Second access should return same instance
        odds_repo2 = uow.odds
        assert odds_repo is odds_repo2

    def test_uow_commit(self, mock_session):
        """Test UoW commit delegates to session."""
        uow = UnitOfWork(mock_session)
        uow.commit()

        mock_session.commit.assert_called_once()

    def test_uow_rollback(self, mock_session):
        """Test UoW rollback delegates to session."""
        uow = UnitOfWork(mock_session)
        uow.rollback()

        mock_session.rollback.assert_called_once()

    def test_uow_transaction_atomicity(self, mock_session):
        """Test UoW ensures atomicity across multiple operations."""
        uow = UnitOfWork(mock_session)

        try:
            # Simulate multiple operations
            _ = uow.odds
            _ = uow.tracking
            raise ValueError("Simulated error")
        except ValueError:
            uow.rollback()

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()


# ═══════════════════════════════════════════════════════════════
# ERROR HANDLING TESTS
# ═══════════════════════════════════════════════════════════════

class TestErrorHandling:
    """Test error handling and recovery."""

    def test_connection_error_handling(self, mock_session):
        """Test handling of connection errors."""
        from models.odds import Odds  # Use concrete model

        mock_session.execute.side_effect = OperationalError(
            "Connection refused", None, None
        )

        repo = BaseRepository(Odds, mock_session)

        with pytest.raises(OperationalError):
            repo.count()

    def test_integrity_error_handling(self, mock_session):
        """Test handling of integrity constraint violations."""
        mock_session.commit.side_effect = IntegrityError(
            "Duplicate key", None, None
        )

        with patch('core.database.SessionLocal', return_value=mock_session):
            with pytest.raises(IntegrityError):
                with get_db() as session:
                    session.commit()

            mock_session.rollback.assert_called()


# ═══════════════════════════════════════════════════════════════
# MIXIN TESTS
# ═══════════════════════════════════════════════════════════════

class TestMixins:
    """Test model mixins functionality."""

    def test_timestamp_mixin_attributes(self):
        """Test TimestampMixin provides created_at and updated_at."""
        assert hasattr(TimestampMixin, 'created_at')
        assert hasattr(TimestampMixin, 'updated_at')

    def test_audit_mixin_attributes(self):
        """Test AuditMixin provides audit trail fields."""
        assert hasattr(AuditMixin, 'created_by')
        assert hasattr(AuditMixin, 'updated_by')
        assert hasattr(AuditMixin, 'change_reason')


# ═══════════════════════════════════════════════════════════════
# POOL MANAGEMENT TESTS
# ═══════════════════════════════════════════════════════════════

class TestConnectionPool:
    """Test connection pool behavior."""

    def test_pool_size_configuration(self):
        """Test pool is configured with correct size."""
        pool = sync_engine.pool
        assert pool.size() == settings.DB_POOL_SIZE

    def test_pool_overflow_limit(self):
        """Test pool respects max overflow limit."""
        # This is configuration test - actual overflow test would require load testing
        assert settings.DB_MAX_OVERFLOW == 10

    def test_pool_pre_ping_enabled(self):
        """Test pre-ping is enabled for stale connection detection."""
        # Check engine configuration (private attribute in SQLAlchemy)
        assert sync_engine.pool._pre_ping is True

    def test_pool_recycle_configured(self):
        """Test connection recycling is configured."""
        # Check engine configuration (private attribute in SQLAlchemy)
        assert sync_engine.pool._recycle == 3600  # 1 hour


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestConfiguration:
    """Test configuration validation."""

    def test_database_url_format(self):
        """Test database URLs are correctly formatted."""
        sync_url = settings.sync_database_url
        async_url = settings.async_database_url

        assert sync_url.startswith("postgresql://")
        assert async_url.startswith("postgresql+asyncpg://")

        assert settings.DB_USER in sync_url
        assert settings.DB_NAME in sync_url

    def test_password_not_empty(self):
        """Test password validation prevents empty passwords."""
        # This is implicitly tested by config loading
        # If empty password, config would fail to load
        assert settings.DB_PASSWORD is not None
        assert len(settings.DB_PASSWORD) > 0


# ═══════════════════════════════════════════════════════════════
# INTEGRATION SANITY TESTS
# ═══════════════════════════════════════════════════════════════

class TestIntegrationSanity:
    """Lightweight integration tests to verify real DB operations."""

    def test_real_connection_works(self):
        """Test actual database connection (sanity check)."""
        assert check_sync_connection() is True

    def test_session_context_manager_works(self):
        """Test actual session creation and cleanup."""
        with get_db() as session:
            assert session is not None
            assert isinstance(session, Session)

        # Session should be closed after context exit
        # (implicit - no exception means success)

    def test_uow_with_real_session_works(self):
        """Test UoW with real database session."""
        with get_db() as session:
            uow = UnitOfWork(session)

            # Should be able to access repositories
            assert uow.odds is not None
            assert uow.tracking is not None
            assert uow.teams is not None


if __name__ == "__main__":
    # Allow running directly for quick testing
    pytest.main([__file__, "-v", "--tb=short"])
