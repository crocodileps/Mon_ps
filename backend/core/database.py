"""
Database Engine & Session Management - Mon_PS Hedge Fund Grade

Provides:
- Synchronous engine and session (for compatibility)
- Asynchronous engine and session (for new code)
- Connection pooling with health checks
- Context managers for safe session handling
"""

from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from core.config import settings
import structlog

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
# SYNCHRONOUS ENGINE (Backward compatible with existing code)
# ═══════════════════════════════════════════════════════════════

sync_engine = create_engine(
    settings.sync_database_url,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Health check before using connection
    echo=settings.DB_ECHO,
)

# Session factory for sync operations
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_db() as db:
            result = db.query(Model).all()

    Automatically handles commit/rollback and session cleanup.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error("database_session_error", error=str(e))
        raise
    finally:
        session.close()


def get_db_dependency() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db_dependency)):
            return db.query(Item).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════
# ASYNCHRONOUS ENGINE (For new high-performance code)
# ═══════════════════════════════════════════════════════════════

async_engine = create_async_engine(
    settings.async_database_url,
    # poolclass auto-selected for async (AsyncAdaptedQueuePool)
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DB_ECHO,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.

    Usage:
        async with get_async_db() as db:
            result = await db.execute(select(Model))
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error("async_database_session_error", error=str(e))
        raise
    finally:
        await session.close()


async def get_async_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI async dependency for database sessions.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db_dependency)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


# ═══════════════════════════════════════════════════════════════
# HEALTH CHECKS
# ═══════════════════════════════════════════════════════════════

def check_sync_connection() -> bool:
    """Check synchronous database connection."""
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("sync_connection_check_failed", error=str(e))
        return False


async def check_async_connection() -> bool:
    """Check asynchronous database connection."""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("async_connection_check_failed", error=str(e))
        return False


def get_pool_status() -> dict:
    """Get connection pool status for monitoring."""
    pool = sync_engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalidatedcount() if hasattr(pool, 'invalidatedcount') else 0,
    }


# ═══════════════════════════════════════════════════════════════
# EVENT LISTENERS (Logging & Monitoring)
# ═══════════════════════════════════════════════════════════════

@event.listens_for(sync_engine, "connect")
def on_connect(dbapi_connection, connection_record):
    """Log new database connections."""
    logger.debug("database_connection_established")


@event.listens_for(sync_engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkouts from pool."""
    logger.debug("database_connection_checkout")


@event.listens_for(sync_engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
    """Log connection returns to pool."""
    logger.debug("database_connection_checkin")
