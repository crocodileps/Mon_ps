"""Dependency Injection Container.

ADR #005: Centralized dependency management.

Architecture:
- Singleton pattern for services
- FastAPI Depends() integration
- Easy testing (mock injection)
"""

from functools import lru_cache
from typing import Optional
from quantum_core.config.settings import Settings

# ─────────────────────────────────────────────────────────────────────────
# SETTINGS (Singleton)
# ─────────────────────────────────────────────────────────────────────────


@lru_cache()
def get_settings() -> Settings:
    """Get Settings singleton.

    Cached with lru_cache (1 instance per application).

    Returns:
        Settings instance (validated)
    """
    return Settings()


# ─────────────────────────────────────────────────────────────────────────
# SERVICES (Singletons - ADR #005)
# ─────────────────────────────────────────────────────────────────────────

# Service instances cache
_services: dict = {}


def get_prediction_service(db_session=None):
    """Get PredictionService singleton.

    ADR #005: Fix service instantiation bug.
    ADR #008: Inject repository (layered architecture).

    Args:
        db_session: Database session (optional - for repository injection)

    Returns:
        PredictionService (singleton)
    """
    from quantum_core.api.predictions.service import PredictionService

    if "prediction" not in _services:
        settings = get_settings()

        # Create repository if DB session provided
        repository = None
        if db_session is not None:
            from quantum_core.repositories.prediction_repository import (
                PostgresPredictionRepository,
            )

            repository = PostgresPredictionRepository(db_session)

        _services["prediction"] = PredictionService(
            repository=repository,
            min_confidence=settings.min_confidence_threshold,
            max_prediction_days=settings.max_prediction_days,
            default_tz=settings.default_timezone,
        )

    return _services["prediction"]


def get_health_check_service():
    """Get HealthCheckService singleton.

    Returns:
        HealthCheckService (singleton)
    """
    # TODO: Implement HealthCheckService
    # from quantum_core.observability.health import HealthCheckService
    #
    # if "health" not in _services:
    #     _services["health"] = HealthCheckService()
    #
    # return _services["health"]
    pass


# ─────────────────────────────────────────────────────────────────────────
# DATABASE (Request-scoped)
# ─────────────────────────────────────────────────────────────────────────


async def get_db_session():
    """Get database session (request-scoped).

    Yields:
        SQLAlchemy session

    Note:
        Automatically commits/rollbacks and closes session.
    """
    # TODO: Implement with SQLAlchemy
    # from quantum_core.database import SessionLocal
    # db = SessionLocal()
    # try:
    #     yield db
    #     await db.commit()
    # except Exception:
    #     await db.rollback()
    #     raise
    # finally:
    #     await db.close()
    pass


# ─────────────────────────────────────────────────────────────────────────
# REPOSITORIES (Request-scoped with DB session)
# ─────────────────────────────────────────────────────────────────────────


def get_prediction_repository(db_session=None):
    """Get PredictionRepository (request-scoped).

    Args:
        db_session: SQLAlchemy session (injected)

    Returns:
        PredictionRepository instance
    """
    # TODO: Implement
    # from quantum_core.repositories.prediction_repository import (
    #     PostgresPredictionRepository,
    #     RedisCachedPredictionRepository,
    # )
    #
    # # Base repository (PostgreSQL)
    # base_repo = PostgresPredictionRepository(db_session)
    #
    # # Wrapped with Redis cache
    # if get_settings().cache_enabled:
    #     return RedisCachedPredictionRepository(base_repo, redis_client)
    #
    # return base_repo
    pass


# ─────────────────────────────────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────────────────────────────────


def cleanup_services():
    """Cleanup services on shutdown.

    Called by FastAPI lifespan shutdown event.
    """
    global _services

    # Close agents, DB connections, etc.
    for service_name, service in _services.items():
        if hasattr(service, "cleanup"):
            service.cleanup()

    _services.clear()
