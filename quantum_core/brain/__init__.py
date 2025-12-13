"""
UnifiedBrain - Hedge Fund Grade Prediction Engine
===============================================================================

Architecture:
    UnifiedBrain coordonne:
    1. DataHubAdapter -> Donnees unifiees
    2. 8 Engines -> Analyses specialisees
    3. BayesianFusion -> Fusion probabilites
    4. EdgeCalculator -> Calcul edges
    5. KellySizer -> Sizing optimal

Usage:
    from quantum_core.brain import get_unified_brain

    brain = get_unified_brain()
    prediction = brain.analyze_match("Liverpool", "Manchester City")

    print(f"Home Win: {prediction.probabilities['home_win']:.1%}")
    print(f"Best Edge: {prediction.best_edge}")
    print(f"Kelly Stake: {prediction.kelly_stake:.1%}")
"""

from .unified_brain import UnifiedBrain, get_unified_brain
from .models import MatchPrediction, MarketEdge, BetRecommendation

__all__ = [
    "UnifiedBrain",
    "get_unified_brain",
    "MatchPrediction",
    "MarketEdge",
    "BetRecommendation"
]
