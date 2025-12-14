"""FastAPI Application - Mon_PS Hedge Fund Grade 2.0.

Architecture professionnelle avec:
- Layered architecture (API/Service/Domain/Data)
- Dependency Injection
- Exception handling global
- CORS configuré
- Logging structuré
- Rate limiting
- Health checks
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
import time
from typing import Any

from quantum_core.api.predictions.routes import router as predictions_router
from quantum_core.api.common.exceptions import (
    MonPSException,
    LowConfidenceError,
    UnifiedBrainError,
)
from quantum_core.api.lifespan import lifespan

# ─────────────────────────────────────────────────────────────────────────
# LOGGING CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────
# FASTAPI APP INSTANCE
# ─────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Mon_PS API",
    description="Quantitative Sports Betting Platform - Hedge Fund Grade 2.0",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────────────────────────────────
# CORS MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────
# REQUEST TIMING MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────────


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to all responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# ─────────────────────────────────────────────────────────────────────────
# EXCEPTION HANDLERS
# ─────────────────────────────────────────────────────────────────────────


@app.exception_handler(MonPSException)
async def monps_exception_handler(request: Request, exc: MonPSException):
    """Handle custom MonPS exceptions."""
    logger.error(f"MonPS Exception: {exc.detail}", exc_info=exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code},
    )


@app.exception_handler(LowConfidenceError)
async def low_confidence_exception_handler(request: Request, exc: LowConfidenceError):
    """Handle low confidence predictions."""
    logger.warning(f"Low confidence prediction: {exc.detail}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.detail, "error_code": "LOW_CONFIDENCE"},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "error_code": "VALIDATION_ERROR"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    logger.exception(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
    )


# ─────────────────────────────────────────────────────────────────────────
# ROUTERS
# ─────────────────────────────────────────────────────────────────────────

app.include_router(
    predictions_router,
    prefix="/api/v1/predictions",
    tags=["Predictions"],
)

# ─────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "api": "Mon_PS Hedge Fund Grade 2.0",
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "message": "Mon_PS API - Hedge Fund Grade 2.0",
        "docs": "/api/docs",
        "health": "/health",
    }


# ─────────────────────────────────────────────────────────────────────────
# LIFECYCLE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────
# ADR #005: Lifespan events (startup/shutdown) moved to lifespan.py
# Using modern FastAPI lifespan context manager instead of deprecated
# @app.on_event("startup") and @app.on_event("shutdown")
