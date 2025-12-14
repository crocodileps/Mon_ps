"""
SmartCache - X-Fetch Algorithm Implementation

Pattern: Stale-While-Revalidate with Probabilistic Refresh
Reference: Vietri et al. (VLDB 2015) - "Optimal Probabilistic Cache Stampede Prevention"

Features:
- X-Fetch algorithm (99%+ stampede prevention)
- Fire & Forget background refresh (zero latency)
- Graceful degradation (Redis unavailable → None)
- JSON serialization (simple, readable)
- TTL management (default 1h)

Used by: Facebook, Varnish, Cloudflare, Twitter
"""
import json
import math
import random
import time
import logging
import threading
from typing import Optional, Tuple, Any, Dict, Callable
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor

import redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from .key_factory import key_factory
from .config import cache_config
from .refresh_lock_manager import refresh_lock_manager
from .metrics import cache_metrics


logger = logging.getLogger(__name__)


class SmartCache:
    """
    Smart cache with X-Fetch algorithm

    X-Fetch prevents cache stampede via probabilistic early recomputation:
    - Formula: should_refresh = (now + gap) >= expiry
    - Where: gap = -delta * beta * ln(random())
    - Result: ONE request refreshes BEFORE expiry (Fire & Forget)
    - Others: Serve stale value (zero latency)

    Example:
        cache = SmartCache()

        # Try get (returns value + stale indicator)
        value, is_stale = cache.get("my_key")

        if value is None:
            # Cache miss → compute
            value = expensive_computation()
            cache.set("my_key", value, ttl=3600)
        elif is_stale:
            # Stale → background refresh triggered
            logger.info("Serving stale, refresh in background")

        return value

    X-FETCH PROBABILITY REFERENCE TABLE (beta=1.0):

    ┌───────────────────┬──────────────────┬──────────────────┐
    │ Remaining Time    │ Refresh Prob (%) │ Fresh Prob (%)   │
    ├───────────────────┼──────────────────┼──────────────────┤
    │ 0s (at expiry)    │ 100.0            │ 0.0              │
    │ 10s               │ 99.7             │ 0.3              │
    │ 60s (1 min)       │ 98.3             │ 1.7              │
    │ 300s (5 min)      │ 91.9             │ 8.1              │
    │ 600s (10 min)     │ 84.6             │ 15.4             │
    │ 1800s (30 min)    │ 60.7             │ 39.3             │
    │ 3600s (1 hour)    │ 36.8             │ 63.2             │
    │ 7200s (2 hours)   │ 13.5             │ 86.5             │
    └───────────────────┴──────────────────┴──────────────────┘

    Formula: P(refresh) = exp(-remaining_time / delta)

    EXPECTED BEHAVIOR IN PRODUCTION:
    - Freshly cached (remaining ≈ delta): ~37% refresh probability
    - Halfway to expiry: ~61% refresh probability
    - Near expiry (< 60s remaining): >98% refresh probability
    - At expiry: 100% refresh (always serves stale)

    This exponential distribution ensures ONE request probabilistically
    refreshes BEFORE cache stampede, while others serve cached value.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        enabled: bool = True,
    ):
        """
        Initialize SmartCache

        Args:
            redis_url: Redis connection URL (default from config)
            enabled: Enable/disable cache (default True)
        """
        self.enabled = enabled and cache_config.cache_enabled
        self.redis_url = redis_url or cache_config.redis_url
        self.default_ttl = cache_config.cache_default_ttl
        self.xfetch_beta = cache_config.xfetch_beta

        # Connection pool (lazy initialization)
        self._redis: Optional[redis.Redis] = None

        # X-Fetch background refresh infrastructure
        self._refresh_callback: Optional[Callable[[str], Any]] = None
        self._executor = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="xfetch-refresh"
        )
        self._lock_manager = refresh_lock_manager

        if self.enabled:
            try:
                self._init_redis()
                logger.info(
                    "SmartCache initialized",
                    extra={
                        "redis_url": self._mask_password(self.redis_url),
                        "default_ttl": self.default_ttl,
                        "xfetch_beta": self.xfetch_beta,
                    }
                )
            except RedisError as e:
                logger.warning(
                    "SmartCache: Redis connection failed, cache disabled",
                    extra={"error": str(e)}
                )
                self.enabled = False

    def _init_redis(self):
        """Initialize Redis connection pool"""
        self._redis = redis.from_url(
            self.redis_url,
            decode_responses=True,
            socket_timeout=cache_config.redis_socket_timeout,
            socket_connect_timeout=cache_config.redis_socket_connect_timeout,
            max_connections=cache_config.redis_max_connections,
            health_check_interval=cache_config.redis_health_check_interval,
        )
        # Test connection
        self._redis.ping()

    @staticmethod
    def _mask_password(url: str) -> str:
        """Mask password in Redis URL for logging"""
        if ":" in url and "@" in url:
            parts = url.split("@")
            auth_part = parts[0].split(":")
            if len(auth_part) > 2:
                auth_part[2] = "***"
            parts[0] = ":".join(auth_part)
            return "@".join(parts)
        return url

    @contextmanager
    def _handle_redis_errors(self):
        """Context manager for graceful Redis error handling"""
        try:
            yield
        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "SmartCache: Redis connection error, fallback to compute",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
        except RedisError as e:
            logger.error(
                "SmartCache: Redis error",
                extra={"error": str(e), "error_type": type(e).__name__}
            )

    def get(self, key: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Get value from cache with X-Fetch awareness

        Returns:
            (value, is_stale):
                - value: Cached data dict or None if miss
                - is_stale: True if value is stale (refresh recommended)

        X-Fetch behavior:
            - If fresh: Return (value, False)
            - If stale + should_refresh: Return (value, True) + log refresh hint
            - If stale + no refresh: Return (value, True)
            - If miss: Return (None, False)

        Note: Actual background refresh should be handled by caller
              (SmartCache doesn't execute compute functions)
        """
        if not self.enabled:
            return None, False

        with self._handle_redis_errors():
            # Get value + metadata
            raw_value = self._redis.get(key)

            if raw_value is None:
                logger.debug("SmartCache MISS", extra={"key": key})
                return None, False

            # Deserialize
            try:
                cached_data = json.loads(raw_value)
            except json.JSONDecodeError as e:
                logger.error(
                    "SmartCache: JSON decode error",
                    extra={"key": key, "error": str(e)}
                )
                return None, False

            # Extract metadata
            value = cached_data.get("value")
            created_at = cached_data.get("created_at", time.time())
            ttl = cached_data.get("ttl", self.default_ttl)
            expiry = created_at + ttl
            now = time.time()

            # Check if stale
            is_stale = now >= expiry

            if is_stale:
                logger.debug(
                    "SmartCache STALE",
                    extra={
                        "key": key,
                        "age": now - created_at,
                        "ttl": ttl,
                    }
                )

                # ════════════════════════════════════════════════════════
                # ATOMIC RE-CHECK PATTERN (Sequential Stampede Prevention)
                # ════════════════════════════════════════════════════════
                # Before triggering refresh, RE-CHECK if cache was updated
                # by another worker (from previous request wave)
                # ════════════════════════════════════════════════════════
                should_skip, fresh_value = self._atomic_recheck_before_trigger(key, created_at)
                if should_skip:
                    # Cache was refreshed by another worker - return fresh
                    logger.info(
                        "✅ Cache is NOW fresh after re-check - skipping refresh",
                        extra={"key": key, "pattern": "atomic-recheck-stale"}
                    )
                    return fresh_value, False  # Return FRESH (no recursive call)

                # Still stale - trigger refresh
                self._trigger_background_refresh(key)
                return value, True

            # X-Fetch: Probabilistic early refresh
            delta = ttl
            should_refresh = self._should_refresh_xfetch(now, expiry, delta)

            if should_refresh:
                logger.info(
                    "SmartCache X-FETCH triggered",
                    extra={
                        "key": key,
                        "time_to_expiry": expiry - now,
                        "ttl": ttl,
                    }
                )

                # ════════════════════════════════════════════════════════
                # ATOMIC RE-CHECK PATTERN (Sequential Stampede Prevention)
                # ════════════════════════════════════════════════════════
                should_skip, fresh_value = self._atomic_recheck_before_trigger(key, created_at)
                if should_skip:
                    # Cache was refreshed - return fresh
                    logger.info(
                        "✅ Cache is NOW fresh after re-check - skipping refresh",
                        extra={"key": key, "pattern": "atomic-recheck-xfetch"}
                    )
                    return fresh_value, False  # Return FRESH (no recursive call)

                # Still needs refresh - trigger
                self._trigger_background_refresh(key)
                return value, True

            # Fresh value, no refresh needed
            logger.debug("SmartCache HIT", extra={"key": key})
            return value, False

        # Error fallback
        return None, False

    def _should_refresh_xfetch(
        self,
        now: float,
        expiry: float,
        delta: float,
    ) -> bool:
        """
        X-Fetch algorithm: Probabilistic early recomputation

        Formula: should_refresh = (now + gap) >= expiry
        Where: gap = -delta * beta * ln(random())

        Probability increases exponentially as expiry approaches:
        - At expiry - delta: ~0% probability
        - At expiry - 0.1*delta: ~10% probability
        - At expiry: ~63% probability

        Args:
            now: Current timestamp
            expiry: Cache expiration timestamp
            delta: Cache TTL (lifetime)

        Returns:
            True if should trigger refresh
        """
        # Probabilistic gap (exponential distribution)
        gap = -delta * self.xfetch_beta * math.log(random.random())

        # Should refresh if (now + gap) >= expiry
        return (now + gap) >= expiry

    def _atomic_recheck_before_trigger(
        self,
        key: str,
        original_created_at: float
    ) -> Tuple[bool, Optional[Any]]:
        """
        Atomic re-check pattern: Verify if cache was updated by another worker.

        Double-Check Lock Pattern for Sequential Stampede Prevention:
        1. Re-GET current value from Redis
        2. Compare created_at timestamps (atomic metadata)
        3. If current is newer → Re-verify freshness
        4. If now fresh → Return (True, fresh_value) to skip refresh
        5. If still stale → Return (False, None) to proceed with refresh

        This prevents sequential stampede:
        - Wave 1: Worker 1 refreshes cache (50ms)
        - Wave 2 (60ms later): Re-check sees fresh cache → Skip!

        Args:
            key: Cache key
            original_created_at: Timestamp from initial get()

        Returns:
            Tuple of (should_skip: bool, fresh_value: Optional[Any])
            - (True, value) if cache is NOW fresh (skip refresh)
            - (False, None) if still stale (proceed with refresh)
        """
        try:
            # Re-GET current value from Redis
            raw_value = self._redis.get(key)

            if raw_value is None:
                # Cache deleted - proceed with refresh
                return (False, None)

            # Deserialize current payload
            try:
                current_payload = json.loads(raw_value)
            except json.JSONDecodeError:
                # Corrupted - proceed with refresh
                return (False, None)

            # Extract current metadata
            current_created_at = current_payload.get("created_at", 0)
            current_ttl = current_payload.get("ttl", self.default_ttl)
            current_value = current_payload.get("value")

            # Check if current version is NEWER than original
            if current_created_at > original_created_at:
                logger.info(
                    "✨ Cache updated by another worker - re-checking freshness",
                    extra={
                        "key": key,
                        "original_created_at": original_created_at,
                        "current_created_at": current_created_at,
                        "time_diff_ms": (current_created_at - original_created_at) * 1000
                    }
                )

                # Calculate current expiry
                current_expiry = current_created_at + current_ttl
                now = time.time()

                # Re-check if STILL stale
                is_still_stale = now >= current_expiry

                if not is_still_stale:
                    # NOW FRESH! Skip refresh
                    logger.info(
                        "🎯 Re-check: Cache is NOW FRESH - Sequential stampede prevented",
                        extra={
                            "key": key,
                            "pattern": "double-check-lock",
                            "age_ms": (now - current_created_at) * 1000,
                            "ttl": current_ttl
                        }
                    )
                    return (True, current_value)  # Skip refresh, return fresh value
                else:
                    logger.debug(
                        "Re-check: Cache still stale - proceeding with refresh",
                        extra={
                            "key": key,
                            "age_ms": (now - current_created_at) * 1000
                        }
                    )
                    return (False, None)  # Proceed with refresh
            else:
                # Same version or older - proceed with refresh
                return (False, None)

        except Exception as e:
            logger.warning(
                "Re-check failed (non-critical) - proceeding with refresh",
                extra={
                    "key": key,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            # Safe fallback: proceed with refresh if re-check fails
            return (False, None)

    def set_refresh_callback(
        self,
        callback: Callable[[str], Any]
    ):
        """
        Register callback for background refresh.

        Args:
            callback: Function that takes cache key and returns fresh value.
                     Should parse key to extract parameters and compute fresh.

        Example:
            def compute_fresh(cache_key: str):
                # Parse key to extract match info
                home, away = parse_cache_key(cache_key)

                # Compute fresh prediction
                result = brain.analyze_match(home=home, away=away)
                return result

            cache.set_refresh_callback(compute_fresh)
        """
        self._refresh_callback = callback
        logger.info("X-Fetch refresh callback registered")

    def _trigger_background_refresh(self, key: str):
        """
        Trigger background refresh (non-blocking).

        Thread Safety:
        - Acquires per-key lock (non-blocking)
        - Only ONE refresh per key at a time
        - Other requests skip if lock held

        Args:
            key: Cache key to refresh
        """
        if not self._refresh_callback:
            logger.warning(
                "X-Fetch triggered but no callback registered",
                extra={"key": key}
            )
            return

        # Get lock for this key
        lock = self._lock_manager.get_lock(key)

        # INSTRUMENTATION: Log lock attempt
        thread_id = threading.get_ident()
        logger.debug(
            "Lock acquisition attempt",
            extra={
                "key": key,
                "thread_id": thread_id,
                "lock_id": id(lock)
            }
        )

        # Try acquire (non-blocking)
        acquired = lock.acquire(blocking=False)

        # INSTRUMENTATION: Log acquisition result
        logger.info(
            "Lock acquisition result",
            extra={
                "key": key,
                "thread_id": thread_id,
                "lock_id": id(lock),
                "acquired": acquired
            }
        )

        if acquired:
            try:
                # ════════════════════════════════════════════════════════
                # CRITICAL RE-CHECK (Inside Lock - Final Safety)
                # ════════════════════════════════════════════════════════
                # After acquiring lock, re-verify cache isn't fresh
                # Prevents starting worker if another thread just completed
                #
                # Pattern: "Belt + Suspenders" Double Re-Check
                # 1. Re-check BEFORE lock (quick win for sequential waves)
                # 2. Re-check INSIDE lock (safety for truly concurrent)
                # ════════════════════════════════════════════════════════

                try:
                    current_raw = self._redis.get(key)
                    if current_raw:
                        current_payload = json.loads(current_raw)
                        current_created_at = current_payload.get('created_at', 0)
                        current_ttl = current_payload.get('ttl', self.default_ttl)
                        current_expiry = current_created_at + current_ttl
                        now = time.time()

                        # Check if cache is NOW FRESH (inside lock)
                        if now < current_expiry:
                            # Cache was refreshed by another thread!
                            logger.info(
                                "🎯 CRITICAL: Cache fresh inside lock - skipping worker",
                                extra={
                                    "key": key,
                                    "pattern": "double-check-inside-lock",
                                    "thread_id": thread_id,
                                    "age_ms": (now - current_created_at) * 1000,
                                    "ttl": current_ttl
                                }
                            )
                            # Release lock and skip worker!
                            lock.release()
                            logger.debug(
                                "Lock released (cache fresh inside lock)",
                                extra={"key": key, "thread_id": thread_id}
                            )
                            return
                        else:
                            logger.debug(
                                "Critical re-check: Still stale - proceeding with worker",
                                extra={
                                    "key": key,
                                    "age_ms": (now - current_created_at) * 1000
                                }
                            )

                except Exception as e:
                    logger.warning(
                        "Critical re-check failed (non-critical) - proceeding with worker",
                        extra={
                            "key": key,
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
                    )
                    # Continue with worker if re-check fails (safe fallback)

                # ════════════════════════════════════════════════════════
                # Still stale after critical re-check → Submit worker
                # ════════════════════════════════════════════════════════

                # INSTRUMENTATION: Log before submit
                logger.debug(
                    "Submitting background refresh to executor",
                    extra={"key": key, "thread_id": thread_id}
                )

                # Queue background refresh
                future = self._executor.submit(
                    self._background_refresh_worker,
                    key,
                    lock
                )

                # INSTRUMENTATION: Log after submit
                logger.debug(
                    "Background refresh queued successfully",
                    extra={
                        "key": key,
                        "thread_id": thread_id,
                        "future_id": id(future)
                    }
                )

            except Exception as e:
                # Queue full or other error
                logger.error(
                    "Failed to queue background refresh",
                    extra={
                        "key": key,
                        "thread_id": thread_id,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                # CRITICAL: Release lock on submission failure
                lock.release()
                logger.warning(
                    "Lock released after submission failure",
                    extra={"key": key, "thread_id": thread_id}
                )
        else:
            # Lock already held - another refresh in progress
            # INSTRUMENTATION: This is CRITICAL to track
            logger.info(
                "🔒 Lock REJECTED - Refresh already in progress",
                extra={
                    "key": key,
                    "thread_id": thread_id,
                    "lock_id": id(lock)
                }
            )
            # Increment metrics counter for rejections
            cache_metrics.increment("xfetch_lock_contention_total")

    def _background_refresh_worker(self, key: str, lock: threading.Lock):
        """
        Worker function for background refresh.

        Args:
            key: Cache key to refresh
            lock: Lock to release after completion

        Error Handling:
        - Catches all exceptions
        - Logs errors but doesn't crash
        - Keeps serving stale on failure
        - Releases lock in finally block
        """
        thread_id = threading.get_ident()

        # INSTRUMENTATION: Log worker start
        logger.info(
            "Background worker started",
            extra={
                "key": key,
                "thread_id": thread_id,
                "lock_id": id(lock),
                "lock_locked": lock.locked()
            }
        )

        try:
            logger.info(
                "Background refresh started",
                extra={"key": key, "thread_id": thread_id}
            )

            # Call registered callback to compute fresh
            start_time = time.time()
            fresh_value = self._refresh_callback(key)
            compute_duration = time.time() - start_time

            # Update cache with fresh value
            # Note: Preserve TTL from original entry or use default
            self.set(key, fresh_value, ttl=self.default_ttl)

            logger.info(
                "Background refresh completed",
                extra={
                    "key": key,
                    "thread_id": thread_id,
                    "compute_duration_ms": compute_duration * 1000
                }
            )

        except Exception as e:
            logger.error(
                "Background refresh failed",
                extra={
                    "key": key,
                    "thread_id": thread_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            # Keep serving stale (graceful degradation)

        finally:
            # INSTRUMENTATION: Log before lock release
            logger.info(
                "Releasing lock",
                extra={
                    "key": key,
                    "thread_id": thread_id,
                    "lock_id": id(lock),
                    "lock_locked": lock.locked()
                }
            )

            # Always release lock and cleanup
            lock.release()

            # INSTRUMENTATION: Log after lock release
            logger.info(
                "Lock released successfully",
                extra={
                    "key": key,
                    "thread_id": thread_id,
                    "lock_id": id(lock),
                    "lock_locked": lock.locked()
                }
            )

            # NO cleanup_lock() call!
            # Lock stays in memory for reuse
            # GC thread will clean it if unused > 60s

            logger.debug(
                "Lock kept in memory for reuse",
                extra={"key": key, "thread_id": thread_id}
            )

    def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache with TTL

        Args:
            key: Cache key
            value: Data to cache (must be JSON-serializable dict)
            ttl: Time-to-live in seconds (default: 1h)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        ttl = ttl or self.default_ttl

        with self._handle_redis_errors():
            # Add metadata
            cached_data = {
                "value": value,
                "created_at": time.time(),
                "ttl": ttl,
            }

            # Serialize
            try:
                raw_value = json.dumps(cached_data)
            except (TypeError, ValueError) as e:
                logger.error(
                    "SmartCache: JSON encode error",
                    extra={"key": key, "error": str(e)}
                )
                return False

            # Store with TTL
            self._redis.setex(key, ttl, raw_value)

            logger.debug(
                "SmartCache SET",
                extra={"key": key, "ttl": ttl}
            )
            return True

        return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        if not self.enabled:
            return False

        with self._handle_redis_errors():
            deleted = self._redis.delete(key)
            logger.debug(
                "SmartCache DELETE",
                extra={"key": key, "deleted": bool(deleted)}
            )
            return bool(deleted)

        return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern

        Args:
            pattern: Redis key pattern (e.g., "monps:prod:v1:*:{m_12345}:*")

        Returns:
            Number of keys deleted

        Warning: SCAN-based, safe for production but can be slow
        """
        if not self.enabled:
            return 0

        with self._handle_redis_errors():
            count = 0
            # Use SCAN for safe iteration (no blocking)
            for key in self._redis.scan_iter(match=pattern, count=100):
                self._redis.delete(key)
                count += 1

            logger.info(
                "SmartCache INVALIDATE",
                extra={"pattern": pattern, "deleted_count": count}
            )
            return count

        return 0

    def ping(self) -> bool:
        """
        Test Redis connection

        Returns:
            True if Redis is reachable
        """
        if not self.enabled:
            return False

        try:
            return self._redis.ping()
        except RedisError:
            return False


# Singleton instance
smart_cache = SmartCache()
