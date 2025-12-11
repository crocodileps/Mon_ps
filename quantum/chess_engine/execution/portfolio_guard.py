"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    PORTFOLIO GUARD - Risk Management                          ║
║                                                                               ║
║  Gere les limites d'exposition:                                              ║
║  - Max 5% par match                                                          ║
║  - Max 3 marches correles par match                                          ║
║  - Pas de limite par ligue (tant que ca marche)                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import PORTFOLIO_CONFIG


class PortfolioGuard:
    """Valide et ajuste les signaux selon les regles de portfolio"""
    
    def __init__(self):
        self.config = PORTFOLIO_CONFIG
        self.active_bets = {}  # match_id -> list of signals
    
    def validate(
        self,
        signals: List[Any],
        match_id: str
    ) -> List[Any]:
        """
        Valide les signaux contre les regles de portfolio.
        
        Args:
            signals: Liste de BetSignal
            match_id: ID du match
        
        Returns:
            Liste filtree de signaux valides
        """
        if not signals:
            return []
        
        max_per_match = self.config.get("max_exposure_per_match", 0.05)
        max_correlated = self.config.get("max_correlated_bets", 3)
        
        # Sort by edge (best first)
        sorted_signals = sorted(
            signals,
            key=lambda s: s.edge_net if hasattr(s, 'edge_net') else 0,
            reverse=True
        )
        
        # Apply limits
        validated = []
        total_stake = 0.0
        
        for signal in sorted_signals:
            # Check correlated limit
            if len(validated) >= max_correlated:
                break
            
            # Check exposure limit
            stake = signal.stake_pct if hasattr(signal, 'stake_pct') else 0.01
            if total_stake + stake > max_per_match:
                # Reduce stake to fit
                remaining = max_per_match - total_stake
                if remaining > 0.005:  # Min viable stake
                    signal.stake_pct = remaining
                    validated.append(signal)
                    total_stake += remaining
                break
            
            validated.append(signal)
            total_stake += stake
        
        return validated
    
    def check_daily_exposure(self, league: str = None) -> Dict[str, float]:
        """Verifie l'exposition journaliere"""
        # Pour l'instant, pas de limite par ligue
        return {
            "total_exposure": sum(
                sum(s.stake_pct for s in signals)
                for signals in self.active_bets.values()
            ),
            "matches_count": len(self.active_bets),
        }
    
    def add_executed(self, match_id: str, signals: List[Any]):
        """Enregistre les paris executes"""
        self.active_bets[match_id] = signals
    
    def clear_settled(self, match_id: str):
        """Supprime un match regle"""
        if match_id in self.active_bets:
            del self.active_bets[match_id]
