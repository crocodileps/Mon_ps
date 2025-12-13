"""
CorrectScoreCalculator - Prédiction de scores exacts via Poisson Bivariée
═══════════════════════════════════════════════════════════════════════════

PRINCIPE:
    Utilise la distribution de Poisson indépendante pour home et away goals.
    P(Home=h, Away=a) = P(Home=h) × P(Away=a)
    
    Avec ajustement de corrélation pour les scores nuls (0-0).

TOP 10 SCORES (typiques):
    1-1, 1-0, 2-1, 0-0, 2-0, 1-2, 0-1, 2-2, 3-1, 0-2

LIQUIDITY TAX:
    Correct Score = 5% (marché peu liquide, spreads larges)

Auteur: Mon_PS Quant Team
Version: 1.0.0
Date: 13 Décembre 2025
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from functools import lru_cache


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Scores à calculer (matrice 7x7 pour couvrir 0-6 goals)
MAX_GOALS = 7

# Top N scores à retourner
TOP_SCORES_COUNT = 10

# Liquidity tax pour Correct Score (marché peu liquide)
CORRECT_SCORE_LIQUIDITY_TAX = 0.05

# Min edge pour Correct Score (seuil élevé car variance haute)
CORRECT_SCORE_MIN_EDGE = 0.12


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ScorePrediction:
    """Prédiction pour un score exact."""
    home_goals: int
    away_goals: int
    probability: float
    fair_odds: float
    rank: int = 0
    
    @property
    def score_str(self) -> str:
        """Retourne le score sous forme de string."""
        return f"{self.home_goals}-{self.away_goals}"
    
    @property
    def market_key(self) -> str:
        """Retourne la clé de marché."""
        return f"cs_{self.home_goals}_{self.away_goals}"
    
    def __repr__(self) -> str:
        return f"ScorePrediction({self.score_str}: {self.probability:.1%}, odds={self.fair_odds:.2f})"


@dataclass
class CorrectScoreAnalysis:
    """Analyse complète des scores exacts."""
    expected_home_goals: float
    expected_away_goals: float
    
    # Matrice complète des probabilités
    score_matrix: Dict[Tuple[int, int], float] = field(default_factory=dict)
    
    # Top 10 scores
    top_scores: List[ScorePrediction] = field(default_factory=list)
    
    # Probabilités agrégées
    home_win_prob: float = 0.0
    draw_prob: float = 0.0
    away_win_prob: float = 0.0
    
    # Scores spéciaux
    nil_nil_prob: float = 0.0  # 0-0
    one_one_prob: float = 0.0  # 1-1
    both_score_prob: float = 0.0
    
    def get_score_prob(self, home: int, away: int) -> float:
        """Retourne la probabilité d'un score spécifique."""
        return self.score_matrix.get((home, away), 0.0)
    
    def get_top_n(self, n: int = 10) -> List[ScorePrediction]:
        """Retourne les top N scores."""
        return self.top_scores[:n]
    
    def summary(self) -> str:
        """Résumé textuel."""
        lines = [
            f"Expected: {self.expected_home_goals:.2f} - {self.expected_away_goals:.2f}",
            f"1X2 from CS: {self.home_win_prob:.1%} / {self.draw_prob:.1%} / {self.away_win_prob:.1%}",
            f"0-0: {self.nil_nil_prob:.1%}",
            f"1-1: {self.one_one_prob:.1%}",
            f"BTTS: {self.both_score_prob:.1%}",
            "",
            "Top 10 Scores:",
        ]
        for pred in self.top_scores[:10]:
            lines.append(f"  {pred.rank}. {pred.score_str}: {pred.probability:.1%} (fair odds: {pred.fair_odds:.2f})")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# CORRECT SCORE CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class CorrectScoreCalculator:
    """
    Calculateur de scores exacts via Poisson Bivariée.
    
    Usage:
        calc = CorrectScoreCalculator()
        analysis = calc.calculate(expected_home=1.8, expected_away=1.2)
        
        print(analysis.summary())
        top_10 = analysis.get_top_n(10)
    """
    
    def __init__(self, correlation_factor: float = 0.05):
        """
        Initialise le calculateur.
        
        Args:
            correlation_factor: Ajustement de corrélation pour 0-0 et scores élevés.
                               Positif = plus de 0-0, négatif = moins de 0-0.
        """
        self.correlation_factor = correlation_factor
    
    @staticmethod
    @lru_cache(maxsize=1000)
    def _poisson_pmf(k: int, lam: float) -> float:
        """
        Probabilité P(X = k) pour Poisson(lambda).
        
        Cached pour performance.
        """
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        if k < 0:
            return 0.0
        
        # Éviter overflow pour grands k
        if k > 20:
            return 0.0
        
        try:
            return (lam ** k) * math.exp(-lam) / math.factorial(k)
        except (OverflowError, ValueError):
            return 0.0
    
    def calculate(
        self,
        expected_home: float,
        expected_away: float,
        max_goals: int = MAX_GOALS
    ) -> CorrectScoreAnalysis:
        """
        Calcule la matrice complète des scores et le top 10.
        
        Args:
            expected_home: Expected goals pour l'équipe à domicile
            expected_away: Expected goals pour l'équipe à l'extérieur
            max_goals: Maximum de buts à considérer par équipe
            
        Returns:
            CorrectScoreAnalysis avec tous les résultats
        """
        # Borner les expected goals
        expected_home = max(0.3, min(5.0, expected_home))
        expected_away = max(0.3, min(5.0, expected_away))
        
        # Créer l'analyse
        analysis = CorrectScoreAnalysis(
            expected_home_goals=expected_home,
            expected_away_goals=expected_away
        )
        
        # Calculer la matrice des probabilités
        all_scores = []
        
        for home in range(max_goals):
            for away in range(max_goals):
                # Probabilité de base (Poisson indépendant)
                prob_home = self._poisson_pmf(home, expected_home)
                prob_away = self._poisson_pmf(away, expected_away)
                prob = prob_home * prob_away
                
                # Ajustement de corrélation
                if home == 0 and away == 0:
                    # 0-0 légèrement plus probable (défenses concentrées)
                    prob *= (1 + self.correlation_factor)
                elif home > 3 or away > 3:
                    # Scores élevés légèrement moins probables
                    prob *= (1 - self.correlation_factor * 0.5)
                
                # Stocker
                analysis.score_matrix[(home, away)] = prob
                
                if prob > 0.001:  # Seuil minimum
                    all_scores.append(ScorePrediction(
                        home_goals=home,
                        away_goals=away,
                        probability=prob,
                        fair_odds=1/prob if prob > 0 else 999.0
                    ))
        
        # Normaliser pour que la somme = 1
        total_prob = sum(analysis.score_matrix.values())
        if total_prob > 0:
            for key in analysis.score_matrix:
                analysis.score_matrix[key] /= total_prob
            
            for pred in all_scores:
                pred.probability /= total_prob
                pred.fair_odds = 1 / pred.probability if pred.probability > 0 else 999.0
        
        # Trier et prendre le top N
        all_scores.sort(key=lambda x: x.probability, reverse=True)
        for i, pred in enumerate(all_scores[:TOP_SCORES_COUNT]):
            pred.rank = i + 1
        
        analysis.top_scores = all_scores[:TOP_SCORES_COUNT]
        
        # Calculer les agrégats
        analysis.home_win_prob = sum(
            prob for (h, a), prob in analysis.score_matrix.items() if h > a
        )
        analysis.draw_prob = sum(
            prob for (h, a), prob in analysis.score_matrix.items() if h == a
        )
        analysis.away_win_prob = sum(
            prob for (h, a), prob in analysis.score_matrix.items() if h < a
        )
        
        analysis.nil_nil_prob = analysis.score_matrix.get((0, 0), 0.0)
        analysis.one_one_prob = analysis.score_matrix.get((1, 1), 0.0)
        analysis.both_score_prob = sum(
            prob for (h, a), prob in analysis.score_matrix.items() if h > 0 and a > 0
        )
        
        return analysis
    
    def get_top_scores_dict(
        self,
        expected_home: float,
        expected_away: float,
        n: int = 10
    ) -> Dict[str, float]:
        """
        Retourne un dictionnaire des top N scores avec leurs probabilités.
        
        Format compatible avec UnifiedBrain.
        """
        analysis = self.calculate(expected_home, expected_away)
        
        return {
            pred.market_key: pred.probability
            for pred in analysis.top_scores[:n]
        }
    
    def calculate_edge(
        self,
        expected_home: float,
        expected_away: float,
        market_odds: Dict[str, float]
    ) -> Dict[str, Dict]:
        """
        Calcule les edges pour les marchés de score exact.
        
        Args:
            expected_home: Expected goals home
            expected_away: Expected goals away
            market_odds: Dict avec clés comme "cs_1_0", "cs_2_1", etc.
            
        Returns:
            Dict avec edges par score
        """
        analysis = self.calculate(expected_home, expected_away)
        edges = {}
        
        for pred in analysis.top_scores:
            odds_key = pred.market_key
            
            if odds_key in market_odds:
                odds = market_odds[odds_key]
                implied_prob = 1 / odds if odds > 0 else 0
                raw_edge = pred.probability - implied_prob
                edge_after_tax = raw_edge - CORRECT_SCORE_LIQUIDITY_TAX
                
                # Kelly (très conservateur pour CS)
                kelly = 0.0
                if edge_after_tax > 0 and odds > 1:
                    kelly = edge_after_tax / (odds - 1)
                    kelly = max(0, min(0.02, kelly * 0.25))  # Quarter Kelly, cap 2%
                
                edges[odds_key] = {
                    "score": pred.score_str,
                    "probability": pred.probability,
                    "fair_odds": pred.fair_odds,
                    "market_odds": odds,
                    "raw_edge": raw_edge,
                    "edge_after_tax": edge_after_tax,
                    "kelly": kelly,
                    "is_value": edge_after_tax >= CORRECT_SCORE_MIN_EDGE,
                    "min_edge_required": CORRECT_SCORE_MIN_EDGE,
                }
        
        return edges


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_correct_score_calculator() -> CorrectScoreCalculator:
    """Retourne l'instance singleton."""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = CorrectScoreCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("⚽ TEST CORRECT SCORE CALCULATOR")
    print("=" * 70)
    
    calc = CorrectScoreCalculator()
    
    # Test 1: Match équilibré
    print("\n📊 Test 1: Match équilibré (1.5 vs 1.5)")
    print("-" * 60)
    analysis = calc.calculate(1.5, 1.5)
    print(analysis.summary())
    
    # Test 2: Favoris domicile
    print("\n📊 Test 2: Favoris domicile (2.0 vs 1.0)")
    print("-" * 60)
    analysis2 = calc.calculate(2.0, 1.0)
    print(analysis2.summary())
    
    # Test 3: Match à buts (Liverpool vs Man City)
    print("\n📊 Test 3: Liverpool vs Man City (1.9 vs 1.9)")
    print("-" * 60)
    analysis3 = calc.calculate(1.9, 1.9)
    print(analysis3.summary())
    
    # Test 4: Calcul d'edges
    print("\n💰 Test 4: Calcul d'edges avec cotes marché")
    print("-" * 60)
    
    market_odds = {
        "cs_1_1": 6.50,
        "cs_1_0": 7.00,
        "cs_2_1": 8.00,
        "cs_0_0": 10.00,
        "cs_2_0": 9.00,
        "cs_1_2": 9.50,
        "cs_0_1": 8.50,
        "cs_2_2": 12.00,
        "cs_3_1": 15.00,
        "cs_0_2": 12.00,
    }
    
    edges = calc.calculate_edge(1.9, 1.9, market_odds)
    
    print(f"Edges calculés: {len(edges)}")
    for key, data in sorted(edges.items(), key=lambda x: x[1]["edge_after_tax"], reverse=True):
        status = "✅" if data["is_value"] else "❌"
        print(f"  {status} {data['score']}: prob={data['probability']:.1%}, "
              f"odds={data['market_odds']:.2f}, edge={data['edge_after_tax']:.1%}, "
              f"kelly={data['kelly']:.2%}")
    
    # Test 5: Dict format pour UnifiedBrain
    print("\n📋 Test 5: Format Dict pour UnifiedBrain")
    print("-" * 60)
    
    scores_dict = calc.get_top_scores_dict(1.9, 1.9, n=10)
    for key, prob in scores_dict.items():
        print(f"  {key}: {prob:.1%}")
    
    print("\n" + "=" * 70)
    print("✅ TESTS TERMINÉS")
    print("=" * 70)
