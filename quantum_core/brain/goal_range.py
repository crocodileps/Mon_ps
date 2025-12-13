"""
GoalRangeCalculator - Calcul des probabilités Goal Range
═══════════════════════════════════════════════════════════════════════════

PRINCIPE:
    Goal Range divise le nombre de buts en tranches exclusives.
    Utilise la distribution de Poisson pour calculer chaque tranche.

4 MARCHÉS GOAL RANGE:
    1. Goals 0-1 (0 ou 1 but total)
    2. Goals 2-3 (2 ou 3 buts total)
    3. Goals 4-5 (4 ou 5 buts total)
    4. Goals 6+ (6 buts ou plus)

CALCUL:
    P(0-1 goals) = P(0) + P(1)
    P(2-3 goals) = P(2) + P(3)
    P(4-5 goals) = P(4) + P(5)
    P(6+ goals) = 1 - P(0-5)

LIQUIDITY TAX:
    Goal Range = 2.5% (marché secondaire)

Auteur: Mon_PS Quant Team
Version: 1.0.0
Date: 13 Décembre 2025
"""

import math
from typing import Dict
from dataclasses import dataclass
from functools import lru_cache


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

GOAL_RANGE_LIQUIDITY_TAX = 0.025
GOAL_RANGE_MIN_EDGE = 0.035


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GoalRangeAnalysis:
    """Analyse des marchés Goal Range."""
    expected_goals: float

    # Probabilités
    goals_0_1_prob: float = 0.20
    goals_2_3_prob: float = 0.45
    goals_4_5_prob: float = 0.25
    goals_6_plus_prob: float = 0.10

    def summary(self) -> str:
        return f"""Goal Range Analysis (xG={self.expected_goals:.2f}):
  0-1 Goals: {self.goals_0_1_prob:.1%}
  2-3 Goals: {self.goals_2_3_prob:.1%}
  4-5 Goals: {self.goals_4_5_prob:.1%}
  6+ Goals:  {self.goals_6_plus_prob:.1%}"""

    def to_dict(self) -> Dict[str, float]:
        return {
            "goals_0_1": self.goals_0_1_prob,
            "goals_2_3": self.goals_2_3_prob,
            "goals_4_5": self.goals_4_5_prob,
            "goals_6_plus": self.goals_6_plus_prob,
        }


# ═══════════════════════════════════════════════════════════════════════════
# GOAL RANGE CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class GoalRangeCalculator:
    """
    Calculateur de probabilités Goal Range via Poisson.

    Usage:
        calc = GoalRangeCalculator()
        analysis = calc.calculate(expected_goals=2.5)
        print(analysis.summary())
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

    def calculate(self, expected_goals: float) -> GoalRangeAnalysis:
        """
        Calcule les probabilités Goal Range.

        Args:
            expected_goals: Expected total goals

        Returns:
            GoalRangeAnalysis
        """
        expected_goals = max(0.5, min(6.0, expected_goals))

        # Calculer P(k) pour k = 0 à 5
        p = [self._poisson_pmf(k, expected_goals) for k in range(6)]

        # Calculer les ranges
        p_0_1 = p[0] + p[1]
        p_2_3 = p[2] + p[3]
        p_4_5 = p[4] + p[5]
        p_6_plus = max(0, 1 - (p_0_1 + p_2_3 + p_4_5))

        return GoalRangeAnalysis(
            expected_goals=expected_goals,
            goals_0_1_prob=p_0_1,
            goals_2_3_prob=p_2_3,
            goals_4_5_prob=p_4_5,
            goals_6_plus_prob=p_6_plus,
        )


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_goal_range_calculator() -> GoalRangeCalculator:
    """Retourne l'instance singleton."""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = GoalRangeCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST GOAL RANGE CALCULATOR")
    print("=" * 60)

    calc = GoalRangeCalculator()

    for xg in [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
        print(f"\nxG = {xg}")
        analysis = calc.calculate(xg)
        print(f"  0-1: {analysis.goals_0_1_prob:.1%} | 2-3: {analysis.goals_2_3_prob:.1%} | "
              f"4-5: {analysis.goals_4_5_prob:.1%} | 6+: {analysis.goals_6_plus_prob:.1%}")

    print("\n" + "=" * 60)
    print("TESTS TERMINES")
    print("=" * 60)
