"""
Models - Structures de donnees pour UnifiedBrain
===============================================================================

Dataclasses immuables pour les predictions et recommandations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class MarketType(Enum):
    """Types de marches supportes."""
    # 1X2
    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"

    # Goals
    OVER_15 = "over_1.5"
    OVER_25 = "over_2.5"
    OVER_35 = "over_3.5"
    UNDER_25 = "under_2.5"

    # BTTS
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"

    # Double Chance
    DC_1X = "dc_1x"
    DC_X2 = "dc_x2"
    DC_12 = "dc_12"

    # DNB
    DNB_HOME = "dnb_home"
    DNB_AWAY = "dnb_away"

    # Corners
    CORNERS_OVER_85 = "corners_over_8.5"
    CORNERS_OVER_95 = "corners_over_9.5"
    CORNERS_OVER_105 = "corners_over_10.5"
    CORNERS_UNDER_105 = "corners_under_10.5"

    # Cards
    CARDS_OVER_35 = "cards_over_3.5"
    CARDS_OVER_45 = "cards_over_4.5"
    CARDS_OVER_55 = "cards_over_5.5"


class Confidence(Enum):
    """Niveaux de confiance."""
    VERY_HIGH = "VERY_HIGH"    # >80%
    HIGH = "HIGH"              # 65-80%
    MEDIUM = "MEDIUM"          # 50-65%
    LOW = "LOW"                # 35-50%
    VERY_LOW = "VERY_LOW"      # <35%


class SignalStrength(Enum):
    """Force du signal de pari."""
    STRONG_BET = "STRONG_BET"      # Edge > 5%, Kelly > 3%
    MEDIUM_BET = "MEDIUM_BET"      # Edge 3-5%, Kelly 1-3%
    SMALL_BET = "SMALL_BET"        # Edge 1-3%, Kelly 0.5-1%
    NO_BET = "NO_BET"              # Edge < 1%
    FADE = "FADE"                  # Edge negatif significatif


@dataclass
class EngineOutput:
    """Output standardise d'un engine."""
    engine_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    weight: float = 1.0
    error: Optional[str] = None


@dataclass
class MarketProbability:
    """Probabilite pour un marche specifique."""
    market: MarketType
    probability: float
    confidence: float

    # Sources
    engines_contributing: List[str] = field(default_factory=list)
    raw_probabilities: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        # Clamp probability
        self.probability = max(0.01, min(0.99, self.probability))


@dataclass
class MarketEdge:
    """Edge calcule pour un marche."""
    market: MarketType
    probability: float
    fair_odds: float
    market_odds: float

    # Edge
    raw_edge: float = 0.0
    edge_after_vig: float = 0.0
    edge_after_liquidity: float = 0.0

    # Kelly
    kelly_fraction: float = 0.0
    recommended_stake: float = 0.0

    # Signal
    signal_strength: SignalStrength = SignalStrength.NO_BET

    def __post_init__(self):
        # Calculer fair odds
        if self.probability > 0:
            self.fair_odds = 1 / self.probability

        # Calculer raw edge
        if self.market_odds > 0:
            implied_prob = 1 / self.market_odds
            self.raw_edge = self.probability - implied_prob


@dataclass
class BetRecommendation:
    """Recommandation de pari finale."""
    market: MarketType
    edge: MarketEdge

    # Recommandation
    action: str = "NO_BET"  # BET, FADE, SKIP
    stake_percentage: float = 0.0
    stake_units: float = 0.0

    # Reasoning
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Metadata
    confidence: Confidence = Confidence.MEDIUM


@dataclass
class MatchPrediction:
    """
    Prediction complete d'un match - OUTPUT PRINCIPAL.

    Contient toutes les probabilites, edges, et recommandations.
    """
    # Identifiants
    home_team: str
    away_team: str
    match_date: Optional[datetime] = None
    prediction_timestamp: datetime = field(default_factory=datetime.now)

    # Profils tactiques
    home_profile: str = "UNKNOWN"
    away_profile: str = "UNKNOWN"
    clash_type: str = "STANDARD"

    # Probabilites principales (1X2)
    home_win_prob: float = 0.40
    draw_prob: float = 0.25
    away_win_prob: float = 0.35

    # Goals
    expected_goals: float = 2.5
    over_15_prob: float = 0.75
    over_25_prob: float = 0.55
    over_35_prob: float = 0.30

    # BTTS
    btts_prob: float = 0.50

    # Corners
    corners_expected: float = 10.0
    corners_over_95_prob: float = 0.50
    corners_over_105_prob: float = 0.40

    # Cards
    cards_expected: float = 4.0
    cards_over_35_prob: float = 0.55
    cards_over_45_prob: float = 0.40

    # Toutes les probabilites par marche
    market_probabilities: Dict[str, MarketProbability] = field(default_factory=dict)

    # Edges calcules
    market_edges: Dict[str, MarketEdge] = field(default_factory=dict)

    # Recommandations
    recommendations: List[BetRecommendation] = field(default_factory=list)
    best_bet: Optional[BetRecommendation] = None

    # Engine outputs
    engine_outputs: Dict[str, EngineOutput] = field(default_factory=dict)
    engines_used: List[str] = field(default_factory=list)
    engines_failed: List[str] = field(default_factory=list)

    # Qualite
    overall_confidence: Confidence = Confidence.MEDIUM
    data_quality_score: float = 0.5

    # Metadata
    model_version: str = "UnifiedBrain_v1.0"

    def get_best_edges(self, min_edge: float = 0.02) -> List[MarketEdge]:
        """Retourne les meilleurs edges au-dessus du seuil."""
        edges = [e for e in self.market_edges.values() if e.edge_after_liquidity >= min_edge]
        return sorted(edges, key=lambda x: x.edge_after_liquidity, reverse=True)

    def get_kelly_bets(self, min_kelly: float = 0.005) -> List[BetRecommendation]:
        """Retourne les paris avec Kelly > seuil."""
        return [r for r in self.recommendations if r.stake_percentage >= min_kelly]

    def summary(self) -> str:
        """Resume textuel de la prediction."""
        lines = [
            f"=== {self.home_team} vs {self.away_team} ===",
            f"Profiles: {self.home_profile} vs {self.away_profile}",
            f"1X2: {self.home_win_prob:.1%} / {self.draw_prob:.1%} / {self.away_win_prob:.1%}",
            f"Expected Goals: {self.expected_goals:.2f}",
            f"BTTS: {self.btts_prob:.1%}",
            f"Corners: {self.corners_expected:.1f}",
            f"Cards: {self.cards_expected:.1f}",
            f"Confidence: {self.overall_confidence.value}",
            f"Quality: {self.data_quality_score:.1%}",
        ]

        if self.best_bet:
            lines.append(f"Best Bet: {self.best_bet.market.value} ({self.best_bet.edge.edge_after_liquidity:.1%} edge)")

        return "\n".join(lines)
