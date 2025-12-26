"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    MODEL C: MATCHUP SCORER                                    ║
║                    Momentum L5 - Version Simplifiée                           ║
║                    Validation: +10% ROI improvement                           ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Source: quantum/orchestrator/quantum_orchestrator_v1.py (lignes 664-848)
Migration: 26 Décembre 2025

VERSION SIMPLIFIÉE:
- Ce modèle calcule le MOMENTUM et donne son VOTE
- La résolution des conflits entre modèles sera faite par le CONSENSUS ENGINE
- Pas de SmartConflictResult ici (architecture Agents: UN seul arbitre)

Logique Momentum:
- BLAZING  → STRONG_BUY (équipe en feu)
- HOT      → BUY (bonne forme)
- WARMING  → BUY (forme correcte)
- NEUTRAL  → HOLD (forme moyenne)
- COOLING  → SKIP (mauvaise forme)
- FREEZING → SKIP (très mauvaise forme)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional, Tuple

from .base import BaseModel, ModelName, ModelVote, Signal, MomentumTrend

# TYPE_CHECKING pour éviter les imports circulaires
if TYPE_CHECKING:
    from fortress_v38.models import TeamDNA
    from fortress_v38.engines.friction_matrix_unified import FrictionMatrix


class ModelMatchupScorer(BaseModel):
    """
    Model C: Momentum L5
    Source: quantum_matchup_scorer_v3_4.py
    Validation: +10% ROI improvement

    Ce modèle donne son VOTE basé sur le momentum.
    La combinaison avec les autres modèles sera faite par le Consensus Engine.
    """

    # Stake multipliers par trend (utilisé pour raw_data, pas pour décision)
    TREND_MULTIPLIERS = {
        MomentumTrend.BLAZING: 1.25,
        MomentumTrend.HOT: 1.15,
        MomentumTrend.WARMING: 1.0,
        MomentumTrend.NEUTRAL: 0.85,
        MomentumTrend.COOLING: 0.0,   # SKIP
        MomentumTrend.FREEZING: 0.0   # SKIP
    }

    def __init__(self, db_pool=None):
        self.db_pool = db_pool

    @property
    def name(self) -> ModelName:
        return ModelName.MATCHUP_SCORER

    def _calculate_momentum(
        self,
        team_name: str,
        context: Optional[Dict]
    ) -> Tuple[float, MomentumTrend, int]:
        """
        Calcule le Momentum L5 d'une équipe.

        Args:
            team_name: Nom de l'équipe
            context: Contexte contenant les données momentum

        Returns:
            Tuple (score, trend, streak_length)
            - score: Score momentum 0-100
            - trend: MomentumTrend enum
            - streak_length: Nombre de matchs consécutifs
        """
        # En production, query la DB pour les 5 derniers matchs
        # Pour le template, on utilise les données du context
        if not context or "momentum" not in context:
            return 50.0, MomentumTrend.NEUTRAL, 0

        team_momentum = context.get("momentum", {}).get(team_name, {})

        score = team_momentum.get("score", 50.0)
        trend_str = team_momentum.get("trend", "NEUTRAL")
        streak = team_momentum.get("streak", 0)

        try:
            trend = MomentumTrend[trend_str]
        except KeyError:
            trend = MomentumTrend.NEUTRAL

        return score, trend, streak

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
        Génère le signal basé sur le Momentum L5.

        Ce modèle donne son VOTE indépendamment.
        La combinaison avec les autres modèles (Z-Score, etc.)
        sera faite par le Consensus Engine central.

        Logique:
        - COOLING/FREEZING → SKIP
        - BLAZING → STRONG_BUY (conf: 85 + streak)
        - HOT → BUY (conf: 70 + streak*2)
        - WARMING → BUY (conf: 60)
        - NEUTRAL → HOLD (conf: 50)
        """
        # Calculer momentum des deux équipes
        home_score, home_trend, home_streak = self._calculate_momentum(home_team, context)
        away_score, away_trend, away_streak = self._calculate_momentum(away_team, context)

        # Déterminer l'équipe avec le meilleur momentum
        if home_score > away_score:
            target = home_team
            best_trend = home_trend
            best_streak = home_streak
        else:
            target = away_team
            best_trend = away_trend
            best_streak = away_streak

        # Skip si COOLING/FREEZING
        if best_trend in [MomentumTrend.COOLING, MomentumTrend.FREEZING]:
            return ModelVote(
                model_name=self.name,
                signal=Signal.SKIP,
                confidence=30,
                reasoning=f"Momentum {best_trend.value} → SKIP",
                raw_data={
                    "home_momentum": home_score,
                    "away_momentum": away_score,
                    "home_trend": home_trend.value,
                    "away_trend": away_trend.value,
                    "best_trend": best_trend.value,
                    "target": None
                }
            )

        # Générer signal basé sur le momentum
        if best_trend == MomentumTrend.BLAZING:
            signal = Signal.STRONG_BUY
            confidence = min(95, 85 + best_streak)  # Cap à 95
        elif best_trend == MomentumTrend.HOT:
            signal = Signal.BUY
            confidence = min(85, 70 + best_streak * 2)  # Cap à 85
        elif best_trend == MomentumTrend.WARMING:
            signal = Signal.BUY
            confidence = 60
        else:  # NEUTRAL
            signal = Signal.HOLD
            confidence = 50

        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            reasoning=f"{target} momentum {best_trend.value} (streak: {best_streak})",
            raw_data={
                "target": target,
                "home_momentum": home_score,
                "away_momentum": away_score,
                "home_trend": home_trend.value,
                "away_trend": away_trend.value,
                "home_streak": home_streak,
                "away_streak": away_streak,
                "best_trend": best_trend.value,
                "stake_multiplier": self.TREND_MULTIPLIERS.get(best_trend, 1.0)
            }
        )
