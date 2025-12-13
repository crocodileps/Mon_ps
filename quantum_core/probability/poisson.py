"""
QUANTUM CORE - PROBABILITY MODULE
=================================
Modèles probabilistes pour prédiction de scores

MODÈLES IMPLÉMENTÉS:
✅ Double Poisson (calcul séparé home/away)
✅ Dixon-Coles (correction scores faibles)
✅ Matrice de scores complète
✅ Calcul de tous les marchés goals

Référence: Dixon & Coles (1997) - "Modelling Association Football Scores"
"""

import math
from typing import Dict, Tuple, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScoreMatrix:
    """Matrice des probabilités de scores"""
    probabilities: Dict[Tuple[int, int], float]
    lambda_home: float
    lambda_away: float
    rho: float  # Paramètre Dixon-Coles

    def get_prob(self, home: int, away: int) -> float:
        """Probabilité d'un score exact"""
        return self.probabilities.get((home, away), 0.0)

    def prob_over(self, threshold: float) -> float:
        """P(total > threshold)"""
        prob = 0.0
        for (h, a), p in self.probabilities.items():
            if h + a > threshold:
                prob += p
        return prob

    def prob_under(self, threshold: float) -> float:
        """P(total < threshold)"""
        return 1.0 - self.prob_over(threshold - 0.01)

    def prob_btts_yes(self) -> float:
        """P(les deux équipes marquent)"""
        prob = 0.0
        for (h, a), p in self.probabilities.items():
            if h > 0 and a > 0:
                prob += p
        return prob

    def prob_btts_no(self) -> float:
        """P(au moins une équipe ne marque pas)"""
        return 1.0 - self.prob_btts_yes()

    def prob_home_win(self) -> float:
        """P(victoire domicile)"""
        prob = 0.0
        for (h, a), p in self.probabilities.items():
            if h > a:
                prob += p
        return prob

    def prob_draw(self) -> float:
        """P(match nul)"""
        prob = 0.0
        for (h, a), p in self.probabilities.items():
            if h == a:
                prob += p
        return prob

    def prob_away_win(self) -> float:
        """P(victoire extérieur)"""
        prob = 0.0
        for (h, a), p in self.probabilities.items():
            if a > h:
                prob += p
        return prob

    def prob_team_over(self, team: str, threshold: float) -> float:
        """P(équipe marque > threshold buts)"""
        prob = 0.0
        for (h, a), p in self.probabilities.items():
            goals = h if team == "home" else a
            if goals > threshold:
                prob += p
        return prob

    def prob_clean_sheet(self, team: str) -> float:
        """P(clean sheet pour une équipe)"""
        prob = 0.0
        for (h, a), p in self.probabilities.items():
            if team == "home" and a == 0:
                prob += p
            elif team == "away" and h == 0:
                prob += p
        return prob

    def most_likely_scores(self, n: int = 5) -> List[Tuple[Tuple[int, int], float]]:
        """Retourne les n scores les plus probables"""
        sorted_scores = sorted(
            self.probabilities.items(),
            key=lambda x: -x[1]
        )
        return sorted_scores[:n]


class PoissonModel:
    """
    Modèle Poisson Simple

    Usage:
        model = PoissonModel(lambda_=2.5)
        prob_2_goals = model.pmf(2)
        prob_over_2 = model.prob_over(2)
    """

    def __init__(self, lambda_: float):
        """
        Args:
            lambda_: Espérance (moyenne) de buts
        """
        self.lambda_ = max(lambda_, 0.001)  # Protection division par zéro

    def pmf(self, k: int) -> float:
        """
        Probability Mass Function: P(X = k)

        Args:
            k: Nombre de buts

        Returns:
            Probabilité d'exactement k buts
        """
        if k < 0:
            return 0.0

        # P(X=k) = (λ^k * e^(-λ)) / k!
        return (self.lambda_ ** k) * math.exp(-self.lambda_) / math.factorial(k)

    def prob_over(self, threshold: float) -> float:
        """
        P(X > threshold)

        Args:
            threshold: Seuil (ex: 2.5 pour Over 2.5)

        Returns:
            Probabilité de dépasser le seuil
        """
        # P(X > threshold) = 1 - P(X <= floor(threshold))
        prob_under = sum(self.pmf(k) for k in range(int(threshold) + 1))
        return 1.0 - prob_under

    def prob_under(self, threshold: float) -> float:
        """P(X < threshold)"""
        return 1.0 - self.prob_over(threshold - 0.01)

    def prob_exact(self, k: int) -> float:
        """Alias pour pmf"""
        return self.pmf(k)


class DixonColesModel:
    """
    Modèle Dixon-Coles pour prédiction de scores de football

    Amélioration du Poisson simple:
    - Calcul séparé des lambdas home/away
    - Correction de dépendance pour scores faibles (0-0, 1-0, 0-1, 1-1)
    - Paramètre rho pour la corrélation

    Référence: Dixon & Coles (1997)

    Usage:
        model = DixonColesModel()
        matrix = model.calculate_score_matrix(
            lambda_home=1.8,
            lambda_away=1.2
        )
        prob_over_25 = matrix.prob_over(2.5)
    """

    # Paramètre de corrélation par défaut (optimisé sur données historiques)
    DEFAULT_RHO = -0.13

    # Scores maximum à considérer
    MAX_GOALS = 8

    def __init__(self, rho: float = None):
        """
        Args:
            rho: Paramètre de corrélation (-0.13 typique pour football)
                 Négatif = les scores faibles sont plus probables
        """
        self.rho = rho if rho is not None else self.DEFAULT_RHO

    @staticmethod
    def poisson_pmf(k: int, lambda_: float) -> float:
        """
        Fonction de masse Poisson

        P(X=k) = (λ^k * e^(-λ)) / k!
        """
        if k < 0 or lambda_ <= 0:
            return 0.0

        return (lambda_ ** k) * math.exp(-lambda_) / math.factorial(k)

    def tau_adjustment(self, home_goals: int, away_goals: int,
                       lambda_home: float, lambda_away: float) -> float:
        """
        Facteur d'ajustement Dixon-Coles (tau)

        Corrige les probabilités pour les scores faibles (0-0, 1-0, 0-1, 1-1)
        qui sont systématiquement sous-estimés par le Poisson simple.

        Args:
            home_goals: Buts domicile
            away_goals: Buts extérieur
            lambda_home: Espérance buts domicile
            lambda_away: Espérance buts extérieur

        Returns:
            Facteur multiplicatif tau
        """
        if home_goals == 0 and away_goals == 0:
            # Score 0-0: augmente la probabilité
            tau = 1.0 - lambda_home * lambda_away * self.rho
        elif home_goals == 0 and away_goals == 1:
            # Score 0-1
            tau = 1.0 + lambda_home * self.rho
        elif home_goals == 1 and away_goals == 0:
            # Score 1-0
            tau = 1.0 + lambda_away * self.rho
        elif home_goals == 1 and away_goals == 1:
            # Score 1-1: diminue légèrement
            tau = 1.0 - self.rho
        else:
            # Pas d'ajustement pour scores > 1
            tau = 1.0

        return max(tau, 0.0)  # Tau ne peut pas être négatif

    def score_probability(self, home_goals: int, away_goals: int,
                          lambda_home: float, lambda_away: float) -> float:
        """
        Probabilité d'un score exact avec ajustement Dixon-Coles

        P(H=h, A=a) = Poisson(h|λ_H) * Poisson(a|λ_A) * τ(h,a)

        Args:
            home_goals: Buts domicile
            away_goals: Buts extérieur
            lambda_home: Espérance buts domicile
            lambda_away: Espérance buts extérieur

        Returns:
            Probabilité du score
        """
        # Probabilité Poisson indépendante
        prob_home = self.poisson_pmf(home_goals, lambda_home)
        prob_away = self.poisson_pmf(away_goals, lambda_away)

        # Ajustement Dixon-Coles
        tau = self.tau_adjustment(home_goals, away_goals, lambda_home, lambda_away)

        return prob_home * prob_away * tau

    def calculate_score_matrix(self, lambda_home: float, lambda_away: float,
                                max_goals: int = None) -> ScoreMatrix:
        """
        Calcule la matrice complète des probabilités de scores

        Args:
            lambda_home: Espérance buts domicile (xG ajusté)
            lambda_away: Espérance buts extérieur (xG ajusté)
            max_goals: Nombre max de buts à considérer (défaut: 8)

        Returns:
            ScoreMatrix avec toutes les probabilités
        """
        max_g = max_goals or self.MAX_GOALS

        probabilities = {}
        total_prob = 0.0

        for h in range(max_g + 1):
            for a in range(max_g + 1):
                prob = self.score_probability(h, a, lambda_home, lambda_away)
                probabilities[(h, a)] = prob
                total_prob += prob

        # Normaliser (les probabilités doivent sommer à 1)
        if total_prob > 0 and abs(total_prob - 1.0) > 0.001:
            for key in probabilities:
                probabilities[key] /= total_prob

        return ScoreMatrix(
            probabilities=probabilities,
            lambda_home=lambda_home,
            lambda_away=lambda_away,
            rho=self.rho
        )

    def calculate_lambdas(self, home_xg: float, away_xga: float,
                          away_xg: float, home_xga: float,
                          league_avg: float = 1.40) -> Tuple[float, float]:
        """
        Calcule les lambdas (espérances de buts) pour un match

        Méthode: Force d'attaque vs Faiblesse de défense normalisée

        λ_home = (xG_home / league_avg) * (xGA_away / league_avg) * league_avg
        λ_away = (xG_away / league_avg) * (xGA_home / league_avg) * league_avg

        Args:
            home_xg: xG moyen de l'équipe à domicile (attaque)
            away_xga: xGA moyen de l'équipe à l'extérieur (défense)
            away_xg: xG moyen de l'équipe à l'extérieur (attaque)
            home_xga: xGA moyen de l'équipe à domicile (défense)
            league_avg: Moyenne de buts par match dans la ligue

        Returns:
            Tuple (lambda_home, lambda_away)
        """
        # Protection division par zéro
        league_avg = max(league_avg, 0.5)

        # Force d'attaque relative
        home_attack = home_xg / league_avg
        away_attack = away_xg / league_avg

        # Faiblesse de défense relative
        away_defense = away_xga / league_avg
        home_defense = home_xga / league_avg

        # Lambdas
        lambda_home = home_attack * away_defense * league_avg
        lambda_away = away_attack * home_defense * league_avg

        # Bornes raisonnables
        lambda_home = max(0.3, min(lambda_home, 4.5))
        lambda_away = max(0.3, min(lambda_away, 4.5))

        return lambda_home, lambda_away


# ═══════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def calculate_match_probabilities(home_xg: float, away_xg: float,
                                   home_xga: float, away_xga: float,
                                   friction: float = 1.0,
                                   form_home: float = 1.0,
                                   form_away: float = 1.0) -> ScoreMatrix:
    """
    Fonction principale pour calculer les probabilités d'un match

    Args:
        home_xg: xG moyen équipe domicile
        away_xg: xG moyen équipe extérieur
        home_xga: xGA moyen équipe domicile
        away_xga: xGA moyen équipe extérieur
        friction: Multiplicateur de friction tactique (1.0 = neutre)
        form_home: Multiplicateur forme domicile
        form_away: Multiplicateur forme extérieur

    Returns:
        ScoreMatrix avec toutes les probabilités
    """
    model = DixonColesModel()

    # Calculer les lambdas de base
    lambda_home, lambda_away = model.calculate_lambdas(
        home_xg=home_xg,
        away_xga=away_xga,
        away_xg=away_xg,
        home_xga=home_xga
    )

    # Appliquer les ajustements
    lambda_home *= friction * form_home
    lambda_away *= friction * form_away

    # Générer la matrice
    return model.calculate_score_matrix(lambda_home, lambda_away)


def get_all_market_probabilities(matrix: ScoreMatrix) -> Dict[str, float]:
    """
    Extrait toutes les probabilités de marchés depuis une ScoreMatrix

    Returns:
        Dict avec tous les marchés et leurs probabilités
    """
    return {
        # 1X2
        "home_win": matrix.prob_home_win(),
        "draw": matrix.prob_draw(),
        "away_win": matrix.prob_away_win(),

        # Double Chance
        "dc_1x": matrix.prob_home_win() + matrix.prob_draw(),
        "dc_12": matrix.prob_home_win() + matrix.prob_away_win(),
        "dc_x2": matrix.prob_draw() + matrix.prob_away_win(),

        # Goals Over
        "over_05": matrix.prob_over(0.5),
        "over_15": matrix.prob_over(1.5),
        "over_25": matrix.prob_over(2.5),
        "over_35": matrix.prob_over(3.5),
        "over_45": matrix.prob_over(4.5),

        # Goals Under
        "under_15": matrix.prob_under(1.5),
        "under_25": matrix.prob_under(2.5),
        "under_35": matrix.prob_under(3.5),
        "under_45": matrix.prob_under(4.5),

        # BTTS
        "btts_yes": matrix.prob_btts_yes(),
        "btts_no": matrix.prob_btts_no(),

        # Team Goals
        "home_over_05": matrix.prob_team_over("home", 0.5),
        "home_over_15": matrix.prob_team_over("home", 1.5),
        "away_over_05": matrix.prob_team_over("away", 0.5),
        "away_over_15": matrix.prob_team_over("away", 1.5),

        # Clean Sheets
        "clean_sheet_home": matrix.prob_clean_sheet("home"),
        "clean_sheet_away": matrix.prob_clean_sheet("away"),

        # Scores exacts (top 10)
        "score_0_0": matrix.get_prob(0, 0),
        "score_1_0": matrix.get_prob(1, 0),
        "score_0_1": matrix.get_prob(0, 1),
        "score_1_1": matrix.get_prob(1, 1),
        "score_2_0": matrix.get_prob(2, 0),
        "score_0_2": matrix.get_prob(0, 2),
        "score_2_1": matrix.get_prob(2, 1),
        "score_1_2": matrix.get_prob(1, 2),
        "score_2_2": matrix.get_prob(2, 2),
        "score_3_0": matrix.get_prob(3, 0),
    }
