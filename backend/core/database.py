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

# VIX Pattern: Log only on state changes, not every operation
# This reduces logging noise and improves performance

# Track pool state to detect changes
_pool_state = {
    "checked_out": 0,
    "overflow": 0,
    "total_connects": 0,
}


@event.listens_for(sync_engine, "connect")
def on_connect(dbapi_connection, connection_record):
    """Log new database connections (state change only)."""
    _pool_state["total_connects"] += 1
    # Only log every 10th connection to reduce noise
    if _pool_state["total_connects"] % 10 == 1:
        logger.info(
            "database_connections_established",
            total=_pool_state["total_connects"],
        )


@event.listens_for(sync_engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout (on overflow only - VIX pattern)."""
    pool = sync_engine.pool
    current_checked_out = pool.checkedout()
    current_overflow = pool.overflow()

    # Log only if we entered overflow state (high load indicator)
    if current_overflow > _pool_state["overflow"]:
        logger.warning(
            "database_pool_overflow",
            checked_out=current_checked_out,
            overflow=current_overflow,
            pool_size=pool.size(),
        )

    _pool_state["checked_out"] = current_checked_out
    _pool_state["overflow"] = current_overflow


@event.listens_for(sync_engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
    """Log connection return (on overflow recovery only - VIX pattern)."""
    pool = sync_engine.pool
    current_overflow = pool.overflow()

    # Log only if we exited overflow state (recovery indicator)
    if _pool_state["overflow"] > 0 and current_overflow == 0:
        logger.info(
            "database_pool_recovered",
            checked_out=pool.checkedout(),
            pool_size=pool.size(),
        )

    _pool_state["overflow"] = current_overflow
