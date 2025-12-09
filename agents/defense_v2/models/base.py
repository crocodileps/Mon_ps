"""
═══════════════════════════════════════════════════════════════════════════════
🏦 AGENT DÉFENSE 2.0 - BASE MODEL
   Modèle de base avec calibration des probabilités
   
   CALIBRATION METHODS:
   - Platt Scaling (logistic regression sur probas)
   - Isotonic Regression (non-parametric)
   - Temperature Scaling (simple)
   
   METRICS:
   - Brier Score (calibration)
   - Log Loss (probabilistic)
   - AUC-ROC (discrimination)
   - Expected Calibration Error (ECE)
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import (
    accuracy_score, roc_auc_score, brier_score_loss, 
    log_loss, precision_score, recall_score, f1_score
)
import warnings
warnings.filterwarnings('ignore')


class CalibratedModel:
    """
    Wrapper pour calibration des probabilités.
    
    La calibration est CRITIQUE pour le betting:
    - Un modèle peut avoir bon AUC mais mauvaises probas
    - Les probas non-calibrées mènent à des Kelly stakes incorrects
    - Une proba de 60% doit correspondre à 60% de succès réels
    """
    
    def __init__(self, base_model, method: str = 'isotonic'):
        """
        Args:
            base_model: Modèle sklearn de base
            method: 'isotonic', 'platt', ou 'temperature'
        """
        self.base_model = base_model
        self.method = method
        self.calibrator = None
        self.is_fitted = False
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'CalibratedModel':
        """
        Entraîne le modèle et le calibrateur.
        
        Process:
        1. Entraîner le modèle de base
        2. Obtenir les probabilités OOF (out-of-fold)
        3. Entraîner le calibrateur sur probas vs labels
        """
        # 1. Entraîner le modèle de base
        self.base_model.fit(X, y)
        
        # 2. Obtenir probas OOF via cross-validation
        try:
            probas_oof = cross_val_predict(
                self.base_model, X, y, 
                cv=5, method='predict_proba'
            )[:, 1]
        except:
            # Fallback: utiliser les probas d'entraînement (moins idéal)
            probas_oof = self.base_model.predict_proba(X)[:, 1]
        
        # 3. Entraîner le calibrateur
        if self.method == 'isotonic':
            self.calibrator = IsotonicRegression(
                y_min=0.001, y_max=0.999, out_of_bounds='clip'
            )
            self.calibrator.fit(probas_oof, y)
        
        elif self.method == 'platt':
            self.calibrator = LogisticRegression(C=1.0, solver='lbfgs')
            self.calibrator.fit(probas_oof.reshape(-1, 1), y)
        
        elif self.method == 'temperature':
            # Simple temperature scaling
            self.temperature = self._find_temperature(probas_oof, y)
        
        self.is_fitted = True
        return self
    
    def _find_temperature(self, probas: np.ndarray, y: np.ndarray) -> float:
        """Trouve la température optimale pour scaling."""
        from scipy.optimize import minimize_scalar
        
        def nll(T):
            scaled = self._apply_temperature(probas, T)
            return log_loss(y, scaled)
        
        result = minimize_scalar(nll, bounds=(0.1, 10.0), method='bounded')
        return result.x
    
    def _apply_temperature(self, probas: np.ndarray, T: float) -> np.ndarray:
        """Applique le temperature scaling."""
        # Convertir probas en logits, diviser par T, reconvertir
        logits = np.log(probas / (1 - probas + 1e-10))
        scaled_logits = logits / T
        return 1 / (1 + np.exp(-scaled_logits))
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Retourne les probabilités calibrées."""
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        
        # Probas brutes
        probas_raw = self.base_model.predict_proba(X)[:, 1]
        
        # Calibrer
        if self.method == 'isotonic':
            probas_cal = self.calibrator.transform(probas_raw)
        elif self.method == 'platt':
            probas_cal = self.calibrator.predict_proba(
                probas_raw.reshape(-1, 1)
            )[:, 1]
        elif self.method == 'temperature':
            probas_cal = self._apply_temperature(probas_raw, self.temperature)
        else:
            probas_cal = probas_raw
        
        # Retourner format sklearn [P(0), P(1)]
        return np.column_stack([1 - probas_cal, probas_cal])
    
    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Retourne les prédictions binaires."""
        probas = self.predict_proba(X)[:, 1]
        return (probas >= threshold).astype(int)


class BaseModel:
    """
    Modèle de base pour l'Agent Défense 2.0.
    
    Features:
    - Support classification et regression
    - Calibration automatique des probabilités
    - Métriques complètes (AUC, Brier, ECE)
    - Feature importance
    """
    
    def __init__(self, 
                 model_type: str = 'random_forest',
                 task: str = 'classification',
                 calibration: str = 'isotonic',
                 params: Dict = None):
        """
        Args:
            model_type: 'random_forest', 'gradient_boosting', 'xgboost'
            task: 'classification' ou 'regression'
            calibration: 'isotonic', 'platt', 'temperature', None
            params: Paramètres du modèle
        """
        self.model_type = model_type
        self.task = task
        self.calibration = calibration
        self.params = params or {}
        
        self.model = None
        self.calibrated_model = None
        self.feature_names = None
        self.feature_importance = None
        self.metrics = {}
        self.is_fitted = False
    
    def _create_model(self):
        """Crée le modèle sklearn."""
        if self.task == 'classification':
            if self.model_type == 'random_forest':
                return RandomForestClassifier(
                    n_estimators=self.params.get('n_estimators', 200),
                    max_depth=self.params.get('max_depth', 12),
                    min_samples_split=self.params.get('min_samples_split', 10),
                    min_samples_leaf=self.params.get('min_samples_leaf', 5),
                    random_state=42,
                    n_jobs=-1
                )
            elif self.model_type == 'gradient_boosting':
                return GradientBoostingClassifier(
                    n_estimators=self.params.get('n_estimators', 150),
                    max_depth=self.params.get('max_depth', 6),
                    learning_rate=self.params.get('learning_rate', 0.05),
                    min_samples_split=self.params.get('min_samples_split', 10),
                    random_state=42
                )
        else:
            # Regression
            from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
            if self.model_type == 'random_forest':
                return RandomForestRegressor(
                    n_estimators=self.params.get('n_estimators', 200),
                    max_depth=self.params.get('max_depth', 12),
                    random_state=42,
                    n_jobs=-1
                )
            elif self.model_type == 'gradient_boosting':
                return GradientBoostingRegressor(
                    n_estimators=self.params.get('n_estimators', 150),
                    max_depth=self.params.get('max_depth', 6),
                    learning_rate=self.params.get('learning_rate', 0.05),
                    random_state=42
                )
        
        raise ValueError(f"Unknown model type: {self.model_type}")
    
    def fit(self, X: Union[np.ndarray, pd.DataFrame], 
            y: Union[np.ndarray, pd.Series],
            feature_names: List[str] = None) -> 'BaseModel':
        """
        Entraîne le modèle.
        
        Args:
            X: Features
            y: Target
            feature_names: Noms des features (optionnel)
        """
        # Convertir en numpy si nécessaire
        if isinstance(X, pd.DataFrame):
            self.feature_names = list(X.columns)
            X = X.values
        else:
            self.feature_names = feature_names or [f'f_{i}' for i in range(X.shape[1])]
        
        if isinstance(y, pd.Series):
            y = y.values
        
        # Créer et entraîner le modèle
        self.model = self._create_model()
        
        if self.task == 'classification' and self.calibration:
            # Modèle calibré
            self.calibrated_model = CalibratedModel(
                self.model, method=self.calibration
            )
            self.calibrated_model.fit(X, y)
        else:
            # Modèle standard
            self.model.fit(X, y)
        
        # Feature importance
        if hasattr(self.model, 'feature_importances_'):
            self.feature_importance = dict(zip(
                self.feature_names, 
                self.model.feature_importances_
            ))
        
        self.is_fitted = True
        return self
    
    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Retourne les prédictions."""
        if isinstance(X, pd.DataFrame):
            X = X.values
        
        if self.task == 'classification' and self.calibrated_model:
            return self.calibrated_model.predict(X)
        return self.model.predict(X)
    
    def predict_proba(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Retourne les probabilités (classification only)."""
        if self.task != 'classification':
            raise ValueError("predict_proba only for classification")
        
        if isinstance(X, pd.DataFrame):
            X = X.values
        
        if self.calibrated_model:
            return self.calibrated_model.predict_proba(X)
        return self.model.predict_proba(X)
    
    def evaluate(self, X: Union[np.ndarray, pd.DataFrame], 
                 y: Union[np.ndarray, pd.Series]) -> Dict[str, float]:
        """
        Évalue le modèle avec métriques complètes.
        
        Returns:
            Dict avec accuracy, auc, brier, log_loss, ece
        """
        if isinstance(X, pd.DataFrame):
            X = X.values
        if isinstance(y, pd.Series):
            y = y.values
        
        metrics = {}
        
        if self.task == 'classification':
            y_pred = self.predict(X)
            y_proba = self.predict_proba(X)[:, 1]
            
            metrics['accuracy'] = accuracy_score(y, y_pred)
            metrics['precision'] = precision_score(y, y_pred, zero_division=0)
            metrics['recall'] = recall_score(y, y_pred, zero_division=0)
            metrics['f1'] = f1_score(y, y_pred, zero_division=0)
            
            try:
                metrics['auc'] = roc_auc_score(y, y_proba)
            except:
                metrics['auc'] = 0.5
            
            metrics['brier'] = brier_score_loss(y, y_proba)
            metrics['log_loss'] = log_loss(y, y_proba)
            
            # Expected Calibration Error
            metrics['ece'] = self._calculate_ece(y, y_proba)
        
        else:
            # Regression
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            y_pred = self.predict(X)
            
            metrics['mse'] = mean_squared_error(y, y_pred)
            metrics['rmse'] = np.sqrt(metrics['mse'])
            metrics['mae'] = mean_absolute_error(y, y_pred)
            metrics['r2'] = r2_score(y, y_pred)
        
        self.metrics = metrics
        return metrics
    
    def _calculate_ece(self, y_true: np.ndarray, y_proba: np.ndarray, 
                       n_bins: int = 10) -> float:
        """
        Calcule l'Expected Calibration Error.
        
        ECE = Σ |B_m| / n × |acc(B_m) - conf(B_m)|
        
        Une bonne calibration = ECE proche de 0
        """
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        
        for i in range(n_bins):
            in_bin = (y_proba >= bin_boundaries[i]) & (y_proba < bin_boundaries[i + 1])
            prop_in_bin = in_bin.mean()
            
            if prop_in_bin > 0:
                avg_confidence = y_proba[in_bin].mean()
                avg_accuracy = y_true[in_bin].mean()
                ece += prop_in_bin * abs(avg_accuracy - avg_confidence)
        
        return ece
    
    def get_top_features(self, n: int = 20) -> List[Tuple[str, float]]:
        """Retourne les top N features par importance."""
        if not self.feature_importance:
            return []
        
        sorted_features = sorted(
            self.feature_importance.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        return sorted_features[:n]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    # Test simple
    from sklearn.datasets import make_classification
    
    print("🧪 Test BaseModel avec calibration")
    
    # Créer données synthétiques
    X, y = make_classification(n_samples=1000, n_features=20, random_state=42)
    
    # Split
    X_train, X_test = X[:800], X[800:]
    y_train, y_test = y[:800], y[800:]
    
    # Entraîner modèle calibré
    model = BaseModel(
        model_type='random_forest',
        task='classification',
        calibration='isotonic'
    )
    model.fit(X_train, y_train)
    
    # Évaluer
    metrics = model.evaluate(X_test, y_test)
    
    print(f"\n📊 Métriques:")
    for name, value in metrics.items():
        print(f"   • {name}: {value:.4f}")
    
    print(f"\n📋 Top 5 features:")
    for name, imp in model.get_top_features(5):
        print(f"   • {name}: {imp:.4f}")
