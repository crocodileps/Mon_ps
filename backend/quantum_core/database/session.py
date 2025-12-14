"""Database session management.

ADR #005: Request-scoped database sessions.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from quantum_core.config.dependencies import get_settings

settings = get_settings()

# Engine (singleton)
engine = create_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.database_echo,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session (request-scoped).

    FastAPI dependency for DB session injection.

    Yields:
        SQLAlchemy session

    Usage:
        @router.post("/endpoint")
        async def endpoint(db: Session = Depends(get_db)):
            # Use db session
            pass
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
