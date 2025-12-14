"""
KeyFactory - Centralized Redis Key Generation
Institutional Grade Pattern (Twitter/LinkedIn standard)

Features:
- Canonical IDs (not entity names → avoid string hell)
- XXHash variants (config-aware caching)
- Cluster Hash Tags (Redis Cluster affinity)
- Namespace versioning (cache schema migration)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import json
import xxhash


class KeyNamespace(Enum):
    """Cache key namespaces"""
    PREDICTION = "pred"
    MARKETS = "markets"
    GOALSCORERS = "goalscorers"
    HEALTH = "health"


@dataclass
class KeyFactory:
    """
    Centralized key generation for Redis cache.

    Pattern: {app}:{env}:{version}:{namespace}:{entity_id}:{variant_hash}
    Example: monps:prod:v1:pred:{m_12345}:a1b2c3d4

    Cluster Hash Tag: {m_12345} ensures all variants of match 12345
    are stored on same Redis node for atomic operations.
    """

    app: str = "monps"
    env: str = "prod"
    version: str = "v1"

    def prediction_key(
        self,
        match_id: str,
        config: Optional[dict] = None
    ) -> str:
        """
        Generate prediction cache key with optional config variant.

        Args:
            match_id: Canonical match ID (e.g., "12345")
            config: Configuration dict (risk, model_version, etc.)

        Returns:
            Key like: monps:prod:v1:pred:{m_12345}:a1b2c3d4
        """
        variant = self._hash_config(config) if config else "default"
        return f"{self.app}:{self.env}:{self.version}:{KeyNamespace.PREDICTION.value}:{{m_{match_id}}}:{variant}"

    def markets_key(self, match_id: str) -> str:
        """Markets cache key"""
        return f"{self.app}:{self.env}:{self.version}:{KeyNamespace.MARKETS.value}:{{m_{match_id}}}"

    def goalscorers_key(self, match_id: str) -> str:
        """Goalscorers cache key"""
        return f"{self.app}:{self.env}:{self.version}:{KeyNamespace.GOALSCORERS.value}:{{m_{match_id}}}"

    def health_key(self) -> str:
        """Health status cache key"""
        return f"{self.app}:{self.env}:{self.version}:{KeyNamespace.HEALTH.value}"

    def invalidation_pattern(self, match_id: str) -> str:
        """
        Pattern to invalidate ALL cache entries for a match.

        Example: monps:prod:v1:*:{m_12345}:*
        """
        return f"{self.app}:{self.env}:{self.version}:*:{{m_{match_id}}}:*"

    @staticmethod
    def _hash_config(config: dict) -> str:
        """
        Hash configuration dict to 12-char variant identifier.

        Uses XXHash (10x faster than MD5, sufficient collision resistance).
        Sorts keys to ensure {"a":1, "b":2} == {"b":2, "a":1}.
        """
        if not config:
            return "default"

        # Sort keys for deterministic hashing
        config_str = json.dumps(config, sort_keys=True, separators=(',', ':'))

        # XXHash64 → first 12 hex chars
        return xxhash.xxh64(config_str.encode()).hexdigest()[:12]


# Singleton instance
key_factory = KeyFactory()
