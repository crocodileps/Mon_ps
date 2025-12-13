"""
Models - Structures de donnees pour UnifiedBrain V2.6
===============================================================================

85 MARCHES SUPPORTES:
- 1X2 (3): home_win, draw, away_win
- Double Chance (3): dc_1x, dc_x2, dc_12
- DNB (2): dnb_home, dnb_away
- BTTS (2): btts_yes, btts_no
- Goals (12): over/under 0.5, 1.5, 2.5, 3.5, 4.5, 5.5
- Corners (6): over/under 8.5, 9.5, 10.5
- Cards (6): over/under 2.5, 3.5, 4.5
- Correct Score (10): top 10 scores (0-0, 1-0, 0-1, 1-1, 2-0, 0-2, 2-1, 1-2, 2-2, 3-1)
- Half-Time (6): ht_1x2, ht_over_05, ht_under_05, ht_btts
- Asian Handicap (8): ah_-0.5, ah_-1.0, ah_-1.5, ah_-2.0 (home & away)
- Goal Range (4): 0-1, 2-3, 4-5, 6+
- Double Result (9): 9 combinaisons HT/FT
- Win to Nil (4): home/away win to nil yes/no
- Odd/Even (2): odd_goals, even_goals
- Exact Goals (6): 0, 1, 2, 3, 4, 5+
- BTTS Both Halves (2): yes/no
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

    # === Correct Score (10) - Top 10 scores les plus probables ===
    CS_0_0 = "cs_0_0"
    CS_1_0 = "cs_1_0"
    CS_0_1 = "cs_0_1"
    CS_1_1 = "cs_1_1"
    CS_2_0 = "cs_2_0"
    CS_0_2 = "cs_0_2"
    CS_2_1 = "cs_2_1"
    CS_1_2 = "cs_1_2"
    CS_2_2 = "cs_2_2"
    CS_3_1 = "cs_3_1"

    # === Half-Time (6) - Marchés première mi-temps ===
    HT_HOME_WIN = "ht_home_win"
    HT_DRAW = "ht_draw"
    HT_AWAY_WIN = "ht_away_win"
    HT_OVER_05 = "ht_over_05"
    HT_UNDER_05 = "ht_under_05"
    HT_BTTS = "ht_btts"

    # === Asian Handicap (8) - Marchés asiatiques ===
    AH_HOME_M05 = "ah_home_m05"   # AH -0.5 Home (Home must win)
    AH_AWAY_P05 = "ah_away_p05"   # AH +0.5 Away (Away must not lose)
    AH_HOME_M10 = "ah_home_m10"   # AH -1.0 Home (Home must win by 2+)
    AH_AWAY_P10 = "ah_away_p10"   # AH +1.0 Away (Away can lose by 1)
    AH_HOME_M15 = "ah_home_m15"   # AH -1.5 Home (Home must win by 2+)
    AH_AWAY_P15 = "ah_away_p15"   # AH +1.5 Away (Away can lose by 1)
    AH_HOME_M20 = "ah_home_m20"   # AH -2.0 Home (Home must win by 3+)
    AH_AWAY_P20 = "ah_away_p20"   # AH +2.0 Away (Away can lose by 2)

    # === Goal Range (4) - Tranches de buts ===
    GOALS_0_1 = "goals_0_1"        # 0-1 buts total
    GOALS_2_3 = "goals_2_3"        # 2-3 buts total
    GOALS_4_5 = "goals_4_5"        # 4-5 buts total
    GOALS_6_PLUS = "goals_6_plus"  # 6+ buts total

    # === Double Result (9) - HT/FT combinés ===
    DR_1_1 = "dr_1_1"  # HT Home, FT Home
    DR_1_X = "dr_1_x"  # HT Home, FT Draw
    DR_1_2 = "dr_1_2"  # HT Home, FT Away
    DR_X_1 = "dr_x_1"  # HT Draw, FT Home
    DR_X_X = "dr_x_x"  # HT Draw, FT Draw
    DR_X_2 = "dr_x_2"  # HT Draw, FT Away
    DR_2_1 = "dr_2_1"  # HT Away, FT Home
    DR_2_X = "dr_2_x"  # HT Away, FT Draw
    DR_2_2 = "dr_2_2"  # HT Away, FT Away

    # === Win to Nil (4) - Marchés défensifs ===
    HOME_WIN_TO_NIL = "home_win_to_nil"      # Home gagne, Away = 0
    HOME_WIN_TO_NIL_NO = "home_win_to_nil_no"  # Home gagne, Away >= 1
    AWAY_WIN_TO_NIL = "away_win_to_nil"      # Away gagne, Home = 0
    AWAY_WIN_TO_NIL_NO = "away_win_to_nil_no"  # Away gagne, Home >= 1

    # === Odd/Even (2) ===
    ODD_GOALS = "odd_goals"    # Nombre impair de buts (1,3,5...)
    EVEN_GOALS = "even_goals"  # Nombre pair de buts (0,2,4...)

    # === Exact Goals (6) ===
    EXACTLY_0_GOALS = "exactly_0_goals"
    EXACTLY_1_GOAL = "exactly_1_goal"
    EXACTLY_2_GOALS = "exactly_2_goals"
    EXACTLY_3_GOALS = "exactly_3_goals"
    EXACTLY_4_GOALS = "exactly_4_goals"
    GOALS_5_PLUS = "goals_5_plus"

    # === BTTS Both Halves (2) ===
    BTTS_BOTH_HALVES_YES = "btts_both_halves_yes"
    BTTS_BOTH_HALVES_NO = "btts_both_halves_no"


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
    "CORRECT_SCORE": [MarketType.CS_0_0, MarketType.CS_1_0, MarketType.CS_0_1, MarketType.CS_1_1,
                      MarketType.CS_2_0, MarketType.CS_0_2, MarketType.CS_2_1, MarketType.CS_1_2,
                      MarketType.CS_2_2, MarketType.CS_3_1],
    "HALF_TIME": [MarketType.HT_HOME_WIN, MarketType.HT_DRAW, MarketType.HT_AWAY_WIN,
                  MarketType.HT_OVER_05, MarketType.HT_UNDER_05, MarketType.HT_BTTS],
    "ASIAN_HANDICAP": [MarketType.AH_HOME_M05, MarketType.AH_AWAY_P05, MarketType.AH_HOME_M10,
                       MarketType.AH_AWAY_P10, MarketType.AH_HOME_M15, MarketType.AH_AWAY_P15,
                       MarketType.AH_HOME_M20, MarketType.AH_AWAY_P20],
    "GOAL_RANGE": [MarketType.GOALS_0_1, MarketType.GOALS_2_3, MarketType.GOALS_4_5, MarketType.GOALS_6_PLUS],
    "DOUBLE_RESULT": [MarketType.DR_1_1, MarketType.DR_1_X, MarketType.DR_1_2,
                      MarketType.DR_X_1, MarketType.DR_X_X, MarketType.DR_X_2,
                      MarketType.DR_2_1, MarketType.DR_2_X, MarketType.DR_2_2],
    "WIN_TO_NIL": [MarketType.HOME_WIN_TO_NIL, MarketType.HOME_WIN_TO_NIL_NO,
                   MarketType.AWAY_WIN_TO_NIL, MarketType.AWAY_WIN_TO_NIL_NO],
    "ODD_EVEN": [MarketType.ODD_GOALS, MarketType.EVEN_GOALS],
    "EXACT_GOALS": [MarketType.EXACTLY_0_GOALS, MarketType.EXACTLY_1_GOAL,
                   MarketType.EXACTLY_2_GOALS, MarketType.EXACTLY_3_GOALS,
                   MarketType.EXACTLY_4_GOALS, MarketType.GOALS_5_PLUS],
    "BTTS_BOTH_HALVES": [MarketType.BTTS_BOTH_HALVES_YES, MarketType.BTTS_BOTH_HALVES_NO],
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

    # Correct Score - Tres peu liquide
    MarketType.CS_0_0: 0.05,
    MarketType.CS_1_0: 0.05,
    MarketType.CS_0_1: 0.05,
    MarketType.CS_1_1: 0.05,
    MarketType.CS_2_0: 0.05,
    MarketType.CS_0_2: 0.05,
    MarketType.CS_2_1: 0.05,
    MarketType.CS_1_2: 0.05,
    MarketType.CS_2_2: 0.05,
    MarketType.CS_3_1: 0.05,

    # Half-Time - Moderement liquide
    MarketType.HT_HOME_WIN: 0.025,
    MarketType.HT_DRAW: 0.025,
    MarketType.HT_AWAY_WIN: 0.025,
    MarketType.HT_OVER_05: 0.025,
    MarketType.HT_UNDER_05: 0.025,
    MarketType.HT_BTTS: 0.025,

    # Asian Handicap - Tres liquide
    MarketType.AH_HOME_M05: 0.015,
    MarketType.AH_AWAY_P05: 0.015,
    MarketType.AH_HOME_M10: 0.015,
    MarketType.AH_AWAY_P10: 0.015,
    MarketType.AH_HOME_M15: 0.015,
    MarketType.AH_AWAY_P15: 0.015,
    MarketType.AH_HOME_M20: 0.015,
    MarketType.AH_AWAY_P20: 0.015,

    # Goal Range - Moderement liquide
    MarketType.GOALS_0_1: 0.025,
    MarketType.GOALS_2_3: 0.025,
    MarketType.GOALS_4_5: 0.025,
    MarketType.GOALS_6_PLUS: 0.03,

    # Double Result - Peu liquide
    MarketType.DR_1_1: 0.035,
    MarketType.DR_1_X: 0.035,
    MarketType.DR_1_2: 0.035,
    MarketType.DR_X_1: 0.035,
    MarketType.DR_X_X: 0.035,
    MarketType.DR_X_2: 0.035,
    MarketType.DR_2_1: 0.035,
    MarketType.DR_2_X: 0.035,
    MarketType.DR_2_2: 0.035,

    # Win to Nil - Moderement liquide
    MarketType.HOME_WIN_TO_NIL: 0.025,
    MarketType.HOME_WIN_TO_NIL_NO: 0.025,
    MarketType.AWAY_WIN_TO_NIL: 0.025,
    MarketType.AWAY_WIN_TO_NIL_NO: 0.025,

    # Odd/Even - Liquide
    MarketType.ODD_GOALS: 0.02,
    MarketType.EVEN_GOALS: 0.02,

    # Exact Goals - Secondaire
    MarketType.EXACTLY_0_GOALS: 0.03,
    MarketType.EXACTLY_1_GOAL: 0.03,
    MarketType.EXACTLY_2_GOALS: 0.03,
    MarketType.EXACTLY_3_GOALS: 0.03,
    MarketType.EXACTLY_4_GOALS: 0.03,
    MarketType.GOALS_5_PLUS: 0.035,

    # BTTS Both Halves - Exotique
    MarketType.BTTS_BOTH_HALVES_YES: 0.035,
    MarketType.BTTS_BOTH_HALVES_NO: 0.035,
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

    # Correct Score - Edge eleve requis
    MarketType.CS_0_0: 0.12,
    MarketType.CS_1_0: 0.12,
    MarketType.CS_0_1: 0.12,
    MarketType.CS_1_1: 0.12,
    MarketType.CS_2_0: 0.12,
    MarketType.CS_0_2: 0.12,
    MarketType.CS_2_1: 0.12,
    MarketType.CS_1_2: 0.12,
    MarketType.CS_2_2: 0.12,
    MarketType.CS_3_1: 0.12,

    # Half-Time
    MarketType.HT_HOME_WIN: 0.04,
    MarketType.HT_DRAW: 0.04,
    MarketType.HT_AWAY_WIN: 0.04,
    MarketType.HT_OVER_05: 0.04,
    MarketType.HT_UNDER_05: 0.04,
    MarketType.HT_BTTS: 0.04,

    # Asian Handicap - Edge bas car tres liquide
    MarketType.AH_HOME_M05: 0.025,
    MarketType.AH_AWAY_P05: 0.025,
    MarketType.AH_HOME_M10: 0.025,
    MarketType.AH_AWAY_P10: 0.025,
    MarketType.AH_HOME_M15: 0.025,
    MarketType.AH_AWAY_P15: 0.025,
    MarketType.AH_HOME_M20: 0.025,
    MarketType.AH_AWAY_P20: 0.025,

    # Goal Range
    MarketType.GOALS_0_1: 0.035,
    MarketType.GOALS_2_3: 0.035,
    MarketType.GOALS_4_5: 0.035,
    MarketType.GOALS_6_PLUS: 0.04,

    # Double Result - Edge eleve requis
    MarketType.DR_1_1: 0.06,
    MarketType.DR_1_X: 0.06,
    MarketType.DR_1_2: 0.06,
    MarketType.DR_X_1: 0.06,
    MarketType.DR_X_X: 0.06,
    MarketType.DR_X_2: 0.06,
    MarketType.DR_2_1: 0.06,
    MarketType.DR_2_X: 0.06,
    MarketType.DR_2_2: 0.06,

    # Win to Nil
    MarketType.HOME_WIN_TO_NIL: 0.04,
    MarketType.HOME_WIN_TO_NIL_NO: 0.04,
    MarketType.AWAY_WIN_TO_NIL: 0.04,
    MarketType.AWAY_WIN_TO_NIL_NO: 0.04,

    # Odd/Even
    MarketType.ODD_GOALS: 0.03,
    MarketType.EVEN_GOALS: 0.03,

    # Exact Goals
    MarketType.EXACTLY_0_GOALS: 0.05,
    MarketType.EXACTLY_1_GOAL: 0.05,
    MarketType.EXACTLY_2_GOALS: 0.05,
    MarketType.EXACTLY_3_GOALS: 0.05,
    MarketType.EXACTLY_4_GOALS: 0.05,
    MarketType.GOALS_5_PLUS: 0.06,

    # BTTS Both Halves
    MarketType.BTTS_BOTH_HALVES_YES: 0.06,
    MarketType.BTTS_BOTH_HALVES_NO: 0.06,
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
    pour les 85 marches supportes (34 + 10 CS + 6 HT + 8 AH + 4 GR + 9 DR + 4 WTN + 2 OE + 6 EG + 2 BBH).
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

    # === Correct Score (Top 10) ===
    correct_score_probs: Dict[str, float] = field(default_factory=dict)  # {cs_1_1: 0.12, ...}
    top_scores: List[str] = field(default_factory=list)  # ["1-1", "1-0", "2-1", ...]

    # === Half-Time (6 marchés) ===
    ht_home_win_prob: float = 0.25
    ht_draw_prob: float = 0.50
    ht_away_win_prob: float = 0.25
    ht_over_05_prob: float = 0.55
    ht_under_05_prob: float = 0.45
    ht_btts_prob: float = 0.20
    expected_ht_goals: float = 1.0

    # === Asian Handicap (8 marchés) ===
    ah_home_m05_prob: float = 0.40  # AH -0.5 Home (Home must win)
    ah_away_p05_prob: float = 0.60  # AH +0.5 Away (Away must not lose)
    ah_home_m10_prob: float = 0.30  # AH -1.0 Home (Home must win by 2+)
    ah_away_p10_prob: float = 0.70  # AH +1.0 Away (Away can lose by 1)
    ah_home_m15_prob: float = 0.25  # AH -1.5 Home (Home must win by 2+)
    ah_away_p15_prob: float = 0.75  # AH +1.5 Away (Away can lose by 1)
    ah_home_m20_prob: float = 0.20  # AH -2.0 Home (Home must win by 3+)
    ah_away_p20_prob: float = 0.80  # AH +2.0 Away (Away can lose by 2)

    # === Goal Range (4 marchés) ===
    goals_0_1_prob: float = 0.20
    goals_2_3_prob: float = 0.45
    goals_4_5_prob: float = 0.25
    goals_6_plus_prob: float = 0.10

    # === Double Result (9 marchés) ===
    dr_1_1_prob: float = 0.15  # HT Home, FT Home
    dr_1_x_prob: float = 0.05  # HT Home, FT Draw
    dr_1_2_prob: float = 0.03  # HT Home, FT Away
    dr_x_1_prob: float = 0.15  # HT Draw, FT Home
    dr_x_x_prob: float = 0.12  # HT Draw, FT Draw
    dr_x_2_prob: float = 0.10  # HT Draw, FT Away
    dr_2_1_prob: float = 0.03  # HT Away, FT Home
    dr_2_x_prob: float = 0.05  # HT Away, FT Draw
    dr_2_2_prob: float = 0.12  # HT Away, FT Away

    # === Win to Nil (4 marchés) ===
    home_win_to_nil_prob: float = 0.15      # Home gagne, Away = 0
    home_win_to_nil_no_prob: float = 0.20   # Home gagne, Away >= 1
    away_win_to_nil_prob: float = 0.12      # Away gagne, Home = 0
    away_win_to_nil_no_prob: float = 0.18   # Away gagne, Home >= 1

    # === Odd/Even (2 marchés) ===
    odd_goals_prob: float = 0.50
    even_goals_prob: float = 0.50

    # === Exact Goals (6 marchés) ===
    exactly_0_goals_prob: float = 0.08
    exactly_1_goal_prob: float = 0.18
    exactly_2_goals_prob: float = 0.25
    exactly_3_goals_prob: float = 0.22
    exactly_4_goals_prob: float = 0.14
    goals_5_plus_prob: float = 0.13

    # === BTTS Both Halves (2 marchés) ===
    btts_both_halves_yes_prob: float = 0.08
    btts_both_halves_no_prob: float = 0.92

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
    model_version: str = "UnifiedBrain_v2.6"
    markets_count: int = 85

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
