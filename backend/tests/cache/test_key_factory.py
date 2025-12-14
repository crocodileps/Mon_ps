"""Unit tests for KeyFactory"""
import pytest
from cache.key_factory import KeyFactory, key_factory


def test_prediction_key_default():
    """Test prediction key without config"""
    key = key_factory.prediction_key("12345")
    assert key == "monps:prod:v1:pred:{m_12345}:default"


def test_prediction_key_with_config():
    """Test prediction key with config variant"""
    config = {"risk": "high", "model": "v2"}
    key = key_factory.prediction_key("12345", config)

    assert key.startswith("monps:prod:v1:pred:{m_12345}:")
    assert len(key.split(":")[-1]) == 12  # 12-char hash


def test_config_hash_deterministic():
    """Test that same config produces same hash"""
    config1 = {"a": 1, "b": 2}
    config2 = {"b": 2, "a": 1}  # Different order

    hash1 = KeyFactory._hash_config(config1)
    hash2 = KeyFactory._hash_config(config2)

    assert hash1 == hash2  # Deterministic despite order


def test_cluster_hash_tag():
    """Test that cluster hash tag is present"""
    key = key_factory.prediction_key("12345")
    assert "{m_12345}" in key  # Cluster affinity


def test_invalidation_pattern():
    """Test invalidation pattern generation"""
    pattern = key_factory.invalidation_pattern("12345")
    assert pattern == "monps:prod:v1:*:{m_12345}:*"
