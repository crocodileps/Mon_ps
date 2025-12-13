"""
CleanSheetCalculator - Equipe ne prend pas de but
═══════════════════════════════════════════════════════════════════════════

PRINCIPE:
    Clean Sheet = L'equipe ne prend AUCUN but dans le match

    Home Clean Sheet = Away marque 0 buts
    Away Clean Sheet = Home marque 0 buts

2 MARCHES:
    1. Home Clean Sheet YES (Away = 0 buts)
    2. Away Clean Sheet YES (Home = 0 buts)

CALCUL:
    P(Home CS) = P(Away = 0) = e^(-away_xg)
    P(Away CS) = P(Home = 0) = e^(-home_xg)

NOTE: Different de Win to Nil!
    - Win to Nil = Gagner + Clean Sheet
    - Clean Sheet = Juste ne pas prendre de but (peut etre 0-0)

LIQUIDITY TAX: 2%

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

CLEAN_SHEET_LIQUIDITY_TAX = 0.02
CLEAN_SHEET_MIN_EDGE = 0.03


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CleanSheetAnalysis:
    """Analyse Clean Sheet."""
    expected_home_goals: float
    expected_away_goals: float
    home_clean_sheet_yes: float = 0.35
    home_clean_sheet_no: float = 0.65
    away_clean_sheet_yes: float = 0.30
    away_clean_sheet_no: float = 0.70

    def summary(self) -> str:
        return f"""Clean Sheet Analysis:
  Home xG: {self.expected_home_goals:.2f} | Away xG: {self.expected_away_goals:.2f}

  Home Clean Sheet (Away=0): YES={self.home_clean_sheet_yes:.1%} | NO={self.home_clean_sheet_no:.1%}
  Away Clean Sheet (Home=0): YES={self.away_clean_sheet_yes:.1%} | NO={self.away_clean_sheet_no:.1%}"""

    def to_dict(self) -> Dict[str, float]:
        return {
            "home_clean_sheet_yes": self.home_clean_sheet_yes,
            "home_clean_sheet_no": self.home_clean_sheet_no,
            "away_clean_sheet_yes": self.away_clean_sheet_yes,
            "away_clean_sheet_no": self.away_clean_sheet_no,
        }


# ═══════════════════════════════════════════════════════════════════════════
# CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class CleanSheetCalculator:
    """Calculateur Clean Sheet via Poisson."""

    def calculate(
        self,
        expected_home_goals: float,
        expected_away_goals: float
    ) -> CleanSheetAnalysis:
        """
        Calcule P(Clean Sheet) pour chaque equipe.

        P(Home CS) = P(Away = 0) = e^(-away_xg)
        P(Away CS) = P(Home = 0) = e^(-home_xg)
        """
        expected_home_goals = max(0.5, min(4.0, expected_home_goals))
        expected_away_goals = max(0.5, min(4.0, expected_away_goals))

        # Clean Sheet = adversaire marque 0
        home_cs_yes = math.exp(-expected_away_goals)  # Away = 0
        away_cs_yes = math.exp(-expected_home_goals)  # Home = 0

        return CleanSheetAnalysis(
            expected_home_goals=expected_home_goals,
            expected_away_goals=expected_away_goals,
            home_clean_sheet_yes=home_cs_yes,
            home_clean_sheet_no=1 - home_cs_yes,
            away_clean_sheet_yes=away_cs_yes,
            away_clean_sheet_no=1 - away_cs_yes,
        )


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_clean_sheet_calculator() -> CleanSheetCalculator:
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = CleanSheetCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST CLEAN SHEET CALCULATOR")
    print("=" * 60)

    calc = CleanSheetCalculator()

    # Test differents scenarios
    scenarios = [
        (1.5, 1.0, "Favori domicile"),
        (1.5, 1.5, "Match equilibre"),
        (1.0, 2.0, "Favori exterieur"),
        (2.0, 2.0, "Match offensif"),
    ]

    for home_xg, away_xg, desc in scenarios:
        analysis = calc.calculate(home_xg, away_xg)
        print(f"\n{desc} (H:{home_xg} vs A:{away_xg}):")
        print(f"  Home CS: {analysis.home_clean_sheet_yes:.1%}")
        print(f"  Away CS: {analysis.away_clean_sheet_yes:.1%}")

    print("\nTESTS TERMINES")
