"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    MON_PS - LEARNING MODULE                                              ║
║                    Agent ML Adaptatif Hybride C+D                                        ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  Architecture:                                                                           ║
║  - Ensemble de 5 modèles (Rules, RF, GB, KNN, Transformer)                              ║
║  - Vote pondéré dynamique                                                                ║
║  - Feedback loop avec mémoire des erreurs                                               ║
║  - Apprentissage dual (Accuracy 40% + Profit 60%)                                       ║
║  - Buffer adaptatif (15-40 matchs)                                                      ║
║  - Pondération temporelle (données récentes > anciennes)                                ║
║                                                                                          ║
║  Auteur: Mya & Claude | Version: 1.0.0 | Date: 12 Décembre 2025                         ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

__version__ = "1.0.0"
__author__ = "Mya & Claude"

# Exposer les classes principales
from .profile_classifier import (
    AdaptiveProfileClassifier,
    ClassificationResult,
    FeedbackData,
    TacticalProfile
)

from .classifiers.rule_based import RuleBasedClassifier
from .classifiers.transformer import TransformerProfileClassifier

from .feedback.error_memory import ErrorMemory, ErrorMemoryEntry
from .feedback.drift_detector import StyleDriftDetector, DriftAlert
from .feedback.dual_objective import DualObjectiveLearner

from .data.temporal_weighting import TemporalDataManager
from .data.adaptive_buffer import AdaptiveBuffer

__all__ = [
    # Main classifier
    "AdaptiveProfileClassifier",
    "ClassificationResult",
    "FeedbackData",
    "TacticalProfile",

    # Classifiers
    "RuleBasedClassifier",
    "TransformerProfileClassifier",

    # Feedback
    "ErrorMemory",
    "ErrorMemoryEntry",
    "StyleDriftDetector",
    "DriftAlert",
    "DualObjectiveLearner",

    # Data
    "TemporalDataManager",
    "AdaptiveBuffer",
]
