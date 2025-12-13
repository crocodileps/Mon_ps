"""
AsianHandicapCalculator - Calcul des probabilités Asian Handicap
═══════════════════════════════════════════════════════════════════════════

PRINCIPE ASIAN HANDICAP:
    L'Asian Handicap élimine le nul en donnant un avantage/désavantage.
    
    AH -0.5 Home: L'équipe domicile doit gagner (équivalent 1X2 Home Win)
    AH +0.5 Home: L'équipe domicile ne doit pas perdre (équivalent DC 1X)
    AH -1.0 Home: L'équipe domicile doit gagner par 2+ (push si +1)
    AH +1.0 Home: L'équipe domicile peut perdre par 1 (push si -1)
    AH -1.5 Home: L'équipe domicile doit gagner par 2+
    AH +1.5 Home: L'équipe domicile peut perdre par 1
    AH -2.0 Home: L'équipe domicile doit gagner par 3+ (push si +2)
    AH +2.0 Home: L'équipe domicile peut perdre par 2 (push si -2)

PUSH (Remboursement):
    Pour les handicaps entiers (-1.0, -2.0, etc.), si le résultat après
    handicap est exactement 0, la mise est remboursée (push).

CALCUL VIA POISSON BIVARIÉE:
    On calcule P(Home - Away > handicap) pour chaque ligne.
    Pour les handicaps entiers, on soustrait P(Home - Away = handicap) / 2.

8 MARCHÉS:
    1. AH Home -0.5  (Home doit gagner)
    2. AH Away +0.5  (Away ne doit pas perdre)
    3. AH Home -1.0  (Home doit gagner par 2+, push si +1)
    4. AH Away +1.0  (Away peut perdre par 1, push si -1)
    5. AH Home -1.5  (Home doit gagner par 2+)
    6. AH Away +1.5  (Away peut perdre par 1)
    7. AH Home -2.0  (Home doit gagner par 3+, push si +2)
    8. AH Away +2.0  (Away peut perdre par 2, push si -2)

LIQUIDITY TAX:
    Asian Handicap = 1.5% (très liquide, spreads serrés)

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

# Lignes Asian Handicap supportées
AH_LINES = [-0.5, -1.0, -1.5, -2.0]

# Liquidity tax pour AH (très liquide)
AH_LIQUIDITY_TAX = 0.015

# Min edge pour AH
AH_MIN_EDGE = 0.025

# Max goals pour la matrice Poisson
MAX_GOALS = 8


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AsianHandicapLine:
    """Représente une ligne Asian Handicap."""
    line: float  # Ex: -0.5, -1.0, -1.5, -2.0
    home_prob: float  # P(Home covers the handicap)
    away_prob: float  # P(Away covers the handicap)
    push_prob: float  # P(Push) - 0 pour demi-lignes
    
    @property
    def home_key(self) -> str:
        """Clé pour home."""
        sign = "m" if self.line < 0 else "p"
        return f"ah_home_{sign}{abs(self.line):.1f}".replace(".", "_")
    
    @property
    def away_key(self) -> str:
        """Clé pour away (ligne inverse)."""
        inverse_line = -self.line
        sign = "p" if inverse_line > 0 else "m"
        return f"ah_away_{sign}{abs(inverse_line):.1f}".replace(".", "_")
    
    def __repr__(self) -> str:
        sign = "+" if self.line > 0 else ""
        return f"AH {sign}{self.line}: Home={self.home_prob:.1%}, Away={self.away_prob:.1%}, Push={self.push_prob:.1%}"


@dataclass
class AsianHandicapAnalysis:
    """Analyse complète des marchés Asian Handicap."""
    expected_home_goals: float
    expected_away_goals: float
    
    # Lignes calculées
    lines: Dict[float, AsianHandicapLine] = field(default_factory=dict)
    
    # Probabilités directes pour UnifiedBrain
    ah_home_m05_prob: float = 0.40  # AH -0.5 Home
    ah_away_p05_prob: float = 0.60  # AH +0.5 Away
    ah_home_m10_prob: float = 0.30  # AH -1.0 Home
    ah_away_p10_prob: float = 0.70  # AH +1.0 Away
    ah_home_m15_prob: float = 0.25  # AH -1.5 Home
    ah_away_p15_prob: float = 0.75  # AH +1.5 Away
    ah_home_m20_prob: float = 0.20  # AH -2.0 Home
    ah_away_p20_prob: float = 0.80  # AH +2.0 Away
    
    def summary(self) -> str:
        """Résumé textuel."""
        lines_str = []
        for line_val in sorted(self.lines.keys()):
            line = self.lines[line_val]
            lines_str.append(f"  AH {line_val:+.1f}: Home={line.home_prob:.1%}, Away={line.away_prob:.1%}")
        
        return f"""Asian Handicap Analysis:
  Expected Goals: {self.expected_home_goals:.2f} - {self.expected_away_goals:.2f}
  
{chr(10).join(lines_str)}"""
    
    def to_dict(self) -> Dict[str, float]:
        """Convertit en dictionnaire pour UnifiedBrain."""
        return {
            "ah_home_m05": self.ah_home_m05_prob,
            "ah_away_p05": self.ah_away_p05_prob,
            "ah_home_m10": self.ah_home_m10_prob,
            "ah_away_p10": self.ah_away_p10_prob,
            "ah_home_m15": self.ah_home_m15_prob,
            "ah_away_p15": self.ah_away_p15_prob,
            "ah_home_m20": self.ah_home_m20_prob,
            "ah_away_p20": self.ah_away_p20_prob,
        }


# ═══════════════════════════════════════════════════════════════════════════
# ASIAN HANDICAP CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class AsianHandicapCalculator:
    """
    Calculateur de probabilités Asian Handicap via Poisson Bivariée.
    
    Usage:
        calc = AsianHandicapCalculator()
        analysis = calc.calculate(
            expected_home=1.8,
            expected_away=1.2
        )
        
        print(analysis.summary())
    """
    
    def __init__(self, lines: List[float] = None):
        """
        Initialise le calculateur.
        
        Args:
            lines: Lignes AH à calculer (default: [-0.5, -1.0, -1.5, -2.0])
        """
        self.lines = lines or AH_LINES
    
    @staticmethod
    @lru_cache(maxsize=1000)
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
    
    def _build_score_matrix(
        self,
        expected_home: float,
        expected_away: float,
        max_goals: int = MAX_GOALS
    ) -> Dict[Tuple[int, int], float]:
        """Construit la matrice des probabilités de score."""
        matrix = {}
        
        for home in range(max_goals + 1):
            for away in range(max_goals + 1):
                p_home = self._poisson_pmf(home, expected_home)
                p_away = self._poisson_pmf(away, expected_away)
                matrix[(home, away)] = p_home * p_away
        
        # Normaliser
        total = sum(matrix.values())
        if total > 0:
            for key in matrix:
                matrix[key] /= total
        
        return matrix
    
    def _calculate_ah_line(
        self,
        line: float,
        score_matrix: Dict[Tuple[int, int], float]
    ) -> AsianHandicapLine:
        """Calcule les probabilités pour une ligne AH spécifique."""
        home_wins = 0.0
        away_wins = 0.0
        push = 0.0
        
        is_whole_number = line == int(line)
        
        for (home, away), prob in score_matrix.items():
            margin = home - away
            adjusted_margin = margin + line
            
            if adjusted_margin > 0:
                home_wins += prob
            elif adjusted_margin < 0:
                away_wins += prob
            else:
                if is_whole_number:
                    push += prob
                else:
                    home_wins += prob / 2
                    away_wins += prob / 2
        
        return AsianHandicapLine(
            line=line,
            home_prob=home_wins,
            away_prob=away_wins,
            push_prob=push
        )
    
    def calculate(
        self,
        expected_home: float,
        expected_away: float
    ) -> AsianHandicapAnalysis:
        """Calcule toutes les lignes Asian Handicap."""
        expected_home = max(0.5, min(4.5, expected_home))
        expected_away = max(0.5, min(4.5, expected_away))
        
        matrix = self._build_score_matrix(expected_home, expected_away)
        
        lines = {}
        for line in self.lines:
            lines[line] = self._calculate_ah_line(line, matrix)
        
        analysis = AsianHandicapAnalysis(
            expected_home_goals=expected_home,
            expected_away_goals=expected_away,
            lines=lines
        )
        
        if -0.5 in lines:
            analysis.ah_home_m05_prob = lines[-0.5].home_prob
            analysis.ah_away_p05_prob = lines[-0.5].away_prob
        
        if -1.0 in lines:
            line = lines[-1.0]
            analysis.ah_home_m10_prob = line.home_prob + (line.push_prob / 2)
            analysis.ah_away_p10_prob = line.away_prob + (line.push_prob / 2)
        
        if -1.5 in lines:
            analysis.ah_home_m15_prob = lines[-1.5].home_prob
            analysis.ah_away_p15_prob = lines[-1.5].away_prob
        
        if -2.0 in lines:
            line = lines[-2.0]
            analysis.ah_home_m20_prob = line.home_prob + (line.push_prob / 2)
            analysis.ah_away_p20_prob = line.away_prob + (line.push_prob / 2)
        
        return analysis
    
    def calculate_edges(
        self,
        analysis: AsianHandicapAnalysis,
        market_odds: Dict[str, float]
    ) -> Dict[str, Dict]:
        """Calcule les edges pour les marchés AH."""
        probs = analysis.to_dict()
        edges = {}
        
        for market, probability in probs.items():
            if market in market_odds:
                odds = market_odds[market]
                implied_prob = 1 / odds if odds > 0 else 0
                raw_edge = probability - implied_prob
                edge_after_tax = raw_edge - AH_LIQUIDITY_TAX
                
                kelly = 0.0
                if edge_after_tax > 0 and odds > 1:
                    kelly = edge_after_tax / (odds - 1)
                    kelly = max(0, min(0.08, kelly * 0.5))
                
                edges[market] = {
                    "probability": probability,
                    "fair_odds": 1 / probability if probability > 0 else 999.0,
                    "market_odds": odds,
                    "raw_edge": raw_edge,
                    "edge_after_tax": edge_after_tax,
                    "kelly": kelly,
                    "is_value": edge_after_tax >= AH_MIN_EDGE,
                    "liquidity_tax": AH_LIQUIDITY_TAX,
                    "min_edge_required": AH_MIN_EDGE,
                }
        
        return edges


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_asian_handicap_calculator() -> AsianHandicapCalculator:
    """Retourne l'instance singleton."""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = AsianHandicapCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("🎯 TEST ASIAN HANDICAP CALCULATOR")
    print("=" * 70)
    
    calc = AsianHandicapCalculator()
    
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
    
    # Test 3: Liverpool vs Man City
    print("\n📊 Test 3: Liverpool vs Man City (1.9 vs 1.9)")
    print("-" * 60)
    analysis3 = calc.calculate(1.9, 1.9)
    print(analysis3.summary())
    
    # Test 4: Dict format
    print("\n📋 Test 4: Format Dict pour UnifiedBrain")
    print("-" * 60)
    ah_probs = analysis3.to_dict()
    for key, prob in ah_probs.items():
        print(f"  {key}: {prob:.1%}")
    
    # Test 5: Calcul d'edges
    print("\n💰 Test 5: Calcul d'edges avec cotes marché")
    print("-" * 60)
    
    market_odds = {
        "ah_home_m05": 2.10,
        "ah_away_p05": 1.80,
        "ah_home_m10": 2.50,
        "ah_away_p10": 1.55,
        "ah_home_m15": 3.20,
        "ah_away_p15": 1.35,
        "ah_home_m20": 4.00,
        "ah_away_p20": 1.25,
    }
    
    edges = calc.calculate_edges(analysis3, market_odds)
    
    print(f"Edges calculés:")
    for key, data in sorted(edges.items(), key=lambda x: x[1]["edge_after_tax"], reverse=True):
        status = "✅" if data["is_value"] else "❌"
        print(f"  {status} {key}: prob={data['probability']:.1%}, "
              f"odds={data['market_odds']:.2f}, edge={data['edge_after_tax']:.1%}")
    
    print("\n" + "=" * 70)
    print("✅ TESTS TERMINÉS")
    print("=" * 70)
