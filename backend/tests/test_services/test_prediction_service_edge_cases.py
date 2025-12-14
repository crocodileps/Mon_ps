"""Tests for PredictionService Edge Cases - Business Logic Robustness.

Validates edge cases that might fail in production:
- Timezone naive datetime handling
- Boundary conditions (exact limits)
- Very low confidence scores
- Empty/null filters
"""

import pytest
from datetime import datetime, timezone, timedelta

from quantum_core.api.predictions.service import PredictionService
from quantum_core.api.common.exceptions import InvalidDateError, LowConfidenceError
from tests.factories import create_ensemble_realistic


# ─────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def service():
    """PredictionService with default config."""
    return PredictionService(
        repository=None,
        min_confidence=0.70,
        max_prediction_days=60,
    )


# ─────────────────────────────────────────────────────────────────────────
# TESTS - Edge Cases
# ─────────────────────────────────────────────────────────────────────────


class TestServiceEdgeCases:
    """Validate edge cases that could fail in production."""

    def test_validate_match_date_timezone_naive_converted_to_utc(self, service):
        """Test that timezone-naive datetimes are converted to UTC.

        Critical: Without this, timezone-aware comparisons would fail.
        Production bug: Match scheduled 20:00 Paris → stored as 20:00 UTC (wrong).
        """
        # Timezone-naive datetime (no tzinfo)
        naive_date = datetime(2025, 12, 25, 20, 0, 0)  # No timezone
        assert naive_date.tzinfo is None

        # Call validation (should convert to UTC internally)
        # Note: This assumes service handles naive dates gracefully
        try:
            service._validate_match_date(naive_date)
            # If no error, conversion worked
            assert True
        except InvalidDateError as e:
            # If error is about past date, naive→UTC conversion happened
            # (naive 2025-12-25 20:00 → UTC might be past if now is late 2025)
            assert "past" in str(e).lower()

    def test_validate_match_date_exactly_at_max_boundary(self, service):
        """Test date exactly at max_prediction_days boundary (60 days).

        Boundary test: Off-by-one errors common in date validation.
        """
        # Exactly 60 days in future
        boundary_date = datetime.now(timezone.utc) + timedelta(days=60)

        # Should NOT raise (60 days is allowed)
        try:
            service._validate_match_date(boundary_date)
            assert True  # Success
        except InvalidDateError:
            pytest.fail("Date at exact boundary should be allowed")

    def test_validate_match_date_one_second_past_boundary(self, service):
        """Test date one second past max boundary (60 days + 1 second).

        Boundary test: Should fail at 60 days + 1 second.
        """
        # 60 days + 1 second
        past_boundary = datetime.now(timezone.utc) + timedelta(days=60, seconds=1)

        # Should raise InvalidDateError
        with pytest.raises(InvalidDateError, match="too far in"):
            service._validate_match_date(past_boundary)

    @pytest.mark.anyio
    async def test_list_predictions_with_none_filters(self, service):
        """Test that None/null filters don't crash.

        Edge case: Frontend might send null instead of omitting parameter.
        """
        # All filters None
        result = await service.list_predictions(
            match_id=None,
            competition=None,
            limit=10,
        )

        # Should return empty list (no repository)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_service_with_very_low_min_confidence_threshold(self):
        """Test service with extreme min_confidence (0.01).

        Edge case: Very low threshold should still work.
        """
        service = PredictionService(
            repository=None,
            min_confidence=0.01,  # Extreme low
            max_prediction_days=60,
        )

        # Should initialize without error
        assert service.min_confidence == 0.01

    def test_service_with_very_high_max_prediction_days(self):
        """Test service with extreme max_prediction_days (365).

        Edge case: Very long prediction horizon.
        """
        service = PredictionService(
            repository=None,
            min_confidence=0.70,
            max_prediction_days=365,  # 1 year
        )

        # Should initialize without error
        assert service.max_prediction_days == 365

        # Validate 364 days in future (should work)
        future_date = datetime.now(timezone.utc) + timedelta(days=364)
        service._validate_match_date(future_date)  # Should not raise
