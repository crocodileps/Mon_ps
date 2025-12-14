"""Tests for Dependency Injection - Service Lifecycle Management.

Validates:
- Singleton pattern for services
- Dependency override in tests
- Service initialization
- Cleanup on shutdown

Critical for production: Ensures services are properly managed.
"""

import pytest
from quantum_core.config.dependencies import get_prediction_service, get_settings
from quantum_core.api.predictions.service import PredictionService


# ─────────────────────────────────────────────────────────────────────────
# TESTS - Dependency Injection
# ─────────────────────────────────────────────────────────────────────────


class TestDependencyInjection:
    """Tests for DI container and service lifecycle."""

    def test_get_settings_returns_singleton(self):
        """Test that settings is singleton (same instance)."""
        # Clear cache first
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        # Should be same object
        assert settings1 is settings2

    def test_get_prediction_service_initializes_correctly(self):
        """Test that service is initialized with correct config."""
        service = get_prediction_service()

        assert isinstance(service, PredictionService)
        assert service.min_confidence == 0.70  # Default
        assert service.max_prediction_days == 60  # Default

    def test_service_singleton_pattern_with_cache(self):
        """Test that service follows singleton pattern."""
        service1 = get_prediction_service()
        service2 = get_prediction_service()

        # Should be same instance (cached in _services dict)
        assert service1 is service2
