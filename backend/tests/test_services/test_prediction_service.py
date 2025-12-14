"""Tests for PredictionService - Business Logic Layer.

Validates:
1. Business logic (validation rules, constraints)
2. Service ↔ Repository integration
3. Error handling
4. Edge cases
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from quantum_core.api.predictions.service import PredictionService
from quantum_core.repositories.prediction_repository import PredictionRepository
from quantum_core.models.predictions import MarketPrediction, EnsemblePrediction
from quantum_core.api.common.exceptions import InvalidDateError
from tests.factories import (
    create_market_prediction,
    create_ensemble_realistic,
    create_ensemble_high_disagreement,
)


class TestPredictionServiceValidation:
    """Tests for service-level validation (business rules)."""

    def test_service_initialization(self):
        """Test service can be initialized."""
        service = PredictionService(
            repository=None,  # Dev mode without repository
            min_confidence=0.70,
            max_prediction_days=60,
        )

        assert service.min_confidence == 0.70
        assert service.max_prediction_days == 60

    def test_service_initialization_with_repository(self):
        """Test service initialization with repository injection."""
        mock_repo = MagicMock(spec=PredictionRepository)

        service = PredictionService(
            repository=mock_repo, min_confidence=0.75, max_prediction_days=30
        )

        assert service.repository == mock_repo
        assert service.min_confidence == 0.75
        assert service.max_prediction_days == 30


class TestPredictionServiceWithRepository:
    """Tests for service integration with repository."""

    @pytest.mark.anyio
    async def test_get_prediction_by_id_with_repository(self):
        """Test getting prediction by ID (repository integration)."""
        # Mock repository
        mock_repo = MagicMock(spec=PredictionRepository)
        prediction = create_market_prediction(prediction_id="test_123")
        mock_repo.get_by_id = AsyncMock(return_value=prediction)

        # Service
        service = PredictionService(repository=mock_repo)

        # Call
        result = await service.get_prediction_by_id("test_123")

        # Validate
        assert result == prediction
        mock_repo.get_by_id.assert_called_once_with("test_123")

    @pytest.mark.anyio
    async def test_get_prediction_by_id_without_repository(self):
        """Test getting prediction without repository (dev mode)."""
        service = PredictionService(repository=None)

        # Should return None (no repository)
        result = await service.get_prediction_by_id("test_123")

        assert result is None

    @pytest.mark.anyio
    async def test_list_predictions_with_repository(self):
        """Test listing predictions (repository integration)."""
        # Mock repository
        mock_repo = MagicMock(spec=PredictionRepository)
        predictions = [
            create_market_prediction(match_id="match_1"),
            create_market_prediction(match_id="match_2"),
        ]
        mock_repo.list = AsyncMock(return_value=predictions)

        # Service
        service = PredictionService(repository=mock_repo)

        # Call (use named parameters, not filters dict)
        result = await service.list_predictions(match_id="match_1", limit=10)

        # Validate
        assert result == predictions
        # Repository is called with positional args (dict, int)
        mock_repo.list.assert_called_once_with({"match_id": "match_1"}, 10)

    @pytest.mark.anyio
    async def test_list_predictions_without_repository(self):
        """Test listing predictions without repository (dev mode)."""
        service = PredictionService(repository=None)

        # Should return empty list
        result = await service.list_predictions()

        assert result == []

    @pytest.mark.anyio
    async def test_update_prediction_with_repository(self):
        """Test updating prediction (repository integration)."""
        # Mock repository
        mock_repo = MagicMock(spec=PredictionRepository)
        updated_pred = create_market_prediction(
            prediction_id="test_123", confidence_score=0.95
        )
        mock_repo.update = AsyncMock(return_value=updated_pred)

        # Service
        service = PredictionService(repository=mock_repo)

        # Call (use named parameters, not dict)
        result = await service.update_prediction(
            "test_123", confidence_score=0.95
        )

        # Validate
        assert result == updated_pred
        mock_repo.update.assert_called_once_with("test_123", {"confidence_score": 0.95})

    @pytest.mark.anyio
    async def test_update_prediction_without_repository(self):
        """Test updating prediction without repository raises error."""
        service = PredictionService(repository=None)

        # Should raise NotImplementedError
        with pytest.raises(NotImplementedError, match="No repository"):
            await service.update_prediction("test_123", confidence_score=0.95)


class TestPredictionServiceBusinessLogic:
    """Tests for business logic (validation rules)."""

    def test_validate_match_date_valid_future_date(self):
        """Test that future date within limit is valid."""
        service = PredictionService(max_prediction_days=60)

        # Future date within 60 days
        future_date = datetime.now(timezone.utc) + timedelta(days=30)

        # Should not raise
        service._validate_match_date(future_date)

    def test_validate_match_date_too_far_future(self):
        """Test that date beyond limit raises error."""
        service = PredictionService(max_prediction_days=60)

        # Future date beyond 60 days
        far_future = datetime.now(timezone.utc) + timedelta(days=90)

        # Should raise InvalidDateError
        with pytest.raises(InvalidDateError, match="too far in"):
            service._validate_match_date(far_future)

    def test_validate_match_date_past_date(self):
        """Test that past date raises error."""
        service = PredictionService()

        # Past date
        past_date = datetime.now(timezone.utc) - timedelta(days=1)

        # Should raise InvalidDateError
        with pytest.raises(InvalidDateError, match="in the past"):
            service._validate_match_date(past_date)

    def test_validate_match_date_timezone_naive_is_handled(self):
        """Test that timezone-naive datetime is converted to aware.

        ADR #005 fix: datetime.now(UTC) instead of utcnow()
        """
        service = PredictionService(default_tz=timezone.utc)

        # Naive datetime (no timezone)
        naive_date = datetime(2025, 12, 20, 15, 0, 0)  # No tzinfo

        # Should convert to aware and not raise
        # (Assumes it's in default_tz)
        service._validate_match_date(naive_date)


class TestPredictionServiceEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.anyio
    async def test_get_nonexistent_prediction(self):
        """Test getting prediction that doesn't exist."""
        # Mock repository returning None
        mock_repo = MagicMock(spec=PredictionRepository)
        mock_repo.get_by_id = AsyncMock(return_value=None)

        service = PredictionService(repository=mock_repo)

        # Should return None
        result = await service.get_prediction_by_id("non_existent")

        assert result is None

    @pytest.mark.anyio
    async def test_update_nonexistent_prediction(self):
        """Test updating prediction that doesn't exist."""
        # Mock repository raising ValueError
        mock_repo = MagicMock(spec=PredictionRepository)
        mock_repo.update = AsyncMock(side_effect=ValueError("Prediction not found"))

        service = PredictionService(repository=mock_repo)

        # Should raise ValueError
        with pytest.raises(ValueError, match="not found"):
            await service.update_prediction("non_existent", confidence_score=0.95)

    def test_service_with_custom_thresholds(self):
        """Test service with custom configuration."""
        service = PredictionService(
            min_confidence=0.85, max_prediction_days=30, default_tz=timezone.utc
        )

        assert service.min_confidence == 0.85
        assert service.max_prediction_days == 30
        assert service.default_tz == timezone.utc


class TestPredictionServiceIntegration:
    """Integration tests with real repository (in-memory SQLite)."""

    @pytest.mark.anyio
    async def test_full_crud_cycle_with_repository(self, db_session):
        """Test complete CRUD cycle through service."""
        from quantum_core.repositories.prediction_repository import (
            PostgresPredictionRepository,
        )

        # Setup
        repository = PostgresPredictionRepository(db_session)
        service = PredictionService(repository=repository)

        # 1. Create prediction via mock generation
        # Note: generate_match_prediction requires UnifiedBrain which is complex
        # Instead, we test repository operations directly through service
        prediction = create_market_prediction(
            prediction_id="integration_test_123", match_id="psg_om"
        )

        # Persist via repository (service delegates)
        await repository.create(prediction)

        # 2. Read via service
        retrieved = await service.get_prediction_by_id("integration_test_123")
        assert retrieved is not None
        assert retrieved.match_id == "psg_om"

        # 3. Update via service
        updated = await service.update_prediction(
            "integration_test_123", confidence_score=0.95
        )
        assert updated.confidence_score == 0.95

        # 4. List via service
        predictions = await service.list_predictions(
            match_id="psg_om"
        )
        assert len(predictions) == 1
        assert predictions[0].confidence_score == 0.95

    @pytest.mark.anyio
    async def test_list_with_multiple_predictions(self, db_session):
        """Test listing multiple predictions through service."""
        from quantum_core.repositories.prediction_repository import (
            PostgresPredictionRepository,
        )

        repository = PostgresPredictionRepository(db_session)
        service = PredictionService(repository=repository)

        # Create 5 predictions
        for i in range(5):
            pred = create_market_prediction(match_id=f"match_{i}")
            await repository.create(pred)

        # List all
        predictions = await service.list_predictions(limit=100)
        assert len(predictions) == 5

        # List with limit
        predictions_limited = await service.list_predictions(limit=3)
        assert len(predictions_limited) == 3
