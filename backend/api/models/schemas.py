"""
Schémas Pydantic pour validation des données
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime

# ========================================
# BETS
# ========================================

class BetCreate(BaseModel):
    """Création d'un pari"""
    match_id: str
    outcome: str
    bookmaker: str
    odds_value: Decimal
    stake: Decimal = Field(gt=0, description="Mise en euros")
    bet_type: str = Field(default="value", description="Type: value, arbitrage, tabac, ligne, etc")
    notes: Optional[str] = None
    status: Optional[str] = Field(None, description="pending, settled, void")
    result: Optional[str] = Field(None, description="won, lost, void")
    actual_profit: Optional[Decimal] = Field(None, description="Profit réel après règlement")
    clv: Optional[float] = Field(None, description="Closing Line Value")
    odds_close: Optional[float] = Field(None, description="Cote de clôture")
    market_type: Optional[str] = Field(None, description="Type de marché")

class BetUpdate(BaseModel):
    """Mise à jour d'un pari après règlement"""
    result: Optional[str] = None
    actual_odds: Optional[Decimal] = None
    payout: Optional[Decimal] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    actual_profit: Optional[Decimal] = None
    clv: Optional[float] = None
    odds_close: Optional[float] = None

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
    status: Optional[str] = None
    actual_profit: Optional[Decimal] = None
    clv: Optional[float] = None
    odds_close: Optional[float] = None
    market_type: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ========================================
# ODDS
# ========================================

class OddResponse(BaseModel):
    """Réponse pour une cote"""
    id: int
    match_id: str
    bookmaker: str
    market_type: str
    outcome: str
    odds_value: Decimal
    timestamp: datetime

    class Config:
        from_attributes = True

class MatchSummary(BaseModel):
    """Résumé d'un match avec meilleures cotes"""
    match_id: str
    sport: str
    league: str
    home_team: str
    away_team: str
    commence_time: datetime
    best_home_odds: Optional[Decimal] = None
    best_away_odds: Optional[Decimal] = None
    best_draw_odds: Optional[Decimal] = None
    bookmaker_count: int

class MatchDetail(BaseModel):
    """Détails complets d'un match"""
    match_id: str
    sport: str
    league: str
    home_team: str
    away_team: str
    commence_time: datetime
    odds: List[OddResponse]

# ========================================
# OPPORTUNITIES
# ========================================

class OpportunityResponse(BaseModel):
    """Opportunité de pari détectée"""
    id: int
    match_id: str
    opportunity_type: str
    value: Decimal
    details: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True

class Opportunity(OpportunityResponse):
    """Alias pour OpportunityResponse"""
    pass

# ========================================
# STATS
# ========================================

class BankrollSummary(BaseModel):
    """Résumé du bankroll"""
    current_bankroll: Decimal
    total_bets: int
    won_bets: int
    lost_bets: int
    pending_bets: int
    total_staked: Decimal
    total_profit: Decimal
    roi: float
    win_rate: float

class Stats(BaseModel):
    """Statistiques complètes"""
    bankroll: BankrollSummary
    by_bookmaker: Dict[str, Any]
    by_bet_type: Dict[str, Any]
    by_market: Dict[str, Any]
    recent_bets: List[BetInDB]

# ========================================
# BANKROLL
# ========================================

class BankrollUpdate(BaseModel):
    """Mise à jour du bankroll"""
    amount: Decimal = Field(description="Montant à ajouter/retirer")
    reason: str = Field(description="Raison: deposit, withdrawal, adjustment")
    notes: Optional[str] = None
