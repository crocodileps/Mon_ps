"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    ADAPTIVE BUFFER                                                       ║
║                    Buffer intelligent pour mise à jour du modèle                         ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  Problème: 1 match = bruit. Mettre à jour après chaque match = overfitting             ║
║  Solution: Buffer qui collecte N matchs avant de décider si mise à jour                ║
║                                                                                          ║
║  Comportement adaptatif:                                                                ║
║  - Modèle performant → buffer plus grand (moins de mises à jour)                       ║
║  - Beaucoup d'erreurs → buffer plus petit (plus réactif)                               ║
║  - Mise à jour urgente si trop d'erreurs récentes                                       ║
║                                                                                          ║
║  Tailles recommandées:                                                                   ║
║  - Minimum: 15 matchs (pattern minimum)                                                  ║
║  - Default: 25 matchs (~2-3 semaines de football)                                       ║
║  - Maximum: 40 matchs (stabilité max)                                                   ║
║                                                                                          ║
║  Auteur: Mya & Claude | Version: 1.0.0 | Date: 12 Décembre 2025                         ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import List, Dict, Optional, Generic, TypeVar, Callable
from datetime import datetime
from dataclasses import dataclass, field
import numpy as np

# Import TacticalProfile pour typing
from ..classifiers.rule_based import TacticalProfile


T = TypeVar('T')


@dataclass
class BufferEntry:
    """
    Entrée dans le buffer
    Représente un feedback après un match
    """
    team_id: str
    team_metrics: Dict[str, float]
    predicted_profile: TacticalProfile
    actual_behavior: TacticalProfile
    profit: float
    match_date: datetime
    was_correct: bool = field(init=False)
    temporal_weight: float = 1.0

    def __post_init__(self):
        self.was_correct = self.predicted_profile == self.actual_behavior


@dataclass
class BufferStats:
    """Statistiques du buffer"""
    current_size: int
    target_size: int
    min_size: int
    max_size: int
    accuracy: float
    total_profit: float
    error_rate_last_10: float
    should_update: bool
    reason: str


class AdaptiveBuffer:
    """
    Buffer adaptatif pour collecter des feedbacks avant mise à jour

    La taille du buffer s'adapte:
    - Si le modèle performe bien → on attend plus longtemps (stabilité)
    - Si le modèle fait des erreurs → on réagit plus vite
    """

    def __init__(self, min_size: int = 15, max_size: int = 40,
                 default_size: int = 25, urgent_error_threshold: float = 0.5):
        """
        Initialize adaptive buffer

        Args:
            min_size: Taille minimum avant de pouvoir update (15 matchs)
            max_size: Taille maximum du buffer (40 matchs)
            default_size: Taille cible par défaut (25 matchs)
            urgent_error_threshold: Taux d'erreur pour trigger urgent update
        """
        self.min_size = min_size
        self.max_size = max_size
        self.target_size = default_size
        self.urgent_error_threshold = urgent_error_threshold

        self.buffer: List[BufferEntry] = []

        # Historique des mises à jour
        self.update_history: List[Dict] = []

        # Stats globales
        self.total_entries_processed = 0
        self.total_updates = 0

    def add(self, team_id: str, team_metrics: Dict[str, float],
           predicted_profile: TacticalProfile, actual_behavior: TacticalProfile,
           profit: float, match_date: Optional[datetime] = None,
           temporal_weight: float = 1.0):
        """
        Ajouter une entrée au buffer

        Args:
            team_id: ID de l'équipe
            team_metrics: Métriques de l'équipe
            predicted_profile: Profil prédit
            actual_behavior: Comportement réel observé
            profit: Profit/perte du pari
            match_date: Date du match
            temporal_weight: Poids temporel
        """
        entry = BufferEntry(
            team_id=team_id,
            team_metrics=team_metrics,
            predicted_profile=predicted_profile,
            actual_behavior=actual_behavior,
            profit=profit,
            match_date=match_date or datetime.now(),
            temporal_weight=temporal_weight
        )

        self.buffer.append(entry)
        self.total_entries_processed += 1

    def should_update(self) -> bool:
        """
        Décider si une mise à jour du modèle est nécessaire

        Returns:
            True si mise à jour recommandée
        """
        # Pas assez de données
        if len(self.buffer) < self.min_size:
            return False

        # Buffer plein → mise à jour
        if len(self.buffer) >= self.target_size:
            return True

        # Condition urgente: trop d'erreurs récentes
        if self._check_urgent_update():
            return True

        return False

    def _check_urgent_update(self) -> bool:
        """
        Vérifier si mise à jour urgente nécessaire
        (trop d'erreurs récentes)
        """
        if len(self.buffer) < 10:
            return False

        # Regarder les 10 dernières entrées
        recent = self.buffer[-10:]
        error_rate = sum(1 for e in recent if not e.was_correct) / len(recent)

        # Si plus de 50% d'erreurs récentes → urgent
        if error_rate > self.urgent_error_threshold and len(self.buffer) >= self.min_size:
            return True

        return False

    def get_update_reason(self) -> str:
        """Raison de la mise à jour"""
        if len(self.buffer) < self.min_size:
            return "insufficient_data"

        if len(self.buffer) >= self.target_size:
            return "buffer_full"

        if self._check_urgent_update():
            recent = self.buffer[-10:]
            error_rate = sum(1 for e in recent if not e.was_correct) / len(recent)
            return f"urgent_high_error_rate_{error_rate:.1%}"

        return "no_update_needed"

    def get_and_clear(self) -> List[BufferEntry]:
        """
        Récupérer les données et vider le buffer

        Returns:
            Liste des entrées
        """
        data = self.buffer.copy()

        # Enregistrer dans l'historique
        self.update_history.append({
            "timestamp": datetime.now().isoformat(),
            "size": len(data),
            "accuracy": self._calculate_accuracy(data),
            "total_profit": sum(e.profit for e in data),
            "reason": self.get_update_reason()
        })

        self.buffer = []
        self.total_updates += 1

        return data

    def _calculate_accuracy(self, entries: List[BufferEntry]) -> float:
        """Calculer l'accuracy d'une liste d'entrées"""
        if not entries:
            return 0
        return sum(1 for e in entries if e.was_correct) / len(entries)

    def adjust_size(self, recent_accuracy: float):
        """
        Ajuster la taille cible selon la performance récente

        Args:
            recent_accuracy: Accuracy sur les dernières prédictions
        """
        old_size = self.target_size

        if recent_accuracy > 0.75:
            # Modèle stable → moins de mises à jour
            self.target_size = min(self.max_size, self.target_size + 3)
        elif recent_accuracy > 0.65:
            # Modèle correct → légère augmentation
            self.target_size = min(self.max_size, self.target_size + 1)
        elif recent_accuracy < 0.55:
            # Modèle instable → plus réactif
            self.target_size = max(self.min_size, self.target_size - 3)
        elif recent_accuracy < 0.60:
            # Modèle moyen → légère réduction
            self.target_size = max(self.min_size, self.target_size - 1)

        # Log si changement
        if old_size != self.target_size:
            print(f"Buffer size adjusted: {old_size} → {self.target_size} (accuracy: {recent_accuracy:.1%})")

    def get_stats(self) -> BufferStats:
        """
        Obtenir les statistiques actuelles

        Returns:
            BufferStats avec toutes les métriques
        """
        accuracy = self._calculate_accuracy(self.buffer) if self.buffer else 0
        total_profit = sum(e.profit for e in self.buffer) if self.buffer else 0

        # Error rate des 10 derniers
        recent = self.buffer[-10:] if len(self.buffer) >= 10 else self.buffer
        error_rate_last_10 = 1 - self._calculate_accuracy(recent) if recent else 0

        return BufferStats(
            current_size=len(self.buffer),
            target_size=self.target_size,
            min_size=self.min_size,
            max_size=self.max_size,
            accuracy=accuracy,
            total_profit=total_profit,
            error_rate_last_10=error_rate_last_10,
            should_update=self.should_update(),
            reason=self.get_update_reason()
        )

    def get_summary(self) -> Dict:
        """Résumé global du buffer"""
        stats = self.get_stats()

        # Analyser par équipe
        team_stats = {}
        for entry in self.buffer:
            if entry.team_id not in team_stats:
                team_stats[entry.team_id] = {"correct": 0, "total": 0, "profit": 0}
            team_stats[entry.team_id]["total"] += 1
            team_stats[entry.team_id]["correct"] += 1 if entry.was_correct else 0
            team_stats[entry.team_id]["profit"] += entry.profit

        # Top erreurs
        worst_teams = sorted(
            [(tid, ts["total"] - ts["correct"], ts["profit"]) for tid, ts in team_stats.items()],
            key=lambda x: -x[1]
        )[:5]

        return {
            "current_size": stats.current_size,
            "target_size": stats.target_size,
            "fill_percentage": stats.current_size / stats.target_size * 100,
            "accuracy": stats.accuracy,
            "total_profit": stats.total_profit,
            "error_rate_last_10": stats.error_rate_last_10,
            "should_update": stats.should_update,
            "update_reason": stats.reason,
            "unique_teams": len(team_stats),
            "worst_performing_teams": [
                {"team_id": tid, "errors": errs, "profit": pft}
                for tid, errs, pft in worst_teams
            ],
            "total_entries_processed": self.total_entries_processed,
            "total_updates": self.total_updates,
            "avg_entries_per_update": self.total_entries_processed / self.total_updates if self.total_updates > 0 else 0
        }

    def peek(self, n: int = 5) -> List[BufferEntry]:
        """
        Voir les N dernières entrées sans les retirer

        Args:
            n: Nombre d'entrées à voir

        Returns:
            Liste des N dernières entrées
        """
        return self.buffer[-n:] if len(self.buffer) >= n else self.buffer

    def get_entries_for_team(self, team_id: str) -> List[BufferEntry]:
        """
        Obtenir toutes les entrées pour une équipe

        Args:
            team_id: ID de l'équipe

        Returns:
            Liste des entrées pour cette équipe
        """
        return [e for e in self.buffer if e.team_id == team_id]

    def get_update_history(self, last_n: int = 10) -> List[Dict]:
        """
        Obtenir l'historique des mises à jour

        Args:
            last_n: Nombre de mises à jour à retourner

        Returns:
            Liste des N dernières mises à jour
        """
        return self.update_history[-last_n:] if self.update_history else []

    def __len__(self) -> int:
        return len(self.buffer)

    def __bool__(self) -> bool:
        return len(self.buffer) > 0


# Export
__all__ = ["AdaptiveBuffer", "BufferEntry", "BufferStats"]
