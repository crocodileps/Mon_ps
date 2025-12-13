"""
ToScoreInHalfCalculator - Quelle equipe marque dans quelle mi-temps
═══════════════════════════════════════════════════════════════════════════

4 MARCHES:
    1. Home to Score 1st Half - Home marque en 1ere MT
    2. Home to Score 2nd Half - Home marque en 2eme MT
    3. Away to Score 1st Half - Away marque en 1ere MT
    4. Away to Score 2nd Half - Away marque en 2eme MT

CALCUL:
    P(Team score Half) = 1 - P(Team = 0 in Half)
    P(Team = 0 in Half) = e^(-team_xg_half)

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

TO_SCORE_HALF_LIQUIDITY_TAX = 0.025
TO_SCORE_HALF_MIN_EDGE = 0.04

HT_RATIO = 0.45
SECOND_HALF_RATIO = 0.55


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ToScoreInHalfAnalysis:
    """Analyse To Score in Half."""
    expected_home_goals: float
    expected_away_goals: float

    home_to_score_1h: float = 0.55
    home_to_score_2h: float = 0.62
    away_to_score_1h: float = 0.48
    away_to_score_2h: float = 0.55

    def summary(self) -> str:
        return f"""To Score in Half Analysis:
  Home xG: {self.expected_home_goals:.2f} | Away xG: {self.expected_away_goals:.2f}

  Home to Score 1H: {self.home_to_score_1h:.1%}
  Home to Score 2H: {self.home_to_score_2h:.1%}
  Away to Score 1H: {self.away_to_score_1h:.1%}
  Away to Score 2H: {self.away_to_score_2h:.1%}"""

    def to_dict(self) -> Dict[str, float]:
        return {
            "home_to_score_1h": self.home_to_score_1h,
            "home_to_score_2h": self.home_to_score_2h,
            "away_to_score_1h": self.away_to_score_1h,
            "away_to_score_2h": self.away_to_score_2h,
        }


# ═══════════════════════════════════════════════════════════════════════════
# CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class ToScoreInHalfCalculator:
    """Calculateur To Score in Half."""

    def calculate(
        self,
        expected_home_goals: float,
        expected_away_goals: float
    ) -> ToScoreInHalfAnalysis:
        """
        Calcule P(Team to Score in Half).

        P(score) = 1 - e^(-xg_half)
        """
        expected_home_goals = max(0.5, min(4.0, expected_home_goals))
        expected_away_goals = max(0.5, min(4.0, expected_away_goals))

        # xG par mi-temps
        home_xg_1h = expected_home_goals * HT_RATIO
        home_xg_2h = expected_home_goals * SECOND_HALF_RATIO
        away_xg_1h = expected_away_goals * HT_RATIO
        away_xg_2h = expected_away_goals * SECOND_HALF_RATIO

        # P(score) = 1 - P(0) = 1 - e^(-xg)
        home_score_1h = 1 - math.exp(-home_xg_1h)
        home_score_2h = 1 - math.exp(-home_xg_2h)
        away_score_1h = 1 - math.exp(-away_xg_1h)
        away_score_2h = 1 - math.exp(-away_xg_2h)

        return ToScoreInHalfAnalysis(
            expected_home_goals=expected_home_goals,
            expected_away_goals=expected_away_goals,
            home_to_score_1h=home_score_1h,
            home_to_score_2h=home_score_2h,
            away_to_score_1h=away_score_1h,
            away_to_score_2h=away_score_2h,
        )


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_to_score_half_calculator() -> ToScoreInHalfCalculator:
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = ToScoreInHalfCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST TO SCORE IN HALF CALCULATOR")
    print("=" * 60)

    calc = ToScoreInHalfCalculator()

    # Test Liverpool vs Man City
    print("\nLiverpool (1.9 xG) vs Man City (1.9 xG):")
    analysis = calc.calculate(1.9, 1.9)
    print(analysis.summary())

    # Test favori domicile
    print("\nFavori domicile (2.0 xG vs 1.0 xG):")
    analysis2 = calc.calculate(2.0, 1.0)
    print(analysis2.summary())

    print("\nTESTS TERMINES")
