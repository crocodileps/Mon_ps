"""
HalfTimeCalculator - Prédiction des marchés mi-temps
═══════════════════════════════════════════════════════════════════════════

PRINCIPE:
    Statistiquement, environ 45% des buts sont marqués en première mi-temps.
    
    Expected HT Goals = Expected FT Goals × 0.45
    
    Ajustements basés sur:
    - Style de jeu (équipes offensives = plus de buts HT)
    - Domicile/Extérieur (home = légèrement plus actif HT)
    - Profil tactique (pressing haut = plus de buts tôt)

6 MARCHÉS HALF-TIME:
    1. HT Home Win (1)
    2. HT Draw (X)
    3. HT Away Win (2)
    4. HT Over 0.5 Goals
    5. HT Under 0.5 Goals
    6. HT BTTS (Both Teams To Score at Half-Time)

LIQUIDITY TAX:
    HT Markets = 2.5% (moins liquide que FT)

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

# Ratio moyen de buts en 1ère mi-temps (statistique football mondial)
HT_GOALS_RATIO = 0.45

# Ajustements par profil tactique
TACTICAL_HT_ADJUSTMENTS = {
    "HIGH_PRESS": 0.05,      # Pressing haut = plus de buts tôt
    "COUNTER": -0.03,        # Contre-attaque = attend les espaces
    "POSSESSION": 0.02,      # Possession = construit progressivement
    "DIRECT": 0.04,          # Jeu direct = actions rapides
    "DEFENSIVE": -0.05,      # Défensif = ferme le jeu
    "TRANSITION": 0.03,      # Transition rapide
    "WIDE_ATTACK": 0.02,     # Attaque latérale
    "UNKNOWN": 0.0,
}

# Liquidity tax pour HT markets
HT_LIQUIDITY_TAX = 0.025

# Min edge pour HT markets
HT_MIN_EDGE = 0.04


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class HalfTimeAnalysis:
    """Analyse complète des marchés mi-temps."""
    # Expected values
    expected_ht_goals: float
    expected_home_ht_goals: float
    expected_away_ht_goals: float
    
    # HT 1X2 Probabilities
    ht_home_win_prob: float = 0.25
    ht_draw_prob: float = 0.50
    ht_away_win_prob: float = 0.25
    
    # HT Over/Under 0.5
    ht_over_05_prob: float = 0.55
    ht_under_05_prob: float = 0.45
    
    # HT BTTS
    ht_btts_prob: float = 0.20
    ht_btts_no_prob: float = 0.80
    
    def summary(self) -> str:
        """Résumé textuel."""
        return f"""Half-Time Analysis:
  Expected HT Goals: {self.expected_ht_goals:.2f} (Home: {self.expected_home_ht_goals:.2f}, Away: {self.expected_away_ht_goals:.2f})
  
  HT 1X2: {self.ht_home_win_prob:.1%} / {self.ht_draw_prob:.1%} / {self.ht_away_win_prob:.1%}
  HT Over 0.5: {self.ht_over_05_prob:.1%}
  HT Under 0.5: {self.ht_under_05_prob:.1%}
  HT BTTS: {self.ht_btts_prob:.1%}"""
    
    def to_dict(self) -> Dict[str, float]:
        """Convertit en dictionnaire de probabilités."""
        return {
            "ht_home_win": self.ht_home_win_prob,
            "ht_draw": self.ht_draw_prob,
            "ht_away_win": self.ht_away_win_prob,
            "ht_over_05": self.ht_over_05_prob,
            "ht_under_05": self.ht_under_05_prob,
            "ht_btts": self.ht_btts_prob,
        }


# ═══════════════════════════════════════════════════════════════════════════
# HALF TIME CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class HalfTimeCalculator:
    """
    Calculateur de probabilités mi-temps.
    
    Usage:
        calc = HalfTimeCalculator()
        analysis = calc.calculate(
            expected_goals=2.5,
            home_win_prob=0.45,
            draw_prob=0.28,
            away_win_prob=0.27,
            home_profile="HIGH_PRESS",
            away_profile="COUNTER"
        )
        
        print(analysis.summary())
    """
    
    def __init__(self, ht_ratio: float = HT_GOALS_RATIO):
        """
        Initialise le calculateur.
        
        Args:
            ht_ratio: Ratio de buts marqués en 1ère mi-temps (default 0.45)
        """
        self.ht_ratio = ht_ratio
    
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
    
    @staticmethod
    @lru_cache(maxsize=500)
    def _poisson_cdf(k: int, lam: float) -> float:
        """Probabilité P(X <= k) pour Poisson(lambda)."""
        if lam <= 0:
            return 1.0
        cdf = 0.0
        for i in range(k + 1):
            cdf += HalfTimeCalculator._poisson_pmf(i, lam)
        return min(1.0, cdf)
    
    def _get_tactical_adjustment(self, home_profile: str, away_profile: str) -> float:
        """
        Calcule l'ajustement tactique pour le ratio HT.
        
        Équipes avec pressing haut = plus de buts en 1ère mi-temps.
        """
        home_adj = TACTICAL_HT_ADJUSTMENTS.get(home_profile.upper(), 0.0)
        away_adj = TACTICAL_HT_ADJUSTMENTS.get(away_profile.upper(), 0.0)
        
        # Moyenne des ajustements
        return (home_adj + away_adj) / 2
    
    def calculate(
        self,
        expected_goals: float,
        home_win_prob: float,
        draw_prob: float,
        away_win_prob: float,
        expected_home_goals: Optional[float] = None,
        expected_away_goals: Optional[float] = None,
        home_profile: str = "UNKNOWN",
        away_profile: str = "UNKNOWN",
        btts_prob: float = 0.50
    ) -> HalfTimeAnalysis:
        """
        Calcule les probabilités HT.
        
        Args:
            expected_goals: Expected total goals (FT)
            home_win_prob: Probabilité victoire domicile (FT)
            draw_prob: Probabilité nul (FT)
            away_win_prob: Probabilité victoire extérieur (FT)
            expected_home_goals: Expected goals équipe domicile (optionnel)
            expected_away_goals: Expected goals équipe extérieur (optionnel)
            home_profile: Profil tactique équipe domicile
            away_profile: Profil tactique équipe extérieur
            btts_prob: Probabilité BTTS (FT)
            
        Returns:
            HalfTimeAnalysis avec toutes les probabilités
        """
        # Borner expected_goals
        expected_goals = max(1.0, min(5.0, expected_goals))
        
        # Calculer l'ajustement tactique
        tactical_adj = self._get_tactical_adjustment(home_profile, away_profile)
        adjusted_ratio = self.ht_ratio + tactical_adj
        adjusted_ratio = max(0.35, min(0.55, adjusted_ratio))  # Borner entre 35% et 55%
        
        # Expected HT goals
        expected_ht_goals = expected_goals * adjusted_ratio
        
        # Si expected home/away non fournis, estimer depuis FT probs
        if expected_home_goals is None or expected_away_goals is None:
            # Estimation basée sur les probabilités FT
            home_strength = home_win_prob / (home_win_prob + away_win_prob) if (home_win_prob + away_win_prob) > 0 else 0.5
            expected_home_goals = expected_goals * (0.5 + (home_strength - 0.5) * 0.5)
            expected_away_goals = expected_goals - expected_home_goals
        
        # Expected HT goals par équipe
        expected_home_ht = expected_home_goals * adjusted_ratio
        expected_away_ht = expected_away_goals * adjusted_ratio
        
        # ─────────────────────────────────────────────────────────────────────
        # HT 1X2
        # ─────────────────────────────────────────────────────────────────────
        # Le nul à la mi-temps est BEAUCOUP plus fréquent (0-0 est commun)
        # Statistiquement: ~35-45% des matchs sont 0-0 à la mi-temps
        
        # Calculer P(0-0 at HT) via Poisson
        p_home_0_ht = self._poisson_pmf(0, expected_home_ht)
        p_away_0_ht = self._poisson_pmf(0, expected_away_ht)
        p_0_0_ht = p_home_0_ht * p_away_0_ht
        
        # Calculer P(Home > Away at HT) et P(Away > Home at HT)
        ht_home_win = 0.0
        ht_draw = 0.0
        ht_away_win = 0.0
        
        # Matrice des scores HT (0-4 goals max par équipe)
        for home in range(5):
            for away in range(5):
                p_home = self._poisson_pmf(home, expected_home_ht)
                p_away = self._poisson_pmf(away, expected_away_ht)
                p_score = p_home * p_away
                
                if home > away:
                    ht_home_win += p_score
                elif home == away:
                    ht_draw += p_score
                else:
                    ht_away_win += p_score
        
        # Normaliser
        total = ht_home_win + ht_draw + ht_away_win
        if total > 0:
            ht_home_win /= total
            ht_draw /= total
            ht_away_win /= total
        
        # ─────────────────────────────────────────────────────────────────────
        # HT Over/Under 0.5
        # ─────────────────────────────────────────────────────────────────────
        # P(Total HT = 0) = P(Home=0) × P(Away=0)
        ht_under_05 = p_0_0_ht
        ht_over_05 = 1 - ht_under_05
        
        # ─────────────────────────────────────────────────────────────────────
        # HT BTTS
        # ─────────────────────────────────────────────────────────────────────
        # P(Both Score at HT) = P(Home >= 1) × P(Away >= 1)
        p_home_scores_ht = 1 - p_home_0_ht
        p_away_scores_ht = 1 - p_away_0_ht
        ht_btts = p_home_scores_ht * p_away_scores_ht
        
        # Créer l'analyse
        return HalfTimeAnalysis(
            expected_ht_goals=expected_ht_goals,
            expected_home_ht_goals=expected_home_ht,
            expected_away_ht_goals=expected_away_ht,
            ht_home_win_prob=ht_home_win,
            ht_draw_prob=ht_draw,
            ht_away_win_prob=ht_away_win,
            ht_over_05_prob=ht_over_05,
            ht_under_05_prob=ht_under_05,
            ht_btts_prob=ht_btts,
            ht_btts_no_prob=1 - ht_btts,
        )
    
    def calculate_edges(
        self,
        analysis: HalfTimeAnalysis,
        market_odds: Dict[str, float]
    ) -> Dict[str, Dict]:
        """
        Calcule les edges pour les marchés HT.
        
        Args:
            analysis: HalfTimeAnalysis
            market_odds: Cotes marché (ex: {"ht_home_win": 3.50, "ht_draw": 2.10, ...})
            
        Returns:
            Dict avec edges par marché
        """
        probs = analysis.to_dict()
        edges = {}
        
        for market, probability in probs.items():
            if market in market_odds:
                odds = market_odds[market]
                implied_prob = 1 / odds if odds > 0 else 0
                raw_edge = probability - implied_prob
                edge_after_tax = raw_edge - HT_LIQUIDITY_TAX
                
                # Kelly (conservateur pour HT)
                kelly = 0.0
                if edge_after_tax > 0 and odds > 1:
                    kelly = edge_after_tax / (odds - 1)
                    kelly = max(0, min(0.05, kelly * 0.5))  # Half Kelly, cap 5%
                
                edges[market] = {
                    "probability": probability,
                    "fair_odds": 1 / probability if probability > 0 else 999.0,
                    "market_odds": odds,
                    "raw_edge": raw_edge,
                    "edge_after_tax": edge_after_tax,
                    "kelly": kelly,
                    "is_value": edge_after_tax >= HT_MIN_EDGE,
                    "liquidity_tax": HT_LIQUIDITY_TAX,
                    "min_edge_required": HT_MIN_EDGE,
                }
        
        return edges


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_half_time_calculator() -> HalfTimeCalculator:
    """Retourne l'instance singleton."""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = HalfTimeCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("⏱️  TEST HALF-TIME CALCULATOR")
    print("=" * 70)
    
    calc = HalfTimeCalculator()
    
    # Test 1: Match équilibré
    print("\n📊 Test 1: Match équilibré (xG=2.5, 40/30/30)")
    print("-" * 60)
    analysis = calc.calculate(
        expected_goals=2.5,
        home_win_prob=0.40,
        draw_prob=0.30,
        away_win_prob=0.30
    )
    print(analysis.summary())
    
    # Test 2: Liverpool vs Man City (High Press vs Wide Attack)
    print("\n📊 Test 2: Liverpool vs Man City (xG=3.7, HIGH_PRESS vs WIDE_ATTACK)")
    print("-" * 60)
    analysis2 = calc.calculate(
        expected_goals=3.7,
        home_win_prob=0.38,
        draw_prob=0.25,
        away_win_prob=0.37,
        home_profile="HIGH_PRESS",
        away_profile="WIDE_ATTACK"
    )
    print(analysis2.summary())
    
    # Test 3: Match défensif (Burnley vs Crystal Palace)
    print("\n📊 Test 3: Match défensif (xG=2.0, DEFENSIVE vs COUNTER)")
    print("-" * 60)
    analysis3 = calc.calculate(
        expected_goals=2.0,
        home_win_prob=0.35,
        draw_prob=0.32,
        away_win_prob=0.33,
        home_profile="DEFENSIVE",
        away_profile="COUNTER"
    )
    print(analysis3.summary())
    
    # Test 4: Calcul d'edges
    print("\n💰 Test 4: Calcul d'edges avec cotes marché")
    print("-" * 60)
    
    market_odds = {
        "ht_home_win": 3.50,
        "ht_draw": 2.10,
        "ht_away_win": 4.00,
        "ht_over_05": 1.45,
        "ht_under_05": 2.75,
        "ht_btts": 5.50,
    }
    
    edges = calc.calculate_edges(analysis2, market_odds)
    
    print(f"Edges calculés (Liverpool vs Man City):")
    for key, data in sorted(edges.items(), key=lambda x: x[1]["edge_after_tax"], reverse=True):
        status = "✅" if data["is_value"] else "❌"
        print(f"  {status} {key}: prob={data['probability']:.1%}, "
              f"odds={data['market_odds']:.2f}, edge={data['edge_after_tax']:.1%}, "
              f"kelly={data['kelly']:.2%}")
    
    print("\n" + "=" * 70)
    print("✅ TESTS TERMINÉS")
    print("=" * 70)
