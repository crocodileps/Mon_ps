"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    TEMPORAL DATA MANAGER                                                 ║
║                    Arsenal 2024 ≠ Arsenal 2025                                           ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  Principe:                                                                               ║
║  - Les données récentes comptent PLUS que les anciennes                                 ║
║  - Un match d'hier a plus de valeur qu'un match d'il y a 6 mois                        ║
║  - Au-delà de max_age_months, les données sont ignorées                                ║
║                                                                                          ║
║  Formule:                                                                                ║
║  weight = exp(-decay_rate × months_ago)                                                 ║
║                                                                                          ║
║  Exemples avec decay_rate = 0.1:                                                        ║
║  - Hier: 1.00                                                                            ║
║  - 1 mois: 0.90                                                                          ║
║  - 3 mois: 0.74                                                                          ║
║  - 6 mois: 0.55                                                                          ║
║  - 12 mois: 0.30 (presque ignoré)                                                       ║
║                                                                                          ║
║  Auteur: Mya & Claude | Version: 1.0.0 | Date: 12 Décembre 2025                         ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np


@dataclass
class WeightedDataPoint:
    """Point de donnée avec poids temporel"""
    data: Dict[str, Any]
    date: datetime
    temporal_weight: float
    age_days: int
    age_months: float

    def get(self, key: str, default: Any = None) -> Any:
        """Accès aux données comme un dict"""
        return self.data.get(key, default)


class TemporalDataManager:
    """
    Gestionnaire de pondération temporelle des données

    Les données récentes ont plus de poids que les anciennes.
    Cela permet de capturer l'état ACTUEL d'une équipe plutôt que
    son historique complet qui peut ne plus être pertinent.
    """

    def __init__(self, decay_rate: float = 0.1, max_age_months: int = 6,
                 min_weight_threshold: float = 0.05):
        """
        Initialize temporal data manager

        Args:
            decay_rate: Taux de décroissance par mois (0.1 = 10% par mois)
            max_age_months: Âge maximum des données en mois
            min_weight_threshold: Poids minimum pour garder une donnée
        """
        self.decay_rate = decay_rate
        self.max_age_months = max_age_months
        self.min_weight_threshold = min_weight_threshold

    def calculate_weight(self, data_date: datetime,
                        reference_date: Optional[datetime] = None) -> float:
        """
        Calculer le poids temporel d'une donnée

        Args:
            data_date: Date de la donnée
            reference_date: Date de référence (défaut: maintenant)

        Returns:
            Poids entre 0 et 1
        """
        if reference_date is None:
            reference_date = datetime.now()

        # Calculer l'âge
        delta = reference_date - data_date
        days_ago = max(0, delta.days)
        months_ago = days_ago / 30.0

        # Trop vieux → poids 0
        if months_ago > self.max_age_months:
            return 0.0

        # Décroissance exponentielle
        weight = np.exp(-self.decay_rate * months_ago)

        return float(weight)

    def filter_and_weight(self, data_points: List[Dict],
                         date_field: str = 'date',
                         reference_date: Optional[datetime] = None) -> List[WeightedDataPoint]:
        """
        Filtrer et pondérer une liste de données

        Args:
            data_points: Liste de dicts avec au moins un champ date
            date_field: Nom du champ contenant la date
            reference_date: Date de référence pour le calcul

        Returns:
            Liste de WeightedDataPoint triée par date décroissante
        """
        if reference_date is None:
            reference_date = datetime.now()

        weighted_data = []

        for point in data_points:
            # Extraire la date
            data_date = point.get(date_field)
            if data_date is None:
                continue

            # Convertir si string
            if isinstance(data_date, str):
                try:
                    data_date = datetime.fromisoformat(data_date.replace('Z', '+00:00'))
                except:
                    continue

            # Calculer le poids
            weight = self.calculate_weight(data_date, reference_date)

            # Ignorer si poids trop faible
            if weight < self.min_weight_threshold:
                continue

            # Calculer l'âge
            delta = reference_date - data_date
            age_days = max(0, delta.days)

            weighted_data.append(WeightedDataPoint(
                data=point,
                date=data_date,
                temporal_weight=weight,
                age_days=age_days,
                age_months=age_days / 30.0
            ))

        # Trier par date décroissante (plus récent d'abord)
        weighted_data.sort(key=lambda x: x.date, reverse=True)

        return weighted_data

    def weighted_average(self, data_points: List[WeightedDataPoint],
                        field: str, default: float = 0.0) -> float:
        """
        Calculer la moyenne pondérée d'un champ

        Args:
            data_points: Liste de WeightedDataPoint
            field: Champ à moyenner
            default: Valeur par défaut si pas de données

        Returns:
            Moyenne pondérée
        """
        if not data_points:
            return default

        total_weight = 0.0
        weighted_sum = 0.0

        for point in data_points:
            value = point.get(field)
            if value is not None:
                try:
                    weighted_sum += float(value) * point.temporal_weight
                    total_weight += point.temporal_weight
                except (ValueError, TypeError):
                    continue

        if total_weight == 0:
            return default

        return weighted_sum / total_weight

    def weighted_stats(self, data_points: List[WeightedDataPoint],
                      field: str) -> Dict[str, float]:
        """
        Calculer les statistiques pondérées d'un champ

        Args:
            data_points: Liste de WeightedDataPoint
            field: Champ à analyser

        Returns:
            Dict avec mean, std, min, max, count
        """
        values_and_weights = []

        for point in data_points:
            value = point.get(field)
            if value is not None:
                try:
                    values_and_weights.append((float(value), point.temporal_weight))
                except (ValueError, TypeError):
                    continue

        if not values_and_weights:
            return {
                "mean": 0, "std": 0, "min": 0, "max": 0,
                "count": 0, "total_weight": 0
            }

        values, weights = zip(*values_and_weights)
        values = np.array(values)
        weights = np.array(weights)

        # Normaliser les poids
        weights_norm = weights / weights.sum()

        # Moyenne pondérée
        mean = np.sum(values * weights_norm)

        # Écart-type pondéré
        variance = np.sum(weights_norm * (values - mean) ** 2)
        std = np.sqrt(variance)

        return {
            "mean": float(mean),
            "std": float(std),
            "min": float(values.min()),
            "max": float(values.max()),
            "count": len(values),
            "total_weight": float(weights.sum())
        }

    def aggregate_team_metrics(self, matches: List[Dict],
                              date_field: str = 'date',
                              metrics: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Agréger les métriques d'une équipe avec pondération temporelle

        Args:
            matches: Liste des matchs avec métriques
            date_field: Nom du champ date
            metrics: Liste des métriques à agréger (None = toutes)

        Returns:
            Dict des métriques agrégées
        """
        # Filtrer et pondérer
        weighted = self.filter_and_weight(matches, date_field)

        if not weighted:
            return {}

        # Déterminer les métriques à agréger
        if metrics is None:
            # Prendre toutes les clés numériques du premier match
            sample = weighted[0].data
            metrics = [
                k for k, v in sample.items()
                if isinstance(v, (int, float)) and k != date_field
            ]

        # Agréger chaque métrique
        aggregated = {}
        for metric in metrics:
            stats = self.weighted_stats(weighted, metric)
            aggregated[metric] = stats["mean"]
            aggregated[f"{metric}_std"] = stats["std"]

        # Ajouter des méta-informations
        aggregated["_n_matches"] = len(weighted)
        aggregated["_total_weight"] = sum(p.temporal_weight for p in weighted)
        aggregated["_oldest_match_days"] = weighted[-1].age_days if weighted else 0
        aggregated["_newest_match_days"] = weighted[0].age_days if weighted else 0

        return aggregated

    def detect_recent_change(self, matches: List[Dict],
                            metric: str,
                            date_field: str = 'date',
                            recent_n: int = 5) -> Optional[Dict]:
        """
        Détecter un changement récent dans une métrique

        Compare les N derniers matchs avec le reste

        Args:
            matches: Liste des matchs
            metric: Métrique à analyser
            date_field: Champ date
            recent_n: Nombre de matchs récents à considérer

        Returns:
            Dict avec info sur le changement ou None
        """
        weighted = self.filter_and_weight(matches, date_field)

        if len(weighted) < recent_n * 2:
            return None

        # Séparer récent vs ancien
        recent = weighted[:recent_n]
        older = weighted[recent_n:]

        # Calculer les stats
        recent_stats = self.weighted_stats(recent, metric)
        older_stats = self.weighted_stats(older, metric)

        # Calculer le Z-score du changement
        if older_stats["std"] < 0.01:
            older_stats["std"] = 0.01

        z_score = abs(recent_stats["mean"] - older_stats["mean"]) / older_stats["std"]

        # Déterminer la direction
        direction = "increase" if recent_stats["mean"] > older_stats["mean"] else "decrease"

        # Changement significatif si Z > 1.5
        is_significant = z_score > 1.5

        return {
            "metric": metric,
            "recent_mean": recent_stats["mean"],
            "older_mean": older_stats["mean"],
            "change": recent_stats["mean"] - older_stats["mean"],
            "change_pct": (recent_stats["mean"] - older_stats["mean"]) / older_stats["mean"] * 100 if older_stats["mean"] != 0 else 0,
            "z_score": z_score,
            "direction": direction,
            "is_significant": is_significant,
            "recent_n": recent_n,
            "total_n": len(weighted)
        }

    def get_weight_curve(self, months_range: int = 12) -> List[Dict]:
        """
        Obtenir la courbe des poids pour visualisation

        Args:
            months_range: Nombre de mois à afficher

        Returns:
            Liste de {months_ago, weight}
        """
        curve = []
        for months in range(0, months_range + 1):
            days = months * 30
            fake_date = datetime.now() - timedelta(days=days)
            weight = self.calculate_weight(fake_date)
            curve.append({
                "months_ago": months,
                "days_ago": days,
                "weight": weight,
                "weight_pct": weight * 100
            })
        return curve

    def get_info(self) -> Dict:
        """Information sur la configuration"""
        return {
            "decay_rate": self.decay_rate,
            "max_age_months": self.max_age_months,
            "min_weight_threshold": self.min_weight_threshold,
            "weight_at_1_month": self.calculate_weight(datetime.now() - timedelta(days=30)),
            "weight_at_3_months": self.calculate_weight(datetime.now() - timedelta(days=90)),
            "weight_at_6_months": self.calculate_weight(datetime.now() - timedelta(days=180)),
            "formula": f"weight = exp(-{self.decay_rate} × months_ago)"
        }


# Fonction utilitaire pour créer des poids pour scikit-learn

def create_sample_weights(dates: List[datetime],
                         decay_rate: float = 0.1,
                         reference_date: Optional[datetime] = None) -> np.ndarray:
    """
    Créer des poids temporels pour scikit-learn (sample_weight)

    Args:
        dates: Liste des dates des échantillons
        decay_rate: Taux de décroissance
        reference_date: Date de référence

    Returns:
        Array numpy des poids
    """
    manager = TemporalDataManager(decay_rate=decay_rate)

    if reference_date is None:
        reference_date = datetime.now()

    weights = np.array([
        manager.calculate_weight(d, reference_date) for d in dates
    ])

    # Normaliser pour que la somme = len(dates)
    weights = weights / weights.sum() * len(weights)

    return weights


# Export
__all__ = ["TemporalDataManager", "WeightedDataPoint", "create_sample_weights"]
