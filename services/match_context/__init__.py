"""
Match Context Calculator - Fatigue & Schedule Engine
═══════════════════════════════════════════════════════════════════════════
Calcule l'EffectiveRestIndex pour chaque équipe avant un match.
Approche Hedge Fund Grade - Pas un simple calcul de jours.

Composants:
- MatchContextConfig: Configuration et seuils
- RestAnalysis: Analyse de repos d'une équipe
- MatchRestComparison: Comparaison entre 2 équipes
- MatchContextCalculator: Calcul EffectiveRestIndex
- MatchContextService: Orchestration et update DB

Auteur: Mon_PS Team
Date: 2025-12-24
Version: 2.0.0
═══════════════════════════════════════════════════════════════════════════
"""
from .config import MatchContextConfig, DEFAULT_CONFIG
from .models import RestAnalysis, MatchRestComparison
from .calculator import MatchContextCalculator
from .service import MatchContextService

__all__ = [
    'MatchContextConfig',
    'DEFAULT_CONFIG',
    'RestAnalysis',
    'MatchRestComparison',
    'MatchContextCalculator',
    'MatchContextService'
]
