"""Unit tests for SmartCache - X-Fetch Algorithm"""
import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock

from cache.smart_cache import SmartCache
from cache.key_factory import key_factory


# ===== FIXTURES =====

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    return redis_mock


@pytest.fixture
def smart_cache_instance(mock_redis):
    """SmartCache instance with mocked Redis"""
    with patch('cache.smart_cache.redis.from_url', return_value=mock_redis):
        cache = SmartCache(enabled=True)
        cache._redis = mock_redis
        return cache


# ===== BASIC FUNCTIONALITY =====

def test_cache_initialization():
    """Test cache initializes correctly"""
    cache = SmartCache(enabled=False)
    assert cache.enabled == False
    assert cache.default_ttl == 3600


def test_cache_miss(smart_cache_instance, mock_redis):
    """Test cache miss returns None"""
    mock_redis.get.return_value = None

    value, is_stale = smart_cache_instance.get("test_key")

    assert value is None
    assert is_stale == False
    mock_redis.get.assert_called_once_with("test_key")


def test_cache_hit_fresh(smart_cache_instance, mock_redis):
    """Test cache hit with fresh value

    MATHEMATICAL FOUNDATION:
    - Created: 10s ago
    - TTL: 3600s
    - Remaining: 3590s
    - P(X-Fetch) = e^(-3590/3600) ≈ 0.369 (36.9%)
    - P(Fresh) = 1 - 0.369 = 0.631 (63.1%)

    STATISTICAL VALIDATION:
    - Sample size: 200 (power analysis: n ≈ 89 for 10% deviation)
    - Expected fresh: 200 * 0.631 = 126.2
    - Variance: n*p*(1-p) = 200*0.631*0.369 ≈ 46.6
    - Std dev: sqrt(46.6) ≈ 6.8
    - 95% CI: 126.2 ± 1.96*6.8 = [112.9, 139.5]

    THRESHOLDS (Conservative - wider than 95% CI):
    - Statistical 95% CI: [112.9, 139.5]
    - Conservative bounds: [110, 150]
    - Minimum: 110 (55% - allows 2.4 std dev below mean)
    - Maximum: 150 (75% - catches X-Fetch malfunction)
    - Rationale: Extra margin for stochastic variance in CI tests
    """
    cached_data = {
        "value": {"prediction": "WIN", "confidence": 0.75},
        "created_at": time.time() - 10,  # Created 10s ago
        "ttl": 3600,  # 1 hour TTL
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    # Statistical sample (increased from 50)
    fresh_count = 0
    sample_size = 200

    for _ in range(sample_size):
        value, is_stale = smart_cache_instance.get("test_key")
        if not is_stale:
            fresh_count += 1

    # Assert with scientific bounds
    fresh_rate = fresh_count / sample_size

    # Lower bound: 55% (allows variance)
    assert fresh_count > 110, (
        f"Fresh rate too low: {fresh_count}/{sample_size} ({fresh_rate:.1%}). "
        f"Expected: ~63%, Min threshold: 55% (110/{sample_size})"
    )

    # Upper bound: 75% (catches X-Fetch malfunction)
    assert fresh_count < 150, (
        f"Fresh rate too high: {fresh_count}/{sample_size} ({fresh_rate:.1%}). "
        f"Max threshold: 75% (150/{sample_size}). X-Fetch may not be triggering."
    )


def test_cache_hit_stale(smart_cache_instance, mock_redis):
    """Test cache hit with stale value"""
    cached_data = {
        "value": {"prediction": "WIN", "confidence": 0.75},
        "created_at": time.time() - 7200,  # 2 hours ago
        "ttl": 3600,  # 1 hour TTL
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    value, is_stale = smart_cache_instance.get("test_key")

    assert value == {"prediction": "WIN", "confidence": 0.75}
    assert is_stale == True  # Should be stale


def test_cache_set(smart_cache_instance, mock_redis):
    """Test cache set stores value with metadata"""
    test_value = {"prediction": "WIN", "confidence": 0.75}

    result = smart_cache_instance.set("test_key", test_value, ttl=1800)

    assert result == True
    mock_redis.setex.assert_called_once()

    # Verify stored data structure
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "test_key"
    assert call_args[0][1] == 1800  # TTL

    stored_data = json.loads(call_args[0][2])
    assert stored_data["value"] == test_value
    assert "created_at" in stored_data
    assert stored_data["ttl"] == 1800


def test_cache_delete(smart_cache_instance, mock_redis):
    """Test cache delete removes key"""
    mock_redis.delete.return_value = 1

    result = smart_cache_instance.delete("test_key")

    assert result == True
    mock_redis.delete.assert_called_once_with("test_key")


# ===== X-FETCH ALGORITHM =====

def test_xfetch_probability_near_expiry(smart_cache_instance):
    """Test X-Fetch triggers at very high rate near expiry

    MATHEMATICAL FOUNDATION:
    - Remaining: 10s
    - Delta: 3600s
    - P(X-Fetch) = e^(-10/3600) = e^(-0.00278) ≈ 0.997 (99.7%)

    STATISTICAL VALIDATION:
    - Sample size: 200 (power analysis: n ≈ 39 for 1% deviation)
    - Expected triggers: 200 * 0.997 = 199.4
    - Variance: minimal (deterministic territory)
    - This is >99% probability (near-deterministic)

    THRESHOLDS (Conservative):
    - Minimum: 195 (97.5% - allows rare variance, 5.7 std dev below)
    - Rationale: Ultra-conservative for near-deterministic scenario
    """
    now = time.time()
    delta = 3600
    expiry = now + 10  # Very near expiry

    triggers = 0
    sample_size = 200

    for _ in range(sample_size):
        if smart_cache_instance._should_refresh_xfetch(now, expiry, delta):
            triggers += 1

    trigger_rate = triggers / sample_size

    # Should trigger almost always (>97.5%)
    assert triggers > 195, (
        f"Near-expiry trigger rate too low: {triggers}/{sample_size} ({trigger_rate:.1%}). "
        f"Expected: >99%, Min threshold: 97.5% (195/{sample_size})"
    )


def test_xfetch_low_probability_far_from_expiry(smart_cache_instance):
    """Test X-Fetch triggers at expected rate far from expiry

    MATHEMATICAL FOUNDATION:
    - Remaining: 3500s
    - Delta: 3600s
    - P(X-Fetch) = e^(-3500/3600) = e^(-0.972) ≈ 0.378 (37.8%)

    STATISTICAL VALIDATION:
    - Sample size: 500 (power analysis: n ≈ 122 for 10% deviation)
    - Expected triggers: 500 * 0.378 = 189
    - Variance: 500*0.378*0.622 ≈ 117.6
    - Std dev: sqrt(117.6) ≈ 10.8
    - 95% CI: 189 ± 1.96*10.8 = [167.8, 210.2]

    THRESHOLDS (Conservative - wider than 95% CI):
    - Statistical 95% CI: [167.8, 210.2]
    - Conservative bounds: [160, 220]
    - Minimum: 160 (32% - catches X-Fetch malfunction, 2.7 std dev below)
    - Maximum: 220 (44% - allows 3 std dev above mean)
    - Rationale: Extra margin for stochastic variance in CI tests
    """
    now = time.time()
    delta = 3600
    expiry = now + 3500  # Far from expiry (97% of TTL remaining)

    triggers = 0
    sample_size = 500  # Increased for precision

    for _ in range(sample_size):
        if smart_cache_instance._should_refresh_xfetch(now, expiry, delta):
            triggers += 1

    trigger_rate = triggers / sample_size

    # Upper bound: 44% (allows variance)
    assert triggers < 220, (
        f"Trigger rate too high: {triggers}/{sample_size} ({trigger_rate:.1%}). "
        f"Expected: ~38%, Max threshold: 44% (220/{sample_size})"
    )

    # Lower bound: 32% (catches broken X-Fetch)
    assert triggers > 160, (
        f"Trigger rate too low: {triggers}/{sample_size} ({trigger_rate:.1%}). "
        f"Expected: ~38%, Min threshold: 32% (160/{sample_size}). "
        f"X-Fetch may be broken."
    )


def test_cache_hit_with_xfetch_trigger(smart_cache_instance, mock_redis):
    """Test cache returns stale=True when X-Fetch triggers near expiry

    MATHEMATICAL FOUNDATION:
    - Created: 3590s ago
    - TTL: 3600s
    - Remaining: 10s
    - P(X-Fetch) = e^(-10/3600) = e^(-0.00278) ≈ 0.997 (99.7%)

    STATISTICAL VALIDATION:
    - Sample size: 200 (increased from 50 for consistency)
    - Expected stale: 200 * 0.997 = 199.4
    - This is deterministic territory (>99%)

    THRESHOLDS (Conservative):
    - Minimum: 195 (97.5% - allows rare variance, 5.7 std dev below)
    """
    now = time.time()
    cached_data = {
        "value": {"prediction": "WIN"},
        "created_at": now - 3590,  # Created 3590s ago
        "ttl": 3600,  # 1h TTL → expires in 10s
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    stale_count = 0
    sample_size = 200  # Increased from 50 for consistency

    for _ in range(sample_size):
        value, is_stale = smart_cache_instance.get("test_key")
        if is_stale:
            stale_count += 1

    stale_rate = stale_count / sample_size

    # Should be stale almost always (X-Fetch triggers near expiry)
    assert stale_count > 195, (
        f"Stale rate too low: {stale_count}/{sample_size} ({stale_rate:.1%}). "
        f"Expected: >99.7%, Min threshold: 97.5% (195/{sample_size})"
    )


# ===== ERROR HANDLING =====

def test_cache_disabled(mock_redis):
    """Test cache with enabled=False"""
    cache = SmartCache(enabled=False)

    value, is_stale = cache.get("test_key")
    assert value is None
    assert is_stale == False

    result = cache.set("test_key", {"data": "test"})
    assert result == False


def test_cache_json_decode_error(smart_cache_instance, mock_redis):
    """Test graceful handling of invalid JSON"""
    mock_redis.get.return_value = "invalid json {"

    value, is_stale = smart_cache_instance.get("test_key")

    assert value is None
    assert is_stale == False


def test_cache_redis_connection_error(smart_cache_instance, mock_redis):
    """Test graceful degradation on Redis error"""
    from redis.exceptions import ConnectionError

    mock_redis.get.side_effect = ConnectionError("Connection refused")

    value, is_stale = smart_cache_instance.get("test_key")

    assert value is None
    assert is_stale == False


# ===== INVALIDATION =====

def test_invalidate_pattern(smart_cache_instance, mock_redis):
    """Test pattern-based invalidation"""
    # Mock SCAN iter
    mock_redis.scan_iter.return_value = [
        "monps:prod:v1:pred:{m_12345}:default",
        "monps:prod:v1:pred:{m_12345}:risk_high",
    ]

    count = smart_cache_instance.invalidate_pattern("monps:prod:v1:*:{m_12345}:*")

    assert count == 2
    assert mock_redis.delete.call_count == 2


def test_ping(smart_cache_instance, mock_redis):
    """Test Redis ping"""
    mock_redis.ping.return_value = True

    result = smart_cache_instance.ping()

    assert result == True
    mock_redis.ping.assert_called()
