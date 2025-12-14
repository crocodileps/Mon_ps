"""
Cache Metrics - Thread-Safe Instrumentation
============================================

Provides exact, quantifiable counts for cache behavior validation.

Usage:
    from cache.metrics import cache_metrics

    # Increment counters
    cache_metrics.increment("cache_hit_fresh")
    cache_metrics.increment("compute_calls")

    # Get counts
    counts = cache_metrics.get_counts()
    print(f"Computes: {counts['compute_calls']}")

    # Reset (before stress test)
    cache_metrics.reset()

Thread Safety:
    All methods use Lock to prevent race conditions under concurrent load.

Author: Quant Engineering Team
Date: 2025-12-14
Methodology: Hedge Fund Grade - Direct Instrumentation
"""

from threading import Lock
from typing import Dict


class CacheMetrics:
    """Thread-safe cache metrics collector.

    Provides exact counts for:
    - Cache hits (fresh vs stale)
    - Cache misses
    - Compute calls (brain.analyze_match) ← CRITICAL
    - X-Fetch triggers

    All operations are thread-safe using Lock.
    """

    def __init__(self):
        """Initialize counters and lock."""
        self.lock = Lock()
        self.cache_hit_fresh = 0      # Served from fresh cache
        self.cache_hit_stale = 0      # Served from stale cache (X-Fetch)
        self.cache_miss = 0           # Cache miss → compute required
        self.compute_calls = 0        # CRITICAL: Direct brain.analyze_match() calls
        self.xfetch_triggers = 0      # X-Fetch probabilistic refresh triggers

    def increment(self, metric: str):
        """Increment a metric counter (thread-safe).

        Args:
            metric: Counter name (e.g., "compute_calls")

        Raises:
            AttributeError: If metric doesn't exist
        """
        with self.lock:
            current = getattr(self, metric)
            setattr(self, metric, current + 1)

    def get_counts(self) -> Dict[str, int]:
        """Get current counts snapshot (thread-safe).

        Returns:
            Dict with all counter values
        """
        with self.lock:
            return {
                "cache_hit_fresh": self.cache_hit_fresh,
                "cache_hit_stale": self.cache_hit_stale,
                "cache_miss": self.cache_miss,
                "compute_calls": self.compute_calls,
                "xfetch_triggers": self.xfetch_triggers,
                "total_requests": (
                    self.cache_hit_fresh +
                    self.cache_hit_stale +
                    self.cache_miss
                )
            }

    def reset(self):
        """Reset all counters to 0 (thread-safe).

        Used before stress tests to get clean baseline.
        """
        with self.lock:
            self.cache_hit_fresh = 0
            self.cache_hit_stale = 0
            self.cache_miss = 0
            self.compute_calls = 0
            self.xfetch_triggers = 0


# Global singleton instance
cache_metrics = CacheMetrics()
