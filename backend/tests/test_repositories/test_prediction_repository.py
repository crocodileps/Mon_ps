"""Tests for PredictionRepository - ADR #008.

Validates:
1. CRUD operations (Create, Read, Update, Delete)
2. ORM ↔ Domain mapping coherence
3. Database persistence
4. Query filtering
"""

import pytest
from typing import List
from datetime import datetime, timezone

from quantum_core.repositories.prediction_repository import (
    PostgresPredictionRepository,
)
from quantum_core.models.predictions import MarketPrediction, MarketCategory
from quantum_core.database.models import PredictionORM
from tests.factories import create_market_prediction


class TestPostgresPredictionRepository:
    """Tests for PostgreSQL implementation of PredictionRepository."""

    @pytest.mark.anyio
    async def test_create_prediction(
        self, db_session, sample_market_prediction: MarketPrediction
    ):
        """Test creating a prediction in database."""
        repository = PostgresPredictionRepository(db_session)

        # Create
        created = await repository.create(sample_market_prediction)

        # Validate returned object
        assert created.prediction_id == sample_market_prediction.prediction_id
        assert created.match_id == sample_market_prediction.match_id
        assert created.fair_odds == sample_market_prediction.fair_odds

        # Validate database persistence
        db_pred = (
            db_session.query(PredictionORM)
            .filter(PredictionORM.prediction_id == created.prediction_id)
            .first()
        )
        assert db_pred is not None
        assert db_pred.match_id == sample_market_prediction.match_id

    @pytest.mark.anyio
    async def test_get_by_id_existing(
        self, db_session, sample_market_prediction: MarketPrediction
    ):
        """Test getting prediction by ID (found)."""
        repository = PostgresPredictionRepository(db_session)

        # Create first
        await repository.create(sample_market_prediction)

        # Get by ID
        retrieved = await repository.get_by_id(sample_market_prediction.prediction_id)

        # Validate
        assert retrieved is not None
        assert retrieved.prediction_id == sample_market_prediction.prediction_id
        assert retrieved.match_id == sample_market_prediction.match_id
        assert retrieved.fair_odds == sample_market_prediction.fair_odds

    @pytest.mark.anyio
    async def test_get_by_id_not_found(self, db_session):
        """Test getting prediction by ID (not found)."""
        repository = PostgresPredictionRepository(db_session)

        # Get non-existent
        retrieved = await repository.get_by_id("non_existent_id")

        # Should be None
        assert retrieved is None

    @pytest.mark.anyio
    async def test_list_predictions_no_filters(self, db_session):
        """Test listing all predictions without filters."""
        repository = PostgresPredictionRepository(db_session)

        # Create 3 predictions
        pred1 = create_market_prediction(match_id="match_1", fair_odds=1.85)
        pred2 = create_market_prediction(match_id="match_2", fair_odds=2.50)
        pred3 = create_market_prediction(match_id="match_3", fair_odds=3.00)

        await repository.create(pred1)
        await repository.create(pred2)
        await repository.create(pred3)

        # List all
        predictions = await repository.list()

        # Validate
        assert len(predictions) == 3

        # Check IDs present
        ids = [p.prediction_id for p in predictions]
        assert pred1.prediction_id in ids
        assert pred2.prediction_id in ids
        assert pred3.prediction_id in ids

    @pytest.mark.anyio
    async def test_list_predictions_with_filter(self, db_session):
        """Test listing predictions with filter."""
        repository = PostgresPredictionRepository(db_session)

        # Create predictions for different matches
        pred1 = create_market_prediction(match_id="psg_om", fair_odds=1.85)
        pred2 = create_market_prediction(match_id="psg_om", fair_odds=2.50)
        pred3 = create_market_prediction(match_id="lyon_marseille", fair_odds=3.00)

        await repository.create(pred1)
        await repository.create(pred2)
        await repository.create(pred3)

        # Filter by match_id
        predictions = await repository.list(filters={"match_id": "psg_om"})

        # Validate
        assert len(predictions) == 2

        # All should be psg_om
        for pred in predictions:
            assert pred.match_id == "psg_om"

    @pytest.mark.anyio
    async def test_list_predictions_with_limit(self, db_session):
        """Test listing predictions with limit."""
        repository = PostgresPredictionRepository(db_session)

        # Create 10 predictions
        for i in range(10):
            pred = create_market_prediction(match_id=f"match_{i}")
            await repository.create(pred)

        # List with limit 5
        predictions = await repository.list(limit=5)

        # Should return only 5
        assert len(predictions) == 5

    @pytest.mark.anyio
    async def test_update_prediction(
        self, db_session, sample_market_prediction: MarketPrediction
    ):
        """Test updating prediction."""
        repository = PostgresPredictionRepository(db_session)

        # Create
        await repository.create(sample_market_prediction)

        # Update
        updated = await repository.update(
            sample_market_prediction.prediction_id,
            {"confidence_score": 0.95, "fair_odds": 2.00},
        )

        # Validate
        assert updated.prediction_id == sample_market_prediction.prediction_id
        assert updated.confidence_score == 0.95
        assert updated.fair_odds == 2.00

        # Validate database persistence
        db_pred = (
            db_session.query(PredictionORM)
            .filter(PredictionORM.prediction_id == sample_market_prediction.prediction_id)
            .first()
        )
        assert db_pred.confidence_score == 0.95
        assert db_pred.fair_odds == 2.00

    @pytest.mark.anyio
    async def test_update_prediction_not_found(self, db_session):
        """Test updating non-existent prediction raises error."""
        repository = PostgresPredictionRepository(db_session)

        # Should raise ValueError
        with pytest.raises(ValueError, match="not found"):
            await repository.update("non_existent_id", {"confidence_score": 0.95})

    @pytest.mark.anyio
    async def test_delete_prediction(
        self, db_session, sample_market_prediction: MarketPrediction
    ):
        """Test deleting prediction."""
        repository = PostgresPredictionRepository(db_session)

        # Create
        await repository.create(sample_market_prediction)

        # Delete
        deleted = await repository.delete(sample_market_prediction.prediction_id)

        # Should return True
        assert deleted is True

        # Should not exist in database
        db_pred = (
            db_session.query(PredictionORM)
            .filter(PredictionORM.prediction_id == sample_market_prediction.prediction_id)
            .first()
        )
        assert db_pred is None

    @pytest.mark.anyio
    async def test_delete_prediction_not_found(self, db_session):
        """Test deleting non-existent prediction."""
        repository = PostgresPredictionRepository(db_session)

        # Should return False
        deleted = await repository.delete("non_existent_id")
        assert deleted is False


class TestRepositoryORMMapping:
    """Tests for ORM ↔ Domain mapping (critical for data integrity)."""

    @pytest.mark.anyio
    async def test_orm_to_domain_mapping(
        self, db_session, sample_market_prediction: MarketPrediction
    ):
        """Test that ORM → Domain mapping preserves data."""
        repository = PostgresPredictionRepository(db_session)

        # Create (goes through to_orm mapping)
        await repository.create(sample_market_prediction)

        # Get (goes through from_orm mapping)
        retrieved = await repository.get_by_id(sample_market_prediction.prediction_id)

        # Compare critical fields
        assert retrieved.prediction_id == sample_market_prediction.prediction_id
        assert retrieved.match_id == sample_market_prediction.match_id
        assert retrieved.market_id == sample_market_prediction.market_id
        assert retrieved.market_name == sample_market_prediction.market_name
        assert retrieved.market_category == sample_market_prediction.market_category
        assert retrieved.probability == sample_market_prediction.probability
        assert retrieved.fair_odds == sample_market_prediction.fair_odds
        assert retrieved.confidence_score == sample_market_prediction.confidence_score
        assert retrieved.data_quality == sample_market_prediction.data_quality

    @pytest.mark.anyio
    async def test_domain_to_orm_mapping(
        self, db_session, sample_market_prediction: MarketPrediction
    ):
        """Test that Domain → ORM mapping creates correct database record."""
        repository = PostgresPredictionRepository(db_session)

        # Create
        await repository.create(sample_market_prediction)

        # Query ORM directly
        db_pred = (
            db_session.query(PredictionORM)
            .filter(PredictionORM.prediction_id == sample_market_prediction.prediction_id)
            .first()
        )

        # Validate ORM fields
        assert db_pred.prediction_id == sample_market_prediction.prediction_id
        assert db_pred.match_id == sample_market_prediction.match_id
        assert db_pred.market_id == sample_market_prediction.market_id
        assert db_pred.fair_odds == sample_market_prediction.fair_odds
        assert db_pred.confidence_score == sample_market_prediction.confidence_score
        # market_category stored as string in DB
        assert db_pred.market_category in ["main_line", "alternative", "player_prop", "exotic"]

    @pytest.mark.anyio
    async def test_enum_mapping_coherence(
        self, db_session, sample_market_prediction: MarketPrediction
    ):
        """Test that Enum fields are mapped correctly.

        Critical: MarketCategory and DataQuality are enums.
        """
        repository = PostgresPredictionRepository(db_session)

        # Create with specific enum values
        prediction = create_market_prediction(
            market_category=MarketCategory.PLAYER_PROP,
        )
        await repository.create(prediction)

        # Retrieve
        retrieved = await repository.get_by_id(prediction.prediction_id)

        # Validate enum value matches (may be string or enum)
        category_value = (
            retrieved.market_category.value
            if hasattr(retrieved.market_category, "value")
            else retrieved.market_category
        )
        assert category_value == "player_prop"


class TestRepositoryEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.anyio
    async def test_create_duplicate_id_should_fail(self, db_session):
        """Test that creating duplicate prediction_id fails."""
        repository = PostgresPredictionRepository(db_session)

        # Create first
        pred1 = create_market_prediction(prediction_id="duplicate_id")
        await repository.create(pred1)

        # Try to create duplicate (same ID)
        pred2 = create_market_prediction(
            prediction_id="duplicate_id", match_id="different_match"
        )

        # Should raise database integrity error
        with pytest.raises(Exception):  # SQLAlchemy IntegrityError
            await repository.create(pred2)
            db_session.commit()  # Force commit to trigger constraint

    @pytest.mark.anyio
    async def test_list_with_invalid_filter_field(self, db_session):
        """Test that invalid filter fields are ignored."""
        repository = PostgresPredictionRepository(db_session)

        # Create prediction
        pred = create_market_prediction()
        await repository.create(pred)

        # Query with invalid filter field (should be ignored)
        predictions = await repository.list(filters={"non_existent_field": "value"})

        # Should return all (filter ignored)
        assert len(predictions) == 1

    @pytest.mark.anyio
    async def test_empty_database_list(self, db_session):
        """Test listing from empty database."""
        repository = PostgresPredictionRepository(db_session)

        # List from empty db
        predictions = await repository.list()

        # Should be empty list
        assert predictions == []
