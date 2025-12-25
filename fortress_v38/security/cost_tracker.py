"""
THE QUANTUM SOVEREIGN V3.8 - COST TRACKER
Suivi des coûts API Claude - Thread-Safe Singleton.
Créé le: 24 Décembre 2025

Tarifs Claude 3.5 Sonnet (Décembre 2024):
- Input:  $3.00 / 1M tokens
- Output: $15.00 / 1M tokens

Budget par défaut: $5.00 / jour
"""

import threading
from datetime import date, datetime
from typing import Optional
import logging

logger = logging.getLogger("quantum_sovereign.cost_tracker")


class CostTracker:
    """
    Singleton Thread-Safe pour tracker les coûts Claude.

    Thread-Safe = Protège contre les dépassements même si
    plusieurs matchs sont analysés en parallèle.

    Exemple du problème résolu:
    - Match A vérifie: "Il reste $0.50" ✅
    - Match B vérifie: "Il reste $0.50" ✅  (en même temps)
    - Match A dépense $0.40
    - Match B dépense $0.40
    - Total: $0.80 dépensé mais on avait que $0.50!

    Avec le Lock, Match B doit attendre que Match A ait fini.
    """

    # Singleton instance
    _instance: Optional['CostTracker'] = None
    _creation_lock = threading.Lock()

    # Tarifs Claude 3.5 Sonnet (USD par token)
    INPUT_COST_PER_TOKEN = 3.00 / 1_000_000   # $3.00 / 1M tokens
    OUTPUT_COST_PER_TOKEN = 15.00 / 1_000_000  # $15.00 / 1M tokens

    def __new__(cls):
        """Singleton pattern - Une seule instance possible"""
        if cls._instance is None:
            with cls._creation_lock:
                # Double-check locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialisation (une seule fois grâce au Singleton)"""
        if self._initialized:
            return

        self._cost_lock = threading.Lock()
        self._daily_costs: dict = {}  # {date_str: total_cost}
        self._call_count: dict = {}   # {date_str: count}
        self._initialized = True

        logger.info("CostTracker initialisé (Singleton)")

    def can_call_claude(self, daily_budget: float = 5.0) -> bool:
        """
        Vérifie si on a encore du budget pour appeler Claude.

        Args:
            daily_budget: Budget maximum par jour en USD

        Returns:
            True si budget disponible, False sinon
        """
        with self._cost_lock:
            current = self._get_today_cost_unsafe()
            return current < daily_budget

    def get_today_cost(self) -> float:
        """
        Retourne le coût total d'aujourd'hui (thread-safe).

        Returns:
            Coût en USD
        """
        with self._cost_lock:
            return self._get_today_cost_unsafe()

    def _get_today_cost_unsafe(self) -> float:
        """Version interne sans lock (appelée par méthodes qui ont déjà le lock)"""
        today = date.today().isoformat()
        return self._daily_costs.get(today, 0.0)

    def reserve_budget(self, estimated_cost: float, daily_budget: float = 5.0) -> bool:
        """
        Réserve le budget AVANT l'appel Claude (approche pessimiste).

        Args:
            estimated_cost: Coût estimé de l'appel
            daily_budget: Budget maximum par jour

        Returns:
            True si réservation réussie, False si budget insuffisant
        """
        with self._cost_lock:
            current = self._get_today_cost_unsafe()

            if current + estimated_cost > daily_budget:
                logger.warning(
                    f"Réservation refusée: ${estimated_cost:.4f} demandé, "
                    f"${daily_budget - current:.4f} disponible"
                )
                return False

            # Réserver le budget
            today = date.today().isoformat()
            self._daily_costs[today] = current + estimated_cost

            logger.debug(f"Budget réservé: ${estimated_cost:.4f}")
            return True

    def log_cost(self, input_tokens: int, output_tokens: int, reserved: float = 0.0) -> float:
        """
        Enregistre le coût réel APRÈS l'appel Claude.

        Args:
            input_tokens: Nombre de tokens en entrée
            output_tokens: Nombre de tokens en sortie
            reserved: Montant qui avait été réservé (pour ajustement)

        Returns:
            Coût réel en USD
        """
        actual_cost = self.calculate_cost(input_tokens, output_tokens)

        with self._cost_lock:
            today = date.today().isoformat()
            current = self._daily_costs.get(today, 0.0)

            # Ajuster: retirer la réservation, ajouter le coût réel
            adjustment = actual_cost - reserved
            self._daily_costs[today] = current + adjustment

            # Incrémenter le compteur d'appels
            self._call_count[today] = self._call_count.get(today, 0) + 1

            logger.info(
                f"Coût Claude: ${actual_cost:.4f} "
                f"(in: {input_tokens}, out: {output_tokens}) - "
                f"Total jour: ${self._daily_costs[today]:.4f}"
            )

        return actual_cost

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calcule le coût d'un appel Claude.

        Args:
            input_tokens: Nombre de tokens en entrée
            output_tokens: Nombre de tokens en sortie

        Returns:
            Coût en USD
        """
        input_cost = input_tokens * self.INPUT_COST_PER_TOKEN
        output_cost = output_tokens * self.OUTPUT_COST_PER_TOKEN
        return input_cost + output_cost

    def estimate_cost(self, prompt_chars: int, expected_output_chars: int = 2000) -> float:
        """
        Estime le coût d'un appel basé sur le nombre de caractères.
        Règle approximative: 1 token ≈ 4 caractères

        Args:
            prompt_chars: Nombre de caractères du prompt
            expected_output_chars: Estimation de la réponse

        Returns:
            Coût estimé en USD
        """
        input_tokens = prompt_chars // 4
        output_tokens = expected_output_chars // 4
        return self.calculate_cost(input_tokens, output_tokens)

    def get_today_stats(self) -> dict:
        """
        Retourne les statistiques du jour.

        Returns:
            Dict avec coût, nombre d'appels, etc.
        """
        with self._cost_lock:
            today = date.today().isoformat()
            cost = self._daily_costs.get(today, 0.0)
            calls = self._call_count.get(today, 0)

            return {
                "date": today,
                "total_cost_usd": round(cost, 4),
                "call_count": calls,
                "avg_cost_per_call": round(cost / calls, 4) if calls > 0 else 0,
                "timestamp": datetime.now().isoformat()
            }

    def reset_daily(self):
        """
        Remet à zéro les compteurs du jour (pour tests uniquement).
        """
        with self._cost_lock:
            today = date.today().isoformat()
            self._daily_costs[today] = 0.0
            self._call_count[today] = 0
            logger.warning("CostTracker reset pour aujourd'hui (tests)")
