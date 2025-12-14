"""Request/Response schemas for Predictions API.

Séparation API models vs Domain models:
- API schemas: Validation input/output HTTP
- Domain models: Business logic (predictions.py)
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

from quantum_core.models.predictions import (
    MarketPrediction,
    EnsemblePrediction,
    ConfidenceLevel,
)


# ─────────────────────────────────────────────────────────────────────────
# REQUEST SCHEMAS
# ─────────────────────────────────────────────────────────────────────────


class PredictionMatchRequest(BaseModel):
    """Request pour générer prédiction d'un match."""

    match_id: str = Field(..., min_length=1, description="ID unique du match")
    competition: str = Field(..., min_length=1, description="Compétition (ex: Ligue 1)")
    match_date: datetime = Field(..., description="Date du match (ISO 8601)")
    home_team_id: Optional[str] = Field(None, description="ID équipe domicile")
    away_team_id: Optional[str] = Field(None, description="ID équipe extérieure")


class PredictionUpdateRequest(BaseModel):
    """Request pour override manuel d'une prédiction."""

    fair_odds: Optional[float] = Field(None, gt=1.0, description="Override fair odds")
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Override confidence"
    )
    confidence_level: Optional[ConfidenceLevel] = Field(
        None, description="Override confidence level"
    )


# ─────────────────────────────────────────────────────────────────────────
# RESPONSE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────


class PredictionResponse(BaseModel):
    """Response standard pour une prédiction."""

    prediction: MarketPrediction
    generated_at: datetime
    match_id: str
    status: str = "success"


class EnsemblePredictionResponse(BaseModel):
    """Response pour ensemble prediction (4 agents)."""

    ensemble: EnsemblePrediction
    agent_details: List[MarketPrediction]
    generated_at: datetime
    match_id: str
    consensus_reached: bool
    status: str = "success"


class BrainHealthResponse(BaseModel):
    """Response health check UnifiedBrain."""

    status: str
    agents_available: List[str]
    orchestrator_status: str
    last_prediction: Optional[datetime] = None
