#!/usr/bin/env python3
"""
🤖 MODULE ML - ENTRAÎNEMENT BTTS
=================================
Entraîne les modèles ML sur les données historiques

Modèles:
- Random Forest
- Gradient Boosting  
- Logistic Regression
- Ensemble (moyenne pondérée)

Auteur: Mon_PS System
Version: 1.0.0
Date: 29/11/2025
"""

import os
import sys
import json
import pickle
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import math

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ML_Trainer')

# Imports ML
try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
    HAS_ML = True
except ImportError:
    HAS_ML = False
    logger.warning("sklearn non disponible")

# Connexion DB
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    logger.error("psycopg2 requis")
    sys.exit(1)


class BTTSMLTrainer:
    """
    Entraîneur ML pour les prédictions BTTS
    """
    
    MODEL_PATH = '/home/Mon_ps/backend/agents/btts_calculator/models'
    
    def __init__(self, db_config: Dict = None):
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 5432,
            'database': 'monps_db',
            'user': 'monps_user',
            'password': 'monps_secure_password_2024'
        }
        self.conn = None
        self._connect()
        
        # Modèles
        self.models = {}
        self.scaler = StandardScaler() if HAS_ML else None
        self.feature_names = []
        self.is_trained = False
        
        # Créer le dossier models
        os.makedirs(self.MODEL_PATH, exist_ok=True)
    
    def _connect(self):
        """Connexion DB"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("✅ Connexion DB établie")
        except:
            try:
                self.db_config['host'] = 'monps_postgres'
                self.conn = psycopg2.connect(**self.db_config)
                logger.info("✅ Connexion DB (Docker)")
            except Exception as e:
                logger.error(f"❌ Connexion échouée: {e}")
                raise
    
    def extract_features(self, home_team: str, away_team: str) -> Optional[np.ndarray]:
        """
        Extrait les features pour un match
        """
        if not HAS_ML:
            return None
        
        features = []
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Features équipe domicile
                cur.execute("""
                    SELECT 
                        home_btts_rate, away_btts_rate, btts_tendency,
                        home_goals_scored_avg, home_goals_conceded_avg,
                        home_clean_sheet_rate, home_failed_to_score_rate,
                        home_over25_rate, xg_for_avg, xg_against_avg
                    FROM team_intelligence
                    WHERE LOWER(team_name) LIKE LOWER(%s)
                    LIMIT 1
                """, (f'%{home_team}%',))
                
                home = cur.fetchone()
                
                # Features équipe extérieur
                cur.execute("""
                    SELECT 
                        home_btts_rate, away_btts_rate, btts_tendency,
                        away_goals_scored_avg, away_goals_conceded_avg,
                        away_clean_sheet_rate, away_failed_to_score_rate,
                        away_over25_rate, xg_for_avg, xg_against_avg
                    FROM team_intelligence
                    WHERE LOWER(team_name) LIKE LOWER(%s)
                    LIMIT 1
                """, (f'%{away_team}%',))
                
                away = cur.fetchone()
                
                if home and away:
                    features = [
                        float(home.get('home_btts_rate') or 50),
                        float(home.get('home_goals_scored_avg') or 1.3),
                        float(home.get('home_goals_conceded_avg') or 1.0),
                        float(home.get('home_clean_sheet_rate') or 30),
                        float(home.get('home_failed_to_score_rate') or 20),
                        float(home.get('xg_for_avg') or 0),
                        float(away.get('away_btts_rate') or 50),
                        float(away.get('away_goals_scored_avg') or 1.0),
                        float(away.get('away_goals_conceded_avg') or 1.4),
                        float(away.get('away_clean_sheet_rate') or 20),
                        float(away.get('away_failed_to_score_rate') or 30),
                        float(away.get('xg_against_avg') or 0),
                    ]
                    
                    return np.array(features).reshape(1, -1)
                    
        except Exception as e:
            logger.error(f"Erreur extraction features: {e}")
        
        return None
    
    def prepare_training_data(self, days: int = 90) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prépare les données d'entraînement depuis l'historique
        """
        if not HAS_ML:
            return None, None
        
        X = []
        y = []
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Récupérer les matchs avec résultats
                cur.execute("""
                    SELECT 
                        home_team, away_team,
                        home_goals, away_goals,
                        CASE WHEN home_goals > 0 AND away_goals > 0 THEN 1 ELSE 0 END as btts
                    FROM matches_results
                    WHERE match_date > NOW() - INTERVAL '%s days'
                    AND home_goals IS NOT NULL
                    ORDER BY match_date DESC
                """, (days,))
                
                matches = cur.fetchall()
                
                logger.info(f"📊 {len(matches)} matchs trouvés")
                
                for match in matches:
                    features = self.extract_features(match['home_team'], match['away_team'])
                    
                    if features is not None:
                        X.append(features.flatten())
                        y.append(match['btts'])
                
                logger.info(f"✅ {len(X)} matchs avec features extraites")
                
                if len(X) > 0:
                    return np.array(X), np.array(y)
                    
        except Exception as e:
            logger.error(f"Erreur préparation données: {e}")
        
        return None, None
    
    def train(self, days: int = 90, test_size: float = 0.2) -> Dict:
        """
        Entraîne les modèles ML
        """
        if not HAS_ML:
            return {'success': False, 'message': 'ML non disponible'}
        
        logger.info(f"🚀 Démarrage entraînement sur {days} jours...")
        
        # Préparer les données
        X, y = self.prepare_training_data(days)
        
        if X is None or len(X) < 50:
            return {
                'success': False,
                'message': f'Pas assez de données ({len(X) if X is not None else 0} matchs)'
            }
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Normaliser
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Entraîner les modèles
        results = {}
        
        # 1. Random Forest
        logger.info("🌲 Entraînement Random Forest...")
        rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        )
        rf.fit(X_train_scaled, y_train)
        rf_pred = rf.predict(X_test_scaled)
        rf_acc = accuracy_score(y_test, rf_pred)
        results['random_forest'] = {'accuracy': rf_acc}
        self.models['rf'] = rf
        
        # 2. Gradient Boosting
        logger.info("🚀 Entraînement Gradient Boosting...")
        gb = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        gb.fit(X_train_scaled, y_train)
        gb_pred = gb.predict(X_test_scaled)
        gb_acc = accuracy_score(y_test, gb_pred)
        results['gradient_boosting'] = {'accuracy': gb_acc}
        self.models['gb'] = gb
        
        # 3. Logistic Regression
        logger.info("📈 Entraînement Logistic Regression...")
        lr = LogisticRegression(max_iter=1000, random_state=42)
        lr.fit(X_train_scaled, y_train)
        lr_pred = lr.predict(X_test_scaled)
        lr_acc = accuracy_score(y_test, lr_pred)
        results['logistic_regression'] = {'accuracy': lr_acc}
        self.models['lr'] = lr
        
        # Moyenne ensemble
        ensemble_acc = (rf_acc + gb_acc + lr_acc) / 3
        results['ensemble'] = {'accuracy': ensemble_acc}
        
        self.is_trained = True
        
        # Sauvegarder les modèles
        self.save_models()
        
        logger.info(f"✅ Entraînement terminé!")
        logger.info(f"   RF: {rf_acc:.1%} | GB: {gb_acc:.1%} | LR: {lr_acc:.1%}")
        logger.info(f"   Ensemble: {ensemble_acc:.1%}")
        
        return {
            'success': True,
            'matches_used': len(X),
            'train_size': len(X_train),
            'test_size': len(X_test),
            'results': results,
            'best_model': max(results.items(), key=lambda x: x[1]['accuracy'])[0]
        }
    
    def predict_proba(self, home_team: str, away_team: str) -> Optional[float]:
        """
        Prédit la probabilité BTTS YES
        """
        if not self.is_trained or not HAS_ML:
            return None
        
        features = self.extract_features(home_team, away_team)
        if features is None:
            return None
        
        features_scaled = self.scaler.transform(features)
        
        # Moyenne pondérée des prédictions
        proba = 0.0
        weights = {'rf': 0.4, 'gb': 0.4, 'lr': 0.2}
        
        for name, model in self.models.items():
            if name in weights:
                p = model.predict_proba(features_scaled)[0][1]
                proba += p * weights[name]
        
        return proba
    
    def save_models(self):
        """Sauvegarde les modèles"""
        if not self.is_trained:
            return
        
        try:
            with open(f'{self.MODEL_PATH}/models.pkl', 'wb') as f:
                pickle.dump({
                    'models': self.models,
                    'scaler': self.scaler,
                    'trained_at': datetime.now().isoformat()
                }, f)
            logger.info(f"✅ Modèles sauvegardés dans {self.MODEL_PATH}")
        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")
    
    def load_models(self) -> bool:
        """Charge les modèles"""
        try:
            path = f'{self.MODEL_PATH}/models.pkl'
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    data = pickle.load(f)
                    self.models = data['models']
                    self.scaler = data['scaler']
                    self.is_trained = True
                    logger.info(f"✅ Modèles chargés (entraînés le {data['trained_at']})")
                    return True
        except Exception as e:
            logger.error(f"Erreur chargement: {e}")
        
        return False


def main():
    """Test du trainer"""
    print("=" * 60)
    print("🤖 TEST ML TRAINER BTTS")
    print("=" * 60)
    
    trainer = BTTSMLTrainer()
    
    # Entraîner sur 60 jours
    result = trainer.train(days=60)
    
    print(f"\nRésultat: {json.dumps(result, indent=2)}")
    
    if result['success']:
        # Test de prédiction
        proba = trainer.predict_proba('Liverpool', 'Manchester City')
        print(f"\nP(BTTS YES) Liverpool vs Man City: {proba:.1%}" if proba else "Prédiction échouée")


if __name__ == "__main__":
    main()
