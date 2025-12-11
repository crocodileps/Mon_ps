"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    EDGE CALCULATOR - Value Detection                          ║
║                                                                               ║
║  Calcule les edges nets apres taxes de liquidite.                            ║
║  Applique les seuils MIN_EDGE adaptatifs par marche et tier.                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Any
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import MIN_EDGE_BY_MARKET, TIER_EDGE_MULTIPLIER, LIQUIDITY_TAX


class EdgeCalculator:
    """Calcule les edges et filtre les opportunites"""
    
    def __init__(self):
        self.min_edge = MIN_EDGE_BY_MARKET
        self.tier_mult = TIER_EDGE_MULTIPLIER
        self.liquidity_tax = LIQUIDITY_TAX
    
    def calculate_all(
        self,
        probabilities: Dict[str, Dict[str, float]],
        odds: Dict[str, Dict[str, float]],
        tier: str,
        league: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calcule les edges pour tous les marches.
        
        Returns:
            Dict par marche avec edge_brut, edge_net, has_edge, selection
        """
        edges = {}
        
        for market, probs in probabilities.items():
            market_odds = odds.get(market, {})
            if not market_odds:
                continue
            
            # Find best edge in this market
            best_edge = self._find_best_edge(market, probs, market_odds, tier)
            edges[market] = best_edge
        
        return edges
    
    def _find_best_edge(
        self,
        market: str,
        probs: Dict[str, float],
        market_odds: Dict[str, float],
        tier: str
    ) -> Dict[str, Any]:
        """Trouve la meilleure selection dans un marche"""
        
        best = {
            "has_edge": False,
            "selection": None,
            "our_prob": 0,
            "implied_prob": 0,
            "odds": 0,
            "edge_brut": 0,
            "edge_net": 0,
            "confidence": 0,
        }
        
        # Get thresholds
        base_min_edge = self.min_edge.get(market, 0.03)
        tier_multiplier = self.tier_mult.get(tier, 1.0)
        min_edge_required = base_min_edge * tier_multiplier
        
        # Liquidity tax
        market_tax = self.liquidity_tax.get("market", {}).get(market, 0.01)
        tier_tax = self.liquidity_tax.get("tier", {}).get(tier, 0.005)
        total_tax = market_tax + tier_tax
        
        for selection, our_prob in probs.items():
            odds_value = market_odds.get(selection, 0)
            if odds_value <= 1.0:
                continue
            
            # Calculate edge
            implied_prob = 1.0 / odds_value
            edge_brut = our_prob - implied_prob
            edge_net = edge_brut - total_tax
            
            # Confidence based on probability distance from 50%
            confidence = min(1.0, abs(our_prob - 0.5) * 2 + 0.5)
            
            # Check if this is better
            if edge_net > best["edge_net"]:
                has_edge = edge_net >= min_edge_required
                
                best = {
                    "has_edge": has_edge,
                    "selection": selection,
                    "our_prob": our_prob,
                    "implied_prob": implied_prob,
                    "odds": odds_value,
                    "edge_brut": edge_brut,
                    "edge_net": edge_net,
                    "confidence": confidence,
                    "min_edge_required": min_edge_required,
                    "tax_applied": total_tax,
                }
        
        return best
    
    def calculate_single(
        self,
        our_prob: float,
        odds: float,
        market: str,
        tier: str
    ) -> Dict[str, Any]:
        """Calcule l'edge pour une selection unique"""
        
        implied_prob = 1.0 / odds
        edge_brut = our_prob - implied_prob
        
        # Taxes
        market_tax = self.liquidity_tax.get("market", {}).get(market, 0.01)
        tier_tax = self.liquidity_tax.get("tier", {}).get(tier, 0.005)
        edge_net = edge_brut - market_tax - tier_tax
        
        # Threshold
        base_min = self.min_edge.get(market, 0.03)
        tier_mult = self.tier_mult.get(tier, 1.0)
        min_required = base_min * tier_mult
        
        return {
            "edge_brut": edge_brut,
            "edge_net": edge_net,
            "has_edge": edge_net >= min_required,
            "min_required": min_required,
        }
