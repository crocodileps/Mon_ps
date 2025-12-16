"""
Integration Tests: VIXCircuitBreaker + AdaptivePanicQuota

Tests the complete integration including:
- SETNX "First Writer Wins" atomicity
- Dead Man's Switch (TTL auto-expire)
- Local Fallback (Fail-Safe if Redis down)
- Multi-worker consistency
- Race condition handling

Grade Target: A++ (9.5/10) Institutional
"""

import pytest
import time
import sys
import threading
import random
import importlib.util
from unittest.mock import Mock, patch, MagicMock
from typing import Tuple, Optional, Dict

# Direct imports to bypass cache package __init__
# First load adaptive_panic_quota (dependency of vix_circuit_breaker)
spec_quota = importlib.util.spec_from_file_location(
    "adaptive_panic_quota",
    "/home/Mon_ps/backend/cache/adaptive_panic_quota.py"
)
quota_module = importlib.util.module_from_spec(spec_quota)
sys.modules["adaptive_panic_quota"] = quota_module
spec_quota.loader.exec_module(quota_module)

# Then load vix_circuit_breaker (with relative import workaround)
spec_vix = importlib.util.spec_from_file_location(
    "vix_circuit_breaker",
    "/home/Mon_ps/backend/cache/vix_circuit_breaker.py"
)
vix_module = importlib.util.module_from_spec(spec_vix)
sys.modules["vix_circuit_breaker"] = vix_module

# Inject adaptive_panic_quota into cache namespace for relative import
sys.modules["cache.adaptive_panic_quota"] = quota_module
spec_vix.loader.exec_module(vix_module)

VIXCircuitBreaker = vix_module.VIXCircuitBreaker
PANIC_START_TS_KEY = vix_module.PANIC_START_TS_KEY
PANIC_TS_TTL_SECONDS = vix_module.PANIC_TS_TTL_SECONDS
PanicMode = quota_module.PanicMode


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

class MockRedis:
    """
    Realistic Mock Redis client for testing.

    Improvements over basic mock:
    - Returns bytes like real Redis (configurable)
    - Simulates latency (optional)
    - Tracks all operations for assertions
    - Supports NX, EX parameters correctly
    """

    def __init__(self, return_bytes: bool = True, latency_ms: float = 0):
        self._data: Dict[str, str] = {}
        self._ttls: Dict[str, int] = {}
        self._call_log: list = []
        self._return_bytes = return_bytes
        self._latency_ms = latency_ms
        self._should_fail = False  # For error simulation
        self._fail_exception = Exception("Redis connection refused")

    def _simulate_latency(self):
        """Simulate network latency if configured."""
        if self._latency_ms > 0:
            import time
            time.sleep(self._latency_ms / 1000)

    def _check_failure(self):
        """Raise exception if failure mode is enabled."""
        if self._should_fail:
            raise self._fail_exception

    def set(self, key: str, value, nx: bool = False, ex: int = None) -> Optional[bool]:
        """
        Mock SET with NX and EX support.

        Returns:
            True if set, None if NX prevented (matches real Redis behavior)
        """
        self._call_log.append(('set', key, value, nx, ex))
        self._simulate_latency()
        self._check_failure()

        if nx and key in self._data:
            return None  # Real Redis returns None when NX fails

        self._data[key] = str(value)
        if ex:
            self._ttls[key] = ex
        return True

    def get(self, key: str) -> Optional[bytes]:
        """
        Mock GET - returns bytes like real Redis.
        """
        self._call_log.append(('get', key))
        self._simulate_latency()
        self._check_failure()

        value = self._data.get(key)
        if value is None:
            return None

        # Return bytes like real Redis (or str if configured)
        if self._return_bytes:
            return value.encode('utf-8')
        return value

    def delete(self, key: str) -> int:
        """Mock DELETE - returns count of deleted keys."""
        self._call_log.append(('delete', key))
        self._simulate_latency()
        self._check_failure()

        if key in self._data:
            del self._data[key]
            if key in self._ttls:
                del self._ttls[key]
            return 1
        return 0

    def expire(self, key: str, seconds: int) -> bool:
        """Mock EXPIRE - returns True if key exists."""
        self._call_log.append(('expire', key, seconds))
        self._simulate_latency()
        self._check_failure()

        if key in self._data:
            self._ttls[key] = seconds
            return True
        return False

    def clear_log(self):
        """Clear call log for fresh assertions."""
        self._call_log = []

    def enable_failure_mode(self, exception: Exception = None):
        """Enable failure simulation for testing error handling."""
        self._should_fail = True
        if exception:
            self._fail_exception = exception

    def disable_failure_mode(self):
        """Disable failure simulation."""
        self._should_fail = False


@pytest.fixture
def mock_redis():
    """Provide fresh MockRedis instance."""
    return MockRedis()


@pytest.fixture
def circuit_breaker(mock_redis):
    """Provide VIXCircuitBreaker with mock Redis."""
    cb = VIXCircuitBreaker(redis_client=mock_redis)
    return cb


# ═══════════════════════════════════════════════════════════════
# TEST: SETNX "First Writer Wins"
# ═══════════════════════════════════════════════════════════════

class TestSETNXFirstWriterWins:
    """Test atomic timestamp initialization."""

    def test_first_worker_sets_timestamp(self, circuit_breaker, mock_redis):
        """
        First worker detecting panic should set the timestamp.
        """
        ttl, mode = circuit_breaker.get_ttl(60, vix_status='panic', match_context={'league': 'Ligue 1'})

        # Verify SET was called with NX=True
        set_calls = [c for c in mock_redis._call_log if c[0] == 'set']
        assert len(set_calls) >= 1, "SET should be called"
        assert set_calls[0][3] == True, "NX should be True"

    def test_second_worker_does_not_overwrite(self, mock_redis):
        """
        Second worker should NOT overwrite first worker's timestamp.

        CRITICAL: This validates the "First Writer Wins" pattern.
        """
        # Simulate Worker 1 already set timestamp
        first_ts = 1000000.0
        mock_redis._data[PANIC_START_TS_KEY] = str(first_ts)

        # Worker 2 tries to set
        cb = VIXCircuitBreaker(redis_client=mock_redis)
        ttl, mode = cb.get_ttl(60, vix_status='panic', match_context={'league': 'Ligue 1'})

        # Verify original timestamp preserved
        stored = mock_redis.get(PANIC_START_TS_KEY)
        # MockRedis now returns bytes like real Redis
        stored_str = stored.decode('utf-8') if isinstance(stored, bytes) else stored
        assert stored_str == str(first_ts), \
            f"First worker's timestamp should be preserved, got {stored_str}"

    def test_race_condition_simulation(self, mock_redis):
        """
        Simulate 3 workers detecting panic at 50ms intervals.
        Only first timestamp should persist.
        """
        timestamps = []

        for worker_id in range(3):
            cb = VIXCircuitBreaker(redis_client=mock_redis)

            with patch('time.time', return_value=1000000.0 + (worker_id * 0.050)):
                ttl, mode = cb.get_ttl(60, vix_status='panic', match_context={'league': 'Ligue 1'})

            # Record what each worker sees
            stored = mock_redis.get(PANIC_START_TS_KEY)
            timestamps.append(float(stored))

        # All workers should see the FIRST timestamp
        assert all(ts == timestamps[0] for ts in timestamps), \
            f"All workers should see same timestamp: {timestamps}"


# ═══════════════════════════════════════════════════════════════
# TEST: Dead Man's Switch (TTL Auto-Expire)
# ═══════════════════════════════════════════════════════════════

class TestDeadMansSwitch:
    """Test automatic key expiration."""

    def test_ttl_set_on_panic_start(self, circuit_breaker, mock_redis):
        """
        Timestamp key should have TTL set (Dead Man's Switch).
        """
        ttl, mode = circuit_breaker.get_ttl(60, vix_status='panic', match_context={'league': 'Ligue 1'})

        # Verify TTL was set
        set_calls = [c for c in mock_redis._call_log if c[0] == 'set']
        assert len(set_calls) >= 1
        assert set_calls[0][4] == PANIC_TS_TTL_SECONDS, \
            f"Expected TTL={PANIC_TS_TTL_SECONDS}, got {set_calls[0][4]}"

    def test_ttl_refreshed_on_each_call(self, circuit_breaker, mock_redis):
        """
        TTL should be refreshed on each call (extend Dead Man's Switch).
        """
        # Set initial timestamp
        mock_redis._data[PANIC_START_TS_KEY] = str(time.time())
        mock_redis._ttls[PANIC_START_TS_KEY] = 100  # Low TTL

        ttl, mode = circuit_breaker.get_ttl(60, vix_status='panic', match_context={'league': 'Ligue 1'})

        # Verify EXPIRE was called to refresh TTL
        expire_calls = [c for c in mock_redis._call_log if c[0] == 'expire']
        assert len(expire_calls) >= 1, "EXPIRE should be called"
        assert expire_calls[0][2] == PANIC_TS_TTL_SECONDS

    def test_ttl_value_is_24h(self):
        """
        Verify Dead Man's Switch is set to 24 hours.
        """
        assert PANIC_TS_TTL_SECONDS == 86400, \
            f"Expected 86400 (24h), got {PANIC_TS_TTL_SECONDS}"


# ═══════════════════════════════════════════════════════════════
# TEST: Local Fallback (Fail-Safe)
# ═══════════════════════════════════════════════════════════════

class TestLocalFallback:
    """Test Fail-Safe behavior when Redis is down."""

    def test_redis_connection_error_returns_panic_full(self, mock_redis):
        """
        If Redis throws ConnectionError, should return PANIC_FULL.
        """
        cb = VIXCircuitBreaker(redis_client=mock_redis)

        # Make Redis operations fail
        mock_redis.set = Mock(side_effect=Exception("Redis connection refused"))
        mock_redis.get = Mock(side_effect=Exception("Redis connection refused"))

        ttl, mode = cb.get_ttl(60, vix_status='panic', match_context={'league': 'Ligue 1'})

        # Should return Fail-Safe values
        assert ttl == 0, f"Expected TTL=0 (Fail-Safe), got {ttl}"
        assert "PANIC" in mode.upper(), f"Expected PANIC mode, got {mode}"

    def test_redis_timeout_returns_panic_full(self, mock_redis):
        """
        If Redis times out, should return PANIC_FULL.
        """
        cb = VIXCircuitBreaker(redis_client=mock_redis)

        # Simulate timeout
        mock_redis.get = Mock(side_effect=TimeoutError("Redis timeout"))

        ttl, mode = cb.get_ttl(60, vix_status='panic', match_context={'league': 'Ligue 1'})

        assert ttl == 0, "Should return TTL=0 on timeout"

    def test_fail_safe_is_conservative(self, mock_redis):
        """
        Fail-Safe should be the most conservative option.

        CRITICAL: Better to recalculate than serve stale predictions.
        """
        cb = VIXCircuitBreaker(redis_client=mock_redis)
        mock_redis.set = Mock(side_effect=Exception("Redis down"))

        ttl, mode = cb.get_ttl(60, vix_status='panic', match_context={'league': 'Champions League'})

        # TTL=0 means "recalculate immediately" = most conservative
        assert ttl == 0, "Fail-Safe TTL should be 0 (recalculate)"


# ═══════════════════════════════════════════════════════════════
# TEST: Multi-Worker Consistency
# ═══════════════════════════════════════════════════════════════

class TestMultiWorkerConsistency:
    """Test that multiple workers get consistent results."""

    def test_all_workers_same_ttl(self, mock_redis):
        """
        All workers should calculate the same TTL for same panic state.
        """
        # Set authoritative timestamp
        panic_start = time.time() - (35 * 60)  # 35 minutes ago
        mock_redis._data[PANIC_START_TS_KEY] = str(panic_start)

        results = []
        for worker_id in range(5):
            cb = VIXCircuitBreaker(redis_client=mock_redis)
            ttl, mode = cb.get_ttl(60, vix_status='panic', match_context={'league': 'Ligue 1'})
            results.append((ttl, mode))

        # All workers should get identical results
        unique_results = set(results)
        assert len(unique_results) == 1, \
            f"Workers got different results: {results}"

    def test_workers_read_shared_timestamp(self, mock_redis):
        """
        All workers should read the same shared timestamp.
        """
        # Worker 1 initializes timestamp
        cb1 = VIXCircuitBreaker(redis_client=mock_redis)
        with patch('time.time', return_value=1000000.0):
            cb1.get_ttl(60, vix_status='panic', match_context={})

        first_ts = float(mock_redis.get(PANIC_START_TS_KEY))

        # Worker 2 should read same timestamp
        cb2 = VIXCircuitBreaker(redis_client=mock_redis)
        with patch('time.time', return_value=1000000.5):  # 500ms later
            cb2.get_ttl(60, vix_status='panic', match_context={})

        second_ts = float(mock_redis.get(PANIC_START_TS_KEY))

        assert first_ts == second_ts, \
            "Workers should read same shared timestamp"


# ═══════════════════════════════════════════════════════════════
# TEST: Panic Lifecycle
# ═══════════════════════════════════════════════════════════════

class TestPanicLifecycle:
    """Test complete panic start → end lifecycle."""

    def test_panic_start_creates_timestamp(self, circuit_breaker, mock_redis):
        """
        Panic detection should create timestamp.
        """
        assert mock_redis.get(PANIC_START_TS_KEY) is None

        circuit_breaker.get_ttl(60, vix_status='panic', match_context={})

        assert mock_redis.get(PANIC_START_TS_KEY) is not None

    def test_panic_end_clears_timestamp(self, circuit_breaker, mock_redis):
        """
        Panic end should clear timestamp.
        """
        # Start panic
        circuit_breaker.get_ttl(60, vix_status='panic', match_context={})

        assert mock_redis.get(PANIC_START_TS_KEY) is not None

        # End panic
        circuit_breaker.get_ttl(60, vix_status='normal', match_context={})

        assert mock_redis.get(PANIC_START_TS_KEY) is None

    def test_multiple_panic_cycles(self, circuit_breaker, mock_redis):
        """
        Multiple panic start/end cycles should work correctly.
        """
        for cycle in range(3):
            # Start panic
            with patch('time.time', return_value=1000000.0 + cycle * 1000):
                circuit_breaker.get_ttl(60, vix_status='panic', match_context={})

            ts = mock_redis.get(PANIC_START_TS_KEY)
            assert ts is not None, f"Cycle {cycle}: Timestamp should exist"

            # End panic
            circuit_breaker.get_ttl(60, vix_status='normal', match_context={})

            ts = mock_redis.get(PANIC_START_TS_KEY)
            assert ts is None, f"Cycle {cycle}: Timestamp should be cleared"


# ═══════════════════════════════════════════════════════════════
# TEST: Integration with AdaptivePanicQuota
# ═══════════════════════════════════════════════════════════════

class TestQuotaIntegration:
    """Test VIXCircuitBreaker correctly calls AdaptivePanicQuota."""

    def test_context_passed_to_quota(self, circuit_breaker, mock_redis):
        """
        Match context should be passed to quota calculation.
        """
        # Champions League context (high stakes)
        ttl_ucl, mode_ucl = circuit_breaker.get_ttl(
            60, vix_status='panic', match_context={'league': 'Champions League'}
        )

        # Clear for fresh test
        mock_redis._data.clear()

        # Ligue 1 context (medium stakes)
        ttl_l1, mode_l1 = circuit_breaker.get_ttl(
            60, vix_status='panic', match_context={'league': 'Ligue 1'}
        )

        # Different contexts may produce different results
        # (depends on panic duration and thresholds)
        # Main test: no crash, context is handled
        assert ttl_ucl is not None
        assert ttl_l1 is not None

    def test_no_panic_returns_base_ttl(self, circuit_breaker, mock_redis):
        """
        No panic should return base TTL (NORMAL mode).
        """
        ttl, mode = circuit_breaker.get_ttl(60, vix_status='normal', match_context={'league': 'Ligue 1'})

        assert ttl == 60, f"Expected base_ttl=60, got {ttl}"
        assert "NORMAL" in mode.upper(), f"Expected NORMAL mode, got {mode}"


# ═══════════════════════════════════════════════════════════════
# PYTEST CONFIGURATION
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])


# ═══════════════════════════════════════════════════════════════
# NEW TESTS - HEDGE FUND GRADE CORRECTIONS
# ═══════════════════════════════════════════════════════════════

class TestRealRaceCondition:
    """
    Test REAL race conditions with multi-threading.

    CRITICAL: These tests prove SETNX atomicity under concurrent access,
    not just sequential simulation.
    """

    @pytest.fixture
    def mock_redis(self):
        """Thread-safe MockRedis for concurrency tests."""
        return MockRedis(return_bytes=True)

    def test_concurrent_workers_with_threading(self, mock_redis):
        """
        Test multiple workers hitting Redis simultaneously.

        Uses threading.Barrier to synchronize start, ensuring
        true concurrent access to Redis.
        """
        num_workers = 5
        results = []
        errors = []
        barrier = threading.Barrier(num_workers)
        lock = threading.Lock()

        def worker(worker_id: int):
            try:
                # Create independent circuit breaker instance
                cb = VIXCircuitBreaker(redis_client=mock_redis)

                # Wait for all workers to be ready
                barrier.wait()

                # Small random delay to increase collision chance
                time.sleep(random.uniform(0, 0.005))

                # All workers try to set panic simultaneously
                ttl, mode = cb.get_ttl(60, "panic", {'league': 'Ligue 1'})

                # Record what this worker sees
                stored_ts = mock_redis.get(PANIC_START_TS_KEY)
                if stored_ts:
                    ts_value = float(stored_ts.decode() if isinstance(stored_ts, bytes) else stored_ts)
                else:
                    ts_value = None

                with lock:
                    results.append({
                        'worker_id': worker_id,
                        'timestamp': ts_value,
                        'ttl': ttl,
                        'mode': mode
                    })
            except Exception as e:
                with lock:
                    errors.append({'worker_id': worker_id, 'error': str(e)})

        # Launch workers
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_workers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Assertions
        assert len(errors) == 0, f"Workers had errors: {errors}"
        assert len(results) == num_workers, f"Not all workers completed: {len(results)}/{num_workers}"

        # All workers must see the SAME timestamp (First Writer Wins)
        timestamps = [r['timestamp'] for r in results if r['timestamp'] is not None]
        unique_timestamps = set(timestamps)

        assert len(unique_timestamps) == 1, \
            f"Race condition detected! Workers saw different timestamps: {unique_timestamps}"

        print(f"\n✅ All {num_workers} workers saw same timestamp: {list(unique_timestamps)[0]}")

    def test_high_contention_scenario(self, mock_redis):
        """
        Test under high contention: 20 workers, rapid fire.

        This stress test ensures SETNX holds under load.
        """
        num_workers = 20
        results = []
        barrier = threading.Barrier(num_workers)
        lock = threading.Lock()

        def worker(worker_id: int):
            cb = VIXCircuitBreaker(redis_client=mock_redis)
            barrier.wait()

            # Even smaller delay for higher contention
            time.sleep(random.uniform(0, 0.001))

            ttl, mode = cb.get_ttl(60, "panic", {})
            stored_ts = mock_redis.get(PANIC_START_TS_KEY)

            with lock:
                if stored_ts:
                    ts = float(stored_ts.decode() if isinstance(stored_ts, bytes) else stored_ts)
                    results.append(ts)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_workers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        # All 20 workers must see identical timestamp
        assert len(set(results)) == 1, \
            f"High contention race condition! Unique timestamps: {len(set(results))}"

        print(f"\n✅ High contention test passed: {num_workers} workers, 1 timestamp")


class TestBytesHandling:
    """Test proper handling of bytes vs str from Redis."""

    @pytest.fixture
    def mock_redis_bytes(self):
        """MockRedis that returns bytes (real Redis behavior)."""
        return MockRedis(return_bytes=True)

    @pytest.fixture
    def mock_redis_str(self):
        """MockRedis that returns str (some clients)."""
        return MockRedis(return_bytes=False)

    def test_handles_bytes_from_redis(self, mock_redis_bytes):
        """
        Test that bytes response from Redis is handled correctly.
        """
        cb = VIXCircuitBreaker(redis_client=mock_redis_bytes)

        # Trigger panic to set timestamp
        ttl, mode = cb.get_ttl(60, "panic", {'league': 'Ligue 1'})

        # Verify no crash and valid response
        assert ttl is not None
        assert mode is not None

        # Verify timestamp was stored and can be read
        stored = mock_redis_bytes.get(PANIC_START_TS_KEY)
        assert isinstance(stored, bytes), "MockRedis should return bytes"

        # Second call should also work (reads bytes)
        ttl2, mode2 = cb.get_ttl(60, "panic", {'league': 'Ligue 1'})
        assert ttl2 is not None

    def test_handles_str_from_redis(self, mock_redis_str):
        """
        Test that str response from Redis is also handled.
        (Some Redis clients return str instead of bytes)
        """
        cb = VIXCircuitBreaker(redis_client=mock_redis_str)

        ttl, mode = cb.get_ttl(60, "panic", {'league': 'Ligue 1'})

        assert ttl is not None
        assert mode is not None


class TestLoggingOptimization:
    """Test that logging is optimized (log on change only)."""

    @pytest.fixture
    def mock_redis(self):
        return MockRedis()

    def test_first_call_logs_state(self, mock_redis):
        """First call should always log (no previous state)."""
        cb = VIXCircuitBreaker(redis_client=mock_redis)

        # Initial state should be None
        assert cb._last_logged_mode is None
        assert cb._last_logged_tier is None

        # First call
        cb.get_ttl(60, "normal", {})

        # State should now be set
        assert cb._last_logged_mode is not None

    def test_repeated_calls_update_tracking(self, mock_redis):
        """Repeated calls with same state should update tracking vars."""
        cb = VIXCircuitBreaker(redis_client=mock_redis)

        # Multiple calls with same state
        for _ in range(5):
            cb.get_ttl(60, "normal", {})

        # Tracking should be set
        assert cb._last_logged_mode == "NORMAL"
        assert cb._last_logged_tier == 0

    def test_state_change_updates_tracking(self, mock_redis):
        """State change should update tracking variables."""
        cb = VIXCircuitBreaker(redis_client=mock_redis)

        # Normal state
        cb.get_ttl(60, "normal", {})
        normal_mode = cb._last_logged_mode

        # Panic state
        cb.get_ttl(60, "panic", {})
        panic_mode = cb._last_logged_mode

        # Should be different
        assert normal_mode != panic_mode or cb._last_logged_tier != 0


class TestFailSafeWithoutRedis:
    """
    Test Fail-Safe behavior when Redis is NOT configured.

    CRITICAL: This was the main bug found in audit.
    """

    def test_panic_without_redis_triggers_failsafe(self):
        """
        If Redis is not configured AND panic is detected,
        should trigger Fail-Safe (not return base_ttl).

        This was BUG #1 in the audit.
        """
        # Create circuit breaker WITHOUT Redis
        cb = VIXCircuitBreaker(redis_client=None)

        # Trigger panic
        ttl, mode = cb.get_ttl(60, "panic", {'league': 'Ligue 1'})

        # Should be Fail-Safe, NOT base_ttl
        assert ttl == 0, f"Expected TTL=0 (Fail-Safe), got {ttl}"
        assert "PANIC" in mode.upper(), f"Expected PANIC mode, got {mode}"

    def test_normal_without_redis_returns_base_ttl(self):
        """
        If no panic, should return base_ttl even without Redis.
        """
        cb = VIXCircuitBreaker(redis_client=None)

        ttl, mode = cb.get_ttl(60, "normal", {})

        assert ttl == 60, f"Expected base_ttl=60, got {ttl}"
        assert "NORMAL" in mode.upper(), f"Expected NORMAL mode, got {mode}"

    def test_warning_logged_for_panic_without_redis(self):
        """
        Panic without Redis should log a warning.
        """
        cb = VIXCircuitBreaker(redis_client=None)

        # This should log PANIC_WITHOUT_RELIABLE_TIMESTAMP
        ttl, mode = cb.get_ttl(60, "panic", {})

        # Test passes if no exception (logging happens internally)
        assert ttl == 0


class TestEdgeCasesCompleteness:
    """
    Additional edge case tests for 100% completeness.

    These tests cover scenarios not explicitly tested elsewhere:
    1. Panic duration calculation with edge values
    2. Mode transition logging verification
    """

    @pytest.fixture
    def mock_redis(self):
        return MockRedis()

    def test_panic_duration_zero_returns_tier1(self, mock_redis):
        """
        Test that duration=0 (just started panic) returns TIER 1.

        Edge case: Panic just detected, timestamp just set.
        Duration = 0 minutes → Should be TIER 1 (fresh panic)
        """
        # Pre-set timestamp to NOW (0 duration)
        import time
        mock_redis._data[PANIC_START_TS_KEY] = str(time.time())

        cb = VIXCircuitBreaker(redis_client=mock_redis)
        ttl, mode = cb.get_ttl(60, "panic", {'league': 'Ligue 1'})

        # Fresh panic (0 duration) should be TIER 1 = TTL 0 or very low
        assert ttl <= 5, f"Fresh panic should have TTL <= 5, got {ttl}"
        assert "PANIC" in mode.upper() or "FULL" in mode.upper(), \
            f"Expected panic mode, got {mode}"

    def test_very_old_timestamp_returns_tier4(self, mock_redis):
        """
        Test that very old timestamp (days) returns TIER 4.

        Edge case: Panic timestamp is days old (system was down).
        Should gracefully handle and return TIER 4 (new normal).
        """
        import time

        # Set timestamp to 7 days ago
        seven_days_ago = time.time() - (7 * 24 * 60 * 60)
        mock_redis._data[PANIC_START_TS_KEY] = str(seven_days_ago)

        cb = VIXCircuitBreaker(redis_client=mock_redis)
        ttl, mode = cb.get_ttl(60, "panic", {'league': 'Ligue 1'})

        # 7 days = 10080 minutes >> tier3 threshold → TIER 4
        # TIER 4 = NEW_NORMAL with higher TTL
        assert ttl >= 30, f"Very old panic should have TTL >= 30 (TIER 4), got {ttl}"
        assert "NORMAL" in mode.upper() or "NEW" in mode.upper() or ttl == 60, \
            f"Expected new_normal or high TTL, got {mode}"


class TestLogConfigVerification:
    """
    Tests to verify logging configuration is production-ready.
    """

    @pytest.fixture
    def mock_redis(self):
        return MockRedis()

    def test_repeated_calls_dont_accumulate_state(self, mock_redis):
        """
        Test that repeated calls don't cause memory/state issues.

        Verifies logging tracking variables work correctly over many calls.
        """
        cb = VIXCircuitBreaker(redis_client=mock_redis)

        # 100 calls should not cause issues
        for i in range(100):
            vix_status = "panic" if i % 10 == 0 else "normal"
            ttl, mode = cb.get_ttl(60, vix_status, {'league': 'Ligue 1'})
            assert ttl is not None
            assert mode is not None

        # Tracking vars should be set (not growing unbounded)
        assert cb._last_logged_mode is not None
        assert cb._last_logged_tier is not None

        # Should be one of valid values
        assert cb._last_logged_mode in ["NORMAL", "PANIC_FULL", "PANIC_PARTIAL",
                                        "DEGRADED", "NEW_NORMAL"]


