"""
Schémas Pydantic pour validation des données
"""
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime

# ========================================
# BETS
# ========================================

class BetCreate(BaseModel):
    """Création d'un pari - TOUS LES CHAMPS OPTIONNELS POUR IMPORT"""
    match_id: str
    outcome: str
    bookmaker: str
    odds_value: Decimal
    stake: Decimal = Field(gt=0, description="Mise en euros")
    bet_type: str = Field(default="value", description="Type: value, arbitrage, tabac, ligne, etc")
    notes: Optional[str] = None
    
    # Champs optionnels pour import de paris passés
    status: Optional[str] = Field(None, description="pending, settled, void")
    result: Optional[str] = Field(None, description="won, lost, void")
    actual_profit: Optional[Decimal] = Field(None, description="Profit réel après règlement")
    clv: Optional[float] = Field(None, description="Closing Line Value")
    odds_close: Optional[float] = Field(None, description="Cote de clôture")
    market_type: Optional[str] = Field(None, description="Type de marché")

class BetUpdate(BaseModel):
    """Mise à jour d'un pari après règlement"""
    result: Optional[str] = None  # "won", "lost", "void"
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
    clv: Optional[float] = Field(None, description="Closing Line Value")
    odds_close: Optional[float] = Field(None, description="Cote de clôture")
    market_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Type de marché: h2h, totals, btts, etc.",
    )
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ========================================
# BANKROLL
# ========================================

class BankrollUpdate(BaseModel):
    """Mise à jour du bankroll"""
    amount: Decimal = Field(description="Montant à ajouter/retirer")
    reason: str = Field(description="Raison: deposit, withdrawal, adjustment")
    notes: Optional[str] = None
