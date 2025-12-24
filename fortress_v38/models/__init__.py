"""
FORTRESS V3.8 - Models Package
==============================

Modèles Pydantic pour la Forteresse.
Anti-Corruption Layer avec validation runtime.
"""

from .odds import (
    MatchOdds,
    OddsMovement,
    create_match_odds_from_dict,
)

__all__ = [
    "MatchOdds",
    "OddsMovement",
    "create_match_odds_from_dict",
]
