"""SQLAlchemy ORM Models.

ADR #008: Domain models (Pydantic) ≠ ORM models (SQLAlchemy).
- ORM models: Database schema only
- Domain models: Business logic + validation
"""

from sqlalchemy import Column, String, Float, DateTime, Integer, JSON, Boolean
from sqlalchemy.sql import func
from datetime import datetime

from quantum_core.database.base import Base


class PredictionORM(Base):
    """Prediction table - SQLAlchemy ORM model.

    Maps to market_predictions table.
    Separate from Pydantic MarketPrediction (domain model).
    """

    __tablename__ = "market_predictions"

    # Primary key
    prediction_id = Column(String, primary_key=True, index=True)

    # Match info
    match_id = Column(String, index=True, nullable=False)
    market_id = Column(String, index=True, nullable=False)
    market_name = Column(String, nullable=False)
    market_category = Column(String, nullable=False)

    # Prediction
    probability = Column(Float, nullable=False)
    fair_odds = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)

    # Optional fields (stored as JSON for flexibility)
    # Note: renamed from 'metadata' to 'extra_data' (metadata is reserved by SQLAlchemy)
    extra_data = Column(JSON, nullable=True)

    # Data quality
    data_quality = Column(String, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Computed at (when prediction was calculated)
    computed_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self):
        return f"<Prediction {self.prediction_id} - {self.match_id}>"


class EnsemblePredictionORM(Base):
    """Ensemble prediction table.

    Stores consensus predictions from multiple agents.
    """

    __tablename__ = "ensemble_predictions"

    # Primary key
    prediction_id = Column(String, primary_key=True, index=True)

    # Match info
    match_id = Column(String, index=True, nullable=False)
    market_name = Column(String, nullable=False)

    # Ensemble method
    ensemble_method = Column(String, nullable=False)

    # Metrics
    prediction_variance = Column(Float, nullable=False)
    model_agreement_score = Column(Float, nullable=False)
    epistemic_uncertainty = Column(Float, nullable=False)
    aleatoric_uncertainty = Column(Float, nullable=False)

    # Individual predictions (stored as JSON array of prediction IDs)
    individual_prediction_ids = Column(JSON, nullable=False)

    # Final prediction (reference to best prediction)
    final_prediction_id = Column(String, nullable=False)

    # Model weights (JSON)
    model_weights = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    computed_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self):
        return f"<Ensemble {self.prediction_id} - {self.match_id}>"
