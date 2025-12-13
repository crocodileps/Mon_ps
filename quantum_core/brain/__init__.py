"""
UnifiedBrain - Hedge Fund Grade Prediction Engine
═══════════════════════════════════════════════════════════════════════════

44 MARCHÉS SUPPORTÉS:
    - 1X2 (3): home_win, draw, away_win
    - Double Chance (3): dc_1x, dc_x2, dc_12
    - Draw No Bet (2): dnb_home, dnb_away
    - BTTS (2): btts_yes, btts_no
    - Goals (12): over/under 0.5, 1.5, 2.5, 3.5, 4.5, 5.5
    - Corners (6): over/under 8.5, 9.5, 10.5
    - Cards (6): over/under 2.5, 3.5, 4.5
    - Correct Score (10): top 10 scores les plus probables

Architecture:
    UnifiedBrain coordonne:
    1. DataHubAdapter → Données unifiées
    2. 8 Engines → Analyses spécialisées
    3. PoissonCalculator → Probabilités over/under
    4. DerivedMarketsCalculator → DC, DNB
    5. CorrectScoreCalculator → Scores exacts
    6. BayesianFusion → Fusion probabilités
    7. EdgeCalculator → Calcul edges
    8. KellySizer → Sizing optimal

Usage:
    from quantum_core.brain import get_unified_brain

    brain = get_unified_brain()
    prediction = brain.analyze_match("Liverpool", "Manchester City")

    # 44 probabilités
    print(prediction.summary())

    # Top 10 scores
    print(prediction.top_scores)
    print(prediction.correct_score_probs)
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
]

__version__ = "2.1.0"
__markets_count__ = 44
