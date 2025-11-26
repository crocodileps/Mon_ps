"""
TRACKING CLV 2.0 - Modèles Pydantic
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from enum import Enum


class MarketType(str, Enum):
    OVER_15 = "over_15"
    UNDER_15 = "under_15"
    OVER_25 = "over_25"
    UNDER_25 = "under_25"
    OVER_35 = "over_35"
    UNDER_35 = "under_35"
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"
    DC_1X = "dc_1x"
    DC_X2 = "dc_x2"
    DC_12 = "dc_12"
    DNB_HOME = "dnb_home"
    DNB_AWAY = "dnb_away"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Recommendation(str, Enum):
    DIAMOND_PICK = "DIAMOND PICK"
    STRONG_BET = "STRONG BET"
    LEAN = "LEAN"
    SKIP = "SKIP"
    AVOID = "AVOID"


class ValueRating(str, Enum):
    DIAMOND = "�� DIAMOND VALUE"
    STRONG = "🔥 STRONG VALUE"
    FAIR = "⚖️ FAIR"
    AVOID = "❌ AVOID"


class Outcome(str, Enum):
    WIN = "win"
    LOSS = "loss"
    PUSH = "push"
    VOID = "void"
    PENDING = "pending"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ============================================================
# Modèles pour sauvegarde
# ============================================================

class MarketPredictionCreate(BaseModel):
    """Prédiction pour un marché"""
    market_type: MarketType
    market_label: str
    selection: str
    
    score: float = Field(ge=0, le=100)
    probability: float = Field(ge=0, le=100)
    confidence: Confidence
    recommendation: Recommendation
    
    value_rating: Optional[ValueRating] = None
    kelly_pct: Optional[float] = None
    edge_pct: Optional[float] = None
    
    odds_at_analysis: Optional[float] = None
    bookmaker_analysis: Optional[str] = None
    implied_prob_market: Optional[float] = None
    
    poisson_prob: Optional[float] = None
    market_prob: Optional[float] = None
    edge_vs_market: Optional[float] = None
    ev_expected: Optional[float] = None
    
    factors: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None


class AnalysisCreate(BaseModel):
    """Création d'une analyse complète"""
    match_id: str
    home_team: str
    away_team: str
    league: str
    commence_time: datetime
    
    xg_home: Optional[float] = None
    xg_away: Optional[float] = None
    xg_total: Optional[float] = None
    
    home_form: Optional[str] = None
    away_form: Optional[str] = None
    h2h_data: Optional[Dict[str, Any]] = None
    
    llm_narrative: Optional[str] = None
    llm_verdict: Optional[str] = None
    llm_confidence: Optional[str] = None
    
    season: Optional[str] = None
    matchday: Optional[int] = None
    is_derby: bool = False
    importance: str = "normal"
    
    predictions: List[MarketPredictionCreate]


class AnalysisResponse(BaseModel):
    """Réponse après sauvegarde"""
    analysis_id: UUID
    match_id: str
    home_team: str
    away_team: str
    predictions_count: int
    top_pick_market: Optional[str] = None
    top_pick_score: Optional[float] = None
    created_at: datetime


# ============================================================
# Modèles pour résolution
# ============================================================

class MatchResult(BaseModel):
    """Résultat d'un match"""
    match_id: str
    home_score: int
    away_score: int
    ht_home_score: Optional[int] = None
    ht_away_score: Optional[int] = None


class PickOutcome(BaseModel):
    """Résultat d'un pick"""
    prediction_id: int
    market_type: MarketType
    outcome: Outcome
    odds_at_prediction: Optional[float] = None
    odds_closing: Optional[float] = None
    clv_pct: Optional[float] = None
    profit_loss: Optional[float] = None


# ============================================================
# Modèles pour statistiques
# ============================================================

class MarketStats(BaseModel):
    """Stats d'un marché"""
    market_type: str
    market_label: str
    total_predictions: int
    total_resolved: int
    wins: int
    losses: int
    win_rate: Optional[float] = None
    roi_pct: Optional[float] = None
    avg_clv: Optional[float] = None
    avg_kelly: Optional[float] = None
    current_streak: int = 0


class GlobalPerformance(BaseModel):
    """Performance globale"""
    total_matches: int
    total_predictions: int
    resolved_predictions: int
    wins: int
    losses: int
    win_rate: Optional[float] = None
    roi_pct: Optional[float] = None
    total_profit: Optional[float] = None
    avg_clv: Optional[float] = None
    clv_positive_rate: Optional[float] = None


class CorrelationPair(BaseModel):
    """Paire de corrélation"""
    market_a: str
    market_b: str
    correlation: float
    sample_size: int
    recommendation: str


class DailyPerformance(BaseModel):
    """Performance journalière"""
    date: str
    total_analyses: int
    wins: int
    losses: int
    win_rate: Optional[float] = None
    daily_profit: Optional[float] = None
    cumulative_profit: Optional[float] = None
    avg_clv: Optional[float] = None


class Alert(BaseModel):
    """Alerte système"""
    alert_type: str
    subject: str
    message: str
    severity: str
    detected_at: datetime


# ============================================================
# Modèles pour dashboard
# ============================================================

class DashboardSynthesis(BaseModel):
    """Synthèse dashboard"""
    total_matches_analyzed: int
    total_predictions: int
    resolved_predictions: int
    global_win_rate: Optional[float] = None
    global_roi: Optional[float] = None
    global_avg_clv: Optional[float] = None
    best_market: Optional[str] = None
    best_market_roi: Optional[float] = None
    worst_market: Optional[str] = None
    worst_market_roi: Optional[float] = None
    today_analyses: int
    today_wins: int
    today_losses: int


class ScoreCalibration(BaseModel):
    """Calibration des scores"""
    score_range: str
    total: int
    wins: int
    actual_win_rate: Optional[float] = None
    expected_win_rate: Optional[float] = None
    roi_pct: Optional[float] = None
    avg_clv: Optional[float] = None


class ValueRatingPerformance(BaseModel):
    """Performance par value rating"""
    value_rating: str
    total_predictions: int
    resolved: int
    wins: int
    win_rate: Optional[float] = None
    total_profit: Optional[float] = None
    avg_clv: Optional[float] = None


class RecentTrend(BaseModel):
    """Tendance récente"""
    market_type: str
    predictions_7d: int
    wins_7d: int
    win_rate_7d: Optional[float] = None
    profit_7d: Optional[float] = None
    avg_clv_7d: Optional[float] = None
    historical_win_rate: Optional[float] = None
    trend: str


class BestCombo(BaseModel):
    """Meilleur combo"""
    market_a: str
    market_b: str
    sample_size: int
    win_rate_a: float
    win_rate_b: float
    both_win_rate: float
    correlation: float
    lift: Optional[float] = None
    recommendation: str
