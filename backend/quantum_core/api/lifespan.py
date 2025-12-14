"""FastAPI Lifespan Events.

ADR #005: Application lifecycle management.

Architecture:
- startup: Initialize services (singleton pattern)
- shutdown: Cleanup resources (connections, etc.)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

from quantum_core.config.dependencies import (
    get_settings,
    get_prediction_service,
    cleanup_services,
)
from quantum_core.observability.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager.

    Startup:
    - Load settings
    - Setup logging
    - Initialize singleton services
    - Warm up ML agents

    Shutdown:
    - Close DB connections
    - Save state if needed
    - Cleanup resources

    Usage:
        app = FastAPI(lifespan=lifespan)
    """

    # ─────────────────────────────────────────────────────────────────────
    # STARTUP
    # ─────────────────────────────────────────────────────────────────────

    logger.info("🚀 Starting Mon_PS API - Hedge Fund Grade 2.0")

    # Load settings
    settings = get_settings()
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug: {settings.debug}")

    # Setup logging (structured)
    setup_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
    )
    logger.info("✅ Logging configured")

    # Initialize singleton services (ADR #005)
    try:
        prediction_service = get_prediction_service()
        logger.info("✅ PredictionService initialized (singleton)")

        # TODO: Initialize database
        # await init_database(settings.database_url)
        # logger.info("✅ Database connected")

        # TODO: Initialize Redis
        # await init_redis(settings.redis_url)
        # logger.info("✅ Redis connected")

        # TODO: Warm up ML agents
        # await prediction_service.warmup()
        # logger.info("✅ ML agents warmed up")

    except Exception as e:
        logger.exception(f"❌ Startup failed: {e}")
        raise

    logger.info("✅ Mon_PS API started successfully")

    # ─────────────────────────────────────────────────────────────────────
    # APPLICATION RUNNING
    # ─────────────────────────────────────────────────────────────────────

    yield  # Application runs here

    # ─────────────────────────────────────────────────────────────────────
    # SHUTDOWN
    # ─────────────────────────────────────────────────────────────────────

    logger.info("👋 Shutting down Mon_PS API")

    try:
        # Cleanup services
        cleanup_services()
        logger.info("✅ Services cleaned up")

        # TODO: Close database connections
        # await close_database()
        # logger.info("✅ Database disconnected")

        # TODO: Close Redis
        # await close_redis()
        # logger.info("✅ Redis disconnected")

    except Exception as e:
        logger.exception(f"⚠️  Shutdown error (non-fatal): {e}")

    logger.info("✅ Mon_PS API shutdown complete")
