"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    MODEL B: QUANTUM SCORER                                    ║
║                    Z-Score Hedge Fund Grade                                   ║
║                    Validation: r=+0.53, BUY=+11.13u/team                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Source: quantum/orchestrator/quantum_orchestrator_v1.py (lignes 523-658)
Migration: 26 Décembre 2025

Composants Z-Score:
- Psyche: mentality (CONSERVATIVE=premium), killer_instinct (inverse)
- Luck: regression_direction (UP=positive)
- Temporal: diesel_factor
- Context: home_strength
- Tier: tier_rank mapping
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from .base import BaseModel, ModelName, ModelVote, Signal

# TYPE_CHECKING pour éviter les imports circulaires
if TYPE_CHECKING:
    from fortress_v38.models import TeamDNA
    from fortress_v38.engines.friction_matrix_unified import FrictionMatrix


class ModelQuantumScorer(BaseModel):
    """
    Model B: Z-Score Hedge Fund Grade
    Source: quantum_scorer_v2_4.py
    Validation: r=+0.53, BUY=+11.13u/team
    """

    # Thresholds validés
    Z_BUY_THRESHOLD = 1.5
    Z_FADE_THRESHOLD = -1.5

    def __init__(self, db_pool=None):
        self.db_pool = db_pool

    @property
    def name(self) -> ModelName:
        return ModelName.QUANTUM_SCORER

    def _calculate_z_score(self, dna: "TeamDNA") -> float:
        """
        Calcule le Z-Score d'une équipe.

        Composants et poids:
        - Psyche.mentality: CONSERVATIVE=1.5 (poids 0.20)
        - Psyche.killer_instinct: 1-value (poids 0.15)
        - Luck.regression: UP=+mag (poids 0.15)
        - Temporal.diesel_factor (poids 0.10)
        - Context.home_strength/100 (poids 0.10)
        - tier_rank → ELITE/GOLD/SILVER/BRONZE (poids 0.15)
        """
        if not dna:
            return 0.0

        # Composants du Z-Score
        components = []
        weights = []

        # Psyche DNA
        if dna.psyche:
            # CONSERVATIVE = +11.73u (premium)
            mentality_score = 1.5 if dna.psyche.mentality == "CONSERVATIVE" else 0
            components.append(mentality_score)
            weights.append(0.2)

            # LOW killer_instinct > HIGH (contre-intuitif)
            killer_score = 1 - dna.psyche.killer_instinct
            components.append(killer_score)
            weights.append(0.15)

        # Luck DNA
        if dna.luck:
            # UNLUCKY = regression UP expected
            if dna.luck.regression_direction == "UP":
                luck_score = dna.luck.regression_magnitude / 100
            else:
                luck_score = -dna.luck.regression_magnitude / 100
            components.append(luck_score)
            weights.append(0.15)

        # Temporal DNA
        if dna.temporal:
            diesel_score = dna.temporal.diesel_factor
            components.append(diesel_score)
            weights.append(0.1)

        # Context DNA
        if dna.context:
            home_score = dna.context.home_strength / 100
            components.append(home_score)
            weights.append(0.1)

        # Tier bonus (adapté pour V2: tier_rank est un int 1-100)
        # Mapping: tier_rank >= 85 → ELITE, >= 65 → GOLD, >= 40 → SILVER, < 40 → BRONZE
        tier_rank = getattr(dna, 'tier_rank', 50)
        if tier_rank >= 85:
            tier_score = 0.3  # ELITE
        elif tier_rank >= 65:
            tier_score = 0.2  # GOLD
        elif tier_rank >= 40:
            tier_score = 0.1  # SILVER
        else:
            tier_score = 0.0  # BRONZE
        components.append(tier_score)
        weights.append(0.15)

        if not components:
            return 0.0

        # Weighted average
        total_weight = sum(weights[:len(components)])
        z_score = sum(c * w for c, w in zip(components, weights)) / total_weight

        # Normalisation [-3, 3]
        return max(-3, min(3, z_score * 3))

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
        Génère le signal Z-Score.

        Logique:
        - z_edge >= 1.5  → STRONG_BUY home
        - z_edge >= 0.5  → BUY home
        - z_edge <= -1.5 → STRONG_BUY away
        - z_edge <= -0.5 → BUY away
        - else           → HOLD
        """
        home_z = self._calculate_z_score(home_dna)
        away_z = self._calculate_z_score(away_dna)
        z_edge = home_z - away_z

        # Déterminer le signal
        if z_edge >= self.Z_BUY_THRESHOLD:
            signal = Signal.STRONG_BUY
            target = home_team
            confidence = min(95, 70 + z_edge * 10)
        elif z_edge >= 0.5:
            signal = Signal.BUY
            target = home_team
            confidence = 60 + z_edge * 10
        elif z_edge <= -self.Z_BUY_THRESHOLD:
            signal = Signal.STRONG_BUY
            target = away_team
            confidence = min(95, 70 + abs(z_edge) * 10)
        elif z_edge <= -0.5:
            signal = Signal.BUY
            target = away_team
            confidence = 60 + abs(z_edge) * 10
        else:
            signal = Signal.HOLD
            target = None
            confidence = 40

        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            reasoning=f"Z-Score: Home={home_z:.2f}, Away={away_z:.2f}, Edge={z_edge:.2f}",
            raw_data={
                "home_z": home_z,
                "away_z": away_z,
                "z_edge": z_edge,
                "target": target
            }
        )
