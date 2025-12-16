# X-Fetch Architecture Design - Production Grade

**Version:** 2.0
**Status:** Design Specification
**Authors:** Quant Engineering Team
**Date:** 2024-12-14

---

## Design Principles

1. **Zero Latency** - Stale values returned instantly (<10ms)
2. **Thread Safe** - No race conditions under concurrent load
3. **Asynchronous Refresh** - Background recomputation never blocks
4. **Stampede Prevention** - Only ONE refresh per cache key
5. **Failure Resilient** - Keep serving stale on compute errors
6. **Observable** - Comprehensive metrics for monitoring
7. **Scalable** - Handle 1000+ req/s sustained load

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       APPLICATION LAYER                          │
│  (FastAPI endpoints calling brain.analyze_match)                 │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                    BRAIN REPOSITORY                              │
│  - calculate_predictions()                                       │
│  - Cache key generation                                          │
│  - TTL calculation                                               │
│  - Callback registration (NEW)                                   │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                     SMART CACHE (X-Fetch)                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐          ┌──────────────────┐                  │
│  │   get()     │─────────>│  Probabilistic   │                  │
│  │             │          │  Staleness Check │                  │
│  └─────────────┘          └────────┬─────────┘                  │
│                                    │                             │
│                           is_stale? │                            │
│                                    │                             │
│                        ┌───────────▼────────────┐                │
│                        │  Return Stale Value    │                │
│                        │  (ZERO LATENCY)        │                │
│                        └───────────┬────────────┘                │
│                                    │                             │
│                        ┌───────────▼────────────┐                │
│                        │  Try Acquire Lock      │                │
│                        │  (non-blocking)        │                │
│                        └───────────┬────────────┘                │
│                                    │                             │
│                           Acquired? │                            │
│                                    │                             │
│                     ┌──────────────▼───────────────┐             │
│                     │  Queue Background Refresh    │             │
│                     │  (ThreadPoolExecutor)        │             │
│                     └──────────────────────────────┘             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│               BACKGROUND REFRESH WORKER                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────┐        ┌─────────────────┐                   │
│  │ Task Executor │───────>│  Call Callback  │                   │
│  │ (ThreadPool)  │        │  (compute fresh)│                   │
│  └───────────────┘        └────────┬────────┘                   │
│                                    │                             │
│                         ┌──────────▼──────────┐                  │
│                         │  brain.analyze_match│                  │
│                         │  (compute)          │                  │
│                         └──────────┬──────────┘                  │
│                                    │                             │
│                         ┌──────────▼──────────┐                  │
│                         │  Update Redis Cache │                  │
│                         │  Release Lock       │                  │
│                         └─────────────────────┘                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                       REDIS CACHE                                │
│  - Key-value storage                                             │
│  - TTL management                                                │
│  - Atomic operations                                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. SmartCache Class (REFACTORED)

**New Components:**
- ThreadPoolExecutor for background refresh
- RefreshLockManager for stampede prevention
- Callback registration mechanism
- Background worker infrastructure

**Updated Interface:**

```python
class SmartCache:
    """
    Production-grade cache with X-Fetch stampede prevention.

    Thread-safe, asynchronous refresh, comprehensive metrics.
    """

    def __init__(
        self,
        redis_url: str,
        enabled: bool = True,
        default_ttl: int = 3600,
        beta: float = 1.0,
        refresh_workers: int = 4,
        queue_size: int = 100
    ):
        """
        Initialize SmartCache.

        Args:
            redis_url: Redis connection URL
            enabled: Enable/disable caching
            default_ttl: Default time-to-live (seconds)
            beta: X-Fetch scaling parameter (0.5-2.0)
            refresh_workers: Background worker thread count
            queue_size: Max queued refresh tasks
        """
        # Existing initialization
        self.enabled = enabled
        self.default_ttl = default_ttl
        self.xfetch_beta = beta

        # NEW: Background refresh infrastructure
        self._refresh_callback = None
        self._executor = ThreadPoolExecutor(
            max_workers=refresh_workers,
            thread_name_prefix="xfetch-refresh"
        )
        self._lock_manager = RefreshLockManager()

    def set_refresh_callback(
        self,
        callback: Callable[[str], Any]
    ):
        """
        Register callback for background refresh.

        Args:
            callback: Function that takes cache key and returns fresh value
                     Should parse key to extract parameters and compute fresh

        Example:
            def compute_fresh(cache_key: str):
                # Parse key: "monps:prod:v1:pred:{m_arsenal_vs_chelsea}:default"
                match_id = extract_match_id(cache_key)

                # Compute fresh prediction
                result = brain.analyze_match(...)
                return result

            cache.set_refresh_callback(compute_fresh)
        """
        self._refresh_callback = callback
        logger.info("X-Fetch refresh callback registered")

    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """
        Get value from cache with X-Fetch logic.

        Returns:
            (value, is_stale): value or None, True if refresh triggered
        """
        # ... existing cache lookup logic ...

        # Check staleness (probabilistic)
        if self._should_refresh_xfetch(now, expiry, delta):
            # Trigger background refresh (NEW)
            self._trigger_background_refresh(key)

            # Return stale immediately (zero latency)
            return value, True

        return value, False

    def _trigger_background_refresh(self, key: str):
        """
        Trigger background refresh (non-blocking).

        Thread Safety:
        - Acquires per-key lock (non-blocking)
        - Only ONE refresh per key at a time
        - Other requests skip if lock held
        """
        if not self._refresh_callback:
            logger.warning(
                "X-Fetch triggered but no callback registered",
                extra={"key": key}
            )
            return

        # Get lock for this key
        lock = self._lock_manager.get_lock(key)

        # Try acquire (non-blocking)
        if lock.acquire(blocking=False):
            try:
                # Queue background refresh
                self._executor.submit(
                    self._background_refresh_worker,
                    key,
                    lock
                )
                logger.debug(
                    "Background refresh queued",
                    extra={"key": key}
                )
            except Exception as e:
                # Queue full or other error
                logger.warning(
                    "Failed to queue background refresh",
                    extra={"key": key, "error": str(e)}
                )
                lock.release()
        else:
            # Lock already held - another refresh in progress
            logger.debug(
                "Refresh already in progress",
                extra={"key": key}
            )

    def _background_refresh_worker(self, key: str, lock: threading.Lock):
        """
        Worker function for background refresh.

        Args:
            key: Cache key to refresh
            lock: Lock to release after completion
        """
        try:
            logger.info(
                "Background refresh started",
                extra={"key": key}
            )

            # Call registered callback
            fresh_value = self._refresh_callback(key)

            # Update cache with fresh value
            # Extract TTL from original cached data or use default
            self.set(key, fresh_value, ttl=self.default_ttl)

            logger.info(
                "Background refresh completed",
                extra={"key": key}
            )

        except Exception as e:
            logger.error(
                "Background refresh failed",
                extra={"key": key, "error": str(e)}
            )
            # Keep serving stale (graceful degradation)

        finally:
            # Always release lock
            lock.release()
            self._lock_manager.cleanup_lock(key)
```

### 2. RefreshLockManager

See `backend/cache/refresh_lock_manager.py` for implementation.

**Purpose**: Thread-safe per-key lock management

**Key Methods**:
- `get_lock(key)`: Get or create lock for key
- `cleanup_lock(key)`: Remove lock to prevent memory leak
- `get_active_lock_count()`: Monitor lock count

### 3. Background Refresh Worker Flow

```
┌─────────────────────────────────────────────────────────────┐
│ BACKGROUND REFRESH WORKER (runs in ThreadPool)             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Input: (cache_key, lock)                                   │
│                                                             │
│ try:                                                        │
│   ┌─────────────────────────────────────────┐              │
│   │ 1. Check callback registered            │              │
│   └───────────────┬─────────────────────────┘              │
│                   │                                         │
│   ┌───────────────▼─────────────────────────┐              │
│   │ 2. Call callback(cache_key)             │              │
│   │    - Parse key to extract params        │              │
│   │    - brain.analyze_match(...)           │              │
│   │    - Get fresh prediction               │              │
│   └───────────────┬─────────────────────────┘              │
│                   │                                         │
│   ┌───────────────▼─────────────────────────┐              │
│   │ 3. Update cache                         │              │
│   │    cache.set(key, fresh_value, ttl)     │              │
│   └───────────────┬─────────────────────────┘              │
│                   │                                         │
│   ┌───────────────▼─────────────────────────┐              │
│   │ 4. Increment metrics                    │              │
│   │    cache_metrics.increment(...)         │              │
│   └─────────────────────────────────────────┘              │
│                                                             │
│ except Exception as e:                                     │
│   ┌─────────────────────────────────────────┐              │
│   │ - Log error                              │              │
│   │ - Keep serving stale (graceful!)         │              │
│   └─────────────────────────────────────────┘              │
│                                                             │
│ finally:                                                    │
│   ┌─────────────────────────────────────────┐              │
│   │ - Release lock                           │              │
│   │ - Cleanup lock from manager              │              │
│   └─────────────────────────────────────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Thread Safety Guarantees

### Scenario: 100 Concurrent Requests on Stale Cache

```python
# All 100 threads execute this flow:

Thread 1-100:
    value, is_stale = cache.get(key)
    # All detect stale (probabilistic or definite)

    # Inside cache.get():
    if is_stale:
        # Try acquire lock (non-blocking)
        lock = lock_manager.get_lock(key)

        # Thread 1: lock.acquire() → SUCCESS
        # Thread 2-100: lock.acquire() → FAIL (already locked)

        if lock.acquire(blocking=False):  # Only Thread 1 succeeds
            # Queue background refresh
            executor.submit(refresh_worker, key, lock)

        # ALL threads return stale immediately (zero latency)
        return value, True

Result:
- 1 background refresh queued ✅
- 99 threads skipped refresh (lock held) ✅
- ALL 100 threads got response <10ms ✅
- NO stampede ✅
```

---

## Repository Integration

### BrainRepository Callback Registration

```python
class BrainRepository:
    def __init__(self, brain_client=None):
        # Existing initialization...

        # NEW: Register X-Fetch callback
        if smart_cache.enabled:
            smart_cache.set_refresh_callback(self._xfetch_refresh_callback)

    def _xfetch_refresh_callback(self, cache_key: str) -> Dict[str, Any]:
        """
        X-Fetch background refresh callback.

        Args:
            cache_key: Full cache key (e.g., "monps:prod:v1:pred:{m_arsenal_vs_chelsea}:default")

        Returns:
            Fresh prediction result
        """
        try:
            # Parse cache key to extract parameters
            # Key format: "monps:prod:v1:pred:{m_home_vs_away}:context"
            match_id = self._extract_match_id_from_key(cache_key)
            home_team, away_team = self._parse_match_id(match_id)

            # Compute fresh prediction
            logger.info(
                "X-Fetch background refresh: Computing fresh prediction",
                extra={"home": home_team, "away": away_team}
            )

            result = self.brain.analyze_match(
                home=home_team,
                away=away_team
            )

            # Increment metrics
            cache_metrics.increment("compute_calls")

            return result

        except Exception as e:
            logger.error(
                "X-Fetch callback error",
                extra={"cache_key": cache_key, "error": str(e)}
            )
            raise  # Re-raise so worker can handle gracefully

    def _extract_match_id_from_key(self, cache_key: str) -> str:
        """Extract match_id from cache key."""
        # "monps:prod:v1:pred:{m_arsenal_vs_chelsea}:default"
        #                      ^^^^^^^^^^^^^^^^^^^^
        parts = cache_key.split(":")
        for part in parts:
            if part.startswith("{") and part.endswith("}"):
                return part[1:-1]  # Remove { }
        raise ValueError(f"Invalid cache key format: {cache_key}")

    def _parse_match_id(self, match_id: str) -> Tuple[str, str]:
        """Parse match_id to extract team names."""
        # "m_arsenal_vs_chelsea" → ("Arsenal", "Chelsea")
        if not match_id.startswith("m_"):
            raise ValueError(f"Invalid match_id: {match_id}")

        teams = match_id[2:].split("_vs_")
        if len(teams) != 2:
            raise ValueError(f"Invalid match_id format: {match_id}")

        home = teams[0].replace("_", " ").title()
        away = teams[1].replace("_", " ").title()

        return home, away
```

---

## Configuration

### Environment Variables

```bash
# X-Fetch Configuration
CACHE_XFETCH_ENABLED=true           # Enable/disable X-Fetch
CACHE_XFETCH_BETA=1.0               # Scaling parameter (0.5-2.0)

# Background Refresh
CACHE_XFETCH_WORKERS=4              # Thread pool size
CACHE_XFETCH_QUEUE_SIZE=100         # Max queued refreshes
```

---

## Testing Strategy

### Unit Tests

```python
# tests/cache/test_smart_cache_xfetch.py

def test_background_refresh_triggered():
    """Test that background refresh is queued on stale access."""
    pass

def test_stampede_prevention():
    """Test that only ONE refresh triggered under concurrent load."""
    pass

def test_callback_invocation():
    """Test that registered callback is called correctly."""
    pass

def test_graceful_degradation_on_callback_error():
    """Test that errors in callback don't crash system."""
    pass
```

---

## Migration Plan

### Phase 1: Implementation (Week 1)
1. Create RefreshLockManager
2. Refactor SmartCache with ThreadPool
3. Add callback registration
4. Unit tests

### Phase 2: Integration (Week 1)
1. Update BrainRepository with callback
2. Integration tests
3. Stress test V2 validation

### Phase 3: Deployment (Week 2)
1. Deploy to staging
2. Monitor metrics
3. Gradual production rollout

---

## Success Criteria

✅ **Background Refresh**: compute_calls > 0 after stale request
✅ **Stampede Prevention**: ≤2 refreshes per 100 concurrent stale requests
✅ **Zero Latency**: Stale requests <10ms P99
✅ **Thread Safety**: No race conditions under 1000 req/s load
✅ **Error Resilience**: Service stable with 50% compute failure rate

---

**Document Status:** APPROVED
**Implementation:** READY TO START
**Estimated Effort:** 20 hours

---

**Next:** PHASE 4 - Implementation
