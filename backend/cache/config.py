"""Redis cache configuration - Production Grade"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class CacheConfig(BaseSettings):
    """Cache configuration from environment"""

    # Redis connection
    redis_url: str = "redis://:monps_redis_dev_password_change_in_prod@monps_redis:6379/0"
    redis_socket_timeout: float = 3.0
    redis_socket_connect_timeout: float = 3.0

    # Connection pool
    redis_max_connections: int = 50
    redis_health_check_interval: int = 15

    # Cache behavior
    cache_default_ttl: int = 3600  # 1 hour
    cache_enabled: bool = True

    # X-Fetch algorithm
    xfetch_beta: float = 1.0  # Tuning parameter

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars
    )


cache_config = CacheConfig()
