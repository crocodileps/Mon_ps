"""Application Settings - Centralized Configuration.

ADR #005: Dependency Injection & Lifecycle Management.

Architecture:
- Pydantic BaseSettings for validation
- Environment variables (.env file)
- Type safety (mypy compliant)
- Default values sensibles
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from datetime import timezone
from typing import Optional


class Settings(BaseSettings):
    """Application configuration - Hedge Fund Grade.

    Loaded from environment variables with defaults.
    Validated at startup (fail fast if misconfigured).

    Usage:
        from quantum_core.config.dependencies import get_settings
        settings = get_settings()  # Singleton
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from .env (API keys, etc.)
    )

    # ─────────────────────────────────────────────────────────────────────
    # APPLICATION
    # ─────────────────────────────────────────────────────────────────────

    app_name: str = "Mon_PS API"
    app_version: str = "2.0.0"
    environment: str = "development"  # development, staging, production
    debug: bool = False

    # ─────────────────────────────────────────────────────────────────────
    # API
    # ─────────────────────────────────────────────────────────────────────

    api_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS
    cors_origins: list[str] = ["*"]  # TODO: Restrict in production
    cors_allow_credentials: bool = True

    # ─────────────────────────────────────────────────────────────────────
    # TIMEZONE (ADR #005 - Fix timezone naive bug)
    # ─────────────────────────────────────────────────────────────────────

    default_timezone: timezone = timezone.utc

    # ─────────────────────────────────────────────────────────────────────
    # PREDICTIONS
    # ─────────────────────────────────────────────────────────────────────

    min_confidence_threshold: float = Field(
        default=0.70, ge=0.0, le=1.0, description="Minimum consensus threshold (probability)"
    )
    max_prediction_days: int = Field(
        default=60, gt=0, description="Maximum days in future for predictions"
    )

    # ─────────────────────────────────────────────────────────────────────
    # DATABASE
    # ─────────────────────────────────────────────────────────────────────

    database_url: str = "postgresql://monps:monps@localhost:5432/monps"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_echo: bool = False  # SQL logging

    # ─────────────────────────────────────────────────────────────────────
    # REDIS (Cache)
    # ─────────────────────────────────────────────────────────────────────

    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 3600  # 1 hour default TTL
    cache_enabled: bool = True

    # ─────────────────────────────────────────────────────────────────────
    # OBSERVABILITY (ADR #006)
    # ─────────────────────────────────────────────────────────────────────

    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_format: str = "json"  # json, text

    # Prometheus
    prometheus_enabled: bool = True
    prometheus_port: int = 9090

    # OpenTelemetry
    otel_enabled: bool = True
    otel_service_name: str = "monps-api"
    otel_exporter_endpoint: Optional[str] = None  # Jaeger/Tempo endpoint

    # ─────────────────────────────────────────────────────────────────────
    # PERFORMANCE
    # ─────────────────────────────────────────────────────────────────────

    service_singleton: bool = True  # Singleton services (ADR #005)

    # ─────────────────────────────────────────────────────────────────────
    # SECURITY
    # ─────────────────────────────────────────────────────────────────────

    secret_key: str = "dev-secret-key-change-in-production"  # TODO: Generate secure key
    api_key_enabled: bool = False  # TODO: Enable in production
