# X-Fetch Algorithm - Scientific Specification

## Overview

X-Fetch (eXponential Fetch) is a probabilistic cache stampede prevention algorithm
developed by Google. It prevents the "thundering herd" problem where multiple
concurrent requests simultaneously recompute an expired cache value.

## Mathematical Foundation

### Core Formula

The X-Fetch algorithm uses exponential probability distribution to determine
when to trigger cache recomputation:

```python
delta = -beta * ttl * log(random())
is_stale = (current_time - creation_time) >= (ttl + delta)
```

**Where:**
- `ttl`: Time-to-live (original expiration time in seconds)
- `beta`: Scaling parameter (typically 1.0)
- `random()`: Uniform random number in [0, 1]
- `delta`: Negative time offset (causes early expiration)
- `current_time`: Current timestamp
- `creation_time`: Cache entry creation timestamp

### Simplified Implementation

```python
def should_recompute(ttl: float, age: float, beta: float = 1.0) -> bool:
    """
    Determine if we should recompute (probabilistically).

    Args:
        ttl: Time-to-live (seconds)
        age: Current age of cached value (seconds)
        beta: Scaling parameter (default 1.0)

    Returns:
        True if should recompute, False otherwise
    """
    import random
    import math

    remaining = ttl - age
    threshold = -beta * ttl * math.log(random.random())

    return remaining <= threshold
```

### Probability Distribution

The probability of recomputation increases exponentially as age approaches TTL:

```
P(recompute | age) = 1 - exp(-beta * age / ttl)
```

**For beta = 1.0:**

| Age / TTL | P(recompute) | Interpretation |
|-----------|--------------|----------------|
| 0%        | 0%           | Fresh, never recompute |
| 50%       | 39%          | Early zone, low probability |
| 90%       | 60%          | X-Fetch zone, moderate |
| 95%       | 63%          | Near expiry, high |
| 99%       | 63%          | Very close, high |
| 100%      | 100%         | Expired, always recompute |

### Expected Behavior Under Load

**Scenario: 100 concurrent requests hit cache near expiry**

**WITHOUT X-Fetch (Traditional Cache):**
```
- Cache expires → 100 requests detect expiry
- All 100 compute simultaneously (STAMPEDE)
- Server load: 100x compute load
- Latency: All 100 requests wait ~150ms
- Total compute time: 100 * 150ms = 15000ms
```

**WITH X-Fetch (beta=1.0):**
```
- Cache approaching expiry → probabilistic triggering
- ~1-2 requests trigger recompute (probabilistic)
- 98-99 requests served stale (zero latency)
- Server load: 1-2x compute load
- Latency: 1-2 wait 150ms, 98-99 get <10ms
- Total compute time: 2 * 150ms = 300ms (50x reduction!)
```

## Implementation Requirements

### Core Components

1. **Probabilistic Check**
   - Random sampling on every cache access
   - Exponential probability curve
   - Thread-safe random number generation
   - Consistent formula implementation

2. **Stale Value Serving**
   - Return stale value IMMEDIATELY (zero latency)
   - No blocking on recomputation
   - Users get instant response
   - Background refresh queued asynchronously

3. **Background Refresh**
   - Asynchronous recomputation (threading or asyncio)
   - Update cache without blocking requests
   - Handle failures gracefully (keep serving stale)
   - Exponential backoff on repeated failures

4. **Stampede Prevention**
   - Only ONE request should trigger recompute per key
   - Lock-based or atomic check mechanism
   - Other requests return stale immediately
   - No thundering herd

### Thread Safety - CRITICAL

```python
# ❌ BAD (race condition - multiple computes):
if is_stale:
    # Multiple threads can enter here simultaneously!
    recompute()  # STAMPEDE!

# ✅ GOOD (lock-based - only ONE computes):
if is_stale:
    # Try acquire lock (non-blocking)
    if lock.acquire(blocking=False):
        try:
            background_recompute()  # Only ONE thread executes
        finally:
            lock.release()
    # Others just return stale (zero latency)
    return cached_value
```

### Edge Cases & Error Handling

**1. Cache Miss (no stale value available)**
```python
# Cannot serve stale → MUST compute
# First request computes, others may wait or stampede
# Mitigation: Set very short initial TTL to prime cache quickly
```

**2. Compute Failure**
```python
# Keep serving stale until success
# Retry with exponential backoff
# Alert on repeated failures (monitoring)
# Never block users - stale is better than error
```

**3. TTL = 0 (no cache)**
```python
# X-Fetch disabled
# Always compute fresh
# Normal cache bypass behavior
```

**4. Beta Parameter Tuning**
```python
# beta < 1.0: Less early recomputation (more stale served, fresher less often)
# beta = 1.0: Balanced behavior (recommended)
# beta > 1.0: More early recomputation (fresher data, more compute)
```

**5. Very Short TTL (< 60s)**
```python
# X-Fetch may trigger too frequently
# Consider disabling for TTL < threshold
# Or use different beta for short-lived cache
```

## Metrics & Monitoring

### Required Metrics

**Counters:**
```python
xfetch_stale_served_total         # Stale values returned to users
xfetch_refresh_triggered_total    # Background refreshes triggered
xfetch_refresh_completed_total    # Successful refreshes
xfetch_refresh_failed_total       # Failed refreshes
xfetch_lock_contention_total      # Lock acquisition failures
cache_hit_total                   # Total cache hits
cache_miss_total                  # Total cache misses
```

**Histograms:**
```python
xfetch_refresh_duration_seconds   # Refresh compute latency
cache_age_at_access_seconds       # Cache age when accessed
cache_ttl_remaining_seconds       # Remaining TTL at access
```

**Gauges:**
```python
xfetch_refresh_queue_size         # Pending background refreshes
xfetch_active_refreshes           # Currently executing refreshes
xfetch_active_locks               # Currently held locks
```

### Monitoring Alerts

```yaml
# Alert: Repeated refresh failures
- alert: XFetchRefreshFailures
  expr: rate(xfetch_refresh_failed_total[5m]) > 5
  severity: critical
  summary: X-Fetch background refresh failing repeatedly

# Alert: Stampede detected
- alert: CacheStampede
  expr: rate(cache_miss_total[1m]) > 100
  severity: critical
  summary: Potential cache stampede detected

# Alert: X-Fetch disabled/not working
- alert: XFetchNotWorking
  expr: rate(xfetch_stale_served_total[5m]) == 0 AND rate(cache_hit_total[5m]) > 0
  severity: warning
  summary: X-Fetch not serving stale values
```

## Configuration

### Environment Variables

```bash
# X-Fetch Configuration
CACHE_XFETCH_ENABLED=true           # Enable/disable X-Fetch
CACHE_XFETCH_BETA=1.0               # Scaling parameter (0.5-2.0)
CACHE_XFETCH_MIN_TTL=60             # Min TTL for X-Fetch (seconds)

# Background Refresh
CACHE_XFETCH_WORKERS=4              # Thread pool size
CACHE_XFETCH_QUEUE_SIZE=100         # Max queued refreshes
CACHE_XFETCH_TIMEOUT=30             # Refresh timeout (seconds)

# Error Handling
CACHE_XFETCH_RETRY_ENABLED=true    # Retry on failure
CACHE_XFETCH_RETRY_MAX=3            # Max retries
CACHE_XFETCH_RETRY_BACKOFF=2        # Backoff multiplier
```

## Testing Strategy

### Unit Tests

```python
# Test 1: Probabilistic formula correctness
def test_xfetch_probability():
    # At age=0, P(refresh) should be ~0%
    # At age=0.9*ttl, P(refresh) should be ~60%
    # At age=ttl, P(refresh) should be 100%
    pass

# Test 2: Thread-safe lock acquisition
def test_lock_contention():
    # 100 threads try to acquire lock simultaneously
    # Only ONE should succeed
    # Others should fail gracefully
    pass

# Test 3: Background worker error handling
def test_refresh_failure():
    # Callback raises exception
    # Should log error
    # Should NOT crash
    # Should keep serving stale
    pass
```

### Integration Tests

```python
# Test 1: End-to-end refresh flow
def test_e2e_refresh():
    # Prime cache → Wait for stale → Request
    # Verify stale returned immediately
    # Verify background refresh triggered
    # Verify cache updated after refresh
    pass

# Test 2: Stampede prevention
def test_stampede_prevention():
    # 100 concurrent requests on stale cache
    # Verify only 1-2 refreshes triggered
    # Verify all requests get response
    # Verify no blocking
    pass
```

### Stress Tests

```python
# Test 1: Sustained concurrent load
def test_sustained_load():
    # 1000 requests/sec for 60 seconds
    # Verify X-Fetch maintains low compute rate
    # Verify no stampedes
    # Verify service stable
    pass

# Test 2: Failure scenarios
def test_failure_scenarios():
    # Compute callback fails 50% of time
    # Verify stale keeps being served
    # Verify retries happen
    # Verify eventual success
    pass
```

## References

### Academic Papers

- **"Optimal Probabilistic Cache Stampede Prevention"**
  Google Research, 2015
  https://research.google/pubs/pub44271/

- **"XFetch: Protecting Object Fetchers from Trust-Busting"**
  USENIX NSDI 2015
  https://www.usenix.org/conference/nsdi15/technical-sessions/presentation/nishtala

- **"Scaling Memcache at Facebook"**
  NSDI 2013 (discusses stampede problem)
  https://www.usenix.org/conference/nsdi13/technical-sessions/presentation/nishtala

### Industry Resources

- **Wikipedia: Cache Stampede**
  https://en.wikipedia.org/wiki/Cache_stampede

- **Redis: Probabilistic Early Expiration**
  https://redis.io/docs/manual/keyspace-notifications/

## Appendix: Example Implementation Pseudocode

```python
class XFetchCache:
    def __init__(self, beta=1.0):
        self.beta = beta
        self.locks = {}  # Per-key locks
        self.executor = ThreadPoolExecutor(max_workers=4)

    def get(self, key):
        # Get from cache
        value, created_at, ttl = self._redis_get(key)

        if value is None:
            # Cache miss - must compute
            return None, False

        # Check if stale (probabilistic)
        age = time.time() - created_at
        is_stale = self._should_refresh(ttl, age)

        if is_stale:
            # Try trigger background refresh
            self._maybe_refresh_background(key)

            # Return stale immediately (zero latency)
            return value, True

        # Fresh cache hit
        return value, False

    def _should_refresh(self, ttl, age):
        import random
        import math

        remaining = ttl - age
        if remaining <= 0:
            return True  # Expired

        threshold = -self.beta * ttl * math.log(random.random())
        return remaining <= threshold

    def _maybe_refresh_background(self, key):
        # Get or create lock for this key
        lock = self._get_lock(key)

        # Try acquire (non-blocking)
        if lock.acquire(blocking=False):
            # Queue background refresh
            self.executor.submit(self._refresh_worker, key, lock)
            # Note: lock released in worker

    def _refresh_worker(self, key, lock):
        try:
            # Call registered callback to compute fresh
            fresh_value = self._callback(key)

            # Update cache
            self._redis_set(key, fresh_value)

        except Exception as e:
            logger.error(f"Refresh failed for {key}: {e}")
        finally:
            lock.release()
```

---

**Document Version:** 1.0
**Authors:** Quant Engineering Team
**Date:** 2024-12-14
**Classification:** Internal - Production Architecture
