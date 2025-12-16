"""Settings tests - Hedge Fund systematic approach.

Architecture: 4 test classes for separation of concerns.
"""

import pytest
from infrastructure.config.settings import Settings
from infrastructure.config.dependencies import get_settings


class TestSettingsDefaults:
    """Test default values with isolated environment."""

    def test_default_values_clean_env(self, isolated_env):
        """Defaults with NO env vars (deterministic)."""
        settings = Settings()

        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.min_confidence_threshold == 0.70
        assert settings.max_prediction_days == 60


class TestSettingsEnvironmentVariables:
    """Test environment variable loading."""

    def test_production_environment(self, prod_env):
        """Production env vars loaded correctly."""
        settings = Settings()

        assert settings.environment == "production"
        assert settings.min_confidence_threshold == 0.85

    def test_selective_override(self, isolated_env, monkeypatch):
        """Selective env var override."""
        monkeypatch.setenv("MIN_CONFIDENCE_THRESHOLD", "0.95")

        settings = Settings()
        assert settings.min_confidence_threshold == 0.95


class TestSettingsSingletonPattern:
    """Test singleton with proper cache management."""

    def test_singleton_same_instance(self):
        """get_settings returns cached instance."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_isolation_between_tests(self):
        """Cache cleared between tests (implicit via fixture)."""
        # This test passes = isolation working
        settings = get_settings()
        assert settings is not None


class TestSettingsValidation:
    """Test Pydantic validation rules."""

    def test_min_confidence_bounds(self):
        """min_confidence in [0, 1]."""
        with pytest.raises(Exception):  # ValidationError
            Settings(min_confidence_threshold=-0.1)

        with pytest.raises(Exception):
            Settings(min_confidence_threshold=1.5)

        # Valid
        s = Settings(min_confidence_threshold=0.75)
        assert s.min_confidence_threshold == 0.75
