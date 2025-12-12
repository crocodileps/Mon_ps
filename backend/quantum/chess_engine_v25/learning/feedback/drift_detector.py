"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    STYLE DRIFT DETECTOR                                                  ║
║                    Détection de changement de style tactique                             ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  Cas d'usage:                                                                            ║
║  - Nouveau coach (changement tactique)                                                   ║
║  - Blessures clés (adaptation forcée)                                                    ║
║  - Évolution progressive de l'équipe                                                     ║
║  - Changement de formation                                                               ║
║                                                                                          ║
║  Méthode:                                                                                ║
║  - Compare les métriques récentes vs historiques                                        ║
║  - Détecte les changements significatifs (Z-score > 2)                                  ║
║  - Suggère une reclassification                                                          ║
║                                                                                          ║
║  Auteur: Mya & Claude | Version: 1.0.0 | Date: 12 Décembre 2025                         ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import numpy as np


# Import TacticalProfile
from ..classifiers.rule_based import TacticalProfile


@dataclass
class DriftAlert:
    """
    Alerte de changement de style détecté

    Indique qu'une équipe a changé de comportement tactique
    et qu'elle devrait être reclassifiée
    """
    team_id: str
    drift_score: float  # Score de changement (Z-score moyen)
    changed_metrics: Dict[str, float]  # Métriques qui ont changé
    old_values: Dict[str, float]  # Anciennes valeurs moyennes
    new_values: Dict[str, float]  # Nouvelles valeurs moyennes
    old_profile: Optional[TacticalProfile] = None
    new_profile_suggestion: Optional[TacticalProfile] = None
    reason: str = ""
    detected_at: datetime = field(default_factory=datetime.now)
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL

    def to_dict(self) -> Dict:
        """Convertir en dict"""
        return {
            "team_id": self.team_id,
            "drift_score": self.drift_score,
            "changed_metrics": self.changed_metrics,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "old_profile": self.old_profile.value if self.old_profile else None,
            "new_profile_suggestion": self.new_profile_suggestion.value if self.new_profile_suggestion else None,
            "reason": self.reason,
            "detected_at": self.detected_at.isoformat(),
            "severity": self.severity
        }


@dataclass
class MetricHistory:
    """Historique d'une métrique pour une équipe"""
    values: List[float] = field(default_factory=list)
    dates: List[datetime] = field(default_factory=list)

    def add(self, value: float, date: Optional[datetime] = None):
        """Ajouter une valeur"""
        self.values.append(value)
        self.dates.append(date or datetime.now())

    def recent(self, n: int) -> List[float]:
        """N dernières valeurs"""
        return self.values[-n:] if len(self.values) >= n else self.values

    def old(self, n: int, skip_recent: int) -> List[float]:
        """N valeurs avant les skip_recent dernières"""
        if len(self.values) < n + skip_recent:
            return []
        return self.values[-(n + skip_recent):-skip_recent]


class StyleDriftDetector:
    """
    Détecte quand une équipe change de style tactique

    Utilise la méthode Z-score pour détecter les changements statistiquement
    significatifs dans les métriques clés.
    """

    # Métriques clés à surveiller
    KEY_METRICS = [
        'possession',              # Style offensif/défensif
        'ppda',                    # Pressing
        'verticality',             # Direct vs patient
        'pressing_intensity',      # Agressivité
        'crosses_per_90',          # Jeu sur les ailes
        'defensive_line_height',   # Hauteur du bloc
        'counter_attack_goals_pct', # Contre-attaque
        'pass_accuracy',           # Qualité de construction
        'shots_per_90',            # Production offensive
        'xg_per_90',               # Qualité des occasions
    ]

    # Seuils de gravité
    SEVERITY_THRESHOLDS = {
        "LOW": 1.5,       # Changement léger
        "MEDIUM": 2.0,    # Changement significatif
        "HIGH": 2.5,      # Changement important
        "CRITICAL": 3.0   # Transformation complète
    }

    def __init__(self, window_size: int = 8, z_threshold: float = 2.0,
                 min_history: int = 10):
        """
        Initialize drift detector

        Args:
            window_size: Taille de la fenêtre pour comparer (matchs)
            z_threshold: Seuil Z-score pour détecter un drift
            min_history: Minimum de matchs avant de pouvoir détecter
        """
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.min_history = min_history

        # Historique par équipe
        self.team_history: Dict[str, Dict[str, MetricHistory]] = {}

        # Profils actuels connus
        self.known_profiles: Dict[str, TacticalProfile] = {}

        # Alertes actives
        self.active_alerts: Dict[str, DriftAlert] = {}

        # Stats
        self.total_checks = 0
        self.drifts_detected = 0

    def update(self, team_id: str, metrics: Dict[str, float],
              match_date: Optional[datetime] = None,
              current_profile: Optional[TacticalProfile] = None):
        """
        Mettre à jour l'historique d'une équipe

        Args:
            team_id: ID de l'équipe
            metrics: Métriques du match
            match_date: Date du match
            current_profile: Profil actuel connu (optionnel)
        """
        if team_id not in self.team_history:
            self.team_history[team_id] = {
                metric: MetricHistory() for metric in self.KEY_METRICS
            }

        # Ajouter les métriques
        for metric in self.KEY_METRICS:
            if metric in metrics:
                self.team_history[team_id][metric].add(
                    metrics[metric],
                    match_date or datetime.now()
                )

        # Mettre à jour le profil connu
        if current_profile:
            self.known_profiles[team_id] = current_profile

    def check(self, team_id: str,
             current_metrics: Optional[Dict[str, float]] = None) -> Optional[DriftAlert]:
        """
        Vérifier si changement de style détecté pour une équipe

        Args:
            team_id: ID de l'équipe
            current_metrics: Métriques actuelles (optionnel, pour mise à jour)

        Returns:
            DriftAlert si changement détecté, None sinon
        """
        self.total_checks += 1

        # Mettre à jour si nouvelles métriques
        if current_metrics:
            self.update(team_id, current_metrics)

        # Vérifier qu'on a assez d'historique
        if team_id not in self.team_history:
            return None

        history = self.team_history[team_id]

        # Vérifier qu'on a assez de données
        sample_metric = list(history.values())[0]
        if len(sample_metric.values) < self.min_history:
            return None

        # Calculer le drift pour chaque métrique
        drift_scores = {}
        old_values = {}
        new_values = {}

        for metric, metric_history in history.items():
            if len(metric_history.values) < self.window_size * 2:
                continue

            # Valeurs récentes vs anciennes
            recent = metric_history.recent(self.window_size)
            old = metric_history.old(self.window_size, self.window_size)

            if not old:
                continue

            # Calculer Z-score
            recent_mean = np.mean(recent)
            old_mean = np.mean(old)
            old_std = np.std(old)

            # Éviter division par zéro
            if old_std < 0.01:
                old_std = 0.01

            z_score = abs(recent_mean - old_mean) / old_std

            if z_score > 1.0:  # Seuil minimum pour être notable
                drift_scores[metric] = z_score
                old_values[metric] = old_mean
                new_values[metric] = recent_mean

        # Aucun changement significatif
        if not drift_scores:
            # Nettoyer alerte active si existante
            if team_id in self.active_alerts:
                del self.active_alerts[team_id]
            return None

        # Score de drift global
        avg_drift = np.mean(list(drift_scores.values()))
        max_drift = max(drift_scores.values())

        # Déterminer la sévérité
        severity = "LOW"
        if max_drift >= self.SEVERITY_THRESHOLDS["CRITICAL"]:
            severity = "CRITICAL"
        elif max_drift >= self.SEVERITY_THRESHOLDS["HIGH"]:
            severity = "HIGH"
        elif max_drift >= self.SEVERITY_THRESHOLDS["MEDIUM"]:
            severity = "MEDIUM"

        # Seuil pour déclencher une alerte
        if avg_drift < self.z_threshold:
            return None

        self.drifts_detected += 1

        # Créer la description
        changed_metrics_str = ", ".join([
            f"{m} ({drift_scores[m]:.1f}σ)"
            for m in sorted(drift_scores.keys(), key=lambda x: -drift_scores[x])[:3]
        ])

        # Créer l'alerte
        alert = DriftAlert(
            team_id=team_id,
            drift_score=avg_drift,
            changed_metrics=drift_scores,
            old_values=old_values,
            new_values=new_values,
            old_profile=self.known_profiles.get(team_id),
            new_profile_suggestion=self._suggest_new_profile(new_values),
            reason=f"Style change detected: {changed_metrics_str}",
            severity=severity
        )

        # Stocker l'alerte active
        self.active_alerts[team_id] = alert

        return alert

    def _suggest_new_profile(self, new_values: Dict[str, float]) -> Optional[TacticalProfile]:
        """
        Suggérer un nouveau profil basé sur les nouvelles valeurs

        Simple heuristique basée sur les métriques dominantes
        """
        if not new_values:
            return None

        # Heuristiques simples
        possession = new_values.get('possession', 50)
        ppda = new_values.get('ppda', 10)
        verticality = new_values.get('verticality', 50)
        defensive_height = new_values.get('defensive_line_height', 40)

        # GEGENPRESS: PPDA très bas + possession moyenne
        if ppda < 8 and 45 < possession < 58:
            return TacticalProfile.GEGENPRESS

        # POSSESSION: Haute possession + PPDA moyen
        if possession > 58 and ppda > 12:
            return TacticalProfile.POSSESSION

        # DIRECT_ATTACK: Haute verticalité + basse possession
        if verticality > 65 and possession < 48:
            return TacticalProfile.DIRECT_ATTACK

        # LOW_BLOCK: Basse possession + ligne basse
        if possession < 42 and defensive_height < 35:
            return TacticalProfile.LOW_BLOCK

        # TRANSITION: Contre-attaque élevée
        counter = new_values.get('counter_attack_goals_pct', 0)
        if counter > 25:
            return TacticalProfile.TRANSITION

        # Par défaut: MID_BLOCK ou BALANCED
        if 42 <= possession <= 52:
            return TacticalProfile.MID_BLOCK

        return TacticalProfile.BALANCED

    def acknowledge_drift(self, team_id: str, new_profile: TacticalProfile):
        """
        Confirmer un changement de style et mettre à jour le profil connu

        Args:
            team_id: ID de l'équipe
            new_profile: Nouveau profil confirmé
        """
        self.known_profiles[team_id] = new_profile

        # Supprimer l'alerte active
        if team_id in self.active_alerts:
            del self.active_alerts[team_id]

    def get_team_trend(self, team_id: str, metric: str,
                      periods: int = 3) -> Optional[Dict]:
        """
        Obtenir la tendance d'une métrique pour une équipe

        Args:
            team_id: ID de l'équipe
            metric: Nom de la métrique
            periods: Nombre de périodes à analyser

        Returns:
            Dict avec trend info ou None
        """
        if team_id not in self.team_history:
            return None

        if metric not in self.team_history[team_id]:
            return None

        history = self.team_history[team_id][metric]

        if len(history.values) < periods * self.window_size:
            return None

        # Calculer la moyenne par période
        period_means = []
        for i in range(periods):
            start = -(i + 1) * self.window_size
            end = -i * self.window_size if i > 0 else None
            period_values = history.values[start:end]
            if period_values:
                period_means.append(np.mean(period_values))

        # Inverser pour avoir chronologique
        period_means = period_means[::-1]

        # Tendance
        if len(period_means) >= 2:
            trend = "increasing" if period_means[-1] > period_means[0] else "decreasing"
            change = period_means[-1] - period_means[0]
        else:
            trend = "stable"
            change = 0

        return {
            "metric": metric,
            "period_means": period_means,
            "current": period_means[-1] if period_means else None,
            "trend": trend,
            "total_change": change,
            "pct_change": change / period_means[0] * 100 if period_means and period_means[0] != 0 else 0
        }

    def get_active_alerts(self) -> List[DriftAlert]:
        """Liste des alertes actives"""
        return list(self.active_alerts.values())

    def get_stats(self) -> Dict:
        """Statistiques du détecteur"""
        return {
            "teams_tracked": len(self.team_history),
            "total_checks": self.total_checks,
            "drifts_detected": self.drifts_detected,
            "detection_rate": self.drifts_detected / self.total_checks if self.total_checks > 0 else 0,
            "active_alerts": len(self.active_alerts),
            "alerts_by_severity": {
                severity: sum(1 for a in self.active_alerts.values() if a.severity == severity)
                for severity in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            }
        }

    def clear_history(self, team_id: str):
        """Effacer l'historique d'une équipe (ex: nouveau coach)"""
        if team_id in self.team_history:
            del self.team_history[team_id]
        if team_id in self.known_profiles:
            del self.known_profiles[team_id]
        if team_id in self.active_alerts:
            del self.active_alerts[team_id]


# Export
__all__ = ["StyleDriftDetector", "DriftAlert"]
