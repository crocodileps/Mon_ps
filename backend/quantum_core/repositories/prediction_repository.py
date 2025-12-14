"""Prediction Repository - Data access layer.

ADR #008: Repository pattern implementation.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from quantum_core.repositories.base import BaseRepository
from quantum_core.models.predictions import MarketPrediction, EnsemblePrediction
from quantum_core.database.models import PredictionORM, EnsemblePredictionORM
import logging

logger = logging.getLogger(__name__)


class PredictionRepository(BaseRepository[MarketPrediction]):
    """Abstract Prediction Repository."""

    pass


class PostgresPredictionRepository(PredictionRepository):
    """PostgreSQL implementation of PredictionRepository.

    ADR #008: Concrete implementation using SQLAlchemy.
    - Maps Pydantic domain models ↔ SQLAlchemy ORM models
    - CRUD operations on predictions
    """

    def __init__(self, db: Session):
        """Initialize with database session.

        Args:
            db: SQLAlchemy session (request-scoped)
        """
        self.db = db

    async def create(self, entity: MarketPrediction) -> MarketPrediction:
        """Create prediction in database.

        Args:
            entity: MarketPrediction domain model

        Returns:
            Created prediction
        """
        # Map domain model → ORM model
        orm_model = self._to_orm(entity)

        # Insert
        self.db.add(orm_model)
        self.db.flush()  # Get generated ID if any

        logger.info(f"Created prediction: {entity.prediction_id}")

        # Return domain model
        return entity

    async def get_by_id(self, entity_id: str) -> Optional[MarketPrediction]:
        """Get prediction by ID.

        Args:
            entity_id: prediction_id

        Returns:
            MarketPrediction if found, None otherwise
        """
        orm_model = (
            self.db.query(PredictionORM)
            .filter(PredictionORM.prediction_id == entity_id)
            .first()
        )

        if orm_model is None:
            return None

        # Map ORM model → domain model
        return self._from_orm(orm_model)

    async def list(
        self, filters: Optional[Dict[str, Any]] = None, limit: int = 100
    ) -> List[MarketPrediction]:
        """List predictions with filters.

        Args:
            filters: {"match_id": "...", "market_category": "..."}
            limit: Max results

        Returns:
            List of predictions
        """
        query = self.db.query(PredictionORM)

        # Apply filters
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if hasattr(PredictionORM, key):
                    filter_conditions.append(getattr(PredictionORM, key) == value)

            if filter_conditions:
                query = query.filter(and_(*filter_conditions))

        # Limit
        query = query.limit(limit)

        # Execute
        orm_models = query.all()

        # Map to domain models
        return [self._from_orm(orm) for orm in orm_models]

    async def update(self, entity_id: str, data: Dict[str, Any]) -> MarketPrediction:
        """Update prediction.

        Args:
            entity_id: prediction_id
            data: Fields to update

        Returns:
            Updated prediction
        """
        orm_model = (
            self.db.query(PredictionORM)
            .filter(PredictionORM.prediction_id == entity_id)
            .first()
        )

        if orm_model is None:
            raise ValueError(f"Prediction {entity_id} not found")

        # Update fields
        for key, value in data.items():
            if hasattr(orm_model, key):
                setattr(orm_model, key, value)

        self.db.flush()

        logger.info(f"Updated prediction: {entity_id}")

        return self._from_orm(orm_model)

    async def delete(self, entity_id: str) -> bool:
        """Delete prediction.

        Args:
            entity_id: prediction_id

        Returns:
            True if deleted, False if not found
        """
        orm_model = (
            self.db.query(PredictionORM)
            .filter(PredictionORM.prediction_id == entity_id)
            .first()
        )

        if orm_model is None:
            return False

        self.db.delete(orm_model)
        self.db.flush()

        logger.info(f"Deleted prediction: {entity_id}")

        return True

    # ─────────────────────────────────────────────────────────────────────
    # MAPPING (ORM ↔ Domain)
    # ─────────────────────────────────────────────────────────────────────

    def _to_orm(self, domain: MarketPrediction) -> PredictionORM:
        """Map domain model → ORM model.

        Args:
            domain: MarketPrediction (Pydantic)

        Returns:
            PredictionORM (SQLAlchemy)
        """
        # Handle enum fields (may be enum or already string from Pydantic)
        market_category_value = (
            domain.market_category.value
            if hasattr(domain.market_category, "value")
            else domain.market_category
        )
        data_quality_value = (
            domain.data_quality.value
            if hasattr(domain.data_quality, "value")
            else domain.data_quality
        )

        return PredictionORM(
            prediction_id=domain.prediction_id,
            match_id=domain.match_id,
            market_id=domain.market_id,
            market_name=domain.market_name,
            market_category=market_category_value,
            probability=domain.probability,
            fair_odds=domain.fair_odds,
            confidence_score=domain.confidence_score,
            data_quality=data_quality_value,
            computed_at=domain.computed_at or datetime.utcnow(),
            extra_data={},  # Optional fields as JSON
        )

    def _from_orm(self, orm: PredictionORM) -> MarketPrediction:  # type: ignore[misc]
        """Map ORM model → domain model.

        Args:
            orm: PredictionORM (SQLAlchemy)

        Returns:
            MarketPrediction (Pydantic)
        """
        return MarketPrediction(
            prediction_id=orm.prediction_id,  # type: ignore[arg-type]
            match_id=orm.match_id,  # type: ignore[arg-type]
            market_id=orm.market_id,  # type: ignore[arg-type]
            market_name=orm.market_name,  # type: ignore[arg-type]
            market_category=orm.market_category,  # type: ignore[arg-type]
            probability=orm.probability,  # type: ignore[arg-type]
            fair_odds=orm.fair_odds,  # type: ignore[arg-type]
            confidence_score=orm.confidence_score,  # type: ignore[arg-type]
            data_quality=orm.data_quality,  # type: ignore[arg-type]
            computed_at=orm.computed_at,  # type: ignore[arg-type]
            # Optional fields (not stored in DB for now)
            edge_vs_market=None,
            clv_expected=None,
            kelly_fraction=None,
            expected_value=None,
            model_agreement=None,
            computation_time_ms=None,
            expires_at=None,
            feature_versions=None,
            missing_features=None,
        )
