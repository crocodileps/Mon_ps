"""
Configuration Ghost Scraper
═══════════════════════════════════════════════════════════════════════════
Stratégie "Low & Slow" - Indétectable par Cloudflare
═══════════════════════════════════════════════════════════════════════════
"""
from dataclasses import dataclass
from typing import List

@dataclass
class ScraperConfig:
    """Configuration pour le Ghost Scraper."""

    # Impersonation Chrome (curl_cffi)
    IMPERSONATE: str = "chrome110"

    # Timeouts
    REQUEST_TIMEOUT: int = 30

    # Délais entre requêtes (secondes)
    MIN_DELAY: float = 15.0
    MAX_DELAY: float = 45.0

    # Volatilité (parfois pause café)
    VOLATILITY_MULTIPLIERS: List[float] = None

    # Retry policy
    MAX_RETRIES: int = 3
    BACKOFF_MIN_SECONDS: int = 60      # 1 minute minimum
    BACKOFF_MAX_SECONDS: int = 300     # 5 minutes maximum
    BACKOFF_MULTIPLIER: int = 2        # Exponentiel

    # Detection patterns
    CLOUDFLARE_CHALLENGE_TEXT: str = "Just a moment..."
    BLOCKED_STATUS_CODES: List[int] = None

    def __post_init__(self):
        if self.VOLATILITY_MULTIPLIERS is None:
            self.VOLATILITY_MULTIPLIERS = [1, 1, 1, 2, 5]
        if self.BLOCKED_STATUS_CODES is None:
            self.BLOCKED_STATUS_CODES = [403, 429, 503]


# Instance par défaut
DEFAULT_CONFIG = ScraperConfig()
