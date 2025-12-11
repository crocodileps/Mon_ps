"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    KELLY SIZER - Stake Calculation                            ║
║                                                                               ║
║  Calcule la taille de mise optimale avec Kelly dynamique.                    ║
║  Philosophie: Plus de stake sur haute confiance + basses cotes.              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Any
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import KELLY_CONFIG


class KellySizer:
    """Calcule les mises avec Kelly dynamique"""
    
    def __init__(self):
        self.config = KELLY_CONFIG
    
    def calculate(
        self,
        edge: float,
        odds: float,
        confidence: float,
        tier: str
    ) -> Dict[str, Any]:
        """
        Calcule la mise optimale.
        
        Args:
            edge: Edge net (notre prob - implied prob - taxes)
            odds: Cote decimale
            confidence: Score de confiance (0-1)
            tier: Tier de l'equipe (ELITE, GOLD, SILVER, STANDARD)
        
        Returns:
            Dict avec kelly_fraction, stake_pct, reasoning
        """
        
        # Kelly full
        if odds <= 1.0 or edge <= 0:
            return self._zero_stake("Invalid odds or negative edge")
        
        kelly_full = edge / (odds - 1)
        
        # Base Kelly fraction
        base_kelly = self.config.get("base_fraction", 0.25)
        kelly_fraction = kelly_full * base_kelly
        
        # ═══════════════════════════════════════════════════════════════════════
        # MULTIPLICATEURS DYNAMIQUES
        # ═══════════════════════════════════════════════════════════════════════
        
        # Confidence multiplier
        if confidence >= 0.80:
            confidence_mult = 1.5
        elif confidence >= 0.65:
            confidence_mult = 1.2
        elif confidence >= 0.50:
            confidence_mult = 1.0
        else:
            confidence_mult = 0.7
        
        # Odds multiplier (prefer low odds = higher probability)
        if odds < 1.50:
            odds_mult = 1.4
        elif odds < 1.80:
            odds_mult = 1.2
        elif odds < 2.20:
            odds_mult = 1.0
        elif odds < 2.80:
            odds_mult = 0.8
        else:
            odds_mult = 0.6
        
        # Tier multiplier
        tier_multipliers = self.config.get("tier_multipliers", {})
        tier_mult = tier_multipliers.get(tier, 1.0)
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAKE FINAL
        # ═══════════════════════════════════════════════════════════════════════
        
        stake_pct = kelly_fraction * confidence_mult * odds_mult * tier_mult
        
        # Caps
        max_stake = self.config.get("max_stake_pct", 0.05)
        min_stake = self.config.get("min_stake_pct", 0.005)
        
        stake_pct = max(min_stake, min(max_stake, stake_pct))
        
        return {
            "kelly_full": kelly_full,
            "kelly_fraction": kelly_fraction,
            "confidence_mult": confidence_mult,
            "odds_mult": odds_mult,
            "tier_mult": tier_mult,
            "stake_pct": stake_pct,
            "stake_pct_display": f"{stake_pct*100:.2f}%",
            "reasoning": f"Kelly={kelly_full:.3f} × base={base_kelly} × conf={confidence_mult} × odds={odds_mult} × tier={tier_mult}",
        }
    
    def _zero_stake(self, reason: str) -> Dict[str, Any]:
        """Retourne une mise nulle"""
        return {
            "kelly_full": 0,
            "kelly_fraction": 0,
            "stake_pct": 0,
            "stake_pct_display": "0.00%",
            "reasoning": reason,
        }
