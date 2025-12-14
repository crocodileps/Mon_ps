"""
Brain API Pydantic Schemas

Request/Response models pour tous les endpoints Brain
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from enum import Enum


class MarketCategory(str, Enum):
    """Catégories de marchés"""
    RESULT = "result"
    GOALS = "goals"
    GOALSCORERS = "goalscorers"
    CORNERS = "corners"
    CARDS = "cards"
    ASIAN_HANDICAP = "asian_handicap"


class DNAContext(BaseModel):
    """Contexte ADN optionnel"""
    home_profile: Optional[str] = Field(None, example="PRESSING_MACHINE")
    away_profile: Optional[str] = Field(None, example="BALANCED_PRAGMATIC")


class BrainCalculateRequest(BaseModel):
    """Request POST /api/v1/brain/calculate"""
    home_team: str = Field(..., min_length=2, max_length=100, example="Liverpool")
    away_team: str = Field(..., min_length=2, max_length=100, example="Chelsea")
    match_date: date = Field(..., example="2025-12-20")
    dna_context: Optional[DNAContext] = None
    force_refresh: bool = Field(False, description="Bypass cache")

    @validator('match_date')
    def validate_future_date(cls, v):
        if v < date.today():
            raise ValueError('match_date must be in the future')
        return v

    @validator('away_team')
    def validate_different_teams(cls, v, values):
        if 'home_team' in values and v == values['home_team']:
            raise ValueError('Teams must be different')
        return v


class GoalscorerRequest(BaseModel):
    """Request POST /api/v1/brain/goalscorer"""
    home_team: str = Field(..., example="Liverpool")
    away_team: str = Field(..., example="Chelsea")
    match_date: date = Field(..., example="2025-12-20")


class MarketPrediction(BaseModel):
    """Prédiction pour un outcome"""
    probability: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    edge: Optional[float] = None


class BrainCalculateResponse(BaseModel):
    """Response POST /api/v1/brain/calculate"""
    prediction_id: str
    home_team: str
    away_team: str
    match_date: date
    markets: Dict[str, Dict[str, MarketPrediction]]
    calculation_time: float
    brain_version: str = "2.8.0"
    created_at: datetime
    is_stale: bool = False
    cached_age_seconds: Optional[int] = None


class GoalscorerPrediction(BaseModel):
    """Prédiction buteur"""
    player: str
    anytime_prob: float = Field(..., ge=0.0, le=1.0)
    first_prob: float = Field(..., ge=0.0, le=1.0)
    last_prob: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)


class GoalscorerResponse(BaseModel):
    """Response POST /api/v1/brain/goalscorer"""
    home_goalscorers: List[GoalscorerPrediction]
    away_goalscorers: List[GoalscorerPrediction]
    first_goalscorer_team_prob: Dict[str, float]


class BrainHealthResponse(BaseModel):
    """Response GET /api/v1/brain/health"""
    status: str
    version: str = "2.8.0"
    markets_count: int = 99
    goalscorer_profiles: int = 876
    last_calculation: Optional[datetime] = None
    uptime_percent: float = 99.9


class MarketInfo(BaseModel):
    """Info marché"""
    id: str
    name: str
    category: MarketCategory
    description: str


class MarketsListResponse(BaseModel):
    """Response GET /api/v1/brain/markets"""
    markets: List[MarketInfo]
    total: int
    categories: Dict[str, int]


class ErrorDetail(BaseModel):
    """Détail erreur"""
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """Response erreur"""
    error: ErrorDetail
    request_id: str
    timestamp: datetime
