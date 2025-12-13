"""
OddEvenCalculator - Calcul des probabilites Odd/Even Goals
═══════════════════════════════════════════════════════════════════════════

PRINCIPE:
    Odd Goals = 1, 3, 5, 7... buts au total
    Even Goals = 0, 2, 4, 6... buts au total

2 MARCHES:
    1. Odd Goals  - Nombre impair de buts
    2. Even Goals - Nombre pair de buts

CALCUL (via Poisson):
    P(Odd) = P(1) + P(3) + P(5) + P(7) + ...
    P(Even) = P(0) + P(2) + P(4) + P(6) + ...

PROPRIETE MATHEMATIQUE:
    Pour une distribution Poisson(lambda):
    P(Even) = (1 + e^(-2*lambda)) / 2
    P(Odd) = (1 - e^(-2*lambda)) / 2

LIQUIDITY TAX: 2% (marche liquide)

Auteur: Mon_PS Quant Team
Version: 1.0.0
Date: 13 Decembre 2025
"""

import math
from typing import Dict
from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

ODD_EVEN_LIQUIDITY_TAX = 0.02
ODD_EVEN_MIN_EDGE = 0.03


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class OddEvenAnalysis:
    """Analyse Odd/Even Goals."""
    expected_goals: float
    odd_goals_prob: float = 0.50
    even_goals_prob: float = 0.50

    def summary(self) -> str:
        return f"""Odd/Even Analysis (xG={self.expected_goals:.2f}):
  Odd Goals (1,3,5...):  {self.odd_goals_prob:.1%}
  Even Goals (0,2,4...): {self.even_goals_prob:.1%}"""

    def to_dict(self) -> Dict[str, float]:
        return {
            "odd_goals": self.odd_goals_prob,
            "even_goals": self.even_goals_prob,
        }


# ═══════════════════════════════════════════════════════════════════════════
# ODD/EVEN CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class OddEvenCalculator:
    """
    Calculateur Odd/Even via formule Poisson fermee.

    Usage:
        calc = OddEvenCalculator()
        analysis = calc.calculate(expected_goals=2.5)
    """

    def calculate(self, expected_goals: float) -> OddEvenAnalysis:
        """
        Calcule P(Odd) et P(Even) via formule Poisson.

        Formule fermee:
            P(Even) = (1 + e^(-2*lambda)) / 2
            P(Odd) = 1 - P(Even)
        """
        expected_goals = max(0.5, min(7.0, expected_goals))

        # Formule Poisson fermee
        exp_term = math.exp(-2 * expected_goals)
        even_prob = (1 + exp_term) / 2
        odd_prob = 1 - even_prob

        return OddEvenAnalysis(
            expected_goals=expected_goals,
            odd_goals_prob=odd_prob,
            even_goals_prob=even_prob,
        )


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_odd_even_calculator() -> OddEvenCalculator:
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = OddEvenCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST ODD/EVEN CALCULATOR")
    print("=" * 60)

    calc = OddEvenCalculator()

    for xg in [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
        analysis = calc.calculate(xg)
        print(f"xG={xg:.1f}: Odd={analysis.odd_goals_prob:.1%} | Even={analysis.even_goals_prob:.1%}")

    print("\nTESTS TERMINES")
