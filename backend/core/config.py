"""
Database Configuration - Mon_PS Hedge Fund Grade

Centralized configuration using Pydantic Settings.
Supports both sync (psycopg2) and async (asyncpg) connections.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """
    Database configuration with environment variable support.

    Environment variables:
        - DB_HOST: PostgreSQL host (default: localhost)
        - DB_PORT: PostgreSQL port (default: 5432)
        - DB_USER: Database user (default: monps)
        - DB_PASSWORD: Database password (default: monps)
        - DB_NAME: Database name (default: monps)
        - DB_POOL_SIZE: Connection pool size (default: 5)
        - DB_MAX_OVERFLOW: Max overflow connections (default: 10)
        - DB_ECHO: Echo SQL statements (default: False)
    """

    # Database connection
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "monps_user"
    DB_PASSWORD: str = "monps_secure_password_2024"
    DB_NAME: str = "monps_db"

    # Connection pool settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # 30 minutes

    # Debug settings
    DB_ECHO: bool = False

    @property
    def sync_database_url(self) -> str:
        """Synchronous database URL (psycopg2)."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def async_database_url(self) -> str:
        """Asynchronous database URL (asyncpg)."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",  # Ignore extra env variables not in model
    }


@lru_cache()
def get_settings() -> DatabaseSettings:
    """
    Get cached database settings.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return DatabaseSettings()


# Convenience export
settings = get_settings()
