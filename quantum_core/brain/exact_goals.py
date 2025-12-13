"""
ExactGoalsCalculator - Calcul des probabilites Exact Total Goals
═══════════════════════════════════════════════════════════════════════════

6 MARCHES:
    1. Exactly 0 goals
    2. Exactly 1 goal
    3. Exactly 2 goals
    4. Exactly 3 goals
    5. Exactly 4 goals
    6. 5+ goals (5 ou plus)

CALCUL: Distribution Poisson directe

LIQUIDITY TAX: 3% (marche secondaire)

Auteur: Mon_PS Quant Team
Version: 1.0.0
Date: 13 Decembre 2025
"""

import math
from typing import Dict
from dataclasses import dataclass
from functools import lru_cache


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

EXACT_GOALS_LIQUIDITY_TAX = 0.03
EXACT_GOALS_MIN_EDGE = 0.05


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ExactGoalsAnalysis:
    """Analyse Exact Goals."""
    expected_goals: float
    exactly_0_prob: float = 0.08
    exactly_1_prob: float = 0.18
    exactly_2_prob: float = 0.25
    exactly_3_prob: float = 0.22
    exactly_4_prob: float = 0.14
    goals_5_plus_prob: float = 0.13

    def summary(self) -> str:
        total = (self.exactly_0_prob + self.exactly_1_prob + self.exactly_2_prob +
                 self.exactly_3_prob + self.exactly_4_prob + self.goals_5_plus_prob)
        return f"""Exact Goals Analysis (xG={self.expected_goals:.2f}):
  0 goals: {self.exactly_0_prob:.1%}
  1 goal:  {self.exactly_1_prob:.1%}
  2 goals: {self.exactly_2_prob:.1%}
  3 goals: {self.exactly_3_prob:.1%}
  4 goals: {self.exactly_4_prob:.1%}
  5+ goals: {self.goals_5_plus_prob:.1%}
  SUM: {total:.1%}"""

    def to_dict(self) -> Dict[str, float]:
        return {
            "exactly_0_goals": self.exactly_0_prob,
            "exactly_1_goal": self.exactly_1_prob,
            "exactly_2_goals": self.exactly_2_prob,
            "exactly_3_goals": self.exactly_3_prob,
            "exactly_4_goals": self.exactly_4_prob,
            "goals_5_plus": self.goals_5_plus_prob,
        }


# ═══════════════════════════════════════════════════════════════════════════
# EXACT GOALS CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class ExactGoalsCalculator:
    """Calculateur Exact Goals via Poisson."""

    @staticmethod
    @lru_cache(maxsize=500)
    def _poisson_pmf(k: int, lam: float) -> float:
        """P(X = k) pour Poisson(lambda)."""
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        if k < 0:
            return 0.0
        try:
            return (lam ** k) * math.exp(-lam) / math.factorial(k)
        except (OverflowError, ValueError):
            return 0.0

    def calculate(self, expected_goals: float) -> ExactGoalsAnalysis:
        """Calcule P(exactly k goals) pour k = 0,1,2,3,4,5+."""
        expected_goals = max(0.5, min(7.0, expected_goals))

        p0 = self._poisson_pmf(0, expected_goals)
        p1 = self._poisson_pmf(1, expected_goals)
        p2 = self._poisson_pmf(2, expected_goals)
        p3 = self._poisson_pmf(3, expected_goals)
        p4 = self._poisson_pmf(4, expected_goals)
        p5_plus = max(0, 1 - (p0 + p1 + p2 + p3 + p4))

        return ExactGoalsAnalysis(
            expected_goals=expected_goals,
            exactly_0_prob=p0,
            exactly_1_prob=p1,
            exactly_2_prob=p2,
            exactly_3_prob=p3,
            exactly_4_prob=p4,
            goals_5_plus_prob=p5_plus,
        )


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_exact_goals_calculator() -> ExactGoalsCalculator:
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = ExactGoalsCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST EXACT GOALS CALCULATOR")
    print("=" * 60)

    calc = ExactGoalsCalculator()

    for xg in [2.0, 2.5, 3.0, 3.5]:
        print(f"\nxG = {xg}")
        analysis = calc.calculate(xg)
        print(analysis.summary())

    print("\nTESTS TERMINES")
