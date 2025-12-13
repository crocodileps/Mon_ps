"""
DoubleResultCalculator - Calcul des probabilités HT/FT combinées
═══════════════════════════════════════════════════════════════════════════

PRINCIPE:
    Double Result = Combinaison du résultat mi-temps ET fin de match.
    9 combinaisons possibles (3 HT × 3 FT).

9 MARCHÉS DOUBLE RESULT:
    1. HT Home / FT Home (1/1)
    2. HT Home / FT Draw (1/X)
    3. HT Home / FT Away (1/2)
    4. HT Draw / FT Home (X/1)
    5. HT Draw / FT Draw (X/X)
    6. HT Draw / FT Away (X/2)
    7. HT Away / FT Home (2/1)
    8. HT Away / FT Draw (2/X)
    9. HT Away / FT Away (2/2)

CALCUL:
    Utilise la matrice de transition HT → FT basée sur les statistiques
    football et ajustée par les expected goals.

    P(HT_i, FT_j) = P(HT_i) × P(FT_j | HT_i)

STATISTIQUES DE BASE (Football professionnel):
    - Si HT Home Win → FT Home Win ~75%, Draw ~15%, Away ~10%
    - Si HT Draw → FT Home Win ~40%, Draw ~35%, Away ~25%
    - Si HT Away Win → FT Home Win ~10%, Draw ~20%, Away ~70%

LIQUIDITY TAX:
    Double Result = 3.5% (marché peu liquide, exotique)

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

DOUBLE_RESULT_LIQUIDITY_TAX = 0.035
DOUBLE_RESULT_MIN_EDGE = 0.06

# Matrice de transition HT → FT (statistiques football pro)
# Format: TRANSITION_MATRIX[HT_result][FT_result] = probability
DEFAULT_TRANSITION_MATRIX = {
    "home": {  # Si Home mène à la mi-temps
        "home": 0.75,  # Conserve l'avantage
        "draw": 0.15,  # Se fait rattraper
        "away": 0.10,  # Retournement
    },
    "draw": {  # Si nul à la mi-temps
        "home": 0.40,  # Home prend l'avantage
        "draw": 0.35,  # Reste nul
        "away": 0.25,  # Away prend l'avantage
    },
    "away": {  # Si Away mène à la mi-temps
        "home": 0.10,  # Retournement
        "draw": 0.20,  # Se fait rattraper
        "away": 0.70,  # Conserve l'avantage
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DoubleResultAnalysis:
    """Analyse des marchés Double Result (HT/FT)."""
    # Probabilités HT
    ht_home_prob: float
    ht_draw_prob: float
    ht_away_prob: float

    # Probabilités FT
    ft_home_prob: float
    ft_draw_prob: float
    ft_away_prob: float

    # 9 combinaisons HT/FT
    ht_home_ft_home_prob: float = 0.0  # 1/1
    ht_home_ft_draw_prob: float = 0.0  # 1/X
    ht_home_ft_away_prob: float = 0.0  # 1/2
    ht_draw_ft_home_prob: float = 0.0  # X/1
    ht_draw_ft_draw_prob: float = 0.0  # X/X
    ht_draw_ft_away_prob: float = 0.0  # X/2
    ht_away_ft_home_prob: float = 0.0  # 2/1
    ht_away_ft_draw_prob: float = 0.0  # 2/X
    ht_away_ft_away_prob: float = 0.0  # 2/2

    def summary(self) -> str:
        return f"""Double Result Analysis:
  HT Probs: {self.ht_home_prob:.1%} / {self.ht_draw_prob:.1%} / {self.ht_away_prob:.1%}
  FT Probs: {self.ft_home_prob:.1%} / {self.ft_draw_prob:.1%} / {self.ft_away_prob:.1%}

  1/1 (HT Home, FT Home): {self.ht_home_ft_home_prob:.1%}
  1/X (HT Home, FT Draw): {self.ht_home_ft_draw_prob:.1%}
  1/2 (HT Home, FT Away): {self.ht_home_ft_away_prob:.1%}
  X/1 (HT Draw, FT Home): {self.ht_draw_ft_home_prob:.1%}
  X/X (HT Draw, FT Draw): {self.ht_draw_ft_draw_prob:.1%}
  X/2 (HT Draw, FT Away): {self.ht_draw_ft_away_prob:.1%}
  2/1 (HT Away, FT Home): {self.ht_away_ft_home_prob:.1%}
  2/X (HT Away, FT Draw): {self.ht_away_ft_draw_prob:.1%}
  2/2 (HT Away, FT Away): {self.ht_away_ft_away_prob:.1%}"""

    def to_dict(self) -> Dict[str, float]:
        return {
            "dr_1_1": self.ht_home_ft_home_prob,
            "dr_1_x": self.ht_home_ft_draw_prob,
            "dr_1_2": self.ht_home_ft_away_prob,
            "dr_x_1": self.ht_draw_ft_home_prob,
            "dr_x_x": self.ht_draw_ft_draw_prob,
            "dr_x_2": self.ht_draw_ft_away_prob,
            "dr_2_1": self.ht_away_ft_home_prob,
            "dr_2_x": self.ht_away_ft_draw_prob,
            "dr_2_2": self.ht_away_ft_away_prob,
        }


# ═══════════════════════════════════════════════════════════════════════════
# DOUBLE RESULT CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class DoubleResultCalculator:
    """
    Calculateur de probabilités Double Result (HT/FT).

    Usage:
        calc = DoubleResultCalculator()
        analysis = calc.calculate(
            ht_home=0.30, ht_draw=0.35, ht_away=0.35,
            ft_home=0.40, ft_draw=0.28, ft_away=0.32
        )
        print(analysis.summary())
    """

    def __init__(self, transition_matrix: Dict = None):
        """
        Initialise avec matrice de transition optionnelle.

        Args:
            transition_matrix: Matrice P(FT | HT), utilise défaut si None
        """
        self.transition = transition_matrix or DEFAULT_TRANSITION_MATRIX

    def _adjust_transition_matrix(
        self,
        ft_home: float,
        ft_draw: float,
        ft_away: float
    ) -> Dict[str, Dict[str, float]]:
        """
        Ajuste la matrice de transition pour être cohérente avec les probs FT.

        La matrice de base est ajustée pour que les marginales
        correspondent aux probabilités FT attendues.
        """
        # Pour simplifier, on utilise la matrice de base
        # Une version plus avancée ajusterait via optimisation
        return self.transition

    def calculate(
        self,
        ht_home: float,
        ht_draw: float,
        ht_away: float,
        ft_home: float,
        ft_draw: float,
        ft_away: float
    ) -> DoubleResultAnalysis:
        """
        Calcule les 9 probabilités Double Result.

        Args:
            ht_home: P(Home win at HT)
            ht_draw: P(Draw at HT)
            ht_away: P(Away win at HT)
            ft_home: P(Home win FT)
            ft_draw: P(Draw FT)
            ft_away: P(Away win FT)

        Returns:
            DoubleResultAnalysis avec les 9 probabilités
        """
        # Normaliser les inputs
        total_ht = ht_home + ht_draw + ht_away
        if total_ht > 0:
            ht_home /= total_ht
            ht_draw /= total_ht
            ht_away /= total_ht

        total_ft = ft_home + ft_draw + ft_away
        if total_ft > 0:
            ft_home /= total_ft
            ft_draw /= total_ft
            ft_away /= total_ft

        # Ajuster la matrice de transition
        trans = self._adjust_transition_matrix(ft_home, ft_draw, ft_away)

        # Calculer les 9 combinaisons via P(HT) × P(FT|HT)
        # Mais on doit aussi s'assurer que les marginales FT sont respectées

        # Méthode: Combinaison bayésienne
        # P(HT=i, FT=j) ∝ P(HT=i) × P(FT=j|HT=i) × adjustment_factor

        raw_probs = {}

        # HT Home
        raw_probs["1_1"] = ht_home * trans["home"]["home"]
        raw_probs["1_x"] = ht_home * trans["home"]["draw"]
        raw_probs["1_2"] = ht_home * trans["home"]["away"]

        # HT Draw
        raw_probs["x_1"] = ht_draw * trans["draw"]["home"]
        raw_probs["x_x"] = ht_draw * trans["draw"]["draw"]
        raw_probs["x_2"] = ht_draw * trans["draw"]["away"]

        # HT Away
        raw_probs["2_1"] = ht_away * trans["away"]["home"]
        raw_probs["2_x"] = ht_away * trans["away"]["draw"]
        raw_probs["2_2"] = ht_away * trans["away"]["away"]

        # Normaliser pour que la somme = 1
        total = sum(raw_probs.values())
        if total > 0:
            for key in raw_probs:
                raw_probs[key] /= total

        # Ajuster pour respecter les marginales FT
        # (Algorithme IPFP simplifié - une itération)
        # Calcul des marginales actuelles
        ft_home_actual = raw_probs["1_1"] + raw_probs["x_1"] + raw_probs["2_1"]
        ft_draw_actual = raw_probs["1_x"] + raw_probs["x_x"] + raw_probs["2_x"]
        ft_away_actual = raw_probs["1_2"] + raw_probs["x_2"] + raw_probs["2_2"]

        # Ajuster (si écart significatif)
        if ft_home_actual > 0.01:
            factor = ft_home / ft_home_actual
            raw_probs["1_1"] *= factor
            raw_probs["x_1"] *= factor
            raw_probs["2_1"] *= factor

        if ft_draw_actual > 0.01:
            factor = ft_draw / ft_draw_actual
            raw_probs["1_x"] *= factor
            raw_probs["x_x"] *= factor
            raw_probs["2_x"] *= factor

        if ft_away_actual > 0.01:
            factor = ft_away / ft_away_actual
            raw_probs["1_2"] *= factor
            raw_probs["x_2"] *= factor
            raw_probs["2_2"] *= factor

        # Re-normaliser
        total = sum(raw_probs.values())
        if total > 0:
            for key in raw_probs:
                raw_probs[key] /= total

        return DoubleResultAnalysis(
            ht_home_prob=ht_home,
            ht_draw_prob=ht_draw,
            ht_away_prob=ht_away,
            ft_home_prob=ft_home,
            ft_draw_prob=ft_draw,
            ft_away_prob=ft_away,
            ht_home_ft_home_prob=raw_probs["1_1"],
            ht_home_ft_draw_prob=raw_probs["1_x"],
            ht_home_ft_away_prob=raw_probs["1_2"],
            ht_draw_ft_home_prob=raw_probs["x_1"],
            ht_draw_ft_draw_prob=raw_probs["x_x"],
            ht_draw_ft_away_prob=raw_probs["x_2"],
            ht_away_ft_home_prob=raw_probs["2_1"],
            ht_away_ft_draw_prob=raw_probs["2_x"],
            ht_away_ft_away_prob=raw_probs["2_2"],
        )


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_double_result_calculator() -> DoubleResultCalculator:
    """Retourne l'instance singleton."""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = DoubleResultCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("TEST DOUBLE RESULT CALCULATOR")
    print("=" * 70)

    calc = DoubleResultCalculator()

    # Test 1: Match équilibré
    print("\nTest 1: Match equilibre")
    print("-" * 60)
    analysis = calc.calculate(
        ht_home=0.30, ht_draw=0.40, ht_away=0.30,
        ft_home=0.35, ft_draw=0.30, ft_away=0.35
    )
    print(analysis.summary())

    # Test 2: Liverpool vs Man City
    print("\nTest 2: Liverpool vs Man City")
    print("-" * 60)
    analysis2 = calc.calculate(
        ht_home=0.31, ht_draw=0.33, ht_away=0.36,
        ft_home=0.38, ft_draw=0.25, ft_away=0.37
    )
    print(analysis2.summary())

    # Test 3: Favoris clair
    print("\nTest 3: Favoris clair (Bayern vs petit club)")
    print("-" * 60)
    analysis3 = calc.calculate(
        ht_home=0.55, ht_draw=0.30, ht_away=0.15,
        ft_home=0.75, ft_draw=0.15, ft_away=0.10
    )
    print(analysis3.summary())

    # Test 4: Dict format
    print("\nTest 4: Format Dict")
    print("-" * 60)
    dr_probs = analysis2.to_dict()
    for key, prob in dr_probs.items():
        print(f"  {key}: {prob:.1%}")

    print("\n" + "=" * 70)
    print("TESTS TERMINES")
    print("=" * 70)
