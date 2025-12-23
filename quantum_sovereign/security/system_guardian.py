"""
THE QUANTUM SOVEREIGN V3.8 - SYSTEM GUARDIAN
Gardien du système - Vérifie le budget Claude avant chaque analyse.
Créé le: 24 Décembre 2025

NOTE: Ce système ANALYSE seulement, il ne place pas de paris.
Mya décide quels matchs jouer. Donc:
- Pas de vérification drawdown
- Pas de vérification pertes consécutives
- Uniquement vérification budget Claude API
"""

from typing import Tuple
from datetime import datetime
import logging

# Import du cost tracker (sera créé dans la tâche suivante)
# from .cost_tracker import CostTracker

logger = logging.getLogger("quantum_sovereign.guardian")


class SystemGuardian:
    """
    Le gardien du système.

    Rôle UNIQUE: Vérifier que le budget Claude n'est pas dépassé
    avant de lancer une analyse de match.

    Le système analyse tous les matchs, Mya décide lesquels jouer.
    Donc pas de blocage basé sur les pertes ou le drawdown.
    """

    def __init__(self, daily_budget_usd: float = 5.0):
        """
        Args:
            daily_budget_usd: Budget maximum Claude par jour (défaut: $5)
        """
        self.daily_budget_usd = daily_budget_usd
        self._cost_tracker = None  # Lazy loading

    @property
    def cost_tracker(self):
        """Lazy loading du CostTracker pour éviter import circulaire"""
        if self._cost_tracker is None:
            from .cost_tracker import CostTracker
            self._cost_tracker = CostTracker()
        return self._cost_tracker

    def can_process(self) -> Tuple[bool, str]:
        """
        Vérifie si on peut analyser un nouveau match.

        Returns:
            Tuple[bool, str]: (peut_continuer, raison)

        Exemples:
            (True, "OK") - Budget suffisant
            (False, "Budget Claude épuisé ($5.00/$5.00)") - Plus de budget
        """
        # Vérification unique: Budget Claude
        budget_ok, budget_msg = self._check_claude_budget()

        if not budget_ok:
            logger.warning(f"SystemGuardian: Blocage - {budget_msg}")
            return False, budget_msg

        return True, "OK"

    def _check_claude_budget(self) -> Tuple[bool, str]:
        """
        Vérifie si le budget Claude quotidien n'est pas dépassé.

        Returns:
            Tuple[bool, str]: (budget_ok, message)
        """
        try:
            current_cost = self.cost_tracker.get_today_cost()
            remaining = self.daily_budget_usd - current_cost

            if remaining <= 0:
                return False, f"Budget Claude épuisé (${current_cost:.2f}/${self.daily_budget_usd:.2f})"

            # Warning si budget faible (< 20%)
            if remaining < (self.daily_budget_usd * 0.20):
                logger.warning(
                    f"Budget Claude faible: ${remaining:.2f} restant "
                    f"(${current_cost:.2f}/${self.daily_budget_usd:.2f})"
                )

            return True, f"Budget OK (${remaining:.2f} restant)"

        except Exception as e:
            # En cas d'erreur de lecture du budget, on laisse passer
            # (fail-open pour ne pas bloquer les analyses)
            logger.error(f"Erreur lecture budget: {e}")
            return True, "Budget check failed - Allowing (fail-open)"

    def get_status(self) -> dict:
        """
        Retourne le statut complet du guardian.
        Utile pour le monitoring et le debugging.
        """
        try:
            current_cost = self.cost_tracker.get_today_cost()
            remaining = self.daily_budget_usd - current_cost

            return {
                "timestamp": datetime.now().isoformat(),
                "daily_budget_usd": self.daily_budget_usd,
                "current_cost_usd": round(current_cost, 4),
                "remaining_usd": round(remaining, 4),
                "budget_percentage_used": round((current_cost / self.daily_budget_usd) * 100, 1),
                "can_process": remaining > 0,
                "status": "OK" if remaining > 0 else "BUDGET_EXHAUSTED"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "status": "ERROR"
            }


# ═══════════════════════════════════════════════════════════
# INSTANCE GLOBALE (Singleton pattern)
# ═══════════════════════════════════════════════════════════

_guardian_instance = None

def get_guardian() -> SystemGuardian:
    """Retourne l'instance unique du SystemGuardian"""
    global _guardian_instance
    if _guardian_instance is None:
        from ..config import CONFIG
        _guardian_instance = SystemGuardian(
            daily_budget_usd=CONFIG.CLAUDE_DAILY_BUDGET_USD
        )
    return _guardian_instance
