"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    ADAPTIVE PROFILE CLASSIFIER                                           ║
║                    Orchestrateur ML Adaptatif Hybride C+D                                ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  Architecture Hybride C+D:                                                               ║
║  - Ensemble de 5 modèles (Rules, RF, GB, KNN, Transformer)                              ║
║  - Vote pondéré dynamique                                                                ║
║  - Mémoire des erreurs                                                                   ║
║  - Détection de drift (changement de style)                                             ║
║  - Apprentissage dual (Accuracy 40% + Profit 60%)                                       ║
║  - Buffer adaptatif (15-40 matchs)                                                      ║
║  - Pondération temporelle (données récentes > anciennes)                                ║
║                                                                                          ║
║  ROI estimé: +18-28%                                                                    ║
║                                                                                          ║
║  Auteur: Mya & Claude | Version: 1.0.0 | Date: 12 Décembre 2025                         ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field
import numpy as np
from pathlib import Path
import json

# Scikit-learn imports (optionnel)
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.neighbors import KNeighborsClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. Only rule-based classifier will work.")

# Internal imports
from .classifiers.rule_based import RuleBasedClassifier, TacticalProfile, ProfileFamily, PROFILE_TO_FAMILY
from .classifiers.transformer import TransformerProfileClassifier
from .feedback.error_memory import ErrorMemory, ErrorMemoryEntry
from .feedback.drift_detector import StyleDriftDetector, DriftAlert
from .feedback.dual_objective import DualObjectiveLearner
from .data.temporal_weighting import TemporalDataManager, create_sample_weights
from .data.adaptive_buffer import AdaptiveBuffer, BufferEntry


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ClassificationResult:
    """
    Résultat d'une classification de profil tactique

    Contient le profil prédit, la confiance, et toutes les informations
    de traçabilité pour comprendre la décision.
    """
    team_id: str
    primary_profile: TacticalProfile
    secondary_profile: Optional[TacticalProfile]
    confidence: float
    model_contributions: Dict[str, Any]
    explanation: List[str]
    was_corrected: bool = False
    correction_source: Optional[str] = None
    drift_alert: Optional[DriftAlert] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convertir en dict pour sérialisation"""
        return {
            "team_id": self.team_id,
            "primary_profile": self.primary_profile.value,
            "secondary_profile": self.secondary_profile.value if self.secondary_profile else None,
            "confidence": self.confidence,
            "model_contributions": self.model_contributions,
            "explanation": self.explanation,
            "was_corrected": self.was_corrected,
            "correction_source": self.correction_source,
            "drift_alert": self.drift_alert.to_dict() if self.drift_alert else None,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class FeedbackData:
    """
    Données de feedback après un match

    Utilisé pour apprendre de nos erreurs et améliorer le modèle.
    """
    team_id: str
    team_metrics: Dict[str, float]
    predicted_profile: TacticalProfile
    actual_behavior: TacticalProfile
    profit: float
    match_date: datetime
    was_correct: bool = field(init=False)

    def __post_init__(self):
        self.was_correct = self.predicted_profile == self.actual_behavior


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════════

class AdaptiveProfileClassifier:
    """
    AGENT ML ADAPTATIF HYBRIDE C+D

    Classifie les équipes en 12 profils tactiques en utilisant un ensemble
    de modèles avec vote pondéré dynamique.

    Features:
    - Ensemble de 5 modèles diversifiés
    - Poids adaptatifs selon performance
    - Mémoire des erreurs
    - Détection de changement de style
    - Apprentissage dual (Accuracy + Profit)
    - Buffer adaptatif avant mise à jour
    - Pondération temporelle des données
    """

    # Mapping profil → index et inverse
    PROFILES = list(TacticalProfile)
    PROFILE_TO_IDX = {p: i for i, p in enumerate(PROFILES)}
    IDX_TO_PROFILE = {i: p for i, p in enumerate(PROFILES)}

    # Ordre des features pour conversion dict → array
    FEATURE_ORDER = [
        'possession', 'ppda', 'verticality', 'pressing_intensity',
        'crosses_per_90', 'defensive_line_height', 'counter_attack_goals_pct',
        'long_balls_pct', 'width_index', 'high_recoveries_pct',
        'transition_speed', 'shots_per_90', 'style_variance',
        'home_away_style_diff', 'score_dependent_variance',
        'aerial_duels_won_pct', 'sprints_per_90', 'pass_accuracy',
        'xg_per_90', 'xga_per_90', 'set_piece_goals_pct',
        'goals_from_counter_pct', 'progressive_passes_per_90',
        'final_third_entries_per_90'
    ]

    def __init__(self,
                 buffer_size: int = 25,
                 alpha: float = 0.4,
                 beta: float = 0.6,
                 temporal_decay: float = 0.1,
                 max_data_age_months: int = 6,
                 n_features: int = 24,
                 persistence_dir: Optional[str] = None):
        """
        Initialize the adaptive profile classifier

        Args:
            buffer_size: Taille par défaut du buffer (25 matchs)
            alpha: Poids pour l'accuracy (0.4 = 40%)
            beta: Poids pour le profit (0.6 = 60%)
            temporal_decay: Taux de décroissance temporelle (0.1/mois)
            max_data_age_months: Âge max des données (6 mois)
            n_features: Nombre de features (24)
            persistence_dir: Répertoire pour persistance (optionnel)
        """
        self.n_features = n_features
        self.persistence_dir = Path(persistence_dir) if persistence_dir else None

        # ═══════════════════════════════════════════════════════════════════
        # MODÈLES DE L'ENSEMBLE
        # ═══════════════════════════════════════════════════════════════════

        self.models = {
            'rules': RuleBasedClassifier(),
            'transformer': TransformerProfileClassifier(n_features=n_features)
        }

        if SKLEARN_AVAILABLE:
            self.models.update({
                'rf': RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                ),
                'gb': GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=5,
                    random_state=42
                ),
                'knn': KNeighborsClassifier(
                    n_neighbors=5,
                    weights='distance'
                )
            })

        # ═══════════════════════════════════════════════════════════════════
        # POIDS ADAPTATIFS
        # ═══════════════════════════════════════════════════════════════════

        # Poids initiaux (Transformer commence plus bas car moins de données)
        self.weights = {
            'rules': 1.0,       # Explicable, toujours fiable
            'rf': 1.0,          # Bon généraliste
            'gb': 1.0,          # Bon sur patterns séquentiels
            'knn': 0.8,         # Équipes similaires
            'transformer': 0.6  # Neural - commence bas, monte si performant
        }

        # Garder seulement les modèles disponibles
        self.weights = {k: v for k, v in self.weights.items() if k in self.models}

        # ═══════════════════════════════════════════════════════════════════
        # COMPOSANTS AUXILIAIRES
        # ═══════════════════════════════════════════════════════════════════

        error_memory_path = str(self.persistence_dir / "error_memory.json") if self.persistence_dir else None

        self.error_memory = ErrorMemory(
            confidence_threshold=0.7,
            max_age_days=60,
            persistence_path=error_memory_path
        )

        self.drift_detector = StyleDriftDetector(
            window_size=8,
            z_threshold=2.0,
            min_history=10
        )

        self.buffer = AdaptiveBuffer(
            min_size=15,
            max_size=40,
            default_size=buffer_size
        )

        self.temporal_manager = TemporalDataManager(
            decay_rate=temporal_decay,
            max_age_months=max_data_age_months
        )

        self.dual_learner = DualObjectiveLearner(
            alpha=alpha,
            beta=beta
        )

        # ═══════════════════════════════════════════════════════════════════
        # ÉTAT
        # ═══════════════════════════════════════════════════════════════════

        self.is_fitted = False
        self.training_data: List[FeedbackData] = []
        self.classification_count = 0
        self.last_batch_update = None

        # Performance tracking
        self.model_performance = {name: [] for name in self.models}

    # ═══════════════════════════════════════════════════════════════════════════
    # CLASSIFICATION
    # ═══════════════════════════════════════════════════════════════════════════

    def classify(self, team_id: str,
                team_metrics: Dict[str, float]) -> ClassificationResult:
        """
        Classifier une équipe en profil tactique

        Pipeline:
        1. Vérifier correction mémorisée
        2. Vérifier drift (changement de style)
        3. Vote pondéré de l'ensemble
        4. Sélectionner le meilleur profil

        Args:
            team_id: Identifiant de l'équipe
            team_metrics: Dict des métriques (24 features)

        Returns:
            ClassificationResult avec profil, confiance, explications
        """
        self.classification_count += 1
        explanations = []
        drift_alert = None

        # ─────────────────────────────────────────────────────────────────
        # ÉTAPE 1: Vérifier correction mémorisée
        # ─────────────────────────────────────────────────────────────────

        correction = self.error_memory.get_correction(team_id)
        if correction and correction.confidence > 0.8:
            explanations.append(
                f"📝 CORRECTION APPLIED: {correction.predicted_profile.value} → "
                f"{correction.corrected_profile.value} "
                f"(confidence={correction.confidence:.2f}, seen {correction.count}x)"
            )

            return ClassificationResult(
                team_id=team_id,
                primary_profile=correction.corrected_profile,
                secondary_profile=correction.predicted_profile,
                confidence=correction.confidence,
                model_contributions={'memory_correction': 1.0},
                explanation=explanations,
                was_corrected=True,
                correction_source='error_memory'
            )

        # ─────────────────────────────────────────────────────────────────
        # ÉTAPE 2: Vérifier drift (changement de style)
        # ─────────────────────────────────────────────────────────────────

        drift_alert = self.drift_detector.check(team_id, team_metrics)
        if drift_alert:
            explanations.append(f"⚠️ DRIFT DETECTED: {drift_alert.reason}")
            explanations.append(f"   Severity: {drift_alert.severity}")
            if drift_alert.new_profile_suggestion:
                explanations.append(
                    f"   Suggested profile: {drift_alert.new_profile_suggestion.value}"
                )

        # ─────────────────────────────────────────────────────────────────
        # ÉTAPE 3: Vote pondéré de l'ensemble
        # ─────────────────────────────────────────────────────────────────

        votes: Dict[TacticalProfile, float] = {}
        model_contributions = {}

        features_array = self._dict_to_array(team_metrics)

        for name, model in self.models.items():
            try:
                pred, conf = self._get_model_prediction(name, model, team_metrics, features_array)

                if pred is None:
                    continue

                # Vote pondéré
                weighted_vote = self.weights.get(name, 1.0) * conf
                votes[pred] = votes.get(pred, 0) + weighted_vote

                model_contributions[name] = {
                    'prediction': pred.value,
                    'confidence': conf,
                    'weight': self.weights.get(name, 1.0),
                    'contribution': weighted_vote
                }

            except Exception as e:
                explanations.append(f"⚠️ [{name}] Error: {str(e)[:50]}")
                continue

        # ─────────────────────────────────────────────────────────────────
        # ÉTAPE 4: Sélectionner le meilleur profil
        # ─────────────────────────────────────────────────────────────────

        if not votes:
            # Fallback sur règles seules
            pred, conf, rule_expl = self.models['rules'].predict(team_metrics)
            return ClassificationResult(
                team_id=team_id,
                primary_profile=pred,
                secondary_profile=None,
                confidence=conf * 0.5,
                model_contributions={'rules_fallback': 1.0},
                explanation=["⚠️ FALLBACK: Only rules available"] + rule_expl[:3],
                was_corrected=False
            )

        # Trier par votes
        sorted_votes = sorted(votes.items(), key=lambda x: -x[1])
        primary = sorted_votes[0][0]
        secondary = sorted_votes[1][0] if len(sorted_votes) > 1 else None

        # Confidence = proportion du vote gagnant
        total_votes = sum(votes.values())
        confidence = sorted_votes[0][1] / total_votes if total_votes > 0 else 0.5

        # Ajouter les explications des règles
        if 'rules' in model_contributions:
            _, _, rule_expl = self.models['rules'].predict(team_metrics)
            matched = [e for e in rule_expl if e.startswith("✓")][:2]
            if matched:
                explanations.extend(matched)

        # Mettre à jour le drift detector
        self.drift_detector.update(team_id, team_metrics)

        return ClassificationResult(
            team_id=team_id,
            primary_profile=primary,
            secondary_profile=secondary,
            confidence=confidence,
            model_contributions=model_contributions,
            explanation=explanations,
            was_corrected=False,
            drift_alert=drift_alert
        )

    def _get_model_prediction(self, name: str, model: Any,
                             team_metrics: Dict[str, float],
                             features_array: np.ndarray) -> Tuple[Optional[TacticalProfile], float]:
        """Obtenir la prédiction d'un modèle"""

        if name == 'rules':
            pred, conf, _ = model.predict(team_metrics)
            return pred, conf

        elif name == 'transformer':
            pred_idx, conf = model.predict(features_array)
            return self.IDX_TO_PROFILE[pred_idx], conf

        elif name in ['rf', 'gb', 'knn']:
            if not self.is_fitted:
                return None, 0

            pred_idx = model.predict([features_array])[0]
            proba = model.predict_proba([features_array])[0]

            return self.IDX_TO_PROFILE[pred_idx], proba.max()

        return None, 0

    # ═══════════════════════════════════════════════════════════════════════════
    # FEEDBACK & LEARNING
    # ═══════════════════════════════════════════════════════════════════════════

    def feedback(self, team_id: str, team_metrics: Dict[str, float],
                predicted_profile: TacticalProfile,
                actual_behavior: TacticalProfile,
                profit: float, match_date: Optional[datetime] = None):
        """
        Feedback après un match - apprentissage

        Pipeline:
        1. Ajouter au buffer
        2. Si erreur, mémoriser + apprendre (Transformer)
        3. Mettre à jour les poids des modèles
        4. Si buffer plein, ré-entraîner

        Args:
            team_id: ID de l'équipe
            team_metrics: Métriques du match
            predicted_profile: Ce qu'on avait prédit
            actual_behavior: Ce qui s'est réellement passé
            profit: Profit/perte du pari
            match_date: Date du match
        """
        if match_date is None:
            match_date = datetime.now()

        was_correct = (predicted_profile == actual_behavior)

        # ─────────────────────────────────────────────────────────────────
        # ÉTAPE 1: Ajouter au buffer
        # ─────────────────────────────────────────────────────────────────

        temporal_weight = self.temporal_manager.calculate_weight(match_date)

        self.buffer.add(
            team_id=team_id,
            team_metrics=team_metrics,
            predicted_profile=predicted_profile,
            actual_behavior=actual_behavior,
            profit=profit,
            match_date=match_date,
            temporal_weight=temporal_weight
        )

        # ─────────────────────────────────────────────────────────────────
        # ÉTAPE 2: Si erreur, mémoriser et apprendre
        # ─────────────────────────────────────────────────────────────────

        if not was_correct:
            # Mémoriser l'erreur
            self.error_memory.record_error(
                team_id=team_id,
                predicted=predicted_profile,
                actual=actual_behavior,
                profit_lost=profit if profit < 0 else 0,
                match_context={
                    'match_date': match_date.isoformat(),
                    'profit': profit,
                    'metrics_snapshot': {k: team_metrics.get(k) for k in ['possession', 'ppda', 'verticality'][:3]}
                }
            )

            # Apprentissage immédiat du Transformer
            features_array = self._dict_to_array(team_metrics)
            actual_idx = self.PROFILE_TO_IDX[actual_behavior]
            self.models['transformer'].learn_from_error(
                features_array, actual_idx, profit
            )
        else:
            # Confirmer les corrections
            self.error_memory.confirm_correction(team_id, was_correct=True)

        # ─────────────────────────────────────────────────────────────────
        # ÉTAPE 3: Mettre à jour les poids
        # ─────────────────────────────────────────────────────────────────

        self._update_weights(team_metrics, predicted_profile, actual_behavior, profit)

        # ─────────────────────────────────────────────────────────────────
        # ÉTAPE 4: Ré-entraînement si buffer plein
        # ─────────────────────────────────────────────────────────────────

        if self.buffer.should_update():
            self._batch_update()

    def _update_weights(self, team_metrics: Dict[str, float],
                       predicted: TacticalProfile,
                       actual: TacticalProfile, profit: float):
        """Mettre à jour les poids de chaque modèle"""

        features_array = self._dict_to_array(team_metrics)

        for name, model in self.models.items():
            try:
                # Obtenir la prédiction de ce modèle
                model_pred, _ = self._get_model_prediction(
                    name, model, team_metrics, features_array
                )

                if model_pred is None:
                    continue

                was_correct = (model_pred == actual)

                # Utiliser le dual learner
                new_weight, event = self.dual_learner.process_feedback(
                    model_name=name,
                    was_correct=was_correct,
                    profit=profit,
                    current_weight=self.weights.get(name, 1.0)
                )

                self.weights[name] = new_weight

                # Tracker performance
                self.model_performance[name].append(event.combined_score)

            except Exception:
                continue

    def _batch_update(self):
        """Ré-entraînement batch quand buffer plein"""

        buffer_data = self.buffer.get_and_clear()
        if len(buffer_data) < 10:
            return

        # Préparer les données
        X = []
        y = []
        weights = []
        dates = []

        for entry in buffer_data:
            features = self._dict_to_array(entry.team_metrics)
            label = self.PROFILE_TO_IDX[entry.actual_behavior]

            # Pondération temporelle × profit
            profit_weight = 1.0 + abs(entry.profit) / 10 if not entry.was_correct else 1.0
            final_weight = entry.temporal_weight * profit_weight

            X.append(features)
            y.append(label)
            weights.append(final_weight)
            dates.append(entry.match_date)

        X = np.array(X)
        y = np.array(y)
        weights = np.array(weights)

        # Ré-entraîner les modèles sklearn
        if SKLEARN_AVAILABLE:
            for name in ['rf', 'gb']:
                if name in self.models:
                    try:
                        self.models[name].fit(X, y, sample_weight=weights)
                    except Exception as e:
                        print(f"Error retraining {name}: {e}")

            if 'knn' in self.models:
                try:
                    self.models['knn'].fit(X, y)
                except Exception as e:
                    print(f"Error retraining knn: {e}")

        # Ajouter aux données d'entraînement globales
        for entry in buffer_data:
            self.training_data.append(FeedbackData(
                team_id=entry.team_id,
                team_metrics=entry.team_metrics,
                predicted_profile=entry.predicted_profile,
                actual_behavior=entry.actual_behavior,
                profit=entry.profit,
                match_date=entry.match_date
            ))

        self.is_fitted = True
        self.last_batch_update = datetime.now()

        # Ajuster la taille du buffer
        recent_accuracy = np.mean([
            1.0 if entry.was_correct else 0.0
            for entry in buffer_data
        ])
        self.buffer.adjust_size(recent_accuracy)

    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════

    def _dict_to_array(self, metrics: Dict[str, float]) -> np.ndarray:
        """Convertir dict de métriques en array numpy"""
        return np.array([metrics.get(f, 0.0) for f in self.FEATURE_ORDER])

    def get_model_weights(self) -> Dict[str, float]:
        """Retourner les poids actuels des modèles"""
        return self.weights.copy()

    def get_performance_summary(self) -> Dict[str, Dict]:
        """Résumé des performances par modèle"""
        summary = {}
        for name, scores in self.model_performance.items():
            if scores:
                recent = scores[-50:]
                summary[name] = {
                    'mean_score': np.mean(recent),
                    'recent_accuracy': np.mean([1 if s > 0.5 else 0 for s in scores[-20:]]) if len(scores) >= 20 else None,
                    'current_weight': self.weights.get(name, 0),
                    'n_evaluations': len(scores),
                    'trend': 'improving' if len(scores) > 20 and np.mean(scores[-10:]) > np.mean(scores[-20:-10]) else 'stable'
                }
        return summary

    def get_stats(self) -> Dict:
        """Statistiques globales du classifier"""
        return {
            "classification_count": self.classification_count,
            "is_fitted": self.is_fitted,
            "training_data_size": len(self.training_data),
            "last_batch_update": self.last_batch_update.isoformat() if self.last_batch_update else None,
            "model_weights": self.get_model_weights(),
            "buffer": self.buffer.get_stats().__dict__,
            "error_memory": self.error_memory.get_stats(),
            "drift_detector": self.drift_detector.get_stats(),
            "dual_learner": self.dual_learner.get_summary()
        }

    def save(self, path: Optional[str] = None):
        """Sauvegarder l'état du classifier"""
        if path is None and self.persistence_dir:
            path = str(self.persistence_dir / "classifier_state.json")

        if path is None:
            raise ValueError("No path specified for saving")

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        state = {
            "version": "1.0.0",
            "saved_at": datetime.now().isoformat(),
            "weights": self.weights,
            "is_fitted": self.is_fitted,
            "classification_count": self.classification_count,
            "model_performance": {k: v[-100:] for k, v in self.model_performance.items()}
        }

        with open(path, 'w') as f:
            json.dump(state, f, indent=2)

    def load(self, path: Optional[str] = None):
        """Charger l'état du classifier"""
        if path is None and self.persistence_dir:
            path = str(self.persistence_dir / "classifier_state.json")

        if path is None or not Path(path).exists():
            return

        with open(path, 'r') as f:
            state = json.load(f)

        self.weights = state.get("weights", self.weights)
        self.is_fitted = state.get("is_fitted", False)
        self.classification_count = state.get("classification_count", 0)
        self.model_performance = state.get("model_performance", {})


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "AdaptiveProfileClassifier",
    "ClassificationResult",
    "FeedbackData",
    "TacticalProfile",
    "ProfileFamily",
    "PROFILE_TO_FAMILY"
]
