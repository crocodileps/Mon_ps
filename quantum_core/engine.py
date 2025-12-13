"""
QUANTUM CORE - ENGINE
=====================
Orchestrateur principal du système de prédiction

Usage:
    from quantum_core.engine import QuantumEngine

    engine = QuantumEngine()

    # Prédiction simple
    pred = engine.predict("Liverpool", "Manchester City", "over_25", odds=1.85)

    # Toutes les prédictions
    all_preds = engine.predict_match("Liverpool", "Manchester City")

    # Trouver les value bets
    value = engine.find_value("Liverpool", "Manchester City", bookmaker_odds)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from .data.manager import DataManager, get_data_manager
from .markets.goals import GoalsPredictor
from .markets.base import Prediction
from .edge.calculator import find_value_bets, calculate_edge

logger = logging.getLogger(__name__)


@dataclass
class MatchAnalysis:
    """Analyse complète d'un match"""
    home_team: str
    away_team: str
    predictions: Dict[str, Prediction]
    value_bets: List[Prediction]
    recommended_bets: List[Prediction]
    summary: str


class QuantumEngine:
    """
    Moteur principal de prédiction

    Coordonne tous les prédicteurs et génère les recommandations.
    """

    def __init__(self, data_manager: DataManager = None):
        """
        Args:
            data_manager: Instance de DataManager (optionnel)
        """
        self.data = data_manager or get_data_manager()

        # Initialiser les prédicteurs
        self.goals_predictor = GoalsPredictor(self.data)

        # TODO: Ajouter les autres prédicteurs
        # self.scorers_predictor = ScorersPredictor(self.data)
        # self.cards_predictor = CardsPredictor(self.data)

        logger.info("✅ QuantumEngine initialisé")

    def predict(self, home_team: str, away_team: str,
                market: str, odds: float = None, **kwargs) -> Prediction:
        """
        Prédiction d'un marché unique

        Args:
            home_team: Équipe à domicile
            away_team: Équipe à l'extérieur
            market: Type de marché (over_25, btts_yes, etc.)
            odds: Cote du bookmaker (optionnel)

        Returns:
            Prediction
        """
        # Router vers le bon prédicteur
        if market.startswith("over_") or market.startswith("under_"):
            threshold = float(market.split("_")[1]) / 10  # over_25 → 2.5
            if market.startswith("over_"):
                return self.goals_predictor.predict_over(
                    home_team, away_team, threshold, odds, **kwargs
                )
            else:
                return self.goals_predictor.predict_under(
                    home_team, away_team, threshold, odds, **kwargs
                )

        elif market.startswith("btts"):
            yes = market == "btts_yes"
            return self.goals_predictor.predict_btts(
                home_team, away_team, yes, odds, **kwargs
            )

        elif market in ["home", "draw", "away"]:
            return self.goals_predictor.predict_1x2(
                home_team, away_team, market, odds, **kwargs
            )

        elif market.startswith("score_"):
            parts = market.split("_")
            h, a = int(parts[1]), int(parts[2])
            return self.goals_predictor.predict_score_exact(
                home_team, away_team, h, a, odds, **kwargs
            )

        else:
            # Marché générique
            self.goals_predictor.market_name = market
            return self.goals_predictor.predict(
                home_team, away_team, odds, **kwargs
            )

    def predict_match(self, home_team: str, away_team: str,
                      bookmaker_odds: Dict[str, float] = None,
                      **kwargs) -> Dict[str, Prediction]:
        """
        Prédit tous les marchés pour un match

        Args:
            home_team: Équipe à domicile
            away_team: Équipe à l'extérieur
            bookmaker_odds: Dict des cotes {market: odds}

        Returns:
            Dict des prédictions {market: Prediction}
        """
        all_predictions = {}

        # Goals markets
        goals_preds = self.goals_predictor.predict_all_goals_markets(
            home_team, away_team, bookmaker_odds, **kwargs
        )
        all_predictions.update(goals_preds)

        # TODO: Ajouter les autres prédicteurs

        return all_predictions

    def analyze_match(self, home_team: str, away_team: str,
                      bookmaker_odds: Dict[str, float] = None,
                      min_edge: float = 3.0,
                      **kwargs) -> MatchAnalysis:
        """
        Analyse complète d'un match avec recommandations

        Args:
            home_team: Équipe à domicile
            away_team: Équipe à l'extérieur
            bookmaker_odds: Dict des cotes
            min_edge: Edge minimum pour recommander

        Returns:
            MatchAnalysis complète
        """
        bookmaker_odds = bookmaker_odds or {}

        # Toutes les prédictions
        predictions = self.predict_match(home_team, away_team, bookmaker_odds, **kwargs)

        # Trouver les value bets
        value_bets = []
        recommended = []

        for market, pred in predictions.items():
            if pred.edge_percentage and pred.edge_percentage >= min_edge:
                value_bets.append(pred)

                if pred.recommendation in ["BET", "STRONG_BET"]:
                    recommended.append(pred)

        # Trier par edge
        value_bets.sort(key=lambda x: -(x.edge_percentage or 0))
        recommended.sort(key=lambda x: -(x.edge_percentage or 0))

        # Générer le résumé
        summary = self._generate_summary(home_team, away_team, predictions, value_bets)

        return MatchAnalysis(
            home_team=home_team,
            away_team=away_team,
            predictions=predictions,
            value_bets=value_bets,
            recommended_bets=recommended,
            summary=summary
        )

    def get_most_likely_scores(self, home_team: str, away_team: str,
                                n: int = 5) -> List[dict]:
        """Retourne les scores les plus probables"""
        return self.goals_predictor.get_most_likely_scores(home_team, away_team, n)

    def _generate_summary(self, home: str, away: str,
                          predictions: Dict, value_bets: List) -> str:
        """Génère un résumé textuel"""
        lines = [
            f"═══ ANALYSE: {home} vs {away} ═══",
            "",
            "📊 PROBABILITÉS CLÉS:",
        ]

        key_markets = ["home_win", "draw", "away_win", "over_25", "btts_yes"]
        for m in key_markets:
            if m in predictions:
                p = predictions[m]
                lines.append(f"  • {m}: {p.probability*100:.1f}% (Fair: {p.fair_odds:.2f})")

        lines.append("")
        lines.append(f"💰 VALUE BETS TROUVÉS: {len(value_bets)}")

        for vb in value_bets[:5]:
            lines.append(f"  ✅ {vb.market}: +{vb.edge_percentage:.1f}% edge | {vb.recommendation}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════════

_engine_instance: Optional[QuantumEngine] = None

def get_engine() -> QuantumEngine:
    """Retourne l'instance singleton du QuantumEngine"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = QuantumEngine()
    return _engine_instance
