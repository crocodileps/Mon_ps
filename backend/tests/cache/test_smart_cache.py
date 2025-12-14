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
    """Test cache hit with fresh value"""
    cached_data = {
        "value": {"prediction": "WIN", "confidence": 0.75},
        "created_at": time.time() - 10,  # Created 10s ago (very fresh)
        "ttl": 3600,  # 1h TTL
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    # Run multiple times to account for probabilistic nature
    fresh_count = 0
    for _ in range(50):
        value, is_stale = smart_cache_instance.get("test_key")
        if not is_stale:
            fresh_count += 1

    # Should be fresh most of the time (low X-Fetch probability)
    assert fresh_count > 25  # At least 50% fresh (allow variance)


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
    """Test X-Fetch triggers near expiry"""
    now = time.time()
    delta = 3600  # 1 hour TTL
    expiry = now + 10  # Expires in 10 seconds

    # Run multiple times (probabilistic)
    triggers = 0
    for _ in range(100):
        if smart_cache_instance._should_refresh_xfetch(now, expiry, delta):
            triggers += 1

    # Near expiry → high probability (should trigger often)
    assert triggers > 30  # At least 30% probability


def test_xfetch_low_probability_far_from_expiry(smart_cache_instance):
    """Test X-Fetch rarely triggers far from expiry"""
    now = time.time()
    delta = 3600  # 1 hour TTL
    expiry = now + 3500  # Expires in ~1 hour (97% of TTL remaining)

    # Run multiple times
    triggers = 0
    for _ in range(100):
        if smart_cache_instance._should_refresh_xfetch(now, expiry, delta):
            triggers += 1

    # Far from expiry → low probability (but allow variance)
    assert triggers < 70  # Less than 70% probability (probabilistic)


def test_cache_hit_with_xfetch_trigger(smart_cache_instance, mock_redis):
    """Test cache returns stale=True when X-Fetch triggers"""
    # Create cached data near expiry
    now = time.time()
    cached_data = {
        "value": {"prediction": "WIN"},
        "created_at": now - 3590,  # Created 3590s ago
        "ttl": 3600,  # 1h TTL → expires in 10s
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    # Run multiple times (probabilistic)
    stale_count = 0
    for _ in range(50):
        value, is_stale = smart_cache_instance.get("test_key")
        if is_stale:
            stale_count += 1

    # Should trigger X-Fetch often (near expiry)
    assert stale_count > 10  # At least 20% of requests


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
