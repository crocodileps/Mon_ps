# 🎯 INSTRUCTIONS CLAUDE CODE - MODULE LEARNING V1.0
## Chess Engine V2.5 - Agent ML Adaptatif Hybride C+D

**Date**: 12 Décembre 2025  
**Auteur**: Mya & Claude  
**Serveur**: 91.98.131.218 (Hetzner)

---

## 📋 CONTEXTE

Tu dois créer le module **Learning Adaptatif Hybride C+D** pour le Chess Engine V2.5.

Ce module permet de :
- Classifier les équipes en 12 profils tactiques
- Apprendre de ses erreurs (mémoire + feedback loop)
- S'adapter aux changements de style (drift detection)
- Optimiser pour le profit (pas juste l'accuracy)

**Architecture validée par Mya** - Ne pas modifier les paramètres.

---

## 📁 ÉTAPE 1 : CRÉER LA STRUCTURE DES DOSSIERS

```bash
cd /root/mon_ps/backend/quantum

mkdir -p chess_engine_v25/learning/classifiers
mkdir -p chess_engine_v25/learning/ensemble
mkdir -p chess_engine_v25/learning/feedback
mkdir -p chess_engine_v25/learning/data
```

---

## 📄 ÉTAPE 2 : CRÉER LES FICHIERS

### 2.1 - `/quantum/chess_engine_v25/learning/__init__.py`

```python
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
```

---

### 2.2 - `/quantum/chess_engine_v25/learning/classifiers/__init__.py`

```python
"""Classifiers module - Individual models for the ensemble"""

from .rule_based import RuleBasedClassifier
from .transformer import TransformerProfileClassifier

__all__ = ["RuleBasedClassifier", "TransformerProfileClassifier"]
```

---

### 2.3 - `/quantum/chess_engine_v25/learning/classifiers/rule_based.py`

```python
"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    RULE-BASED CLASSIFIER                                                 ║
║                    Classification par règles expertes                                    ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  Avantages:                                                                              ║
║  - 100% explicable (on sait POURQUOI une équipe est classée ainsi)                      ║
║  - Pas besoin de données d'entraînement                                                 ║
║  - Fonctionne immédiatement                                                             ║
║  - Base de comparaison pour les modèles ML                                              ║
║                                                                                          ║
║  Auteur: Mya & Claude | Version: 1.0.0 | Date: 12 Décembre 2025                         ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
import numpy as np


class TacticalProfile(Enum):
    """Les 12 profils tactiques ADN"""
    
    # Offensifs (4)
    POSSESSION = "POSSESSION"       # Man City, Barça - Possession 60%+, jeu patient
    GEGENPRESS = "GEGENPRESS"       # Liverpool, Dortmund - Pressing ultra-haut
    WIDE_ATTACK = "WIDE_ATTACK"     # Real Madrid - Centres, largeur maximum
    DIRECT_ATTACK = "DIRECT_ATTACK" # Leicester titre - Verticalité, passes longues
    
    # Défensifs (3)
    LOW_BLOCK = "LOW_BLOCK"         # Atlético Madrid - Défense basse, contre
    MID_BLOCK = "MID_BLOCK"         # Équipes milieu tableau - Équilibre
    PARK_THE_BUS = "PARK_THE_BUS"   # Mode survie - Ultra-défensif
    
    # Hybrides (3)
    TRANSITION = "TRANSITION"       # Tottenham Conte - Défense → Attaque rapide
    ADAPTIVE = "ADAPTIVE"           # Ancelotti - Caméléon, change selon adversaire
    BALANCED = "BALANCED"           # Équipes moyennes - Pas d'identité forte
    
    # Contextuels (2)
    HOME_DOMINANT = "HOME_DOMINANT" # Très différent domicile vs extérieur
    SCORE_DEPENDENT = "SCORE_DEPENDENT"  # Change selon score en cours


class ProfileFamily(Enum):
    """Familles de profils pour la matrice de friction niveau 1"""
    OFFENSIVE = "OFFENSIVE"
    DEFENSIVE = "DEFENSIVE"
    HYBRID = "HYBRID"
    CONTEXTUAL = "CONTEXTUAL"


# Mapping profil → famille
PROFILE_TO_FAMILY = {
    TacticalProfile.POSSESSION: ProfileFamily.OFFENSIVE,
    TacticalProfile.GEGENPRESS: ProfileFamily.OFFENSIVE,
    TacticalProfile.WIDE_ATTACK: ProfileFamily.OFFENSIVE,
    TacticalProfile.DIRECT_ATTACK: ProfileFamily.OFFENSIVE,
    
    TacticalProfile.LOW_BLOCK: ProfileFamily.DEFENSIVE,
    TacticalProfile.MID_BLOCK: ProfileFamily.DEFENSIVE,
    TacticalProfile.PARK_THE_BUS: ProfileFamily.DEFENSIVE,
    
    TacticalProfile.TRANSITION: ProfileFamily.HYBRID,
    TacticalProfile.ADAPTIVE: ProfileFamily.HYBRID,
    TacticalProfile.BALANCED: ProfileFamily.HYBRID,
    
    TacticalProfile.HOME_DOMINANT: ProfileFamily.CONTEXTUAL,
    TacticalProfile.SCORE_DEPENDENT: ProfileFamily.CONTEXTUAL,
}


@dataclass
class RuleExplanation:
    """Explication d'une règle appliquée"""
    metric: str
    value: float
    operator: str
    threshold: float
    matched: bool
    explanation: str


class RuleBasedClassifier:
    """
    Classification par règles expertes
    Explicable et prévisible - la base de l'ensemble
    """
    
    # Prototypes de référence pour chaque profil
    PROTOTYPES = {
        TacticalProfile.POSSESSION: {
            "possession": 62, "ppda": 14, "verticality": 35,
            "passes_per_90": 550, "pass_accuracy": 88
        },
        TacticalProfile.GEGENPRESS: {
            "possession": 52, "ppda": 6, "pressing_intensity": 85,
            "high_recoveries_pct": 35, "sprints_per_90": 130
        },
        TacticalProfile.WIDE_ATTACK: {
            "possession": 55, "crosses_per_90": 22, "width_index": 70,
            "final_third_entries_per_90": 45
        },
        TacticalProfile.DIRECT_ATTACK: {
            "possession": 42, "verticality": 75, "long_balls_pct": 18,
            "aerial_duels_per_90": 45
        },
        TacticalProfile.LOW_BLOCK: {
            "possession": 38, "defensive_line_height": 30,
            "pressing_intensity": 35, "counter_attack_goals_pct": 30
        },
        TacticalProfile.MID_BLOCK: {
            "possession": 47, "defensive_line_height": 42,
            "pressing_intensity": 55
        },
        TacticalProfile.PARK_THE_BUS: {
            "possession": 32, "shots_per_90": 7,
            "defensive_line_height": 25, "pressing_intensity": 25
        },
        TacticalProfile.TRANSITION: {
            "possession": 45, "counter_attack_goals_pct": 28,
            "transition_speed": 70, "verticality": 60
        },
        TacticalProfile.ADAPTIVE: {
            "style_variance": 0.35, "tactical_flexibility": 0.7
        },
        TacticalProfile.BALANCED: {
            "possession": 50, "style_variance": 0.15,
            "defensive_line_height": 45
        },
        TacticalProfile.HOME_DOMINANT: {
            "home_away_style_diff": 0.45, "home_win_rate": 0.65,
            "away_win_rate": 0.30
        },
        TacticalProfile.SCORE_DEPENDENT: {
            "score_dependent_variance": 0.40, "late_goals_pct": 0.25
        }
    }
    
    # Règles de classification (metric, operator, threshold)
    PROFILE_RULES = {
        TacticalProfile.POSSESSION: {
            'possession': ('>', 58),
            'ppda': ('>', 12),
            'verticality': ('<', 45),
            'pass_accuracy': ('>', 85)
        },
        TacticalProfile.GEGENPRESS: {
            'ppda': ('<', 8),
            'pressing_intensity': ('>', 75),
            'high_recoveries_pct': ('>', 30)
        },
        TacticalProfile.WIDE_ATTACK: {
            'crosses_per_90': ('>', 18),
            'width_index': ('>', 60),
            'possession': ('between', (48, 60))
        },
        TacticalProfile.DIRECT_ATTACK: {
            'verticality': ('>', 70),
            'possession': ('<', 48),
            'long_balls_pct': ('>', 15)
        },
        TacticalProfile.LOW_BLOCK: {
            'possession': ('<', 42),
            'defensive_line_height': ('<', 35),
            'pressing_intensity': ('<', 40)
        },
        TacticalProfile.MID_BLOCK: {
            'possession': ('between', (42, 52)),
            'defensive_line_height': ('between', (35, 50)),
            'pressing_intensity': ('between', (40, 65))
        },
        TacticalProfile.PARK_THE_BUS: {
            'possession': ('<', 35),
            'shots_per_90': ('<', 8),
            'defensive_line_height': ('<', 30)
        },
        TacticalProfile.TRANSITION: {
            'counter_attack_goals_pct': ('>', 25),
            'transition_speed': ('>', 65),
            'verticality': ('>', 55)
        },
        TacticalProfile.ADAPTIVE: {
            'style_variance': ('>', 0.30),
            'tactical_flexibility': ('>', 0.5)
        },
        TacticalProfile.BALANCED: {
            'possession': ('between', (46, 54)),
            'style_variance': ('<', 0.20)
        },
        TacticalProfile.HOME_DOMINANT: {
            'home_away_style_diff': ('>', 0.40)
        },
        TacticalProfile.SCORE_DEPENDENT: {
            'score_dependent_variance': ('>', 0.35)
        }
    }
    
    def __init__(self):
        self.classification_history = []
    
    def predict(self, features: Dict[str, float]) -> Tuple[TacticalProfile, float, List[str]]:
        """
        Classifier une équipe avec explications
        
        Args:
            features: Dict des métriques de l'équipe
            
        Returns:
            Tuple (profil, confidence, explications)
        """
        scores = {}
        all_explanations = {}
        
        for profile, rules in self.PROFILE_RULES.items():
            score = 0
            matched_rules = []
            total_rules = len(rules)
            
            for metric, (operator, threshold) in rules.items():
                value = features.get(metric, 0)
                matched = False
                explanation = ""
                
                if operator == '>':
                    matched = value > threshold
                    explanation = f"{metric}={value:.1f} > {threshold}"
                elif operator == '<':
                    matched = value < threshold
                    explanation = f"{metric}={value:.1f} < {threshold}"
                elif operator == 'between':
                    low, high = threshold
                    matched = low <= value <= high
                    explanation = f"{low} ≤ {metric}={value:.1f} ≤ {high}"
                elif operator == '>=':
                    matched = value >= threshold
                    explanation = f"{metric}={value:.1f} ≥ {threshold}"
                elif operator == '<=':
                    matched = value <= threshold
                    explanation = f"{metric}={value:.1f} ≤ {threshold}"
                
                if matched:
                    score += 1
                    matched_rules.append(f"✓ {explanation}")
                else:
                    matched_rules.append(f"✗ {explanation}")
            
            scores[profile] = score / total_rules if total_rules > 0 else 0
            all_explanations[profile] = matched_rules
        
        # Meilleur profil
        best_profile = max(scores, key=scores.get)
        confidence = scores[best_profile]
        
        # Obtenir le second meilleur pour comparaison
        sorted_profiles = sorted(scores.items(), key=lambda x: -x[1])
        if len(sorted_profiles) > 1:
            gap = sorted_profiles[0][1] - sorted_profiles[1][1]
            # Ajuster la confiance selon l'écart
            if gap > 0.3:
                confidence = min(0.95, confidence + 0.1)
            elif gap < 0.1:
                confidence = max(0.3, confidence - 0.1)
        
        explanations = all_explanations[best_profile]
        
        return best_profile, confidence, explanations
    
    def predict_proba(self, features: Dict[str, float]) -> Dict[TacticalProfile, float]:
        """
        Retourne les probabilités normalisées pour chaque profil
        
        Args:
            features: Dict des métriques de l'équipe
            
        Returns:
            Dict profil → probabilité
        """
        scores = {}
        
        for profile, rules in self.PROFILE_RULES.items():
            score = 0
            total_rules = len(rules)
            
            for metric, (operator, threshold) in rules.items():
                value = features.get(metric, 0)
                
                if operator == '>':
                    score += 1 if value > threshold else 0
                elif operator == '<':
                    score += 1 if value < threshold else 0
                elif operator == 'between':
                    low, high = threshold
                    score += 1 if low <= value <= high else 0
                elif operator == '>=':
                    score += 1 if value >= threshold else 0
                elif operator == '<=':
                    score += 1 if value <= threshold else 0
            
            scores[profile] = score / total_rules if total_rules > 0 else 0
        
        # Normaliser pour que la somme = 1
        total = sum(scores.values()) + 0.001
        return {p: s / total for p, s in scores.items()}
    
    def calculate_distance_to_prototype(self, features: Dict[str, float], 
                                        profile: TacticalProfile) -> float:
        """
        Calcule la distance euclidienne au prototype du profil
        Plus petite = plus proche du profil idéal
        
        Args:
            features: Métriques de l'équipe
            profile: Profil cible
            
        Returns:
            Distance normalisée (0-1)
        """
        prototype = self.PROTOTYPES.get(profile, {})
        if not prototype:
            return 1.0
        
        distances = []
        for metric, proto_value in prototype.items():
            actual_value = features.get(metric, proto_value)
            
            # Normaliser par la valeur du prototype
            if proto_value != 0:
                normalized_diff = abs(actual_value - proto_value) / abs(proto_value)
            else:
                normalized_diff = abs(actual_value)
            
            distances.append(normalized_diff)
        
        # Distance euclidienne normalisée
        if distances:
            return min(1.0, np.sqrt(np.mean([d**2 for d in distances])))
        return 1.0
    
    def get_family(self, profile: TacticalProfile) -> ProfileFamily:
        """Retourne la famille d'un profil"""
        return PROFILE_TO_FAMILY.get(profile, ProfileFamily.BALANCED)
    
    def explain_classification(self, features: Dict[str, float]) -> Dict:
        """
        Explication détaillée de la classification
        
        Args:
            features: Métriques de l'équipe
            
        Returns:
            Dict avec profil, score, distance au prototype, règles matchées
        """
        profile, confidence, explanations = self.predict(features)
        distance = self.calculate_distance_to_prototype(features, profile)
        proba = self.predict_proba(features)
        
        # Top 3 profils
        sorted_proba = sorted(proba.items(), key=lambda x: -x[1])[:3]
        
        return {
            "primary_profile": profile,
            "confidence": confidence,
            "distance_to_prototype": distance,
            "family": self.get_family(profile),
            "matched_rules": [e for e in explanations if e.startswith("✓")],
            "unmatched_rules": [e for e in explanations if e.startswith("✗")],
            "top_3_candidates": [
                {"profile": p.value, "score": s} for p, s in sorted_proba
            ],
            "is_clear_classification": confidence > 0.7 and distance < 0.5
        }


# Export pour utilisation externe
__all__ = [
    "RuleBasedClassifier",
    "TacticalProfile",
    "ProfileFamily",
    "PROFILE_TO_FAMILY"
]
```

---

### 2.4 - `/quantum/chess_engine_v25/learning/classifiers/transformer.py`

```python
"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    TRANSFORMER PROFILE CLASSIFIER                                        ║
║                    Neural Network avec Attention (Option D)                              ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  Architecture:                                                                           ║
║  - Feature embedding (24 → 64 dimensions)                                               ║
║  - Self-Attention multi-head (4 heads)                                                   ║
║  - Feed-forward network                                                                  ║
║  - Classification head (12 profils)                                                      ║
║                                                                                          ║
║  Avantages:                                                                              ║
║  - Capture les patterns complexes                                                        ║
║  - Interactions non-linéaires entre features                                            ║
║  - Online learning (apprend des erreurs en temps réel)                                  ║
║                                                                                          ║
║  Auteur: Mya & Claude | Version: 1.0.0 | Date: 12 Décembre 2025                         ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Tuple, Optional, List, Dict
import numpy as np
from dataclasses import dataclass

# Note: PyTorch est optionnel - on utilise une version numpy si non disponible
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("Warning: PyTorch not available. Using numpy fallback for TransformerClassifier.")


@dataclass
class AttentionOutput:
    """Résultat de l'attention avec interprétabilité"""
    logits: np.ndarray
    attention_weights: np.ndarray
    feature_importance: Dict[str, float]


class TransformerProfileClassifier:
    """
    Neural Network avec Attention pour classification des profils tactiques
    
    Capture les patterns complexes et les interactions entre features
    que les méthodes traditionnelles ne peuvent pas capturer.
    
    Deux modes:
    - Mode PyTorch (si disponible): Full neural network avec backprop
    - Mode Numpy (fallback): Version simplifiée sans backprop
    """
    
    # Ordre des features (doit correspondre à la conversion dict → array)
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
    
    def __init__(self, n_features: int = 24, n_profiles: int = 12,
                 d_model: int = 64, n_heads: int = 4, dropout: float = 0.1):
        """
        Initialize the Transformer classifier
        
        Args:
            n_features: Number of input features (24 DNA vectors)
            n_profiles: Number of tactical profiles (12)
            d_model: Internal dimension of the model
            n_heads: Number of attention heads
            dropout: Dropout rate for regularization
        """
        self.n_features = n_features
        self.n_profiles = n_profiles
        self.d_model = d_model
        self.n_heads = n_heads
        self.dropout = dropout
        
        if TORCH_AVAILABLE:
            self._init_pytorch()
        else:
            self._init_numpy()
        
        # Tracking
        self.training_losses = []
        self.prediction_history = []
    
    def _init_pytorch(self):
        """Initialize PyTorch model"""
        self.model = TorchTransformerClassifier(
            n_features=self.n_features,
            n_profiles=self.n_profiles,
            d_model=self.d_model,
            n_heads=self.n_heads,
            dropout=self.dropout
        )
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(), 
            lr=0.001, 
            weight_decay=0.01
        )
        self.mode = "pytorch"
    
    def _init_numpy(self):
        """Initialize numpy fallback (simplified version)"""
        np.random.seed(42)
        
        # Weights pour une version simplifiée
        self.W_embed = np.random.randn(self.n_features, self.d_model) * 0.1
        self.W_query = np.random.randn(self.d_model, self.d_model) * 0.1
        self.W_key = np.random.randn(self.d_model, self.d_model) * 0.1
        self.W_value = np.random.randn(self.d_model, self.d_model) * 0.1
        self.W_out = np.random.randn(self.d_model, self.n_profiles) * 0.1
        self.b_out = np.zeros(self.n_profiles)
        
        self.mode = "numpy"
    
    def predict(self, features: np.ndarray) -> Tuple[int, float]:
        """
        Prédiction avec confidence
        
        Args:
            features: Array de features (24 valeurs)
            
        Returns:
            Tuple (index_profil, confidence)
        """
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        if TORCH_AVAILABLE and self.mode == "pytorch":
            return self._predict_pytorch(features)
        else:
            return self._predict_numpy(features)
    
    def _predict_pytorch(self, features: np.ndarray) -> Tuple[int, float]:
        """Prédiction avec PyTorch"""
        self.model.eval()
        with torch.no_grad():
            x = torch.tensor(features, dtype=torch.float32)
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1)
            pred = torch.argmax(probs, dim=1).item()
            conf = probs[0, pred].item()
        return pred, conf
    
    def _predict_numpy(self, features: np.ndarray) -> Tuple[int, float]:
        """Prédiction avec numpy (version simplifiée)"""
        # Embedding
        embedded = np.dot(features, self.W_embed)  # (1, d_model)
        
        # Self-attention simplifiée
        Q = np.dot(embedded, self.W_query)
        K = np.dot(embedded, self.W_key)
        V = np.dot(embedded, self.W_value)
        
        attention = np.dot(Q, K.T) / np.sqrt(self.d_model)
        attention = self._softmax(attention)
        attended = np.dot(attention, V)
        
        # Output
        logits = np.dot(attended, self.W_out) + self.b_out
        probs = self._softmax(logits.flatten())
        
        pred = np.argmax(probs)
        conf = probs[pred]
        
        return int(pred), float(conf)
    
    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """
        Retourne les probabilités pour chaque classe
        
        Args:
            features: Array de features
            
        Returns:
            Array de probabilités (12 valeurs)
        """
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        if TORCH_AVAILABLE and self.mode == "pytorch":
            self.model.eval()
            with torch.no_grad():
                x = torch.tensor(features, dtype=torch.float32)
                logits = self.model(x)
                probs = torch.softmax(logits, dim=1)
            return probs.numpy()
        else:
            # Version numpy
            embedded = np.dot(features, self.W_embed)
            Q = np.dot(embedded, self.W_query)
            K = np.dot(embedded, self.W_key)
            V = np.dot(embedded, self.W_value)
            attention = self._softmax(np.dot(Q, K.T) / np.sqrt(self.d_model))
            attended = np.dot(attention, V)
            logits = np.dot(attended, self.W_out) + self.b_out
            return self._softmax(logits)
    
    def learn_from_error(self, features: np.ndarray, correct_label: int,
                        profit: float, epochs: int = 3) -> float:
        """
        Apprentissage online quand une erreur est détectée
        
        L'idée: quand on se trompe, on apprend immédiatement de cette erreur
        Le profit perdu pondère l'importance de l'apprentissage
        
        Args:
            features: Features de l'équipe mal classée
            correct_label: Index du profil correct
            profit: Profit/perte de la prédiction (négatif si perte)
            epochs: Nombre de passes d'apprentissage
            
        Returns:
            Loss finale après apprentissage
        """
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        if not TORCH_AVAILABLE or self.mode != "pytorch":
            # Version numpy: apprentissage simplifié par ajustement des poids
            return self._learn_numpy(features, correct_label, profit)
        
        self.model.train()
        
        x = torch.tensor(features, dtype=torch.float32)
        y = torch.tensor([correct_label], dtype=torch.long)
        
        # Pondération par le profit perdu (erreurs coûteuses = plus importantes)
        loss_weight = 1.0 + abs(profit) / 5 if profit < 0 else 1.0
        
        final_loss = 0
        for _ in range(epochs):
            self.optimizer.zero_grad()
            logits = self.model(x)
            loss = nn.CrossEntropyLoss()(logits, y) * loss_weight
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
            final_loss = loss.item()
        
        self.training_losses.append(final_loss)
        return final_loss
    
    def _learn_numpy(self, features: np.ndarray, correct_label: int,
                    profit: float) -> float:
        """Apprentissage simplifié pour version numpy"""
        # Prédiction actuelle
        probs = self.predict_proba(features)
        current_pred = np.argmax(probs)
        
        # Learning rate adaptatif selon le profit perdu
        lr = 0.01 * (1.0 + abs(profit) / 5) if profit < 0 else 0.01
        
        # Ajuster W_out pour augmenter la proba du bon label
        target = np.zeros(self.n_profiles)
        target[correct_label] = 1.0
        
        gradient = probs.flatten() - target
        
        # Mise à jour simplifiée
        embedded = np.dot(features, self.W_embed)
        self.W_out -= lr * np.outer(embedded.flatten(), gradient)
        self.b_out -= lr * gradient
        
        # Calculer loss
        loss = -np.log(probs.flatten()[correct_label] + 1e-10)
        self.training_losses.append(loss)
        
        return float(loss)
    
    def get_attention_weights(self, features: np.ndarray) -> AttentionOutput:
        """
        Obtenir les poids d'attention pour interprétabilité
        
        Permet de comprendre quelles features sont les plus importantes
        pour la classification
        
        Args:
            features: Array de features
            
        Returns:
            AttentionOutput avec poids et feature importance
        """
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        if TORCH_AVAILABLE and self.mode == "pytorch":
            self.model.eval()
            with torch.no_grad():
                x = torch.tensor(features, dtype=torch.float32)
                logits, attention_weights = self.model(x, return_attention=True)
                att_weights = attention_weights.numpy()
        else:
            # Version numpy
            embedded = np.dot(features, self.W_embed)
            Q = np.dot(embedded, self.W_query)
            K = np.dot(embedded, self.W_key)
            att_weights = self._softmax(np.dot(Q, K.T) / np.sqrt(self.d_model))
            
            logits = self.predict_proba(features)
        
        # Calculer l'importance des features
        # (basé sur la magnitude des embeddings)
        feature_importance = {}
        for i, name in enumerate(self.FEATURE_ORDER):
            if i < features.shape[1]:
                importance = abs(features[0, i] * self.W_embed[i].sum() if self.mode == "numpy" else features[0, i])
                feature_importance[name] = float(importance)
        
        # Normaliser
        total = sum(feature_importance.values()) + 0.001
        feature_importance = {k: v/total for k, v in feature_importance.items()}
        
        return AttentionOutput(
            logits=logits if isinstance(logits, np.ndarray) else logits.numpy(),
            attention_weights=att_weights,
            feature_importance=feature_importance
        )
    
    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Softmax stable numériquement"""
        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e_x / (e_x.sum(axis=-1, keepdims=True) + 1e-10)
    
    def get_training_stats(self) -> Dict:
        """Statistiques d'entraînement"""
        if not self.training_losses:
            return {"total_updates": 0}
        
        return {
            "total_updates": len(self.training_losses),
            "avg_loss": np.mean(self.training_losses[-50:]) if self.training_losses else 0,
            "recent_loss": self.training_losses[-1] if self.training_losses else 0,
            "loss_trend": (
                "decreasing" if len(self.training_losses) > 10 and 
                np.mean(self.training_losses[-10:]) < np.mean(self.training_losses[-20:-10])
                else "stable"
            ),
            "mode": self.mode
        }


if TORCH_AVAILABLE:
    class TorchTransformerClassifier(nn.Module):
        """
        PyTorch implementation of the Transformer classifier
        """
        
        def __init__(self, n_features: int = 24, n_profiles: int = 12,
                    d_model: int = 64, n_heads: int = 4, dropout: float = 0.1):
            super().__init__()
            
            self.n_profiles = n_profiles
            
            # Feature embedding
            self.feature_embedding = nn.Sequential(
                nn.Linear(n_features, d_model),
                nn.LayerNorm(d_model),
                nn.ReLU(),
                nn.Dropout(dropout)
            )
            
            # Self-Attention
            self.attention = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
            
            # Layer norm après attention
            self.norm1 = nn.LayerNorm(d_model)
            
            # Feed-forward network
            self.ff_network = nn.Sequential(
                nn.Linear(d_model, d_model * 4),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_model * 4, d_model),
            )
            
            # Layer norm après FF
            self.norm2 = nn.LayerNorm(d_model)
            
            # Classification head
            self.classifier = nn.Sequential(
                nn.Linear(d_model, d_model // 2),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(d_model // 2, n_profiles)
            )
        
        def forward(self, x: torch.Tensor, return_attention: bool = False):
            """
            Forward pass
            
            Args:
                x: Input tensor (batch, n_features)
                return_attention: If True, also return attention weights
                
            Returns:
                logits (and optionally attention weights)
            """
            # Embedding
            embedded = self.feature_embedding(x)  # (batch, d_model)
            embedded = embedded.unsqueeze(1)  # (batch, 1, d_model) pour attention
            
            # Self-Attention
            attended, attention_weights = self.attention(embedded, embedded, embedded)
            
            # Residual + Norm
            x = self.norm1(embedded + attended)
            
            # Feed-forward avec residual
            ff_out = self.ff_network(x)
            x = self.norm2(x + ff_out)
            
            # Squeeze et classifier
            x = x.squeeze(1)  # (batch, d_model)
            logits = self.classifier(x)
            
            if return_attention:
                return logits, attention_weights
            return logits


# Export
__all__ = ["TransformerProfileClassifier", "AttentionOutput"]
```

---

### 2.5 - `/quantum/chess_engine_v25/learning/feedback/__init__.py`

```python
"""Feedback module - Error memory, drift detection, dual learning"""

from .error_memory import ErrorMemory, ErrorMemoryEntry
from .drift_detector import StyleDriftDetector, DriftAlert
from .dual_objective import DualObjectiveLearner

__all__ = [
    "ErrorMemory", 
    "ErrorMemoryEntry", 
    "StyleDriftDetector", 
    "DriftAlert",
    "DualObjectiveLearner"
]
```

---

### 2.6 - `/quantum/chess_engine_v25/learning/feedback/error_memory.py`

```python
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
```

---

### 2.7 - `/quantum/chess_engine_v25/learning/feedback/drift_detector.py`

```python
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
```

---

### 2.8 - `/quantum/chess_engine_v25/learning/feedback/dual_objective.py`

```python
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
```

---

### 2.9 - `/quantum/chess_engine_v25/learning/data/__init__.py`

```python
"""Data module - Temporal weighting and adaptive buffer"""

from .temporal_weighting import TemporalDataManager
from .adaptive_buffer import AdaptiveBuffer

__all__ = ["TemporalDataManager", "AdaptiveBuffer"]
```

---

### 2.10 - `/quantum/chess_engine_v25/learning/data/temporal_weighting.py`

```python
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
```

---

### 2.11 - `/quantum/chess_engine_v25/learning/data/adaptive_buffer.py`

```python
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
```

---

### 2.12 - `/quantum/chess_engine_v25/learning/ensemble/__init__.py`

```python
"""Ensemble module - Adaptive ensemble and weight management"""

# Note: Main ensemble logic is in profile_classifier.py
# This module can be extended for additional ensemble strategies

__all__ = []
```

---

### 2.13 - `/quantum/chess_engine_v25/learning/profile_classifier.py` (FICHIER PRINCIPAL)

```python
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
```

---

## 📋 ÉTAPE 3 : TESTER LE MODULE

```bash
cd /root/mon_ps/backend/quantum/chess_engine_v25

# Test rapide Python
python3 -c "
from learning import AdaptiveProfileClassifier, TacticalProfile

# Créer le classifier
classifier = AdaptiveProfileClassifier()

# Test classification
result = classifier.classify(
    team_id='liverpool',
    team_metrics={
        'possession': 52,
        'ppda': 6.5,
        'verticality': 55,
        'pressing_intensity': 82,
        'high_recoveries_pct': 35
    }
)

print(f'✅ Profile: {result.primary_profile.value}')
print(f'✅ Confidence: {result.confidence:.2f}')
print('✅ Module Learning fonctionne!')
"
```

---

## 📊 RÉCAPITULATIF

| Fichier | Lignes | Description |
|---------|--------|-------------|
| `__init__.py` | 61 | Exports publics |
| `profile_classifier.py` | 701 | **ORCHESTRATEUR PRINCIPAL** |
| `classifiers/rule_based.py` | 383 | Règles expertes |
| `classifiers/transformer.py` | 434 | Neural + Attention |
| `feedback/error_memory.py` | 360 | Mémoire erreurs |
| `feedback/drift_detector.py` | 424 | Détection changement |
| `feedback/dual_objective.py` | 452 | Accuracy + Profit |
| `data/temporal_weighting.py` | 406 | Pondération temporelle |
| `data/adaptive_buffer.py` | 349 | Buffer adaptatif |
| **TOTAL** | **~3,600** | |

---

## ⚠️ NOTES IMPORTANTES

1. **Ordre de création**: Créer les dossiers d'abord, puis les fichiers `__init__.py`, puis les modules
2. **Dépendances optionnelles**: scikit-learn et PyTorch sont optionnels (fallback numpy)
3. **Persistance**: Le chemin de persistance est optionnel
4. **Tests**: Toujours tester après création avec le snippet Python fourni

---

**Fin des instructions. Claude Code peut maintenant créer tous les fichiers sur le serveur.**
