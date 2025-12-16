"""
Database Configuration - Mon_PS Hedge Fund Grade

Centralized configuration using Pydantic Settings.
Supports both sync (psycopg2) and async (asyncpg) connections.
"""

from functools import lru_cache
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """
    Database configuration with environment variable support.

    Environment variables (REQUIRED in .env):
        - DB_HOST: PostgreSQL host (default: localhost)
        - DB_PORT: PostgreSQL port (default: 5432)
        - DB_USER: Database user (REQUIRED, no default)
        - DB_PASSWORD: Database password (REQUIRED, no default)
        - DB_NAME: Database name (REQUIRED, no default)
        - DB_POOL_SIZE: Connection pool size (default: 5)
        - DB_MAX_OVERFLOW: Max overflow connections (default: 10)
        - DB_ECHO: Echo SQL statements (default: False)
    """

    # Database connection
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str  # REQUIRED - Must be in .env
    DB_PASSWORD: str  # REQUIRED - Must be in .env
    DB_NAME: str  # REQUIRED - Must be in .env

    # Connection pool settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600  # 1 hour (increased from 30 min for stability)

    # Debug settings
    DB_ECHO: bool = False

    @field_validator("DB_PASSWORD")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Ensure DB_PASSWORD is not empty."""
        if not v or v.strip() == "":
            raise ValueError(
                "DB_PASSWORD cannot be empty. Set it in .env file. "
                "See .env.example for configuration template."
            )
        return v

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
