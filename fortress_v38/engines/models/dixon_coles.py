"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    MODEL D: DIXON-COLES                                       ║
║                    Probabilités BTTS/Over via Poisson                         ║
║                    Source: orchestrator_v11_4_god_tier.py                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Source: quantum/orchestrator/quantum_orchestrator_v1.py (lignes 853-997)
Migration: 26 Décembre 2025

Ce modèle calcule les probabilités des marchés via Dixon-Coles simplifié:
- Over 2.5 / Under 2.5
- BTTS Yes / BTTS No
- Over 3.5 / Under 3.5
- Expected Goals

Logique Signal (basé sur Edge = notre_prob - implied_prob):
- edge < 2%  → HOLD (pas d'edge significatif)
- edge ≥ 10% → STRONG_BUY
- edge ≥ 5%  → BUY
- else       → HOLD
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Dict, Optional

from .base import BaseModel, ModelName, ModelVote, Signal

# TYPE_CHECKING pour éviter les imports circulaires
if TYPE_CHECKING:
    from fortress_v38.models import TeamDNA
    from fortress_v38.engines.friction_matrix_unified import FrictionMatrix


class ModelDixonColes(BaseModel):
    """
    Model D: Probabilités BTTS/Over via Dixon-Coles
    Source: orchestrator_v11_4_god_tier.py

    Ce modèle calcule les probabilités des marchés
    et génère un signal basé sur l'edge par rapport aux cotes.
    """

    def __init__(self, db_pool=None):
        self.db_pool = db_pool

    @property
    def name(self) -> ModelName:
        return ModelName.DIXON_COLES

    def _poisson_prob(self, k: int, lam: float) -> float:
        """
        Calcule P(X = k) pour une distribution de Poisson.

        Args:
            k: Nombre d'événements
            lam: Lambda (expected value)

        Returns:
            Probabilité P(X = k)
        """
        return (lam ** k) * math.exp(-lam) / math.factorial(k)

    def _calculate_probabilities(
        self,
        home_dna: "TeamDNA",
        away_dna: "TeamDNA",
        friction: "FrictionMatrix"
    ) -> Dict[str, float]:
        """
        Calcule les probabilités via Dixon-Coles simplifié.

        En production, cela utiliserait le vrai modèle Dixon-Coles
        avec les paramètres calibrés sur les données historiques.

        Args:
            home_dna: DNA de l'équipe à domicile
            away_dna: DNA de l'équipe à l'extérieur
            friction: Matrice de friction entre les équipes

        Returns:
            Dict avec les probabilités de chaque marché
        """
        # Lambda (expected goals) basé sur DNA
        home_attack = 1.4  # Baseline home attack
        away_attack = 1.2  # Baseline away attack

        # Ajustement basé sur Context DNA
        if home_dna and home_dna.context:
            home_attack *= (home_dna.context.home_strength / 70)
        if away_dna and away_dna.context:
            away_attack *= (away_dna.context.away_strength / 70)

        # Ajustement friction (kinetic = énergie du match)
        if friction:
            home_attack *= (1 + friction.kinetic_home / 200)
            away_attack *= (1 + friction.kinetic_away / 200)

        # Calcul expected total
        expected_total = home_attack + away_attack

        # Over 2.5: P(total >= 3)
        prob_under_25 = sum(
            self._poisson_prob(h, home_attack) * self._poisson_prob(a, away_attack)
            for h in range(3) for a in range(3) if h + a < 3
        )
        prob_over_25 = 1 - prob_under_25

        # BTTS: P(home >= 1) * P(away >= 1)
        prob_home_scores = 1 - self._poisson_prob(0, home_attack)
        prob_away_scores = 1 - self._poisson_prob(0, away_attack)
        prob_btts = prob_home_scores * prob_away_scores

        # Over 3.5: P(total >= 4)
        prob_under_35 = sum(
            self._poisson_prob(h, home_attack) * self._poisson_prob(a, away_attack)
            for h in range(4) for a in range(4) if h + a < 4
        )
        prob_over_35 = 1 - prob_under_35

        return {
            "over_25": prob_over_25,
            "under_25": 1 - prob_over_25,
            "btts_yes": prob_btts,
            "btts_no": 1 - prob_btts,
            "over_35": prob_over_35,
            "under_35": 1 - prob_over_35,
            "expected_goals": expected_total,
            "home_attack": home_attack,
            "away_attack": away_attack
        }

    async def generate_signal(
        self,
        home_team: str,
        away_team: str,
        home_dna: "TeamDNA",
        away_dna: "TeamDNA",
        friction: "FrictionMatrix",
        odds: Dict[str, float],
        context: Optional[Dict] = None
    ) -> ModelVote:
        """
        Génère le signal basé sur les probabilités Dixon-Coles.

        Compare nos probabilités calculées avec les cotes du marché
        pour trouver le meilleur edge.

        Seuils:
        - edge < 2%  → HOLD
        - edge ≥ 10% → STRONG_BUY
        - edge ≥ 5%  → BUY
        """
        # Calculer les probabilités
        probs = self._calculate_probabilities(home_dna, away_dna, friction)

        # Trouver le meilleur edge
        best_market = None
        best_edge = -float('inf')
        best_prob = 0.0

        # Mapping des marchés (notre clé → clé dans odds)
        market_mapping = {
            "over_25": "over_25",
            "btts_yes": "btts_yes",
            "over_35": "over_35"
        }

        for market_key, odds_key in market_mapping.items():
            if odds_key in odds and odds[odds_key] > 1:
                implied_prob = 1 / odds[odds_key]
                our_prob = probs[market_key]
                edge = our_prob - implied_prob

                if edge > best_edge:
                    best_edge = edge
                    best_market = market_key
                    best_prob = our_prob

        # Pas d'edge significatif (< 2%)
        if best_edge < 0.02:
            return ModelVote(
                model_name=self.name,
                signal=Signal.HOLD,
                confidence=40,
                reasoning="Pas d'edge significatif trouvé",
                raw_data=probs
            )

        # Signal basé sur l'edge
        if best_edge >= 0.10:
            signal = Signal.STRONG_BUY
            confidence = min(90, 70 + best_edge * 200)
        elif best_edge >= 0.05:
            signal = Signal.BUY
            confidence = min(80, 60 + best_edge * 200)
        else:
            signal = Signal.HOLD
            confidence = 50

        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            market=best_market,
            probability=best_prob,
            reasoning=f"Dixon-Coles: {best_market} P={best_prob:.1%}, Edge={best_edge:.1%}",
            raw_data={
                **probs,
                "best_market": best_market,
                "best_edge": best_edge
            }
        )
