"""
UnifiedBrain - Hedge Fund Grade Prediction Engine
═══════════════════════════════════════════════════════════════════════════

50 MARCHÉS SUPPORTÉS:
    - 1X2 (3): home_win, draw, away_win
    - Double Chance (3): dc_1x, dc_x2, dc_12
    - Draw No Bet (2): dnb_home, dnb_away
    - BTTS (2): btts_yes, btts_no
    - Goals (12): over/under 0.5, 1.5, 2.5, 3.5, 4.5, 5.5
    - Corners (6): over/under 8.5, 9.5, 10.5
    - Cards (6): over/under 2.5, 3.5, 4.5
    - Correct Score (10): top 10 scores les plus probables
    - Half-Time (6): ht_1x2, ht_over_05, ht_btts

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
]

__version__ = "2.2.0"
__markets_count__ = 50
