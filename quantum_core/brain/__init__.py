"""
UnifiedBrain - Hedge Fund Grade Prediction Engine
═══════════════════════════════════════════════════════════════════════════

85 MARCHÉS SUPPORTÉS:
    - 1X2 (3): home_win, draw, away_win
    - Double Chance (3): dc_1x, dc_x2, dc_12
    - Draw No Bet (2): dnb_home, dnb_away
    - BTTS (2): btts_yes, btts_no
    - Goals (12): over/under 0.5, 1.5, 2.5, 3.5, 4.5, 5.5
    - Corners (6): over/under 8.5, 9.5, 10.5
    - Cards (6): over/under 2.5, 3.5, 4.5
    - Correct Score (10): top 10 scores les plus probables
    - Half-Time (6): ht_1x2, ht_over_05, ht_btts
    - Asian Handicap (8): ah_-0.5, ah_-1.0, ah_-1.5, ah_-2.0 (home & away)
    - Goal Range (4): 0-1, 2-3, 4-5, 6+
    - Double Result (9): 9 combinaisons HT/FT
    - Win to Nil (4): home/away win to nil yes/no
    - Odd/Even (2): odd_goals, even_goals
    - Exact Goals (6): 0, 1, 2, 3, 4, 5+
    - BTTS Both Halves (2): yes/no

Architecture:
    UnifiedBrain coordonne:
    1. DataHubAdapter → Données unifiées
    2. 8 Engines → Analyses spécialisées
    3. PoissonCalculator → Probabilités over/under
    4. DerivedMarketsCalculator → DC, DNB
    5. CorrectScoreCalculator → Scores exacts
    6. HalfTimeCalculator → Marchés mi-temps
    7. BayesianFusion → Fusion probabilités
    8. EdgeCalculator → Calcul edges
    9. KellySizer → Sizing optimal

Usage:
    from quantum_core.brain import get_unified_brain

    brain = get_unified_brain()
    prediction = brain.analyze_match("Liverpool", "Manchester City")

    # 50 probabilités
    print(prediction.summary())

    # Top 10 scores
    print(prediction.top_scores)

    # Half-Time
    print(f"HT 1X2: {prediction.ht_home_win_prob} / {prediction.ht_draw_prob} / {prediction.ht_away_win_prob}")
"""

from .unified_brain import UnifiedBrain, get_unified_brain
from .models import (
    MatchPrediction, MarketProbability, MarketEdge, BetRecommendation,
    MarketType, Confidence, SignalStrength, MARKET_CATEGORIES,
    LIQUIDITY_TAX, MIN_EDGE_BY_MARKET
)
from .correct_score import (
    CorrectScoreCalculator, CorrectScoreAnalysis, ScorePrediction,
    get_correct_score_calculator
)
from .half_time import (
    HalfTimeCalculator, HalfTimeAnalysis, get_half_time_calculator
)
from .asian_handicap import (
    AsianHandicapCalculator, AsianHandicapAnalysis, AsianHandicapLine,
    get_asian_handicap_calculator
)
from .goal_range import (
    GoalRangeCalculator, GoalRangeAnalysis, get_goal_range_calculator
)
from .double_result import (
    DoubleResultCalculator, DoubleResultAnalysis, get_double_result_calculator
)
from .win_to_nil import (
    WinToNilCalculator, WinToNilAnalysis, get_win_to_nil_calculator
)
from .odd_even import (
    OddEvenCalculator, OddEvenAnalysis, get_odd_even_calculator
)
from .exact_goals import (
    ExactGoalsCalculator, ExactGoalsAnalysis, get_exact_goals_calculator
)
from .btts_both_halves import (
    BttsBothHalvesCalculator, BttsBothHalvesAnalysis, get_btts_both_halves_calculator
)

__all__ = [
    # Brain
    "UnifiedBrain",
    "get_unified_brain",
    # Models
    "MatchPrediction",
    "MarketProbability",
    "MarketEdge",
    "BetRecommendation",
    "MarketType",
    "Confidence",
    "SignalStrength",
    "MARKET_CATEGORIES",
    "LIQUIDITY_TAX",
    "MIN_EDGE_BY_MARKET",
    # Correct Score
    "CorrectScoreCalculator",
    "CorrectScoreAnalysis",
    "ScorePrediction",
    "get_correct_score_calculator",
    # Half-Time
    "HalfTimeCalculator",
    "HalfTimeAnalysis",
    "get_half_time_calculator",
    # Asian Handicap
    "AsianHandicapCalculator",
    "AsianHandicapAnalysis",
    "AsianHandicapLine",
    "get_asian_handicap_calculator",
    # Goal Range
    "GoalRangeCalculator",
    "GoalRangeAnalysis",
    "get_goal_range_calculator",
    # Double Result
    "DoubleResultCalculator",
    "DoubleResultAnalysis",
    "get_double_result_calculator",
    # Win to Nil
    "WinToNilCalculator",
    "WinToNilAnalysis",
    "get_win_to_nil_calculator",
    # Odd/Even
    "OddEvenCalculator",
    "OddEvenAnalysis",
    "get_odd_even_calculator",
    # Exact Goals
    "ExactGoalsCalculator",
    "ExactGoalsAnalysis",
    "get_exact_goals_calculator",
    # BTTS Both Halves
    "BttsBothHalvesCalculator",
    "BttsBothHalvesAnalysis",
    "get_btts_both_halves_calculator",
]

__version__ = "2.6.0"
__markets_count__ = 85
