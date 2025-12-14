"""Predictions API Routes.

Endpoints:
- POST /match - Générer prédiction
- GET /{prediction_id} - Récupérer prédiction
- GET / - Lister prédictions (filtres)
- PUT /{prediction_id} - Override prédiction
- GET /brain/health - Health check UnifiedBrain
"""

from fastapi import APIRouter, Depends, Query, status
from datetime import datetime
from typing import Optional, List

from quantum_core.api.predictions.schemas import (
    PredictionMatchRequest,
    PredictionUpdateRequest,
    EnsemblePredictionResponse,
    PredictionResponse,
    BrainHealthResponse,
)
from quantum_core.api.predictions.service import PredictionService
from quantum_core.models.predictions import MarketPrediction

# ─────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────

router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────
# DEPENDENCY INJECTION
# ─────────────────────────────────────────────────────────────────────────


def get_prediction_service() -> PredictionService:
    """Dependency: Get PredictionService instance."""
    return PredictionService()


# ─────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────


@router.post(
    "/match",
    response_model=EnsemblePredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Générer prédiction pour un match",
    description="""
    Génère une prédiction pour un match via UnifiedBrain V2.8.
    
    Process:
    1. Valide date du match
    2. Fetch features équipes (ADN)
    3. Run 4 agents ML en parallèle
    4. Orchestrator combine prédictions
    5. Valide consensus > 70%
    6. Audit trail
    
    Returns: EnsemblePrediction avec consensus 4 agents
    
    Raises:
    - 400: Date invalide (passé ou trop loin)
    - 404: Match non trouvé
    - 422: Consensus < 70%
    - 500: Erreur UnifiedBrain
    """,
)
async def generate_match_prediction(
    request: PredictionMatchRequest,
    service: PredictionService = Depends(get_prediction_service),
):
    """Générer prédiction pour un match."""
    ensemble = await service.generate_match_prediction(
        match_id=request.match_id,
        competition=request.competition,
        match_date=request.match_date,
        home_team_id=request.home_team_id,
        away_team_id=request.away_team_id,
    )

    return EnsemblePredictionResponse(
        ensemble=ensemble,
        agent_details=ensemble.individual_predictions,
        generated_at=datetime.utcnow(),
        match_id=request.match_id,
        consensus_reached=ensemble.model_agreement_score >= 0.70,
        status="success",
    )


@router.get(
    "/{prediction_id}",
    response_model=PredictionResponse,
    summary="Récupérer une prédiction par ID",
)
async def get_prediction(
    prediction_id: str,
    service: PredictionService = Depends(get_prediction_service),
):
    """Récupérer une prédiction par son ID."""
    prediction = await service.get_prediction_by_id(prediction_id)

    if not prediction:
        from quantum_core.api.common.exceptions import MatchNotFoundError

        raise MatchNotFoundError(prediction_id)

    return PredictionResponse(
        prediction=prediction,
        generated_at=datetime.utcnow(),
        match_id=prediction.market_id,
        status="success",
    )


@router.get(
    "/",
    response_model=List[PredictionResponse],
    summary="Lister prédictions avec filtres",
)
async def list_predictions(
    match_id: Optional[str] = Query(None, description="Filter by match ID"),
    competition: Optional[str] = Query(None, description="Filter by competition"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    service: PredictionService = Depends(get_prediction_service),
):
    """Lister prédictions avec filtres optionnels."""
    predictions = await service.list_predictions(
        match_id=match_id,
        competition=competition,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )

    return [
        PredictionResponse(
            prediction=pred,
            generated_at=datetime.utcnow(),
            match_id=pred.market_id,
            status="success",
        )
        for pred in predictions
    ]


@router.put(
    "/{prediction_id}",
    response_model=PredictionResponse,
    summary="Override manuel d'une prédiction",
)
async def update_prediction(
    prediction_id: str,
    request: PredictionUpdateRequest,
    service: PredictionService = Depends(get_prediction_service),
):
    """Override manuel d'une prédiction (expert override)."""
    prediction = await service.update_prediction(
        prediction_id=prediction_id,
        fair_odds=request.fair_odds,
        confidence_score=request.confidence_score,
        confidence_level=request.confidence_level,
    )

    return PredictionResponse(
        prediction=prediction,
        generated_at=datetime.utcnow(),
        match_id=prediction.market_id,
        status="success",
    )


@router.get(
    "/brain/health",
    response_model=BrainHealthResponse,
    summary="Health check UnifiedBrain",
)
async def brain_health(
    service: PredictionService = Depends(get_prediction_service),
):
    """Health check UnifiedBrain (4 agents + orchestrator)."""
    health = await service.get_brain_health()

    return BrainHealthResponse(**health)
