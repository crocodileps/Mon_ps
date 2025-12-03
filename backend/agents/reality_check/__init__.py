"""
🧠 REALITY CHECK MODULE V1.0
============================

Module d'analyse qualitative pour valider/ajuster les prédictions statistiques.

Composants:
- RealityChecker: Classe principale d'analyse
- RealityDataService: Accès aux données Reality Check
- RealityScoreCalculator: Calcul du score final

Usage:
    from agents.reality_check import RealityChecker
    
    checker = RealityChecker()
    result = checker.analyze_match("Manchester City", "Southampton")
"""

from .reality_checker import RealityChecker
from .data_service import RealityDataService

__all__ = ['RealityChecker', 'RealityDataService']
__version__ = '1.0.0'
