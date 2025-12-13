"""
QUANTUM CORE - GOALS MARKET PREDICTOR
=====================================
Prédicteurs pour les marchés de buts

MARCHÉS SUPPORTÉS:
✅ Over/Under 0.5, 1.5, 2.5, 3.5, 4.5
✅ BTTS Yes/No
✅ Score Exact
✅ Team Over/Under
✅ Clean Sheet

MODÈLES UTILISÉS:
✅ Double Poisson (calcul séparé home/away)
✅ Dixon-Coles (correction scores faibles)
✅ Friction tactique
✅ Ajustement forme

Philosophie: LES DONNÉES DICTENT LE PROFIL, PAS LA RÉPUTATION
"""

from typing import List, Dict
from .base import MarketPredictor, Prediction
from ..probability.poisson import (
    DixonColesModel,
    ScoreMatrix,
    calculate_match_probabilities,
    get_all_market_probabilities
)
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# GOALS PREDICTOR (Classe principale)
# ═══════════════════════════════════════════════════════════════════════

class GoalsPredictor(MarketPredictor):
    """
    Prédicteur principal pour tous les marchés de buts

    Utilise:
    - Double Poisson pour calculer lambda_home et lambda_away séparément
    - Dixon-Coles pour corriger les scores faibles
    - Friction tactique pour ajuster selon les styles de jeu
    - Forme récente (L5) pour ajustement dynamique

    Usage:
        predictor = GoalsPredictor()

        # Prédiction Over 2.5
        pred = predictor.predict_over(
            home_team="Liverpool",
            away_team="Manchester City",
            threshold=2.5,
            bookmaker_odds=1.85
        )

        # Toutes les prédictions goals
        all_preds = predictor.predict_all_goals_markets(
            home_team="Liverpool",
            away_team="Manchester City",
            odds={"over_25": 1.85, "btts_yes": 1.70}
        )
    """

    market_name = "goals"
    market_category = "GOALS"
    model_version = "2.0-dixon-coles"

    # League average goals (à ajuster par ligue)
    LEAGUE_AVG = {
        "EPL": 2.85,
        "La Liga": 2.65,
        "Serie A": 2.75,
        "Bundesliga": 3.10,
        "Ligue 1": 2.70,
        "default": 2.75
    }

    def __init__(self, data_manager=None):
        super().__init__(data_manager)
        self.dixon_coles = DixonColesModel(rho=-0.13)

    def get_required_data(self) -> List[str]:
        return [
            "team_dna_unified_v2",
            "team_narrative_dna_v3",
            "defensive_line.temporal"
        ]

    def calculate_probability(self, home_team: str, away_team: str,
                               market: str = "over_25", **kwargs) -> float:
        """
        Calcule la probabilité d'un marché de buts

        Args:
            home_team: Équipe à domicile
            away_team: Équipe à l'extérieur
            market: Type de marché (over_25, btts_yes, etc.)

        Returns:
            Probabilité entre 0 et 1
        """
        # Générer la matrice de scores
        matrix = self._generate_score_matrix(home_team, away_team, **kwargs)

        # Extraire la probabilité selon le marché
        all_probs = get_all_market_probabilities(matrix)

        return all_probs.get(market, 0.5)

    def _generate_score_matrix(self, home_team: str, away_team: str,
                                league: str = "EPL", **kwargs) -> ScoreMatrix:
        """
        Génère la matrice complète des probabilités de scores

        Cette méthode est le cœur du prédicteur. Elle:
        1. Récupère les xG/xGA des deux équipes
        2. Calcule les lambdas ajustés
        3. Applique Dixon-Coles
        4. Retourne la matrice de scores
        """
        # 1. Récupérer les données
        home_xg = self.data.get_team_xg(home_team, location="home")
        away_xg = self.data.get_team_xg(away_team, location="away")
        home_xga = self.data.get_team_xga(home_team, location="home")
        away_xga = self.data.get_team_xga(away_team, location="away")

        # 2. Calculer les lambdas de base
        league_avg = self.LEAGUE_AVG.get(league, self.LEAGUE_AVG["default"]) / 2

        lambda_home, lambda_away = self.dixon_coles.calculate_lambdas(
            home_xg=home_xg,
            away_xga=away_xga,
            away_xg=away_xg,
            home_xga=home_xga,
            league_avg=league_avg
        )

        # 3. Ajustements contextuels
        # Friction tactique
        friction = self.data.get_friction_multiplier(home_team, away_team)

        # Forme récente
        form_home = self.data.get_form_multiplier(home_team)
        form_away = self.data.get_form_multiplier(away_team)

        # Appliquer les ajustements
        lambda_home *= friction * form_home
        lambda_away *= friction * form_away

        # Bornes de sécurité
        lambda_home = max(0.3, min(lambda_home, 4.0))
        lambda_away = max(0.3, min(lambda_away, 4.0))

        logger.debug(f"{home_team} vs {away_team}: λH={lambda_home:.2f}, λA={lambda_away:.2f}")

        # 4. Générer la matrice Dixon-Coles
        return self.dixon_coles.calculate_score_matrix(lambda_home, lambda_away)

    # ═══════════════════════════════════════════════════════════════════
    # PRÉDICTIONS SPÉCIFIQUES
    # ═══════════════════════════════════════════════════════════════════

    def predict_over(self, home_team: str, away_team: str,
                     threshold: float, bookmaker_odds: float = None,
                     **kwargs) -> Prediction:
        """
        Prédit Over X.5 goals

        Args:
            threshold: Seuil (ex: 2.5 pour Over 2.5)
            bookmaker_odds: Cote du bookmaker
        """
        self.market_name = f"over_{str(threshold).replace('.', '')}"

        matrix = self._generate_score_matrix(home_team, away_team, **kwargs)
        prob = matrix.prob_over(threshold)

        return self._build_prediction(
            home_team, away_team, prob, bookmaker_odds,
            explanation=f"Over {threshold} goals"
        )

    def predict_under(self, home_team: str, away_team: str,
                      threshold: float, bookmaker_odds: float = None,
                      **kwargs) -> Prediction:
        """Prédit Under X.5 goals"""
        self.market_name = f"under_{str(threshold).replace('.', '')}"

        matrix = self._generate_score_matrix(home_team, away_team, **kwargs)
        prob = matrix.prob_under(threshold)

        return self._build_prediction(
            home_team, away_team, prob, bookmaker_odds,
            explanation=f"Under {threshold} goals"
        )

    def predict_btts(self, home_team: str, away_team: str,
                     yes: bool = True, bookmaker_odds: float = None,
                     **kwargs) -> Prediction:
        """Prédit BTTS Yes/No"""
        self.market_name = "btts_yes" if yes else "btts_no"

        matrix = self._generate_score_matrix(home_team, away_team, **kwargs)
        prob = matrix.prob_btts_yes() if yes else matrix.prob_btts_no()

        return self._build_prediction(
            home_team, away_team, prob, bookmaker_odds,
            explanation=f"BTTS {'Yes' if yes else 'No'}"
        )

    def predict_score_exact(self, home_team: str, away_team: str,
                            home_goals: int, away_goals: int,
                            bookmaker_odds: float = None,
                            **kwargs) -> Prediction:
        """Prédit un score exact"""
        self.market_name = f"score_{home_goals}_{away_goals}"

        matrix = self._generate_score_matrix(home_team, away_team, **kwargs)
        prob = matrix.get_prob(home_goals, away_goals)

        return self._build_prediction(
            home_team, away_team, prob, bookmaker_odds,
            explanation=f"Score exact {home_goals}-{away_goals}"
        )

    def predict_1x2(self, home_team: str, away_team: str,
                    outcome: str = "home", bookmaker_odds: float = None,
                    **kwargs) -> Prediction:
        """
        Prédit 1X2

        Args:
            outcome: "home", "draw", ou "away"
        """
        self.market_name = outcome

        matrix = self._generate_score_matrix(home_team, away_team, **kwargs)

        if outcome == "home":
            prob = matrix.prob_home_win()
        elif outcome == "draw":
            prob = matrix.prob_draw()
        else:
            prob = matrix.prob_away_win()

        return self._build_prediction(
            home_team, away_team, prob, bookmaker_odds,
            explanation=f"1X2: {outcome.capitalize()}"
        )

    def predict_clean_sheet(self, home_team: str, away_team: str,
                            team: str = "home", bookmaker_odds: float = None,
                            **kwargs) -> Prediction:
        """Prédit Clean Sheet pour une équipe"""
        self.market_name = f"clean_sheet_{team}"

        matrix = self._generate_score_matrix(home_team, away_team, **kwargs)
        prob = matrix.prob_clean_sheet(team)

        team_name = home_team if team == "home" else away_team
        return self._build_prediction(
            home_team, away_team, prob, bookmaker_odds,
            explanation=f"Clean Sheet for {team_name}"
        )

    # ═══════════════════════════════════════════════════════════════════
    # PRÉDICTIONS EN MASSE
    # ═══════════════════════════════════════════════════════════════════

    def predict_all_goals_markets(self, home_team: str, away_team: str,
                                   bookmaker_odds: Dict[str, float] = None,
                                   **kwargs) -> Dict[str, Prediction]:
        """
        Prédit TOUS les marchés de buts en une seule fois

        Args:
            home_team: Équipe à domicile
            away_team: Équipe à l'extérieur
            bookmaker_odds: Dict des cotes {market: odds}

        Returns:
            Dict des prédictions {market: Prediction}
        """
        bookmaker_odds = bookmaker_odds or {}

        # Générer la matrice une seule fois
        matrix = self._generate_score_matrix(home_team, away_team, **kwargs)
        all_probs = get_all_market_probabilities(matrix)

        predictions = {}

        for market, prob in all_probs.items():
            odds = bookmaker_odds.get(market)

            self.market_name = market
            predictions[market] = self._build_prediction(
                home_team, away_team, prob, odds,
                explanation=f"{market}: {prob*100:.1f}%"
            )

        return predictions

    def get_most_likely_scores(self, home_team: str, away_team: str,
                                n: int = 5, **kwargs) -> List[dict]:
        """Retourne les N scores les plus probables"""
        matrix = self._generate_score_matrix(home_team, away_team, **kwargs)

        scores = matrix.most_likely_scores(n)

        return [
            {
                "score": f"{h}-{a}",
                "probability": round(prob * 100, 2),
                "fair_odds": round(1/prob, 2) if prob > 0.001 else 999
            }
            for (h, a), prob in scores
        ]

    # ═══════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════

    def _build_prediction(self, home: str, away: str, prob: float,
                          bookmaker_odds: float = None,
                          explanation: str = "") -> Prediction:
        """Helper pour construire une Prediction"""
        return self.predict(
            home_team=home,
            away_team=away,
            bookmaker_odds=bookmaker_odds
        )


# ═══════════════════════════════════════════════════════════════════════
# SPECIFIC PREDICTORS (pour compatibilité)
# ═══════════════════════════════════════════════════════════════════════

class Over25Predictor(GoalsPredictor):
    """Prédicteur spécialisé Over 2.5"""
    market_name = "over_25"

    def calculate_probability(self, home_team: str, away_team: str, **kwargs) -> float:
        matrix = self._generate_score_matrix(home_team, away_team, **kwargs)
        return matrix.prob_over(2.5)


class BTTSPredictor(GoalsPredictor):
    """Prédicteur spécialisé BTTS"""
    market_name = "btts_yes"

    def calculate_probability(self, home_team: str, away_team: str, **kwargs) -> float:
        matrix = self._generate_score_matrix(home_team, away_team, **kwargs)
        return matrix.prob_btts_yes()
