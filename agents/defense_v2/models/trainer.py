"""
═══════════════════════════════════════════════════════════════════════════════
🏦 AGENT DÉFENSE 2.0 - MODEL TRAINER
   Entraînement multi-marchés avec validation croisée
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import pickle
import json
from datetime import datetime
from sklearn.model_selection import train_test_split, cross_val_score
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import MARKETS, MODEL_PARAMS, MODEL_DIR, THRESHOLDS
from .base import BaseModel


class ModelTrainer:
    """
    Entraîne les modèles pour tous les marchés définis.
    
    MARCHÉS COUVERTS (27):
    - Goals: over_15, over_25, over_35, btts, total_goals, cs_home, cs_away
    - Timing: 1h_over_05, 1h_over_15, 2h_goals, late_goal
    - Cards: over_35_cards, over_45_cards, total_cards
    - Corners: over_85, over_95, over_105, total_corners
    - Advanced: high_volatility, regression_play
    """
    
    def __init__(self, 
                 model_type: str = 'random_forest',
                 calibration: str = 'isotonic'):
        """
        Args:
            model_type: Type de modèle sklearn
            calibration: Méthode de calibration
        """
        self.model_type = model_type
        self.calibration = calibration
        self.models = {}
        self.metrics = {}
        self.feature_importance = {}
        self.training_date = None
    
    def train_all_markets(self, X: pd.DataFrame, y: pd.DataFrame,
                          test_size: float = 0.2,
                          markets: List[str] = None) -> Dict[str, Dict]:
        """
        Entraîne les modèles pour tous les marchés.
        
        Args:
            X: Features DataFrame
            y: Targets DataFrame (colonnes = marchés)
            test_size: Proportion test set
            markets: Liste des marchés à entraîner (None = tous)
        
        Returns:
            Dict avec métriques par marché
        """
        self.training_date = datetime.now().isoformat()
        
        # Filtrer les marchés disponibles
        available_targets = [col for col in y.columns if col in MARKETS or col in y.columns]
        
        if markets:
            targets_to_train = [t for t in markets if t in available_targets]
        else:
            targets_to_train = available_targets
        
        print("=" * 80)
        print(f"🏦 ENTRAÎNEMENT MULTI-MARCHÉS - {len(targets_to_train)} marchés")
        print("=" * 80)
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        print(f"\n📊 Dataset: {len(X_train)} train, {len(X_test)} test")
        
        results = {}
        
        for target in targets_to_train:
            if target not in y.columns:
                continue
            
            # Déterminer le type de tâche
            market_config = MARKETS.get(target, {})
            task = market_config.get('type', 'classification')
            
            # Récupérer les données pour ce target
            y_target_train = y_train[target].values
            y_target_test = y_test[target].values
            
            # Vérifier qu'il y a assez de variance
            if task == 'classification':
                unique_values = np.unique(y_target_train)
                if len(unique_values) < 2:
                    print(f"   ⚠️ {target}: Pas assez de variance, skip")
                    continue
                if len(unique_values) > 2:
                    # Multiclass détecté - convertir en régression ou skip
                    print(f"   ⚠️ {target}: Multiclass détecté ({len(unique_values)} classes), traité comme régression")
                    task = 'regression' 
            
            print(f"\n📈 {target} ({task})...", end=" ")
            
            try:
                # Créer et entraîner le modèle
                model = BaseModel(
                    model_type=self.model_type,
                    task=task,
                    calibration=self.calibration if task == 'classification' else None,
                    params=MODEL_PARAMS.get(self.model_type, {})
                )
                
                model.fit(X_train, y_target_train, feature_names=list(X.columns))
                
                # Évaluer
                metrics = model.evaluate(X_test, y_target_test)
                
                # Stocker
                self.models[target] = model
                self.metrics[target] = metrics
                self.feature_importance[target] = model.get_top_features(20)
                
                # Afficher résultat
                if task == 'classification':
                    print(f"AUC={metrics.get('auc', 0):.3f}, Brier={metrics.get('brier', 0):.3f}, ECE={metrics.get('ece', 0):.3f}")
                else:
                    print(f"RMSE={metrics.get('rmse', 0):.3f}, R²={metrics.get('r2', 0):.3f}")
                
                results[target] = {
                    'metrics': metrics,
                    'task': task,
                    'top_features': self.feature_importance[target][:5]
                }
                
            except Exception as e:
                print(f"❌ Erreur: {e}")
                continue
        
        # Résumé
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: Dict) -> None:
        """Affiche un résumé des entraînements."""
        print("\n" + "=" * 80)
        print("📊 RÉSUMÉ ENTRAÎNEMENT")
        print("=" * 80)
        
        classification_models = [(k, v) for k, v in results.items() if v['task'] == 'classification']
        regression_models = [(k, v) for k, v in results.items() if v['task'] == 'regression']
        
        if classification_models:
            print("\n📈 CLASSIFICATION:")
            print(f"   {'Marché':<25} {'AUC':>8} {'Brier':>8} {'ECE':>8} {'Acc':>8}")
            print("   " + "-" * 60)
            
            for market, data in sorted(classification_models, key=lambda x: -x[1]['metrics'].get('auc', 0)):
                m = data['metrics']
                print(f"   {market:<25} {m.get('auc', 0):>8.3f} {m.get('brier', 0):>8.3f} {m.get('ece', 0):>8.3f} {m.get('accuracy', 0):>8.1%}")
        
        if regression_models:
            print("\n📈 REGRESSION:")
            print(f"   {'Marché':<25} {'RMSE':>8} {'MAE':>8} {'R²':>8}")
            print("   " + "-" * 45)
            
            for market, data in sorted(regression_models, key=lambda x: x[1]['metrics'].get('rmse', 999)):
                m = data['metrics']
                print(f"   {market:<25} {m.get('rmse', 0):>8.3f} {m.get('mae', 0):>8.3f} {m.get('r2', 0):>8.3f}")
    
    def save_models(self, path: Path = None) -> str:
        """Sauvegarde tous les modèles."""
        if path is None:
            path = MODEL_DIR
        
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # Sauvegarder les modèles
        models_path = path / f'models_{timestamp}.pkl'
        with open(models_path, 'wb') as f:
            pickle.dump(self.models, f)
        
        # Sauvegarder les métadonnées
        metadata = {
            'training_date': self.training_date,
            'model_type': self.model_type,
            'calibration': self.calibration,
            'metrics': self.metrics,
            'markets': list(self.models.keys()),
            'feature_importance': {k: v[:10] for k, v in self.feature_importance.items()}
        }
        
        meta_path = path / f'metadata_{timestamp}.json'
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        print(f"\n💾 Modèles sauvegardés: {models_path}")
        print(f"💾 Métadonnées: {meta_path}")
        
        return str(models_path)
    
    def load_models(self, path: str) -> None:
        """Charge les modèles depuis un fichier."""
        with open(path, 'rb') as f:
            self.models = pickle.load(f)
        print(f"✅ {len(self.models)} modèles chargés depuis {path}")
    
    def predict(self, market: str, X: pd.DataFrame) -> Dict[str, Any]:
        """
        Prédit pour un marché spécifique.
        
        Returns:
            Dict avec 'prediction', 'probability', 'confidence'
        """
        if market not in self.models:
            raise ValueError(f"Market {market} not trained")
        
        model = self.models[market]
        
        result = {
            'market': market,
            'prediction': model.predict(X)[0],
        }
        
        if model.task == 'classification':
            proba = model.predict_proba(X)[0, 1]
            result['probability'] = proba
            result['confidence'] = abs(proba - 0.5) * 2  # 0-1 scale
        else:
            result['value'] = model.predict(X)[0]
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("🧪 Test ModelTrainer")
    
    # Import loader et engineer
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data.loader import DefenseDataLoader
    from features.engineer import FeatureEngineer
    
    # Charger données
    loader = DefenseDataLoader()
    loader.load_all()
    
    # Créer features
    engineer = FeatureEngineer(loader)
    matches = loader.get_matches().head(500)  # 500 matchs pour test rapide
    X, y = engineer.build_dataset(matches)
    
    print(f"\n📊 Dataset: {X.shape[0]} matchs × {X.shape[1]} features")
    print(f"📋 Targets: {list(y.columns)}")
    
    # Entraîner
    trainer = ModelTrainer(model_type='random_forest', calibration='isotonic')
    results = trainer.train_all_markets(X, y, test_size=0.2)
    
    # Sauvegarder
    trainer.save_models()
