"""
ScoreInBothHalvesCalculator - Au moins 1 but dans chaque mi-temps
═══════════════════════════════════════════════════════════════════════════

PRINCIPE:
    Score in Both Halves = Au moins 1 but marque en 1ere MT
                           ET au moins 1 but marque en 2eme MT

    (Peu importe QUELLE equipe marque, juste qu'il y ait des buts)

2 MARCHES:
    1. Score in Both Halves YES
    2. Score in Both Halves NO

CALCUL:
    P(SIBH YES) = P(>=1 but HT) * P(>=1 but 2H)
    P(>=1 but) = 1 - P(0 buts) = 1 - e^(-lambda)

Distribution: 45% en 1ere MT, 55% en 2eme MT

LIQUIDITY TAX: 2.5%

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

SIBH_LIQUIDITY_TAX = 0.025
SIBH_MIN_EDGE = 0.04

HT_RATIO = 0.45
SECOND_HALF_RATIO = 0.55


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ScoreInBothHalvesAnalysis:
    """Analyse Score in Both Halves."""
    expected_goals: float
    score_both_halves_yes: float = 0.55
    score_both_halves_no: float = 0.45

    # Details
    score_ht_prob: float = 0.0
    score_2h_prob: float = 0.0

    def summary(self) -> str:
        return f"""Score in Both Halves (xG={self.expected_goals:.2f}):
  YES: {self.score_both_halves_yes:.1%}
  NO:  {self.score_both_halves_no:.1%}

  Details:
    P(score HT): {self.score_ht_prob:.1%}
    P(score 2H): {self.score_2h_prob:.1%}"""

    def to_dict(self) -> Dict[str, float]:
        return {
            "score_both_halves_yes": self.score_both_halves_yes,
            "score_both_halves_no": self.score_both_halves_no,
        }


# ═══════════════════════════════════════════════════════════════════════════
# CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class ScoreInBothHalvesCalculator:
    """Calculateur Score in Both Halves."""

    def calculate(self, expected_goals: float) -> ScoreInBothHalvesAnalysis:
        """
        Calcule P(Score in Both Halves).

        P(SIBH) = P(>=1 but HT) * P(>=1 but 2H)
        """
        expected_goals = max(1.0, min(6.0, expected_goals))

        # xG par mi-temps
        xg_ht = expected_goals * HT_RATIO
        xg_2h = expected_goals * SECOND_HALF_RATIO

        # P(>=1 but) = 1 - P(0 but) = 1 - e^(-lambda)
        score_ht = 1 - math.exp(-xg_ht)
        score_2h = 1 - math.exp(-xg_2h)

        sibh_yes = score_ht * score_2h
        sibh_no = 1 - sibh_yes

        return ScoreInBothHalvesAnalysis(
            expected_goals=expected_goals,
            score_both_halves_yes=sibh_yes,
            score_both_halves_no=sibh_no,
            score_ht_prob=score_ht,
            score_2h_prob=score_2h,
        )


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_score_both_halves_calculator() -> ScoreInBothHalvesCalculator:
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = ScoreInBothHalvesCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST SCORE IN BOTH HALVES CALCULATOR")
    print("=" * 60)

    calc = ScoreInBothHalvesCalculator()

    for xg in [2.0, 2.5, 3.0, 3.5, 4.0]:
        analysis = calc.calculate(xg)
        print(f"xG={xg:.1f}: YES={analysis.score_both_halves_yes:.1%} | NO={analysis.score_both_halves_no:.1%}")

    print("\n" + calc.calculate(2.8).summary())
    print("\nTESTS TERMINES")
