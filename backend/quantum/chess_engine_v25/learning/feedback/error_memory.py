"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    ERROR MEMORY                                                          ║
║                    Mémoire des équipes mal classées                                      ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  Principe:                                                                               ║
║  - Quand on se trompe sur une équipe, on mémorise la correction                         ║
║  - Si l'équipe revient, on applique la correction directement                           ║
║  - La confiance augmente si la correction est confirmée                                 ║
║  - La correction expire après N jours (équipes changent)                                ║
║                                                                                          ║
║  Auteur: Mya & Claude | Version: 1.0.0 | Date: 12 Décembre 2025                         ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
from pathlib import Path


# Import TacticalProfile depuis rule_based pour éviter import circulaire
from ..classifiers.rule_based import TacticalProfile


@dataclass
class ErrorMemoryEntry:
    """
    Entrée dans la mémoire des erreurs

    Représente une correction mémorisée pour une équipe
    """
    team_id: str
    predicted_profile: TacticalProfile
    corrected_profile: TacticalProfile
    confidence: float
    count: int  # Nombre de fois que la correction a été confirmée
    last_updated: datetime
    profit_lost: float = 0.0
    match_contexts: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convertir en dict pour sérialisation"""
        return {
            "team_id": self.team_id,
            "predicted_profile": self.predicted_profile.value,
            "corrected_profile": self.corrected_profile.value,
            "confidence": self.confidence,
            "count": self.count,
            "last_updated": self.last_updated.isoformat(),
            "profit_lost": self.profit_lost,
            "match_contexts": self.match_contexts[-5:]  # Garder les 5 derniers
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ErrorMemoryEntry":
        """Créer depuis un dict"""
        return cls(
            team_id=data["team_id"],
            predicted_profile=TacticalProfile(data["predicted_profile"]),
            corrected_profile=TacticalProfile(data["corrected_profile"]),
            confidence=data["confidence"],
            count=data["count"],
            last_updated=datetime.fromisoformat(data["last_updated"]),
            profit_lost=data.get("profit_lost", 0.0),
            match_contexts=data.get("match_contexts", [])
        )


class ErrorMemory:
    """
    Mémoire des équipes mal classées

    Évite de répéter les mêmes erreurs en mémorisant les corrections
    La confiance augmente quand une correction est confirmée
    Les corrections expirent après max_age_days
    """

    def __init__(self, confidence_threshold: float = 0.7,
                 max_age_days: int = 60,
                 persistence_path: Optional[str] = None):
        """
        Initialize error memory

        Args:
            confidence_threshold: Seuil pour appliquer une correction
            max_age_days: Âge max d'une correction avant expiration
            persistence_path: Chemin pour sauvegarder la mémoire (optionnel)
        """
        self.memory: Dict[str, ErrorMemoryEntry] = {}
        self.confidence_threshold = confidence_threshold
        self.max_age_days = max_age_days
        self.persistence_path = persistence_path

        # Stats
        self.total_corrections = 0
        self.corrections_applied = 0
        self.corrections_confirmed = 0

        # Charger depuis fichier si existe
        if persistence_path:
            self._load()

    def record_error(self, team_id: str, predicted: TacticalProfile,
                    actual: TacticalProfile, profit_lost: float,
                    match_context: Optional[Dict] = None):
        """
        Enregistrer une erreur de classification

        Args:
            team_id: ID de l'équipe
            predicted: Profil prédit (erroné)
            actual: Profil réel observé
            profit_lost: Profit perdu à cause de l'erreur
            match_context: Contexte du match (optionnel)
        """
        self.total_corrections += 1

        if team_id in self.memory:
            entry = self.memory[team_id]

            if entry.corrected_profile == actual:
                # Même correction → augmenter confiance
                entry.confidence = min(0.95, entry.confidence + 0.1)
                entry.count += 1
                entry.last_updated = datetime.now()
                entry.profit_lost += abs(profit_lost)
            else:
                # Correction différente → équipe changeante
                # On garde la nouvelle correction avec confiance plus basse
                entry.corrected_profile = actual
                entry.confidence = 0.6  # Reset confidence
                entry.count = 1
                entry.last_updated = datetime.now()
                entry.profit_lost = abs(profit_lost)
                entry.match_contexts = []

            if match_context:
                entry.match_contexts.append({
                    **match_context,
                    "date": datetime.now().isoformat()
                })
        else:
            # Nouvelle entrée
            self.memory[team_id] = ErrorMemoryEntry(
                team_id=team_id,
                predicted_profile=predicted,
                corrected_profile=actual,
                confidence=0.6,  # Commence modéré
                count=1,
                last_updated=datetime.now(),
                profit_lost=abs(profit_lost),
                match_contexts=[{**(match_context or {}), "date": datetime.now().isoformat()}]
            )

        # Sauvegarder
        if self.persistence_path:
            self._save()

    def get_correction(self, team_id: str) -> Optional[ErrorMemoryEntry]:
        """
        Récupérer une correction si elle existe et est fiable

        Args:
            team_id: ID de l'équipe

        Returns:
            ErrorMemoryEntry si correction disponible et fiable, None sinon
        """
        if team_id not in self.memory:
            return None

        entry = self.memory[team_id]

        # Vérifier l'âge
        age_days = (datetime.now() - entry.last_updated).days
        if age_days > self.max_age_days:
            del self.memory[team_id]
            if self.persistence_path:
                self._save()
            return None

        # Vérifier la confiance
        if entry.confidence < self.confidence_threshold:
            return None

        self.corrections_applied += 1
        return entry

    def confirm_correction(self, team_id: str, was_correct: bool):
        """
        Confirmer ou infirmer une correction appliquée

        Args:
            team_id: ID de l'équipe
            was_correct: True si la correction était correcte
        """
        if team_id not in self.memory:
            return

        entry = self.memory[team_id]

        if was_correct:
            # Correction confirmée → augmenter confiance
            entry.confidence = min(0.95, entry.confidence + 0.05)
            entry.count += 1
            entry.last_updated = datetime.now()
            self.corrections_confirmed += 1
        else:
            # Correction infirmée → réduire confiance
            entry.confidence *= 0.8

            # Si confiance trop basse, supprimer
            if entry.confidence < 0.4:
                del self.memory[team_id]

        if self.persistence_path:
            self._save()

    def cleanup_expired(self):
        """Nettoyer les corrections expirées"""
        now = datetime.now()
        expired = []

        for team_id, entry in self.memory.items():
            age_days = (now - entry.last_updated).days
            if age_days > self.max_age_days:
                expired.append(team_id)

        for team_id in expired:
            del self.memory[team_id]

        if expired and self.persistence_path:
            self._save()

        return len(expired)

    def get_stats(self) -> Dict:
        """Statistiques de la mémoire"""
        if not self.memory:
            return {
                "total_entries": 0,
                "avg_confidence": 0,
                "total_profit_saved_potential": 0
            }

        confidences = [e.confidence for e in self.memory.values()]
        profits = [e.profit_lost for e in self.memory.values()]

        return {
            "total_entries": len(self.memory),
            "avg_confidence": sum(confidences) / len(confidences),
            "high_confidence_entries": sum(1 for c in confidences if c >= 0.8),
            "total_corrections_recorded": self.total_corrections,
            "corrections_applied": self.corrections_applied,
            "corrections_confirmed": self.corrections_confirmed,
            "confirmation_rate": (
                self.corrections_confirmed / self.corrections_applied
                if self.corrections_applied > 0 else 0
            ),
            "total_profit_lost_from_errors": sum(profits),
            "avg_profit_lost_per_error": sum(profits) / len(profits) if profits else 0,
        }

    def get_most_problematic_teams(self, top_n: int = 10) -> List[Dict]:
        """
        Équipes les plus problématiques (erreurs les plus coûteuses)

        Args:
            top_n: Nombre d'équipes à retourner

        Returns:
            Liste des équipes avec leurs stats
        """
        sorted_entries = sorted(
            self.memory.values(),
            key=lambda e: e.profit_lost,
            reverse=True
        )[:top_n]

        return [
            {
                "team_id": e.team_id,
                "predicted": e.predicted_profile.value,
                "actual": e.corrected_profile.value,
                "profit_lost": e.profit_lost,
                "count": e.count,
                "confidence": e.confidence
            }
            for e in sorted_entries
        ]

    def _save(self):
        """Sauvegarder la mémoire sur disque"""
        if not self.persistence_path:
            return

        path = Path(self.persistence_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "stats": {
                "total_corrections": self.total_corrections,
                "corrections_applied": self.corrections_applied,
                "corrections_confirmed": self.corrections_confirmed
            },
            "memory": {
                team_id: entry.to_dict()
                for team_id, entry in self.memory.items()
            }
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load(self):
        """Charger la mémoire depuis disque"""
        if not self.persistence_path:
            return

        path = Path(self.persistence_path)
        if not path.exists():
            return

        try:
            with open(path, 'r') as f:
                data = json.load(f)

            # Restaurer stats
            stats = data.get("stats", {})
            self.total_corrections = stats.get("total_corrections", 0)
            self.corrections_applied = stats.get("corrections_applied", 0)
            self.corrections_confirmed = stats.get("corrections_confirmed", 0)

            # Restaurer mémoire
            self.memory = {
                team_id: ErrorMemoryEntry.from_dict(entry_data)
                for team_id, entry_data in data.get("memory", {}).items()
            }

            # Cleanup expired
            self.cleanup_expired()

        except Exception as e:
            print(f"Error loading error memory: {e}")
            self.memory = {}

    def __len__(self) -> int:
        return len(self.memory)

    def __contains__(self, team_id: str) -> bool:
        return team_id in self.memory


# Export
__all__ = ["ErrorMemory", "ErrorMemoryEntry"]
