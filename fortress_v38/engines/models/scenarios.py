"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    MODEL E: SCENARIOS                                         ║
║                    20 Scénarios avec Monte Carlo Filter                       ║
║                    Note: Seuls = -58.4u, avec MC filter = positif            ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Source: quantum/orchestrator/quantum_orchestrator_v1.py (lignes 1000-1110)
Migration: 26 Décembre 2025

Ce modèle détecte des scénarios de match basés sur les DNA des équipes.
20 scénarios sont déclarés et implémentés.

IMPORTANT: Ce modèle nécessite une validation Monte Carlo pour être rentable.
Sans MC filter: -58.4u (négatif)
Avec MC filter: positif

Les 20 scénarios organisés en 5 groupes:

GROUPE A - TACTIQUES (5):
- TOTAL_CHAOS, THE_SIEGE, SNIPER_DUEL, ATTRITION_WAR, GLASS_CANNON

GROUPE B - TEMPORELS (4):
- LATE_PUNISHMENT, EXPLOSIVE_START, DIESEL_DUEL, CLUTCH_KILLER

GROUPE C - PHYSIQUES (4):
- FATIGUE_COLLAPSE, PRESSING_DEATH, PACE_EXPLOITATION, BENCH_WARFARE

GROUPE D - PSYCHOLOGIQUES (4):
- CONSERVATIVE_WALL, KILLER_INSTINCT, COLLAPSE_ALERT, NOTHING_TO_LOSE

GROUPE E - NEMESIS (3):
- NEMESIS_TRAP, PREY_HUNT, AERIAL_RAID
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

    # Marchés suggérés par scénario (20 scénarios complets)
    SCENARIO_MARKETS = {
        # GROUPE A - TACTIQUES
        "TOTAL_CHAOS": "over_35",
        "THE_SIEGE": "under_25",
        "SNIPER_DUEL": "btts_yes",
        "ATTRITION_WAR": "under_25",
        "GLASS_CANNON": "btts_yes",
        # GROUPE B - TEMPORELS
        "LATE_PUNISHMENT": "over_25",
        "EXPLOSIVE_START": "first_half_over_15",
        "DIESEL_DUEL": "second_half_over_15",
        "CLUTCH_KILLER": "over_25",
        # GROUPE C - PHYSIQUES
        "FATIGUE_COLLAPSE": "over_25",
        "PRESSING_DEATH": "home_over_15",
        "PACE_EXPLOITATION": "btts_yes",
        "BENCH_WARFARE": "second_half_over_15",
        # GROUPE D - PSYCHOLOGIQUES
        "CONSERVATIVE_WALL": "under_25",
        "KILLER_INSTINCT": "home_over_15",
        "COLLAPSE_ALERT": "over_25",
        "NOTHING_TO_LOSE": "draw",
        # GROUPE E - NEMESIS
        "NEMESIS_TRAP": "away_over_05",
        "PREY_HUNT": "home_over_15",
        "AERIAL_RAID": "home_over_05",
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

        Logique complète des 20 scénarios basée sur scenarios_definitions.py

        Args:
            home_dna: DNA de l'équipe à domicile
            away_dna: DNA de l'équipe à l'extérieur
            friction: Matrice de friction entre les équipes

        Returns:
            List of (scenario_name, confidence) tuples
        """
        detected = []

        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE A - TACTIQUES (5)
        # ═══════════════════════════════════════════════════════════════════════

        # 1. TOTAL_CHAOS: chaos_potential élevé (Festival de buts)
        if friction and hasattr(friction, 'chaos_potential'):
            if friction.chaos_potential > 65:
                detected.append(("TOTAL_CHAOS", float(friction.chaos_potential)))

        # 2. THE_SIEGE: Écart de possession élevé (Domination stérile)
        if home_dna and home_dna.physical and away_dna and away_dna.physical:
            home_poss = getattr(home_dna.physical, 'possession_pct', 50)
            away_poss = getattr(away_dna.physical, 'possession_pct', 50)
            poss_gap = abs(home_poss - away_poss)
            if poss_gap > 18:
                confidence = min(85.0, 55 + poss_gap)
                detected.append(("THE_SIEGE", confidence))

        # 3. SNIPER_DUEL: Deux équipes avec killer_instinct élevé
        if home_dna and home_dna.psyche and away_dna and away_dna.psyche:
            home_killer = home_dna.psyche.killer_instinct
            away_killer = away_dna.psyche.killer_instinct
            if home_killer > 0.6 and away_killer > 0.6:
                confidence = (home_killer + away_killer) / 2 * 100
                detected.append(("SNIPER_DUEL", confidence))

        # 4. ATTRITION_WAR: Deux équipes conservatrices (Guerre d'usure)
        if home_dna and home_dna.psyche and away_dna and away_dna.psyche:
            home_mentality = getattr(home_dna.psyche, 'mentality', '')
            away_mentality = getattr(away_dna.psyche, 'mentality', '')
            if home_mentality == "CONSERVATIVE" and away_mentality == "CONSERVATIVE":
                detected.append(("ATTRITION_WAR", 78.0))
            elif home_mentality == "CONSERVATIVE" or away_mentality == "CONSERVATIVE":
                # Au moins un conservateur + faible killer_instinct
                if home_dna.psyche.killer_instinct < 0.45 and away_dna.psyche.killer_instinct < 0.45:
                    detected.append(("ATTRITION_WAR", 65.0))

        # 5. GLASS_CANNON: Fort en attaque, faible en défense
        if home_dna and home_dna.psyche:
            if home_dna.psyche.killer_instinct > 0.7:
                collapse = getattr(home_dna.psyche, 'collapse_rate', 0)
                if collapse > 0.2:
                    detected.append(("GLASS_CANNON", 70.0))
        if away_dna and away_dna.psyche:
            if away_dna.psyche.killer_instinct > 0.7:
                collapse = getattr(away_dna.psyche, 'collapse_rate', 0)
                if collapse > 0.2:
                    detected.append(("GLASS_CANNON", 70.0))

        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE B - TEMPORELS (4)
        # ═══════════════════════════════════════════════════════════════════════

        # 6. LATE_PUNISHMENT: diesel_factor élevé (Punition tardive)
        if home_dna and home_dna.temporal:
            if home_dna.temporal.diesel_factor > 0.6:
                confidence = home_dna.temporal.diesel_factor * 100
                detected.append(("LATE_PUNISHMENT", confidence))

        # 7. EXPLOSIVE_START: fast_starter élevé des deux côtés
        if home_dna and home_dna.temporal and away_dna and away_dna.temporal:
            home_fast = getattr(home_dna.temporal, 'fast_starter', 0)
            away_fast = getattr(away_dna.temporal, 'fast_starter', 0)
            if home_fast > 0.55 and away_fast > 0.55:
                confidence = (home_fast + away_fast) / 2 * 100
                detected.append(("EXPLOSIVE_START", confidence))

        # 8. DIESEL_DUEL: Deux diesels (Match qui s'emballe en 2H)
        if home_dna and home_dna.temporal and away_dna and away_dna.temporal:
            home_diesel = home_dna.temporal.diesel_factor
            away_diesel = getattr(away_dna.temporal, 'away_diesel', away_dna.temporal.diesel_factor)
            if home_diesel > 0.62 and away_diesel > 0.62:
                confidence = (home_diesel + away_diesel) / 2 * 100
                detected.append(("DIESEL_DUEL", confidence))

        # 9. CLUTCH_KILLER: late_game_threat élevé + adversaire qui craque
        if home_dna and home_dna.temporal and away_dna and away_dna.psyche:
            late_threat = getattr(home_dna.temporal, 'late_game_threat', 0)
            away_collapse = getattr(away_dna.psyche, 'collapse_rate', 0)
            if late_threat > 0.7 and away_collapse > 0.2:
                confidence = (late_threat * 0.6 + (1 - away_collapse) * 0.4) * 100
                detected.append(("CLUTCH_KILLER", confidence))

        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE C - PHYSIQUES (4)
        # ═══════════════════════════════════════════════════════════════════════

        # 10. FATIGUE_COLLAPSE: Approximé via late_game metrics
        if away_dna and away_dna.physical and home_dna and home_dna.temporal:
            away_late_xg = getattr(away_dna.physical, 'late_game_xg_avg', 0)
            home_diesel = getattr(home_dna.temporal, 'diesel_factor', 0)
            # Si away faiblit en fin de match et home est diesel
            if away_late_xg < 0.4 and home_diesel > 0.6:
                detected.append(("FATIGUE_COLLAPSE", 68.0))

        # 11. PRESSING_DEATH: pressing_intensity élevé
        if home_dna and home_dna.physical:
            pressing = getattr(home_dna.physical, 'pressing_intensity', 0)
            if pressing > 75:
                confidence = min(85.0, 50 + pressing * 0.4)
                detected.append(("PRESSING_DEATH", confidence))

        # 12. PACE_EXPLOITATION: Basé sur style et tempo clash
        if friction and hasattr(friction, 'tempo_clash_score'):
            if friction.tempo_clash_score > 65:
                detected.append(("PACE_EXPLOITATION", float(friction.tempo_clash_score)))

        # 13. BENCH_WARFARE: Approximé via roster quality difference
        if home_dna and home_dna.roster and away_dna and away_dna.roster:
            home_dep = getattr(home_dna.roster, 'top3_dependency', 0.5)
            away_dep = getattr(away_dna.roster, 'top3_dependency', 0.5)
            # Moins dépendant = meilleur banc
            if home_dep < 0.4 and away_dep > 0.6:
                detected.append(("BENCH_WARFARE", 70.0))

        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE D - PSYCHOLOGIQUES (4)
        # ═══════════════════════════════════════════════════════════════════════

        # 14. CONSERVATIVE_WALL: Mentality conservative
        if home_dna and home_dna.psyche:
            mentality = getattr(home_dna.psyche, 'mentality', '')
            if mentality == "CONSERVATIVE":
                detected.append(("CONSERVATIVE_WALL", 75.0))

        # 15. KILLER_INSTINCT: killer_instinct élevé vs collapse_rate élevé adverse
        if home_dna and home_dna.psyche and away_dna and away_dna.psyche:
            home_killer = home_dna.psyche.killer_instinct
            away_collapse = getattr(away_dna.psyche, 'collapse_rate', 0)
            if home_killer > 0.75 and away_collapse > 0.22:
                confidence = (home_killer * 0.7 + away_collapse * 0.3) * 100
                detected.append(("KILLER_INSTINCT", confidence))

        # 16. COLLAPSE_ALERT: collapse_rate + panic_factor élevés
        if home_dna and home_dna.psyche:
            collapse = getattr(home_dna.psyche, 'collapse_rate', 0)
            panic = getattr(home_dna.psyche, 'panic_factor', 0)
            if collapse > 0.28 and panic > 0.35:
                confidence = (collapse + panic) / 2 * 100 + 20
                detected.append(("COLLAPSE_ALERT", min(85.0, confidence)))

        # 17. NOTHING_TO_LOSE: Approximé via points/position basse
        if away_dna and away_dna.context:
            points = getattr(away_dna.context, 'points', 50)
            losses = getattr(away_dna.context, 'losses', 0)
            wins = getattr(away_dna.context, 'wins', 0)
            # Équipe en difficulté mais combative
            if points < 15 and losses > wins:
                if home_dna and home_dna.psyche:
                    home_lead_prot = getattr(home_dna.psyche, 'lead_protection', 0.5)
                    # Home complaisant (faible lead protection)
                    if home_lead_prot < 0.5:
                        detected.append(("NOTHING_TO_LOSE", 68.0))

        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE E - NEMESIS (3)
        # ═══════════════════════════════════════════════════════════════════════

        # 18. NEMESIS_TRAP: Équipe contre son nemesis
        if home_dna and home_dna.nemesis and away_dna:
            nemesis_teams = getattr(home_dna.nemesis, 'nemesis_teams', [])
            if nemesis_teams and away_dna.team_name in nemesis_teams:
                detected.append(("NEMESIS_TRAP", 80.0))

        # 19. PREY_HUNT: Inverse de nemesis (away est une proie)
        if away_dna and away_dna.nemesis and home_dna:
            nemesis_teams = getattr(away_dna.nemesis, 'nemesis_teams', [])
            if nemesis_teams and home_dna.team_name in nemesis_teams:
                # Away considère Home comme nemesis = Home est la proie
                # Inverser: Home chasse sa proie
                detected.append(("PREY_HUNT", 75.0))
        # Alternative: H2H favorable
        if friction and hasattr(friction, 'h2h_avg_goals'):
            if friction.h2h_avg_goals > 3.0:
                # Match historiquement avec beaucoup de buts
                if home_dna and home_dna.psyche and home_dna.psyche.killer_instinct > 0.65:
                    detected.append(("PREY_HUNT", 72.0))

        # 20. AERIAL_RAID: aerial_win_pct élevé
        if home_dna and home_dna.physical:
            aerial = getattr(home_dna.physical, 'aerial_win_pct', 0)
            if aerial > 55:
                confidence = min(80.0, 50 + aerial * 0.5)
                detected.append(("AERIAL_RAID", confidence))

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
