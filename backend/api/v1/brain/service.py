"""
Brain Service Layer - Business Logic
"""

import uuid
from datetime import datetime
from typing import Dict, Any
import logging

from .repository import BrainRepository
from .schemas import (
    BrainCalculateRequest,
    BrainCalculateResponse,
    GoalscorerRequest,
    GoalscorerResponse,
    BrainHealthResponse,
    MarketsListResponse
)

logger = logging.getLogger(__name__)


class BrainService:
    """Service layer pour Brain API

    Supports dependency injection for testing.
    """

    def __init__(self, repository=None):
        """
        Initialize service

        Args:
            repository: Optional BrainRepository (for dependency injection in tests)
        """
        self.repository = repository or BrainRepository()

    def calculate_predictions(self, request: BrainCalculateRequest) -> BrainCalculateResponse:
        """Calculate 99 markets predictions"""
        try:
            # Call repository
            result = self.repository.calculate_predictions(
                home_team=request.home_team,
                away_team=request.away_team,
                match_date=datetime.combine(request.match_date, datetime.min.time()),
                dna_context=request.dna_context.dict() if request.dna_context else None
            )

            # Build response
            return BrainCalculateResponse(
                prediction_id=str(uuid.uuid4()),
                home_team=request.home_team,
                away_team=request.away_team,
                match_date=request.match_date,
                markets=result["markets"],
                calculation_time=result["calculation_time"],
                brain_version=result["brain_version"],
                created_at=result["created_at"]
            )

        except Exception as e:
            logger.error(f"Service calculate failed: {e}")
            raise

    def calculate_goalscorers(self, request: GoalscorerRequest) -> GoalscorerResponse:
        """Calculate top 5 goalscorers"""
        try:
            result = self.repository.calculate_goalscorers(
                home_team=request.home_team,
                away_team=request.away_team,
                match_date=datetime.combine(request.match_date, datetime.min.time())
            )

            return GoalscorerResponse(**result)

        except Exception as e:
            logger.error(f"Service goalscorer failed: {e}")
            raise

    def get_health(self) -> BrainHealthResponse:
        """Get Brain health status"""
        try:
            status = self.repository.get_health_status()
            return BrainHealthResponse(**status)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise

    def get_markets_list(self) -> MarketsListResponse:
        """Get list of 99 supported markets"""
        try:
            markets = self.repository.get_supported_markets()

            # Count by category
            categories = {}
            for market in markets:
                cat = market["category"]
                categories[cat] = categories.get(cat, 0) + 1

            return MarketsListResponse(
                markets=markets,
                total=len(markets),
                categories=categories
            )
        except Exception as e:
            logger.error(f"Markets list failed: {e}")
            raise
