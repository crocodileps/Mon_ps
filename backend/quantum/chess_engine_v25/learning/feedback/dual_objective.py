"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    DUAL OBJECTIVE LEARNER                                                ║
║                    Apprentissage Accuracy (40%) + Profit (60%)                           ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  Principe:                                                                               ║
║  - On ne veut pas juste classifier correctement                                         ║
║  - On veut classifier d'une manière qui GÉNÈRE DU PROFIT                               ║
║  - Une erreur qui coûte 10 unités > une erreur qui coûte 0.5 unité                     ║
║                                                                                          ║
║  Formule:                                                                                ║
║  Score = α × Accuracy + β × Profit_Score                                                ║
║  Avec α = 0.4 et β = 0.6 (profit plus important)                                        ║
║                                                                                          ║
║  Auteur: Mya & Claude | Version: 1.0.0 | Date: 12 Décembre 2025                         ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np


@dataclass
class LearningEvent:
    """Événement d'apprentissage avec les deux objectifs"""
    timestamp: datetime
    model_name: str
    was_correct: bool
    profit: float
    accuracy_score: float
    profit_score: float
    combined_score: float
    weight_adjustment: float


class DualObjectiveLearner:
    """
    Apprentissage dual optimisant:
    1. Accuracy de classification (40%)
    2. Profit généré par les paris (60%)

    Le profit est plus important car c'est l'objectif final du système.
    Une classification correcte qui ne génère pas de profit a moins de valeur
    qu'une classification qui génère du profit.
    """

    def __init__(self, alpha: float = 0.4, beta: float = 0.6,
                 profit_normalization: float = 5.0,
                 min_weight: float = 0.3, max_weight: float = 2.0):
        """
        Initialize dual objective learner

        Args:
            alpha: Poids pour l'accuracy (défaut 0.4 = 40%)
            beta: Poids pour le profit (défaut 0.6 = 60%)
            profit_normalization: Facteur pour normaliser les profits
            min_weight: Poids minimum pour un modèle
            max_weight: Poids maximum pour un modèle
        """
        if not np.isclose(alpha + beta, 1.0):
            raise ValueError("alpha + beta doit égaler 1.0")

        self.alpha = alpha
        self.beta = beta
        self.profit_normalization = profit_normalization
        self.min_weight = min_weight
        self.max_weight = max_weight

        # Historique des événements
        self.events: List[LearningEvent] = []

        # Statistiques par modèle
        self.model_stats: Dict[str, Dict] = {}

    def calculate_accuracy_score(self, was_correct: bool) -> float:
        """
        Score d'accuracy binaire

        Args:
            was_correct: True si classification correcte

        Returns:
            Score 0 ou 1
        """
        return 1.0 if was_correct else 0.0

    def calculate_profit_score(self, profit: float) -> float:
        """
        Score de profit normalisé entre 0 et 1

        Utilise tanh pour borner le profit à [-1, 1] puis ramène à [0, 1]

        Args:
            profit: Profit en unités (peut être négatif)

        Returns:
            Score entre 0 et 1
        """
        # Normaliser avec tanh (borne à [-1, 1])
        normalized = np.tanh(profit / self.profit_normalization)

        # Ramener à [0, 1]
        return (normalized + 1) / 2

    def calculate_combined_score(self, was_correct: bool, profit: float) -> Tuple[float, float, float]:
        """
        Score combiné avec les deux objectifs

        Args:
            was_correct: True si classification correcte
            profit: Profit en unités

        Returns:
            Tuple (accuracy_score, profit_score, combined_score)
        """
        accuracy_score = self.calculate_accuracy_score(was_correct)
        profit_score = self.calculate_profit_score(profit)

        combined = self.alpha * accuracy_score + self.beta * profit_score

        return accuracy_score, profit_score, combined

    def calculate_weight_adjustment(self, combined_score: float) -> float:
        """
        Facteur d'ajustement du poids d'un modèle selon son score

        Args:
            combined_score: Score combiné entre 0 et 1

        Returns:
            Facteur multiplicatif (ex: 1.08 = +8%)
        """
        # Échelle progressive
        if combined_score > 0.8:
            return 1.10  # +10% - Excellent
        elif combined_score > 0.7:
            return 1.06  # +6% - Très bon
        elif combined_score > 0.6:
            return 1.02  # +2% - Bon
        elif combined_score > 0.5:
            return 1.00  # Stable - Moyen
        elif combined_score > 0.4:
            return 0.98  # -2% - Sous la moyenne
        elif combined_score > 0.3:
            return 0.94  # -6% - Mauvais
        else:
            return 0.90  # -10% - Très mauvais

    def process_feedback(self, model_name: str, was_correct: bool,
                        profit: float, current_weight: float) -> Tuple[float, LearningEvent]:
        """
        Traiter un feedback et calculer le nouveau poids

        Args:
            model_name: Nom du modèle
            was_correct: Si la prédiction était correcte
            profit: Profit généré
            current_weight: Poids actuel du modèle

        Returns:
            Tuple (nouveau_poids, événement)
        """
        # Calculer les scores
        accuracy_score, profit_score, combined_score = self.calculate_combined_score(
            was_correct, profit
        )

        # Calculer l'ajustement
        adjustment = self.calculate_weight_adjustment(combined_score)

        # Calculer le nouveau poids (borné)
        new_weight = current_weight * adjustment
        new_weight = np.clip(new_weight, self.min_weight, self.max_weight)

        # Créer l'événement
        event = LearningEvent(
            timestamp=datetime.now(),
            model_name=model_name,
            was_correct=was_correct,
            profit=profit,
            accuracy_score=accuracy_score,
            profit_score=profit_score,
            combined_score=combined_score,
            weight_adjustment=adjustment
        )

        # Enregistrer
        self.events.append(event)
        self._update_model_stats(model_name, event)

        return new_weight, event

    def _update_model_stats(self, model_name: str, event: LearningEvent):
        """Mettre à jour les statistiques d'un modèle"""
        if model_name not in self.model_stats:
            self.model_stats[model_name] = {
                "total_events": 0,
                "correct": 0,
                "total_profit": 0,
                "combined_scores": [],
                "last_10_accuracy": [],
                "last_10_profit": []
            }

        stats = self.model_stats[model_name]
        stats["total_events"] += 1
        stats["correct"] += 1 if event.was_correct else 0
        stats["total_profit"] += event.profit
        stats["combined_scores"].append(event.combined_score)

        # Garder les 10 derniers pour tendance
        stats["last_10_accuracy"].append(event.accuracy_score)
        stats["last_10_profit"].append(event.profit)
        if len(stats["last_10_accuracy"]) > 10:
            stats["last_10_accuracy"].pop(0)
            stats["last_10_profit"].pop(0)

    def get_model_performance(self, model_name: str) -> Optional[Dict]:
        """
        Obtenir les performances d'un modèle

        Args:
            model_name: Nom du modèle

        Returns:
            Dict avec les métriques ou None
        """
        if model_name not in self.model_stats:
            return None

        stats = self.model_stats[model_name]
        n = stats["total_events"]

        if n == 0:
            return None

        return {
            "model": model_name,
            "total_predictions": n,
            "accuracy": stats["correct"] / n,
            "total_profit": stats["total_profit"],
            "avg_profit_per_prediction": stats["total_profit"] / n,
            "avg_combined_score": np.mean(stats["combined_scores"]),
            "recent_accuracy": np.mean(stats["last_10_accuracy"]) if stats["last_10_accuracy"] else 0,
            "recent_profit": sum(stats["last_10_profit"]) if stats["last_10_profit"] else 0,
            "trend": self._calculate_trend(stats)
        }

    def _calculate_trend(self, stats: Dict) -> str:
        """Calculer la tendance récente"""
        scores = stats["combined_scores"]
        if len(scores) < 20:
            return "insufficient_data"

        recent = np.mean(scores[-10:])
        previous = np.mean(scores[-20:-10])

        diff = recent - previous
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        else:
            return "stable"

    def compare_models(self) -> List[Dict]:
        """
        Comparer tous les modèles

        Returns:
            Liste triée par score combiné moyen
        """
        performances = []
        for model_name in self.model_stats:
            perf = self.get_model_performance(model_name)
            if perf:
                performances.append(perf)

        # Trier par score combiné moyen
        return sorted(performances, key=lambda x: -x["avg_combined_score"])

    def get_learning_curve(self, model_name: str, window: int = 20) -> List[float]:
        """
        Obtenir la courbe d'apprentissage (moving average du score combiné)

        Args:
            model_name: Nom du modèle
            window: Taille de la fenêtre pour la moyenne mobile

        Returns:
            Liste des scores moyens
        """
        if model_name not in self.model_stats:
            return []

        scores = self.model_stats[model_name]["combined_scores"]
        if len(scores) < window:
            return scores

        # Moving average
        curve = []
        for i in range(window - 1, len(scores)):
            window_scores = scores[i - window + 1:i + 1]
            curve.append(np.mean(window_scores))

        return curve

    def should_adjust_alpha_beta(self) -> Optional[Dict]:
        """
        Suggérer un ajustement des poids alpha/beta

        Si l'accuracy est excellente mais le profit mauvais, suggérer
        d'augmenter beta. Et vice versa.

        Returns:
            Dict avec suggestion ou None
        """
        if len(self.events) < 100:
            return None

        # Analyser les 50 derniers événements
        recent = self.events[-50:]

        avg_accuracy = np.mean([e.accuracy_score for e in recent])
        avg_profit = np.mean([e.profit for e in recent])

        # Cas: Bonne accuracy mais mauvais profit
        if avg_accuracy > 0.7 and avg_profit < 0:
            return {
                "suggestion": "increase_beta",
                "reason": f"High accuracy ({avg_accuracy:.1%}) but negative profit ({avg_profit:.2f}u)",
                "new_alpha": max(0.3, self.alpha - 0.05),
                "new_beta": min(0.7, self.beta + 0.05)
            }

        # Cas: Mauvaise accuracy mais bon profit
        if avg_accuracy < 0.5 and avg_profit > 2:
            return {
                "suggestion": "increase_alpha",
                "reason": f"Low accuracy ({avg_accuracy:.1%}) but good profit ({avg_profit:.2f}u)",
                "new_alpha": min(0.5, self.alpha + 0.05),
                "new_beta": max(0.5, self.beta - 0.05)
            }

        return None

    def apply_weights_adjustment(self, new_alpha: float, new_beta: float):
        """
        Appliquer de nouveaux poids alpha/beta

        Args:
            new_alpha: Nouveau poids accuracy
            new_beta: Nouveau poids profit
        """
        if not np.isclose(new_alpha + new_beta, 1.0):
            raise ValueError("alpha + beta doit égaler 1.0")

        self.alpha = new_alpha
        self.beta = new_beta

    def get_summary(self) -> Dict:
        """Résumé global du learner"""
        if not self.events:
            return {
                "total_events": 0,
                "alpha": self.alpha,
                "beta": self.beta
            }

        return {
            "total_events": len(self.events),
            "alpha": self.alpha,
            "beta": self.beta,
            "overall_accuracy": np.mean([e.accuracy_score for e in self.events]),
            "overall_profit": sum(e.profit for e in self.events),
            "avg_combined_score": np.mean([e.combined_score for e in self.events]),
            "models_tracked": len(self.model_stats),
            "best_model": self.compare_models()[0]["model"] if self.model_stats else None,
            "adjustment_suggestion": self.should_adjust_alpha_beta()
        }


# Fonctions utilitaires pour calculs de loss

def weighted_cross_entropy(predicted_probs: np.ndarray, true_label: int,
                          profit: float, alpha: float = 0.4,
                          beta: float = 0.6) -> float:
    """
    Cross-entropy pondérée par le profit

    Les erreurs coûteuses ont un poids plus élevé dans la loss

    Args:
        predicted_probs: Probabilités prédites pour chaque classe
        true_label: Index de la vraie classe
        profit: Profit/perte associé
        alpha: Poids accuracy
        beta: Poids profit

    Returns:
        Loss value
    """
    # Cross-entropy standard
    ce_loss = -np.log(predicted_probs[true_label] + 1e-10)

    # Pondération par le profit
    # Si profit négatif (erreur coûteuse), augmenter le poids de la loss
    profit_weight = 1.0 + abs(profit) / 5 if profit < 0 else 1.0

    # Loss pondérée
    weighted_loss = ce_loss * profit_weight

    return weighted_loss


def profit_aware_loss(predicted: int, true: int, profit: float,
                     confidence: float) -> float:
    """
    Loss qui prend en compte le profit ET la confiance

    Une erreur avec haute confiance est pire qu'une erreur avec basse confiance

    Args:
        predicted: Classe prédite
        true: Vraie classe
        profit: Profit/perte
        confidence: Confiance de la prédiction

    Returns:
        Loss value
    """
    was_correct = (predicted == true)

    if was_correct:
        # Récompense si correct
        return -profit * confidence  # Négatif car on minimise
    else:
        # Pénalité si incorrect
        # Plus la confiance était haute, plus la pénalité est grande
        return abs(profit) * (1 + confidence)


# Export
__all__ = [
    "DualObjectiveLearner",
    "LearningEvent",
    "weighted_cross_entropy",
    "profit_aware_loss"
]
