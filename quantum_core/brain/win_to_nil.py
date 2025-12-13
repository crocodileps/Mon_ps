"""
WinToNilCalculator - Calcul des probabilités Win to Nil
═══════════════════════════════════════════════════════════════════════════

PRINCIPE:
    Win to Nil = Victoire + Clean Sheet (adversaire ne marque pas).
    
    Home Win to Nil: Home gagne ET Away = 0 buts (scores: 1-0, 2-0, 3-0...)
    Away Win to Nil: Away gagne ET Home = 0 buts (scores: 0-1, 0-2, 0-3...)

4 MARCHÉS:
    1. Home Win to Nil YES - Home gagne, Away = 0
    2. Home Win to Nil NO  - Home gagne, Away >= 1
    3. Away Win to Nil YES - Away gagne, Home = 0
    4. Away Win to Nil NO  - Away gagne, Home >= 1

CALCUL:
    Méthode 1 (via BTTS):
        P(Home WTN) ≈ P(Home Win) × P(Away = 0 | Home Win)
        
    Méthode 2 (via Correct Score - PLUS PRÉCIS):
        P(Home WTN) = P(1-0) + P(2-0) + P(3-0) + P(4-0) + ...
        P(Away WTN) = P(0-1) + P(0-2) + P(0-3) + P(0-4) + ...

LIQUIDITY TAX:
    Win to Nil = 2.5% (marché secondaire)

Auteur: Mon_PS Quant Team
Version: 1.0.0
Date: 13 Décembre 2025
"""

import math
from typing import Dict, Optional
from dataclasses import dataclass
from functools import lru_cache


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

WIN_TO_NIL_LIQUIDITY_TAX = 0.025
WIN_TO_NIL_MIN_EDGE = 0.04


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class WinToNilAnalysis:
    """Analyse des marchés Win to Nil."""
    # Inputs
    home_win_prob: float
    away_win_prob: float
    
    # 4 marchés Win to Nil
    home_win_to_nil_yes: float = 0.15  # Home gagne, Away = 0
    home_win_to_nil_no: float = 0.20   # Home gagne, Away >= 1
    away_win_to_nil_yes: float = 0.12  # Away gagne, Home = 0
    away_win_to_nil_no: float = 0.18   # Away gagne, Home >= 1
    
    def summary(self) -> str:
        return f"""Win to Nil Analysis:
  Home Win: {self.home_win_prob:.1%}
  Away Win: {self.away_win_prob:.1%}
  
  Home Win to Nil YES: {self.home_win_to_nil_yes:.1%} (1-0, 2-0, 3-0...)
  Home Win to Nil NO:  {self.home_win_to_nil_no:.1%} (2-1, 3-1, 3-2...)
  Away Win to Nil YES: {self.away_win_to_nil_yes:.1%} (0-1, 0-2, 0-3...)
  Away Win to Nil NO:  {self.away_win_to_nil_no:.1%} (1-2, 1-3, 2-3...)
  
  Vérifications:
    Home WTN YES + NO = {self.home_win_to_nil_yes + self.home_win_to_nil_no:.1%} (≈ Home Win {self.home_win_prob:.1%})
    Away WTN YES + NO = {self.away_win_to_nil_yes + self.away_win_to_nil_no:.1%} (≈ Away Win {self.away_win_prob:.1%})"""
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "home_win_to_nil": self.home_win_to_nil_yes,
            "home_win_to_nil_no": self.home_win_to_nil_no,
            "away_win_to_nil": self.away_win_to_nil_yes,
            "away_win_to_nil_no": self.away_win_to_nil_no,
        }


# ═══════════════════════════════════════════════════════════════════════════
# WIN TO NIL CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class WinToNilCalculator:
    """
    Calculateur de probabilités Win to Nil.
    
    Deux méthodes de calcul:
    1. Via Correct Score (plus précis si disponible)
    2. Via Poisson (fallback)
    
    Usage:
        calc = WinToNilCalculator()
        
        # Méthode 1: Via Correct Score
        analysis = calc.calculate_from_scores(
            correct_score_probs={"1-0": 0.08, "2-0": 0.05, "0-1": 0.07, ...},
            home_win_prob=0.40,
            away_win_prob=0.35
        )
        
        # Méthode 2: Via Poisson
        analysis = calc.calculate_from_poisson(
            expected_home=1.8,
            expected_away=1.2,
            home_win_prob=0.45,
            away_win_prob=0.30
        )
    """
    
    @staticmethod
    @lru_cache(maxsize=500)
    def _poisson_pmf(k: int, lam: float) -> float:
        """Probabilité P(X = k) pour Poisson(lambda)."""
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        if k < 0:
            return 0.0
        try:
            return (lam ** k) * math.exp(-lam) / math.factorial(k)
        except (OverflowError, ValueError):
            return 0.0
    
    def calculate_from_scores(
        self,
        correct_score_probs: Dict[str, float],
        home_win_prob: float,
        away_win_prob: float
    ) -> WinToNilAnalysis:
        """
        Calcule Win to Nil via les probabilités Correct Score.
        
        Args:
            correct_score_probs: Dict des probabilités par score (ex: {"1-0": 0.08})
            home_win_prob: P(Home Win)
            away_win_prob: P(Away Win)
            
        Returns:
            WinToNilAnalysis
        """
        home_wtn_yes = 0.0
        away_wtn_yes = 0.0
        
        for score_str, prob in correct_score_probs.items():
            # Parser le score (format "X-Y" ou "cs_X_Y")
            if "-" in score_str:
                parts = score_str.replace("cs_", "").split("-")
            elif "_" in score_str:
                parts = score_str.replace("cs_", "").split("_")
            else:
                continue
            
            try:
                home_goals = int(parts[0])
                away_goals = int(parts[1])
            except (ValueError, IndexError):
                continue
            
            # Home Win to Nil: Home gagne (home > away) ET away = 0
            if home_goals > away_goals and away_goals == 0:
                home_wtn_yes += prob
            
            # Away Win to Nil: Away gagne (away > home) ET home = 0
            if away_goals > home_goals and home_goals == 0:
                away_wtn_yes += prob
        
        # Win to Nil NO = Win - Win to Nil YES
        home_wtn_no = max(0, home_win_prob - home_wtn_yes)
        away_wtn_no = max(0, away_win_prob - away_wtn_yes)
        
        return WinToNilAnalysis(
            home_win_prob=home_win_prob,
            away_win_prob=away_win_prob,
            home_win_to_nil_yes=home_wtn_yes,
            home_win_to_nil_no=home_wtn_no,
            away_win_to_nil_yes=away_wtn_yes,
            away_win_to_nil_no=away_wtn_no,
        )
    
    def calculate_from_poisson(
        self,
        expected_home: float,
        expected_away: float,
        home_win_prob: float,
        away_win_prob: float,
        max_goals: int = 7
    ) -> WinToNilAnalysis:
        """
        Calcule Win to Nil via distribution Poisson.
        
        Args:
            expected_home: Expected goals home
            expected_away: Expected goals away
            home_win_prob: P(Home Win)
            away_win_prob: P(Away Win)
            max_goals: Max goals pour le calcul
            
        Returns:
            WinToNilAnalysis
        """
        # P(Away = 0)
        p_away_zero = self._poisson_pmf(0, expected_away)
        
        # P(Home = 0)
        p_home_zero = self._poisson_pmf(0, expected_home)
        
        # Home Win to Nil = somme P(home=k, away=0) pour k >= 1
        home_wtn_yes = 0.0
        for h in range(1, max_goals + 1):
            home_wtn_yes += self._poisson_pmf(h, expected_home) * p_away_zero
        
        # Away Win to Nil = somme P(home=0, away=k) pour k >= 1
        away_wtn_yes = 0.0
        for a in range(1, max_goals + 1):
            away_wtn_yes += p_home_zero * self._poisson_pmf(a, expected_away)
        
        # Win to Nil NO
        home_wtn_no = max(0, home_win_prob - home_wtn_yes)
        away_wtn_no = max(0, away_win_prob - away_wtn_yes)
        
        return WinToNilAnalysis(
            home_win_prob=home_win_prob,
            away_win_prob=away_win_prob,
            home_win_to_nil_yes=home_wtn_yes,
            home_win_to_nil_no=home_wtn_no,
            away_win_to_nil_yes=away_wtn_yes,
            away_win_to_nil_no=away_wtn_no,
        )
    
    def calculate(
        self,
        expected_home: float,
        expected_away: float,
        home_win_prob: float,
        away_win_prob: float,
        correct_score_probs: Optional[Dict[str, float]] = None
    ) -> WinToNilAnalysis:
        """
        Calcule Win to Nil (méthode automatique).

        Utilise Correct Score si les scores WTN sont présents, sinon Poisson.
        """
        # Toujours utiliser Poisson car les scores WTN (1-0, 2-0, etc.)
        # ne sont souvent pas dans le top 10 des scores probables
        return self.calculate_from_poisson(
            expected_home, expected_away, home_win_prob, away_win_prob
        )


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_win_to_nil_calculator() -> WinToNilCalculator:
    """Retourne l'instance singleton."""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = WinToNilCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("TEST WIN TO NIL CALCULATOR")
    print("=" * 70)
    
    calc = WinToNilCalculator()
    
    # Test 1: Via Poisson
    print("\nTest 1: Calcul via Poisson (Liverpool vs Man City)")
    print("-" * 60)
    analysis1 = calc.calculate_from_poisson(
        expected_home=1.9,
        expected_away=1.9,
        home_win_prob=0.36,
        away_win_prob=0.36
    )
    print(analysis1.summary())
    
    # Test 2: Via Correct Score
    print("\nTest 2: Calcul via Correct Score")
    print("-" * 60)
    cs_probs = {
        "1-0": 0.06, "2-0": 0.04, "3-0": 0.02,
        "0-1": 0.06, "0-2": 0.04, "0-3": 0.02,
        "1-1": 0.10, "2-1": 0.08, "1-2": 0.08,
        "2-2": 0.06, "3-1": 0.04, "1-3": 0.04,
    }
    analysis2 = calc.calculate_from_scores(
        correct_score_probs=cs_probs,
        home_win_prob=0.38,
        away_win_prob=0.35
    )
    print(analysis2.summary())
    
    # Test 3: Match déséquilibré (Bayern vs petit club)
    print("\nTest 3: Bayern vs Petit Club")
    print("-" * 60)
    analysis3 = calc.calculate_from_poisson(
        expected_home=3.0,
        expected_away=0.8,
        home_win_prob=0.80,
        away_win_prob=0.08
    )
    print(analysis3.summary())
    
    # Test 4: Dict format
    print("\nTest 4: Format Dict pour UnifiedBrain")
    print("-" * 60)
    wtn_dict = analysis1.to_dict()
    for key, prob in wtn_dict.items():
        print(f"  {key}: {prob:.1%}")
    
    print("\n" + "=" * 70)
    print("TESTS TERMINES")
    print("=" * 70)
