"""
Schémas Pydantic pour l'API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# ========================================
# ODDS (Cotes)
# ========================================

class OddBase(BaseModel):
    """Schéma de base pour une cote"""
    sport: str
    league: Optional[str] = None
    match_id: str
    home_team: str
    away_team: str
    commence_time: datetime
    bookmaker: str
    market_type: str
    outcome_name: str
    odds_value: Decimal
    point: Optional[Decimal] = None

class OddInDB(OddBase):
    """Cote telle qu'en base de données"""
    id: int
    last_update: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

class OddResponse(OddBase):
    """Réponse API pour une cote"""
    id: int
    last_update: datetime
    
    class Config:
        from_attributes = True

# ========================================
# MATCHES
# ========================================

class MatchSummary(BaseModel):
    """Résumé d'un match"""
    match_id: str
    home_team: str
    away_team: str
    sport: str
    league: Optional[str] = None
    commence_time: datetime
    nb_bookmakers: int
    best_home_odd: Optional[Decimal] = None
    best_away_odd: Optional[Decimal] = None
    best_draw_odd: Optional[Decimal] = None

class MatchDetail(MatchSummary):
    """Détails complets d'un match avec toutes les cotes"""
    odds: List[OddResponse]

# ========================================
# OPPORTUNITIES (Opportunités)
# ========================================

class Opportunity(BaseModel):
    """Opportunité détectée (arbitrage ou value bet)"""
    match_id: str
    home_team: str
    away_team: str
    sport: str
    commence_time: datetime
    opportunity_type: str  # "arbitrage" ou "value"
    outcome: str
    best_odd: Decimal
    worst_odd: Decimal
    spread_pct: float
    bookmaker_best: str
    bookmaker_worst: str
    nb_bookmakers: int
    estimated_value: Optional[float] = None

# ========================================
# BETS (Paris)
# ========================================

class BetCreate(BaseModel):
    """Création d'un pari"""
    match_id: str
    outcome: str
    bookmaker: str
    odds_value: Decimal
    stake: Decimal = Field(gt=0, description="Mise en euros")
    bet_type: str = Field(default="value", description="Type: value, arbitrage, etc")
    notes: Optional[str] = None

class BetUpdate(BaseModel):
    """Mise à jour d'un pari"""
    result: Optional[str] = None  # "won", "lost", "void"
    actual_odds: Optional[Decimal] = None
    payout: Optional[Decimal] = None
    notes: Optional[str] = None

class BetInDB(BaseModel):
    """Pari en base de données"""
    id: int
    match_id: str
    outcome: str
    bookmaker: str
    odds_value: Decimal
    stake: Decimal
    bet_type: str
    result: Optional[str] = None
    actual_odds: Optional[Decimal] = None
    payout: Optional[Decimal] = None
    profit_loss: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# ========================================
# BANKROLL
# ========================================

class BankrollSummary(BaseModel):
    """Résumé du bankroll"""
    current_balance: Decimal
    initial_balance: Decimal
    total_staked: Decimal
    total_returned: Decimal
    total_profit: Decimal
    roi: float
    nb_bets: int
    nb_won: int
    nb_lost: int
    nb_pending: int
    win_rate: float

# ========================================
# STATISTICS
# ========================================

class Stats(BaseModel):
    """Statistiques globales"""
    total_odds: int
    total_matches: int
    total_bookmakers: int
    total_sports: int
    last_update: datetime
    api_requests_remaining: Optional[int] = None
