"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    MODEL E: SCENARIOS                                         ║
║                    20 Scénarios avec Monte Carlo Filter                       ║
║                    Note: Seuls = -58.4u, avec MC filter = positif            ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Source: quantum/orchestrator/quantum_orchestrator_v1.py (lignes 1000-1110)
Migration: 26 Décembre 2025

Ce modèle détecte des scénarios de match basés sur les DNA des équipes.
20 scénarios sont déclarés, 6 sont actuellement implémentés.

IMPORTANT: Ce modèle nécessite une validation Monte Carlo pour être rentable.
Sans MC filter: -58.4u (négatif)
Avec MC filter: positif

Les 6 scénarios implémentés:
- SNIPER_DUEL: Deux équipes avec killer_instinct élevé → btts_yes
- LATE_PUNISHMENT: diesel_factor élevé + adversaire pressing_decay → over_25
- GLASS_CANNON: Fort en attaque, faible en défense → btts_yes
- CONSERVATIVE_WALL: Mentality conservative → under_25
- TOTAL_CHAOS: chaos_potential élevé → over_35
- NEMESIS_TRAP: Équipe contre son nemesis → dépend du contexte
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from .base import BaseModel, ModelName, ModelVote, Signal

# TYPE_CHECKING pour éviter les imports circulaires
if TYPE_CHECKING:
    from fortress_v38.models import TeamDNA
    from fortress_v38.engines.friction_matrix_unified import FrictionMatrix


class ModelScenarios(BaseModel):
    """
    Model E: 20 Scénarios avec Monte Carlo Filter
    Source: quantum/services/scenario_detector.py
    Note: Seuls = -58.4u, avec MC filter = positif

    Ce modèle détecte des patterns de match spécifiques
    et suggère des marchés appropriés.
    """

    # Les 20 scénarios possibles
    SCENARIOS = [
        "TOTAL_CHAOS", "THE_SIEGE", "SNIPER_DUEL", "ATTRITION_WAR", "GLASS_CANNON",
        "LATE_PUNISHMENT", "EXPLOSIVE_START", "DIESEL_DUEL", "CLUTCH_KILLER",
        "FATIGUE_COLLAPSE", "PRESSING_DEATH", "PACE_EXPLOITATION", "BENCH_WARFARE",
        "CONSERVATIVE_WALL", "KILLER_INSTINCT", "COLLAPSE_ALERT", "NOTHING_TO_LOSE",
        "NEMESIS_TRAP", "PREY_HUNT", "AERIAL_RAID"
    ]

    # Marchés suggérés par scénario
    SCENARIO_MARKETS = {
        "SNIPER_DUEL": "btts_yes",
        "LATE_PUNISHMENT": "over_25",
        "GLASS_CANNON": "btts_yes",
        "CONSERVATIVE_WALL": "under_25",
        "TOTAL_CHAOS": "over_35",
        "NEMESIS_TRAP": None  # Dépend du contexte
    }

    def __init__(self, db_pool=None):
        self.db_pool = db_pool

    @property
    def name(self) -> ModelName:
        return ModelName.SCENARIOS

    def _detect_scenarios(
        self,
        home_dna: "TeamDNA",
        away_dna: "TeamDNA",
        friction: "FrictionMatrix"
    ) -> List[Tuple[str, float]]:
        """
        Détecte les scénarios actifs basés sur les DNA.

        Args:
            home_dna: DNA de l'équipe à domicile
            away_dna: DNA de l'équipe à l'extérieur
            friction: Matrice de friction entre les équipes

        Returns:
            List of (scenario_name, confidence) tuples
        """
        detected = []

        # SNIPER_DUEL: Deux équipes avec killer_instinct élevé
        if home_dna and home_dna.psyche and away_dna and away_dna.psyche:
            home_killer = home_dna.psyche.killer_instinct
            away_killer = away_dna.psyche.killer_instinct
            if home_killer > 0.6 and away_killer > 0.6:
                confidence = (home_killer + away_killer) / 2 * 100
                detected.append(("SNIPER_DUEL", confidence))

        # LATE_PUNISHMENT: diesel_factor élevé + adversaire pressing_decay
        if home_dna and home_dna.temporal and away_dna and away_dna.physical:
            if home_dna.temporal.diesel_factor > 0.6:
                if hasattr(away_dna.physical, 'pressing_decay') and away_dna.physical.pressing_decay > 0.2:
                    confidence = home_dna.temporal.diesel_factor * 100
                    detected.append(("LATE_PUNISHMENT", confidence))

        # GLASS_CANNON: Fort en attaque, faible en défense
        if home_dna and home_dna.psyche:
            if home_dna.psyche.killer_instinct > 0.7:
                if hasattr(home_dna.psyche, 'collapse_rate') and home_dna.psyche.collapse_rate > 0.2:
                    detected.append(("GLASS_CANNON", 70.0))

        # CONSERVATIVE_WALL: Mentality conservative
        if home_dna and home_dna.psyche:
            if hasattr(home_dna.psyche, 'mentality') and home_dna.psyche.mentality == "CONSERVATIVE":
                detected.append(("CONSERVATIVE_WALL", 75.0))

        # TOTAL_CHAOS: chaos_potential élevé (dans friction)
        if friction and hasattr(friction, 'chaos_potential'):
            if friction.chaos_potential > 65:
                detected.append(("TOTAL_CHAOS", float(friction.chaos_potential)))

        # NEMESIS_TRAP: Équipe contre son nemesis
        if home_dna and home_dna.nemesis and away_dna:
            if hasattr(home_dna.nemesis, 'nemesis_teams'):
                if away_dna.team_name in home_dna.nemesis.nemesis_teams:
                    detected.append(("NEMESIS_TRAP", 80.0))

        return detected

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
        Génère le signal basé sur les scénarios détectés.

        ATTENTION: Ce modèle est rentable UNIQUEMENT avec validation
        Monte Carlo. Sans MC filter = -58.4u.

        Logique:
        - confidence ≥ 75 → BUY
        - else → HOLD
        """
        # Détecter les scénarios
        scenarios = self._detect_scenarios(home_dna, away_dna, friction)

        # Aucun scénario détecté
        if not scenarios:
            return ModelVote(
                model_name=self.name,
                signal=Signal.HOLD,
                confidence=40,
                reasoning="Aucun scénario clair détecté",
                raw_data={"scenarios": [], "requires_mc_filter": True}
            )

        # Meilleur scénario (plus haute confidence)
        best_scenario, best_confidence = max(scenarios, key=lambda x: x[1])

        # Marché suggéré
        market = self.SCENARIO_MARKETS.get(best_scenario)

        # Signal basé sur la confidence
        if best_confidence >= 75:
            signal = Signal.BUY
        else:
            signal = Signal.HOLD

        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=best_confidence,
            market=market,
            reasoning=f"Scénario {best_scenario} détecté ({best_confidence:.0f}%)",
            raw_data={
                "scenarios": scenarios,
                "best_scenario": best_scenario,
                "suggested_market": market,
                "requires_mc_filter": True  # Rappel: nécessite MC validation
            }
        )
