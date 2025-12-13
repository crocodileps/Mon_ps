"""
BttsBothHalvesCalculator - Both Teams to Score in Both Halves
═══════════════════════════════════════════════════════════════════════════

PRINCIPE:
    BTTS Both Halves = Les DEUX equipes marquent EN PREMIERE MI-TEMPS
                       ET EN DEUXIEME MI-TEMPS.

    C'est un marche tres exigeant car il faut 4 evenements:
    1. Home marque en 1ere MT
    2. Away marque en 1ere MT
    3. Home marque en 2eme MT
    4. Away marque en 2eme MT

2 MARCHES:
    1. BTTS Both Halves YES
    2. BTTS Both Halves NO

CALCUL:
    P(BTTS BH) = P(Home score HT) x P(Away score HT) x P(Home score 2H) x P(Away score 2H)

    Avec distribution 45% en 1ere MT, 55% en 2eme MT:
    - P(Team score HT) = 1 - P(Team = 0 goals HT)
    - P(Team score 2H) = 1 - P(Team = 0 goals 2H)

LIQUIDITY TAX: 3.5% (marche exotique)

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

BTTS_BH_LIQUIDITY_TAX = 0.035
BTTS_BH_MIN_EDGE = 0.06

# Distribution des buts par mi-temps
HT_GOALS_RATIO = 0.45
SECOND_HALF_RATIO = 0.55


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BttsBothHalvesAnalysis:
    """Analyse BTTS Both Halves."""
    expected_home_goals: float
    expected_away_goals: float
    btts_both_halves_yes: float = 0.08
    btts_both_halves_no: float = 0.92

    # Details intermediaires
    home_score_ht_prob: float = 0.0
    away_score_ht_prob: float = 0.0
    home_score_2h_prob: float = 0.0
    away_score_2h_prob: float = 0.0

    def summary(self) -> str:
        return f"""BTTS Both Halves Analysis:
  Expected Goals: Home={self.expected_home_goals:.2f}, Away={self.expected_away_goals:.2f}

  BTTS Both Halves YES: {self.btts_both_halves_yes:.1%}
  BTTS Both Halves NO:  {self.btts_both_halves_no:.1%}

  Details:
    Home score HT: {self.home_score_ht_prob:.1%}
    Away score HT: {self.away_score_ht_prob:.1%}
    Home score 2H: {self.home_score_2h_prob:.1%}
    Away score 2H: {self.away_score_2h_prob:.1%}"""

    def to_dict(self) -> Dict[str, float]:
        return {
            "btts_both_halves_yes": self.btts_both_halves_yes,
            "btts_both_halves_no": self.btts_both_halves_no,
        }


# ═══════════════════════════════════════════════════════════════════════════
# BTTS BOTH HALVES CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class BttsBothHalvesCalculator:
    """Calculateur BTTS Both Halves via Poisson."""

    @staticmethod
    @lru_cache(maxsize=500)
    def _poisson_zero(lam: float) -> float:
        """P(X = 0) pour Poisson(lambda) = e^(-lambda)."""
        if lam <= 0:
            return 1.0
        return math.exp(-lam)

    def calculate(
        self,
        expected_home_goals: float,
        expected_away_goals: float
    ) -> BttsBothHalvesAnalysis:
        """
        Calcule P(BTTS Both Halves).

        Logique:
        1. Diviser les xG en HT (45%) et 2H (55%)
        2. Calculer P(score) = 1 - P(0 goals) pour chaque equipe/mi-temps
        3. Multiplier les 4 probabilites independantes
        """
        expected_home_goals = max(0.5, min(4.0, expected_home_goals))
        expected_away_goals = max(0.5, min(4.0, expected_away_goals))

        # xG par mi-temps
        home_xg_ht = expected_home_goals * HT_GOALS_RATIO
        home_xg_2h = expected_home_goals * SECOND_HALF_RATIO
        away_xg_ht = expected_away_goals * HT_GOALS_RATIO
        away_xg_2h = expected_away_goals * SECOND_HALF_RATIO

        # P(score) = 1 - P(0 goals)
        home_score_ht = 1 - self._poisson_zero(home_xg_ht)
        home_score_2h = 1 - self._poisson_zero(home_xg_2h)
        away_score_ht = 1 - self._poisson_zero(away_xg_ht)
        away_score_2h = 1 - self._poisson_zero(away_xg_2h)

        # BTTS Both Halves = tous les 4 evenements
        btts_bh_yes = home_score_ht * away_score_ht * home_score_2h * away_score_2h
        btts_bh_no = 1 - btts_bh_yes

        return BttsBothHalvesAnalysis(
            expected_home_goals=expected_home_goals,
            expected_away_goals=expected_away_goals,
            btts_both_halves_yes=btts_bh_yes,
            btts_both_halves_no=btts_bh_no,
            home_score_ht_prob=home_score_ht,
            away_score_ht_prob=away_score_ht,
            home_score_2h_prob=home_score_2h,
            away_score_2h_prob=away_score_2h,
        )


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_btts_both_halves_calculator() -> BttsBothHalvesCalculator:
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = BttsBothHalvesCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("TEST BTTS BOTH HALVES CALCULATOR")
    print("=" * 70)

    calc = BttsBothHalvesCalculator()

    # Test 1: Match equilibre
    print("\nTest 1: Match equilibre (1.5 vs 1.5)")
    analysis1 = calc.calculate(1.5, 1.5)
    print(analysis1.summary())

    # Test 2: Liverpool vs Man City
    print("\nTest 2: Liverpool vs Man City (1.9 vs 1.9)")
    analysis2 = calc.calculate(1.9, 1.9)
    print(analysis2.summary())

    # Test 3: Match offensif
    print("\nTest 3: Match offensif (2.5 vs 2.0)")
    analysis3 = calc.calculate(2.5, 2.0)
    print(analysis3.summary())

    print("\nTESTS TERMINES")
