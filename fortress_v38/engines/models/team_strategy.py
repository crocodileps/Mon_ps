"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    MODEL A: TEAM STRATEGY                                     ║
║                    Stratégie optimale par équipe                              ║
║                    Validation: +1,434.6u sur 344 stratégies                   ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Source: quantum/orchestrator/quantum_orchestrator_v1.py (lignes 411-518)
Migration: 26 Décembre 2025

Logique:
- Compare les ROI des MarketDNA des deux équipes
- Détermine la spécialité (OVER/UNDER/BTTS_YES/BTTS_NO/BALANCED)
- Génère signal basé sur le meilleur ROI
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from .base import BaseModel, ModelName, ModelVote, Signal

# TYPE_CHECKING pour éviter les imports circulaires
if TYPE_CHECKING:
    from fortress_v38.models import TeamDNA
    from fortress_v38.engines.friction_matrix_unified import FrictionMatrix


class ModelTeamStrategy(BaseModel):
    """
    Model A: Stratégie optimale par équipe
    Source: quantum.team_strategies
    Validation: +1,434.6u sur 344 stratégies
    """

    def __init__(self, db_pool=None):
        self.db_pool = db_pool

    @property
    def name(self) -> ModelName:
        return ModelName.TEAM_STRATEGY

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
        """Génère le signal basé sur la meilleure stratégie de chaque équipe"""

        # Récupérer les stratégies des deux équipes (MarketDNA)
        home_strategy = home_dna.market if home_dna.market else None
        away_strategy = away_dna.market if away_dna.market else None

        best_team = None
        best_strategy = None
        best_roi = -float('inf')
        best_market = None

        # Comparer les stratégies (adapté pour MarketDNA V2)
        # V2 utilise: roi (au lieu de best_strategy_roi)
        #            specialists booleans (au lieu de best_strategy string)
        #            exploit_markets (au lieu de best_markets)
        if home_strategy and home_strategy.roi > best_roi:
            best_roi = home_strategy.roi
            best_team = home_team
            # Dériver best_strategy depuis les booleans V2
            if home_strategy.over_specialist:
                best_strategy = "OVER_SPECIALIST"
            elif home_strategy.under_specialist:
                best_strategy = "UNDER_SPECIALIST"
            elif home_strategy.btts_yes_specialist:
                best_strategy = "BTTS_YES"
            elif home_strategy.btts_no_specialist:
                best_strategy = "BTTS_NO"
            else:
                best_strategy = "BALANCED"
            # exploit_markets est une List[Dict], extraire le premier marché
            best_market = home_strategy.exploit_markets[0].get('market') if home_strategy.exploit_markets else None

        if away_strategy and away_strategy.roi > best_roi:
            best_roi = away_strategy.roi
            best_team = away_team
            if away_strategy.over_specialist:
                best_strategy = "OVER_SPECIALIST"
            elif away_strategy.under_specialist:
                best_strategy = "UNDER_SPECIALIST"
            elif away_strategy.btts_yes_specialist:
                best_strategy = "BTTS_YES"
            elif away_strategy.btts_no_specialist:
                best_strategy = "BTTS_NO"
            else:
                best_strategy = "BALANCED"
            best_market = away_strategy.exploit_markets[0].get('market') if away_strategy.exploit_markets else None

        # Aucune stratégie trouvée
        if not best_strategy:
            return ModelVote(
                model_name=self.name,
                signal=Signal.SKIP,
                confidence=0,
                reasoning="Aucune stratégie validée trouvée"
            )

        # Déterminer le signal basé sur le ROI
        # Seuils validés: +1,434.6u
        if best_roi >= 50:
            signal = Signal.STRONG_BUY
            confidence = min(95, 70 + best_roi / 5)
        elif best_roi >= 20:
            signal = Signal.BUY
            confidence = min(85, 60 + best_roi / 3)
        elif best_roi >= 0:
            signal = Signal.HOLD
            confidence = 50
        else:
            signal = Signal.SKIP
            confidence = 30

        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            market=best_market,
            reasoning=f"Strategy {best_strategy} for {best_team}: ROI {best_roi:.1f}%",
            raw_data={
                "team": best_team,
                "strategy": best_strategy,
                "roi": best_roi,
                "market": best_market
            }
        )
