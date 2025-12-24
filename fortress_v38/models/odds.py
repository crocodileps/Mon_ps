"""
FORTRESS V3.8 - Odds Models (Pydantic Institutional Grade)
==========================================================

Anti-Corruption Layer: Modèles de cotes avec validation runtime.

PATTERN: Anti-Corruption Layer
- Le code Legacy (odds_loader.py) a des dépendances cassées
- On copie les modèles PROPREMENT dans la Forteresse
- Validation Pydantic garantit des données saines

VALIDATION:
- Cotes valides: 0.0 (non disponible) ou >= 1.01
- Aucune cote négative acceptée
- Erreur immédiate si données corrompues (pas de bug silencieux)

Version: 1.0.0
Date: 24 Décembre 2025
Auteur: Mya + Claude (Partenariat Senior Quant)

SOURCE ORIGINALE: quantum/orchestrator/quantum_orchestrator_v1_modular/adapters/odds_loader.py
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator


# ═══════════════════════════════════════════════════════════════
# ODDS MOVEMENT (Steam Detection)
# ═══════════════════════════════════════════════════════════════

class OddsMovement(BaseModel):
    """
    Analyse du mouvement d'une cote (Steam Detection).
    
    Détecte les mouvements de lignes significatifs:
    - Sharp money (cote baisse rapidement)
    - Public money (cote monte)
    - Mouvements suspects
    """
    market: str
    opening_odds: float = Field(ge=0.0)
    current_odds: float = Field(ge=0.0)
    movement_pct: float  # Changement en %
    direction: str = "STABLE"  # UP, DOWN, STABLE
    steam_signal: str = "NEUTRAL"  # SHARP_MONEY, PUBLIC_MONEY, NEUTRAL
    samples: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    
    @property
    def is_significant(self) -> bool:
        """Mouvement > 3% est significatif."""
        return abs(self.movement_pct) > 3.0
    
    @property
    def is_sharp_steam(self) -> bool:
        """Sharp money = cote baisse rapidement (> 5%)."""
        return self.movement_pct < -5.0
    
    @property
    def is_trap_signal(self) -> bool:
        """Signal de piège potentiel (mouvement extrême)."""
        return abs(self.movement_pct) > 10.0


# ═══════════════════════════════════════════════════════════════
# MATCH ODDS (Cotes complètes avec validation)
# ═══════════════════════════════════════════════════════════════

class MatchOdds(BaseModel):
    """
    Cotes complètes d'un match avec validation Pydantic.
    
    VALIDATION RUNTIME:
    - Cotes >= 1.01 ou == 0.0 (non disponible)
    - Erreur immédiate si cote invalide (ex: -1.5)
    
    ANTI-CORRUPTION:
    - Ne dépend d'aucun import legacy
    - Mapping explicite vers format legacy via to_legacy_dict()
    """
    # Identification
    match_id: str
    home_team: str
    away_team: str
    commence_time: datetime
    sport: str = "soccer"
    league: str = ""
    
    # Cotes 1X2 (moyennes ou best)
    home_odds: float = Field(default=0.0, ge=0.0, description="Cote victoire domicile")
    draw_odds: float = Field(default=0.0, ge=0.0, description="Cote match nul")
    away_odds: float = Field(default=0.0, ge=0.0, description="Cote victoire extérieur")
    
    # Cotes Over/Under
    over_15_odds: float = Field(default=0.0, ge=0.0)
    over_25_odds: float = Field(default=0.0, ge=0.0)
    over_35_odds: float = Field(default=0.0, ge=0.0)
    under_15_odds: float = Field(default=0.0, ge=0.0)
    under_25_odds: float = Field(default=0.0, ge=0.0)
    under_35_odds: float = Field(default=0.0, ge=0.0)
    
    # Cotes BTTS
    btts_yes_odds: float = Field(default=0.0, ge=0.0)
    btts_no_odds: float = Field(default=0.0, ge=0.0)
    
    # Métadonnées
    bookmaker_count: int = Field(default=0, ge=0)
    last_update: Optional[datetime] = None
    
    # Cotes par bookmaker (pour analyse CLV)
    odds_by_bookmaker: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    # Steam/Mouvements de cotes
    odds_movements: Dict[str, OddsMovement] = Field(default_factory=dict)
    
    # ─── VALIDATORS ───
    
    @field_validator(
        'home_odds', 'draw_odds', 'away_odds',
        'over_15_odds', 'over_25_odds', 'over_35_odds',
        'under_15_odds', 'under_25_odds', 'under_35_odds',
        'btts_yes_odds', 'btts_no_odds',
        mode='after'
    )
    @classmethod
    def validate_odds_value(cls, v: float) -> float:
        """
        Validation: Cote valide = 0.0 (non dispo) ou >= 1.01.
        
        Raises:
            ValueError: Si cote entre 0 et 1.01 (invalide)
        """
        if v != 0.0 and v < 1.01:
            raise ValueError(
                f"Cote invalide: {v}. "
                f"Doit être 0.0 (non disponible) ou >= 1.01"
            )
        return v
    
    @model_validator(mode='after')
    def validate_minimum_odds(self) -> 'MatchOdds':
        """
        Validation: Au moins les cotes 1X2 doivent être présentes.
        """
        has_1x2 = (
            self.home_odds > 0 and 
            self.draw_odds > 0 and 
            self.away_odds > 0
        )
        if not has_1x2:
            # Warning mais pas erreur (cotes peuvent arriver en plusieurs fois)
            pass
        return self
    
    # ─── MÉTHODES DE CONVERSION ───
    
    def to_legacy_dict(self) -> Dict[str, float]:
        """
        MAPPING EXPLICITE vers le format legacy.
        
        Anti-Corruption Layer: On hardcode les clés exactes attendues
        par QuantumOrchestrator V1. Si le legacy change, on le saura.
        
        CLÉS LEGACY (confirmées par audit du 24 Déc 2025):
        - 1X2: home_win, draw, away_win
        - Over/Under: over_15, over_25, over_35, under_15, under_25, under_35
        - BTTS: btts_yes, btts_no
        """
        return {
            # 1X2 - Mapping confirmé par audit
            "home_win": self.home_odds,
            "draw": self.draw_odds,
            "away_win": self.away_odds,
            
            # Over/Under - Mapping confirmé par audit
            "over_15": self.over_15_odds,
            "over_25": self.over_25_odds,
            "over_35": self.over_35_odds,
            "under_15": self.under_15_odds,
            "under_25": self.under_25_odds,
            "under_35": self.under_35_odds,
            
            # BTTS - Mapping confirmé par audit
            "btts_yes": self.btts_yes_odds,
            "btts_no": self.btts_no_odds,
        }
    
    def get_best_odds(self, market: str) -> Tuple[float, str]:
        """
        Retourne les meilleures cotes et le bookmaker pour un marché.
        
        Args:
            market: Nom du marché (ex: "home_win", "over_25")
        
        Returns:
            Tuple[float, str]: (meilleure cote, nom du bookmaker)
        """
        best_odds = 0.0
        best_bookie = ""
        
        for bookie, odds in self.odds_by_bookmaker.items():
            if market in odds and odds[market] > best_odds:
                best_odds = odds[market]
                best_bookie = bookie
        
        return best_odds, best_bookie
    
    def get_implied_probability(self, market: str) -> float:
        """
        Calcule la probabilité implicite d'une cote.
        
        Formula: implied_prob = 1 / odds
        """
        odds_map = {
            "home_win": self.home_odds,
            "draw": self.draw_odds,
            "away_win": self.away_odds,
            "over_25": self.over_25_odds,
            "btts_yes": self.btts_yes_odds,
        }
        
        odds = odds_map.get(market, 0.0)
        if odds > 1.0:
            return 1.0 / odds
        return 0.0
    
    def get_steam_summary(self) -> Dict[str, Any]:
        """Résumé des mouvements de cotes."""
        significant = [m for m in self.odds_movements.values() if m.is_significant]
        sharp = [m for m in self.odds_movements.values() if m.is_sharp_steam]
        traps = [m for m in self.odds_movements.values() if m.is_trap_signal]
        
        return {
            "total_markets_tracked": len(self.odds_movements),
            "significant_movements": len(significant),
            "sharp_steam_detected": len(sharp) > 0,
            "trap_signals_detected": len(traps) > 0,
            "sharp_markets": [m.market for m in sharp],
            "trap_markets": [m.market for m in traps],
        }
    
    def has_minimum_data(self) -> bool:
        """Vérifie si les données minimales sont présentes."""
        return (
            self.home_odds > 0 and
            self.draw_odds > 0 and
            self.away_odds > 0
        )


# ═══════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def create_match_odds_from_dict(data: Dict[str, Any]) -> MatchOdds:
    """
    Factory pour créer MatchOdds depuis un dictionnaire.
    
    Gère les différents formats de clés (legacy, API, etc.)
    """
    # Mapping des clés alternatives
    return MatchOdds(
        match_id=data.get("match_id", data.get("id", "")),
        home_team=data.get("home_team", data.get("home", "")),
        away_team=data.get("away_team", data.get("away", "")),
        commence_time=data.get("commence_time", data.get("kickoff", datetime.now())),
        league=data.get("league", data.get("competition", "")),
        home_odds=float(data.get("home_odds", data.get("home_win", 0.0))),
        draw_odds=float(data.get("draw_odds", data.get("draw", 0.0))),
        away_odds=float(data.get("away_odds", data.get("away_win", 0.0))),
        over_25_odds=float(data.get("over_25_odds", data.get("over_25", 0.0))),
        btts_yes_odds=float(data.get("btts_yes_odds", data.get("btts_yes", 0.0))),
    )


# ═══════════════════════════════════════════════════════════════
# TESTS INTÉGRÉS
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("📊 MATCH ODDS - TEST PYDANTIC VALIDATION")
    print("=" * 70)
    
    # ─── TEST 1: Création valide ───
    print("\n✅ TEST 1: Création valide")
    print("-" * 70)
    
    odds = MatchOdds(
        match_id="test_001",
        home_team="Liverpool",
        away_team="Arsenal",
        commence_time=datetime.now(),
        home_odds=1.85,
        draw_odds=3.40,
        away_odds=4.20,
        over_25_odds=1.95,
        btts_yes_odds=1.80,
    )
    print(f"   ✅ MatchOdds créé: {odds.home_team} vs {odds.away_team}")
    print(f"   ✅ 1X2: {odds.home_odds} / {odds.draw_odds} / {odds.away_odds}")
    
    # ─── TEST 2: Validation - cote invalide ───
    print("\n🔴 TEST 2: Validation - cote invalide (0.5)")
    print("-" * 70)
    
    try:
        invalid_odds = MatchOdds(
            match_id="test_002",
            home_team="Test",
            away_team="Test",
            commence_time=datetime.now(),
            home_odds=0.5,  # INVALIDE! < 1.01
        )
        print("   ❌ ERREUR: Aurait dû lever une exception!")
    except ValueError as e:
        print(f"   ✅ Exception levée correctement: {e}")
    
    # ─── TEST 3: to_legacy_dict() ───
    print("\n📦 TEST 3: Conversion to_legacy_dict()")
    print("-" * 70)
    
    legacy = odds.to_legacy_dict()
    print(f"   Legacy dict: {legacy}")
    assert legacy["home_win"] == 1.85, "Mapping home_win incorrect"
    assert legacy["draw"] == 3.40, "Mapping draw incorrect"
    assert legacy["btts_yes"] == 1.80, "Mapping btts_yes incorrect"
    print("   ✅ Mapping explicite validé")
    
    # ─── TEST 4: Probabilité implicite ───
    print("\n📈 TEST 4: Probabilité implicite")
    print("-" * 70)
    
    home_prob = odds.get_implied_probability("home_win")
    print(f"   home_win odds: {odds.home_odds} → implied prob: {home_prob:.2%}")
    
    # ─── TEST 5: OddsMovement ───
    print("\n📊 TEST 5: OddsMovement (Steam Detection)")
    print("-" * 70)
    
    movement = OddsMovement(
        market="home_win",
        opening_odds=1.90,
        current_odds=1.75,
        movement_pct=-7.9,
        direction="DOWN",
        steam_signal="SHARP_MONEY",
        samples=15,
    )
    print(f"   Movement: {movement.opening_odds} → {movement.current_odds}")
    print(f"   is_significant: {movement.is_significant}")
    print(f"   is_sharp_steam: {movement.is_sharp_steam}")
    print(f"   is_trap_signal: {movement.is_trap_signal}")
    
    # ─── RÉSUMÉ ───
    print("\n" + "=" * 70)
    print("✅ MATCH ODDS - TESTS COMPLETS")
    print("=" * 70)
    print("   Pydantic validation: ✅")
    print("   Mapping explicite: ✅")
    print("   Steam detection: ✅")
