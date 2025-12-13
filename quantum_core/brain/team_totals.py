"""
Team Totals Calculator - Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════

MARCHÉS:
    - Home Team Over/Under 0.5, 1.5, 2.5
    - Away Team Over/Under 0.5, 1.5, 2.5

CALCUL:
    Utilise la distribution de Poisson sur expected_home_goals et expected_away_goals

    P(Team Over X.5) = 1 - P(Team <= X)
    P(Team <= X) = Σ(k=0 to X) [e^(-λ) × λ^k / k!]

CONFIGURATION:
    - LIQUIDITY_TAX: 2% (marchés liquides)
    - MIN_EDGE: 3%

Auteur: Mon_PS Quant Team
Version: 1.0.0
Date: 13 Décembre 2025
"""

import math
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

LIQUIDITY_TAX = 0.02  # 2% pour marchés liquides
MIN_EDGE = 0.03  # 3% minimum edge


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TeamTotalsAnalysis:
    """Analyse Team Totals."""

    # Home Team
    home_over_05_prob: float = 0.0
    home_over_15_prob: float = 0.0
    home_over_25_prob: float = 0.0
    home_under_05_prob: float = 0.0
    home_under_15_prob: float = 0.0
    home_under_25_prob: float = 0.0

    # Away Team
    away_over_05_prob: float = 0.0
    away_over_15_prob: float = 0.0
    away_over_25_prob: float = 0.0
    away_under_05_prob: float = 0.0
    away_under_15_prob: float = 0.0
    away_under_25_prob: float = 0.0

    # Expected goals utilisés
    expected_home_goals: float = 0.0
    expected_away_goals: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════
# CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class TeamTotalsCalculator:
    """
    Calcule les probabilités Team Totals.

    Principe:
        - Home Over 0.5 = P(Home >= 1 but)
        - Home Over 1.5 = P(Home >= 2 buts)
        - Home Over 2.5 = P(Home >= 3 buts)
        - Idem pour Away

    Utilise Poisson: P(X = k) = e^(-λ) × λ^k / k!
    """

    def __init__(self):
        self.liquidity_tax = LIQUIDITY_TAX
        self.min_edge = MIN_EDGE
        logger.info("TeamTotalsCalculator initialisé")

    # ─────────────────────────────────────────────────────────────────────
    # POISSON HELPERS
    # ─────────────────────────────────────────────────────────────────────

    def _poisson_pmf(self, k: int, lambda_: float) -> float:
        """Probability Mass Function de Poisson."""
        if lambda_ <= 0:
            return 1.0 if k == 0 else 0.0
        return (math.exp(-lambda_) * (lambda_ ** k)) / math.factorial(k)

    def _poisson_cdf(self, k: int, lambda_: float) -> float:
        """Cumulative Distribution Function: P(X <= k)."""
        return sum(self._poisson_pmf(i, lambda_) for i in range(k + 1))

    def _team_over_prob(self, expected_goals: float, threshold: float) -> float:
        """
        Calcule P(Team >= threshold goals).

        Args:
            expected_goals: xG de l'équipe
            threshold: Seuil (0.5, 1.5, 2.5)

        Returns:
            Probabilité que l'équipe marque >= threshold buts
        """
        # Over 0.5 = P(X >= 1) = 1 - P(X = 0)
        # Over 1.5 = P(X >= 2) = 1 - P(X <= 1)
        # Over 2.5 = P(X >= 3) = 1 - P(X <= 2)

        k = int(threshold)  # 0.5 -> 0, 1.5 -> 1, 2.5 -> 2
        prob_under = self._poisson_cdf(k, expected_goals)
        return 1.0 - prob_under

    # ─────────────────────────────────────────────────────────────────────
    # MAIN CALCULATE
    # ─────────────────────────────────────────────────────────────────────

    def calculate(
        self,
        expected_home_goals: float,
        expected_away_goals: float
    ) -> TeamTotalsAnalysis:
        """
        Calcule toutes les probabilités Team Totals.

        Args:
            expected_home_goals: xG de l'équipe à domicile
            expected_away_goals: xG de l'équipe à l'extérieur

        Returns:
            TeamTotalsAnalysis avec toutes les probabilités
        """
        analysis = TeamTotalsAnalysis(
            expected_home_goals=expected_home_goals,
            expected_away_goals=expected_away_goals
        )

        # ─────────────────────────────────────────────────────────────────
        # HOME TEAM
        # ─────────────────────────────────────────────────────────────────

        analysis.home_over_05_prob = self._team_over_prob(expected_home_goals, 0.5)
        analysis.home_over_15_prob = self._team_over_prob(expected_home_goals, 1.5)
        analysis.home_over_25_prob = self._team_over_prob(expected_home_goals, 2.5)

        analysis.home_under_05_prob = 1.0 - analysis.home_over_05_prob
        analysis.home_under_15_prob = 1.0 - analysis.home_over_15_prob
        analysis.home_under_25_prob = 1.0 - analysis.home_over_25_prob

        # ─────────────────────────────────────────────────────────────────
        # AWAY TEAM
        # ─────────────────────────────────────────────────────────────────

        analysis.away_over_05_prob = self._team_over_prob(expected_away_goals, 0.5)
        analysis.away_over_15_prob = self._team_over_prob(expected_away_goals, 1.5)
        analysis.away_over_25_prob = self._team_over_prob(expected_away_goals, 2.5)

        analysis.away_under_05_prob = 1.0 - analysis.away_over_05_prob
        analysis.away_under_15_prob = 1.0 - analysis.away_over_15_prob
        analysis.away_under_25_prob = 1.0 - analysis.away_over_25_prob

        logger.debug(
            f"TeamTotals: Home xG={expected_home_goals:.2f} "
            f"(O0.5={analysis.home_over_05_prob:.1%}, O1.5={analysis.home_over_15_prob:.1%}, O2.5={analysis.home_over_25_prob:.1%}) | "
            f"Away xG={expected_away_goals:.2f} "
            f"(O0.5={analysis.away_over_05_prob:.1%}, O1.5={analysis.away_over_15_prob:.1%}, O2.5={analysis.away_over_25_prob:.1%})"
        )

        return analysis


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_team_totals_calculator() -> TeamTotalsCalculator:
    """Factory singleton pour TeamTotalsCalculator."""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = TeamTotalsCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    calc = TeamTotalsCalculator()

    # Test Liverpool (1.8 xG) vs Man City (2.0 xG)
    print("=" * 70)
    print("TEST: Liverpool (1.8 xG) vs Man City (2.0 xG)")
    print("=" * 70)

    analysis = calc.calculate(1.8, 2.0)

    print(f"\nHOME (Liverpool) - xG: {analysis.expected_home_goals:.2f}")
    print(f"   Over 0.5: {analysis.home_over_05_prob:.1%}")
    print(f"   Over 1.5: {analysis.home_over_15_prob:.1%}")
    print(f"   Over 2.5: {analysis.home_over_25_prob:.1%}")

    print(f"\nAWAY (Man City) - xG: {analysis.expected_away_goals:.2f}")
    print(f"   Over 0.5: {analysis.away_over_05_prob:.1%}")
    print(f"   Over 1.5: {analysis.away_over_15_prob:.1%}")
    print(f"   Over 2.5: {analysis.away_over_25_prob:.1%}")

    # Test équipe défensive (0.8 xG) vs offensive (2.5 xG)
    print("\n" + "=" * 70)
    print("TEST: Équipe défensive (0.8 xG) vs Équipe offensive (2.5 xG)")
    print("=" * 70)

    analysis2 = calc.calculate(0.8, 2.5)

    print(f"\nHOME (Défensive) - xG: {analysis2.expected_home_goals:.2f}")
    print(f"   Over 0.5: {analysis2.home_over_05_prob:.1%}")
    print(f"   Over 1.5: {analysis2.home_over_15_prob:.1%}")
    print(f"   Over 2.5: {analysis2.home_over_25_prob:.1%}")

    print(f"\nAWAY (Offensive) - xG: {analysis2.expected_away_goals:.2f}")
    print(f"   Over 0.5: {analysis2.away_over_05_prob:.1%}")
    print(f"   Over 1.5: {analysis2.away_over_15_prob:.1%}")
    print(f"   Over 2.5: {analysis2.away_over_25_prob:.1%}")
