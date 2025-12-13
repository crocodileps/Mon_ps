"""
Models - Structures de donnees pour UnifiedBrain V2.0
===============================================================================

34 MARCHES SUPPORTES:
- 1X2 (3): home_win, draw, away_win
- Double Chance (3): dc_1x, dc_x2, dc_12
- DNB (2): dnb_home, dnb_away
- BTTS (2): btts_yes, btts_no
- Goals (12): over/under 0.5, 1.5, 2.5, 3.5, 4.5, 5.5
- Corners (6): over/under 8.5, 9.5, 10.5
- Cards (6): over/under 2.5, 3.5, 4.5
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class MarketType(Enum):
    """Types de marches supportes - 34 marches."""

    # === 1X2 (3) ===
    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"

    # === Double Chance (3) ===
    DC_1X = "dc_1x"       # Home or Draw
    DC_X2 = "dc_x2"       # Draw or Away
    DC_12 = "dc_12"       # Home or Away (No Draw)

    # === Draw No Bet (2) ===
    DNB_HOME = "dnb_home"
    DNB_AWAY = "dnb_away"

    # === BTTS (2) ===
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"

    # === Goals Over (6) ===
    OVER_05 = "over_0.5"
    OVER_15 = "over_1.5"
    OVER_25 = "over_2.5"
    OVER_35 = "over_3.5"
    OVER_45 = "over_4.5"
    OVER_55 = "over_5.5"

    # === Goals Under (6) ===
    UNDER_05 = "under_0.5"
    UNDER_15 = "under_1.5"
    UNDER_25 = "under_2.5"
    UNDER_35 = "under_3.5"
    UNDER_45 = "under_4.5"
    UNDER_55 = "under_5.5"

    # === Corners Over (3) ===
    CORNERS_OVER_85 = "corners_over_8.5"
    CORNERS_OVER_95 = "corners_over_9.5"
    CORNERS_OVER_105 = "corners_over_10.5"

    # === Corners Under (3) ===
    CORNERS_UNDER_85 = "corners_under_8.5"
    CORNERS_UNDER_95 = "corners_under_9.5"
    CORNERS_UNDER_105 = "corners_under_10.5"

    # === Cards Over (3) ===
    CARDS_OVER_25 = "cards_over_2.5"
    CARDS_OVER_35 = "cards_over_3.5"
    CARDS_OVER_45 = "cards_over_4.5"

    # === Cards Under (3) ===
    CARDS_UNDER_25 = "cards_under_2.5"
    CARDS_UNDER_35 = "cards_under_3.5"
    CARDS_UNDER_45 = "cards_under_4.5"


# === MARKET CATEGORIES ===
MARKET_CATEGORIES = {
    "1X2": [MarketType.HOME_WIN, MarketType.DRAW, MarketType.AWAY_WIN],
    "DOUBLE_CHANCE": [MarketType.DC_1X, MarketType.DC_X2, MarketType.DC_12],
    "DNB": [MarketType.DNB_HOME, MarketType.DNB_AWAY],
    "BTTS": [MarketType.BTTS_YES, MarketType.BTTS_NO],
    "GOALS_OVER": [MarketType.OVER_05, MarketType.OVER_15, MarketType.OVER_25,
                   MarketType.OVER_35, MarketType.OVER_45, MarketType.OVER_55],
    "GOALS_UNDER": [MarketType.UNDER_05, MarketType.UNDER_15, MarketType.UNDER_25,
                    MarketType.UNDER_35, MarketType.UNDER_45, MarketType.UNDER_55],
    "CORNERS_OVER": [MarketType.CORNERS_OVER_85, MarketType.CORNERS_OVER_95, MarketType.CORNERS_OVER_105],
    "CORNERS_UNDER": [MarketType.CORNERS_UNDER_85, MarketType.CORNERS_UNDER_95, MarketType.CORNERS_UNDER_105],
    "CARDS_OVER": [MarketType.CARDS_OVER_25, MarketType.CARDS_OVER_35, MarketType.CARDS_OVER_45],
    "CARDS_UNDER": [MarketType.CARDS_UNDER_25, MarketType.CARDS_UNDER_35, MarketType.CARDS_UNDER_45],
}


# === LIQUIDITY TAX BY MARKET ===
# Marches moins liquides = taxe plus elevee
LIQUIDITY_TAX = {
    # 1X2 - Tres liquide
    MarketType.HOME_WIN: 0.01,
    MarketType.DRAW: 0.01,
    MarketType.AWAY_WIN: 0.01,

    # Double Chance - Liquide
    MarketType.DC_1X: 0.015,
    MarketType.DC_X2: 0.015,
    MarketType.DC_12: 0.015,

    # DNB - Liquide
    MarketType.DNB_HOME: 0.015,
    MarketType.DNB_AWAY: 0.015,

    # BTTS - Tres liquide
    MarketType.BTTS_YES: 0.01,
    MarketType.BTTS_NO: 0.01,

    # Goals Over - Variable
    MarketType.OVER_05: 0.02,
    MarketType.OVER_15: 0.015,
    MarketType.OVER_25: 0.01,
    MarketType.OVER_35: 0.015,
    MarketType.OVER_45: 0.02,
    MarketType.OVER_55: 0.025,

    # Goals Under - Variable
    MarketType.UNDER_05: 0.025,
    MarketType.UNDER_15: 0.02,
    MarketType.UNDER_25: 0.015,
    MarketType.UNDER_35: 0.015,
    MarketType.UNDER_45: 0.02,
    MarketType.UNDER_55: 0.02,

    # Corners - Moins liquide
    MarketType.CORNERS_OVER_85: 0.025,
    MarketType.CORNERS_OVER_95: 0.02,
    MarketType.CORNERS_OVER_105: 0.025,
    MarketType.CORNERS_UNDER_85: 0.025,
    MarketType.CORNERS_UNDER_95: 0.02,
    MarketType.CORNERS_UNDER_105: 0.025,

    # Cards - Moins liquide
    MarketType.CARDS_OVER_25: 0.03,
    MarketType.CARDS_OVER_35: 0.025,
    MarketType.CARDS_OVER_45: 0.03,
    MarketType.CARDS_UNDER_25: 0.03,
    MarketType.CARDS_UNDER_35: 0.025,
    MarketType.CARDS_UNDER_45: 0.03,
}


# === MIN EDGE BY MARKET ===
# Edge minimum requis pour considerer le pari
MIN_EDGE_BY_MARKET = {
    # 1X2
    MarketType.HOME_WIN: 0.03,
    MarketType.DRAW: 0.04,
    MarketType.AWAY_WIN: 0.03,

    # Double Chance
    MarketType.DC_1X: 0.025,
    MarketType.DC_X2: 0.025,
    MarketType.DC_12: 0.025,

    # DNB
    MarketType.DNB_HOME: 0.03,
    MarketType.DNB_AWAY: 0.03,

    # BTTS
    MarketType.BTTS_YES: 0.03,
    MarketType.BTTS_NO: 0.03,

    # Goals Over
    MarketType.OVER_05: 0.04,
    MarketType.OVER_15: 0.035,
    MarketType.OVER_25: 0.03,
    MarketType.OVER_35: 0.04,
    MarketType.OVER_45: 0.05,
    MarketType.OVER_55: 0.06,

    # Goals Under
    MarketType.UNDER_05: 0.06,
    MarketType.UNDER_15: 0.05,
    MarketType.UNDER_25: 0.035,
    MarketType.UNDER_35: 0.035,
    MarketType.UNDER_45: 0.04,
    MarketType.UNDER_55: 0.04,

    # Corners
    MarketType.CORNERS_OVER_85: 0.05,
    MarketType.CORNERS_OVER_95: 0.045,
    MarketType.CORNERS_OVER_105: 0.05,
    MarketType.CORNERS_UNDER_85: 0.05,
    MarketType.CORNERS_UNDER_95: 0.045,
    MarketType.CORNERS_UNDER_105: 0.05,

    # Cards
    MarketType.CARDS_OVER_25: 0.06,
    MarketType.CARDS_OVER_35: 0.055,
    MarketType.CARDS_OVER_45: 0.06,
    MarketType.CARDS_UNDER_25: 0.06,
    MarketType.CARDS_UNDER_35: 0.055,
    MarketType.CARDS_UNDER_45: 0.06,
}


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

    # Poisson metadata
    poisson_lambda: Optional[float] = None
    calculation_method: str = "bayesian"

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

    # Metadata
    liquidity_tax: float = 0.0
    min_edge_required: float = 0.0
    meets_threshold: bool = False

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
    category: str = "UNKNOWN"


@dataclass
class MatchPrediction:
    """
    Prediction complete d'un match - OUTPUT PRINCIPAL.

    Contient toutes les probabilites, edges, et recommandations
    pour les 34 marches supportes.
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

    # === 1X2 ===
    home_win_prob: float = 0.40
    draw_prob: float = 0.25
    away_win_prob: float = 0.35

    # === Double Chance (calcule) ===
    dc_1x_prob: float = 0.65
    dc_x2_prob: float = 0.60
    dc_12_prob: float = 0.75

    # === DNB (calcule) ===
    dnb_home_prob: float = 0.53
    dnb_away_prob: float = 0.47

    # === Goals ===
    expected_goals: float = 2.5
    expected_home_goals: float = 1.3
    expected_away_goals: float = 1.2

    # Over probabilities
    over_05_prob: float = 0.92
    over_15_prob: float = 0.75
    over_25_prob: float = 0.55
    over_35_prob: float = 0.30
    over_45_prob: float = 0.15
    over_55_prob: float = 0.07

    # Under probabilities
    under_05_prob: float = 0.08
    under_15_prob: float = 0.25
    under_25_prob: float = 0.45
    under_35_prob: float = 0.70
    under_45_prob: float = 0.85
    under_55_prob: float = 0.93

    # === BTTS ===
    btts_prob: float = 0.50
    btts_no_prob: float = 0.50

    # === Corners ===
    corners_expected: float = 10.0
    corners_over_85_prob: float = 0.60
    corners_over_95_prob: float = 0.50
    corners_over_105_prob: float = 0.40
    corners_under_85_prob: float = 0.40
    corners_under_95_prob: float = 0.50
    corners_under_105_prob: float = 0.60

    # === Cards ===
    cards_expected: float = 4.0
    cards_over_25_prob: float = 0.70
    cards_over_35_prob: float = 0.55
    cards_over_45_prob: float = 0.40
    cards_under_25_prob: float = 0.30
    cards_under_35_prob: float = 0.45
    cards_under_45_prob: float = 0.60

    # Toutes les probabilites par marche
    market_probabilities: Dict[str, MarketProbability] = field(default_factory=dict)

    # Edges calcules
    market_edges: Dict[str, MarketEdge] = field(default_factory=dict)

    # Recommandations
    recommendations: List[BetRecommendation] = field(default_factory=list)
    best_bet: Optional[BetRecommendation] = None
    best_bets_by_category: Dict[str, BetRecommendation] = field(default_factory=dict)

    # Engine outputs
    engine_outputs: Dict[str, EngineOutput] = field(default_factory=dict)
    engines_used: List[str] = field(default_factory=list)
    engines_failed: List[str] = field(default_factory=list)

    # Qualite
    overall_confidence: Confidence = Confidence.MEDIUM
    data_quality_score: float = 0.5

    # Metadata
    model_version: str = "UnifiedBrain_v2.0"
    markets_count: int = 34

    def get_best_edges(self, min_edge: float = 0.02) -> List[MarketEdge]:
        """Retourne les meilleurs edges au-dessus du seuil."""
        edges = [e for e in self.market_edges.values() if e.edge_after_liquidity >= min_edge]
        return sorted(edges, key=lambda x: x.edge_after_liquidity, reverse=True)

    def get_kelly_bets(self, min_kelly: float = 0.005) -> List[BetRecommendation]:
        """Retourne les paris avec Kelly > seuil."""
        return [r for r in self.recommendations if r.stake_percentage >= min_kelly]

    def get_bets_by_category(self, category: str) -> List[BetRecommendation]:
        """Retourne les recommandations pour une categorie."""
        return [r for r in self.recommendations if r.category == category]

    def summary(self) -> str:
        """Resume textuel de la prediction."""
        lines = [
            f"=== {self.home_team} vs {self.away_team} ===",
            f"Profiles: {self.home_profile} vs {self.away_profile}",
            f"1X2: {self.home_win_prob:.1%} / {self.draw_prob:.1%} / {self.away_win_prob:.1%}",
            f"DC: 1X={self.dc_1x_prob:.1%} | X2={self.dc_x2_prob:.1%} | 12={self.dc_12_prob:.1%}",
            f"DNB: Home={self.dnb_home_prob:.1%} | Away={self.dnb_away_prob:.1%}",
            f"Expected Goals: {self.expected_goals:.2f} (H:{self.expected_home_goals:.2f} A:{self.expected_away_goals:.2f})",
            f"Goals: O1.5={self.over_15_prob:.1%} | O2.5={self.over_25_prob:.1%} | O3.5={self.over_35_prob:.1%}",
            f"BTTS: {self.btts_prob:.1%}",
            f"Corners: {self.corners_expected:.1f} (O9.5={self.corners_over_95_prob:.1%})",
            f"Cards: {self.cards_expected:.1f} (O3.5={self.cards_over_35_prob:.1%})",
            f"Confidence: {self.overall_confidence.value}",
            f"Quality: {self.data_quality_score:.1%}",
            f"Markets: {self.markets_count}",
        ]

        if self.best_bet:
            lines.append(f"\nBest Bet: {self.best_bet.market.value}")
            lines.append(f"  Edge: {self.best_bet.edge.edge_after_liquidity:.1%}")
            lines.append(f"  Signal: {self.best_bet.edge.signal_strength.value}")

        if self.best_bets_by_category:
            lines.append("\nBest by Category:")
            for cat, rec in self.best_bets_by_category.items():
                lines.append(f"  {cat}: {rec.market.value} ({rec.edge.edge_after_liquidity:.1%})")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Export vers dictionnaire pour API."""
        return {
            "match": {
                "home_team": self.home_team,
                "away_team": self.away_team,
                "home_profile": self.home_profile,
                "away_profile": self.away_profile,
                "clash_type": self.clash_type,
            },
            "probabilities": {
                "1x2": {
                    "home": self.home_win_prob,
                    "draw": self.draw_prob,
                    "away": self.away_win_prob,
                },
                "double_chance": {
                    "1x": self.dc_1x_prob,
                    "x2": self.dc_x2_prob,
                    "12": self.dc_12_prob,
                },
                "dnb": {
                    "home": self.dnb_home_prob,
                    "away": self.dnb_away_prob,
                },
                "goals": {
                    "expected": self.expected_goals,
                    "over_15": self.over_15_prob,
                    "over_25": self.over_25_prob,
                    "over_35": self.over_35_prob,
                },
                "btts": self.btts_prob,
                "corners": {
                    "expected": self.corners_expected,
                    "over_95": self.corners_over_95_prob,
                },
                "cards": {
                    "expected": self.cards_expected,
                    "over_35": self.cards_over_35_prob,
                },
            },
            "best_bet": {
                "market": self.best_bet.market.value if self.best_bet else None,
                "edge": self.best_bet.edge.edge_after_liquidity if self.best_bet else None,
                "signal": self.best_bet.edge.signal_strength.value if self.best_bet else None,
            } if self.best_bet else None,
            "quality": {
                "confidence": self.overall_confidence.value,
                "data_quality": self.data_quality_score,
                "engines_used": len(self.engines_used),
            },
            "model_version": self.model_version,
        }
