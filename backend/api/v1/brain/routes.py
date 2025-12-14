"""
Brain API Routes - 4 endpoints FastAPI
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import logging

from .schemas import (
    BrainCalculateRequest,
    BrainCalculateResponse,
    GoalscorerRequest,
    GoalscorerResponse,
    BrainHealthResponse,
    MarketsListResponse,
    ErrorResponse
)
from .service import BrainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/brain", tags=["Brain"])

# Service instance
brain_service = BrainService()


@router.post(
    "/calculate",
    response_model=BrainCalculateResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate 99 markets predictions",
    description="Calculate predictions for all 99 markets using UnifiedBrain V2.8.0"
)
async def calculate_predictions(request: BrainCalculateRequest) -> BrainCalculateResponse:
    """
    Calculate predictions for 99 markets

    - **home_team**: Home team name
    - **away_team**: Away team name
    - **match_date**: Match date (YYYY-MM-DD, must be future)
    - **dna_context**: Optional DNA tactical context
    - **force_refresh**: Bypass cache (default: false)
    """
    try:
        return brain_service.calculate_predictions(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/goalscorer",
    response_model=GoalscorerResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate goalscorer predictions",
    description="Calculate top 5 goalscorers for each team"
)
async def calculate_goalscorers(request: GoalscorerRequest) -> GoalscorerResponse:
    """
    Calculate top 5 goalscorers predictions

    Returns anytime, first, last goalscorer probabilities
    """
    try:
        return brain_service.calculate_goalscorers(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/health",
    response_model=BrainHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Brain health check",
    description="Get UnifiedBrain health status and metrics"
)
async def get_health() -> BrainHealthResponse:
    """
    Brain health check

    Returns operational status, version, and metrics
    """
    try:
        return brain_service.get_health()
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get(
    "/markets",
    response_model=MarketsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List supported markets",
    description="Get list of all 99 supported markets"
)
async def get_markets() -> MarketsListResponse:
    """
    List all 99 supported markets

    Returns market ID, name, category, description
    """
    try:
        return brain_service.get_markets_list()
    except Exception as e:
        logger.error(f"Markets list error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve markets")
