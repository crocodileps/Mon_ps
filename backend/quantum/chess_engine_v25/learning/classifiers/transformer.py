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
