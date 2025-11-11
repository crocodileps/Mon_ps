"""
Agent A : Anomaly Detector
Détecte les cotes anormales et opportunités d'arbitrage
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import psycopg2
import logging

logger = logging.getLogger(__name__)


class AnomalyDetectorAgent:
    """
    Agent A : Détection d'anomalies dans les cotes
    
    Stratégie :
    - Identifie les cotes qui s'écartent significativement de la norme
    - Détecte les erreurs potentielles des bookmakers
    - Score basé sur l'isolation (plus isolé = plus anormal)
    """
    
    def __init__(self, db_config):
        self.db_config = db_config
        self.model = IsolationForest(
            contamination=0.1,  # 10% des cotes sont considérées comme anormales
            random_state=42
        )
        self.scaler = StandardScaler()
        self.name = "Anomaly Detector"
        
    def fetch_current_odds(self):
        """Récupère les cotes actuelles"""
        conn = psycopg2.connect(**self.db_config)
        query = """
            SELECT 
                match_id,
                sport,
                home_team,
                away_team,
                bookmaker,
                home_odds,
                away_odds,
                draw_odds,
                collected_at
            FROM odds_history
            WHERE collected_at >= NOW() - INTERVAL '1 hour'
            ORDER BY collected_at DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    
    def calculate_features(self, df):
        """
        Calcule les features pour détection d'anomalies
        """
        features = []
        
        for match_id in df['match_id'].unique():
            match_odds = df[df['match_id'] == match_id]
            
            # Features statistiques
            home_mean = match_odds['home_odds'].mean()
            home_std = match_odds['home_odds'].std()
            away_mean = match_odds['away_odds'].mean()
            away_std = match_odds['away_odds'].std()
            
            # Probabilités implicites
            match_odds['home_prob'] = 1 / match_odds['home_odds']
            match_odds['away_prob'] = 1 / match_odds['away_odds']
            match_odds['draw_prob'] = 1 / match_odds['draw_odds'].fillna(3.0)
            
            # Marge du bookmaker
            match_odds['total_prob'] = (
                match_odds['home_prob'] + 
                match_odds['away_prob'] + 
                match_odds['draw_prob']
            )
            match_odds['margin'] = match_odds['total_prob'] - 1.0
            
            # Écart par rapport à la moyenne
            match_odds['home_zscore'] = (
                (match_odds['home_odds'] - home_mean) / (home_std + 0.001)
            )
            match_odds['away_zscore'] = (
                (match_odds['away_odds'] - away_mean) / (away_std + 0.001)
            )
            
            features.append(match_odds)
        
        return pd.concat(features, ignore_index=True)
    
    def detect_anomalies(self):
        """
        Détecte les anomalies dans les cotes actuelles
        
        Returns:
            DataFrame avec scores d'anomalie
        """
        logger.info(f"[{self.name}] Début détection anomalies...")
        
        # Récupérer données
        df = self.fetch_current_odds()
        
        if len(df) == 0:
            logger.warning(f"[{self.name}] Aucune donnée disponible")
            return pd.DataFrame()
        
        # Calculer features
        df = self.calculate_features(df)
        
        # Préparer features pour ML
        feature_cols = [
            'home_odds', 'away_odds', 
            'home_prob', 'away_prob', 
            'margin', 'home_zscore', 'away_zscore'
        ]
        
        X = df[feature_cols].fillna(0)
        X_scaled = self.scaler.fit_transform(X)
        
        # Prédiction anomalies
        predictions = self.model.fit_predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        # Ajouter résultats
        df['is_anomaly'] = predictions == -1
        df['anomaly_score'] = -scores  # Plus haut = plus anormal
        
        # Filtrer les anomalies
        anomalies = df[df['is_anomaly']].copy()
        anomalies = anomalies.sort_values('anomaly_score', ascending=False)
        
        logger.info(f"[{self.name}] Détecté {len(anomalies)} anomalies sur {len(df)} cotes")
        
        return anomalies
    
    def generate_signals(self, top_n=10):
        """
        Génère des signaux de trading basés sur les anomalies
        
        Returns:
            List de signaux avec confiance
        """
        anomalies = self.detect_anomalies()
        
        if len(anomalies) == 0:
            return []
        
        signals = []
        
        for idx, row in anomalies.head(top_n).iterrows():
            # Déterminer la direction
            if row['home_zscore'] > 2:  # Cote home anormalement haute
                direction = 'BACK_HOME'
                reason = f"Cote home {row['home_odds']:.2f} anormalement haute (z={row['home_zscore']:.2f})"
            elif row['away_zscore'] > 2:  # Cote away anormalement haute
                direction = 'BACK_AWAY'
                reason = f"Cote away {row['away_odds']:.2f} anormalement haute (z={row['away_zscore']:.2f})"
            else:
                direction = 'REVIEW'
                reason = f"Anomalie détectée (score={row['anomaly_score']:.3f})"
            
            signal = {
                'agent': self.name,
                'match': f"{row['home_team']} vs {row['away_team']}",
                'sport': row['sport'],
                'bookmaker': row['bookmaker'],
                'direction': direction,
                'confidence': min(row['anomaly_score'] * 10, 100),  # Scale 0-100
                'odds': {
                    'home': row['home_odds'],
                    'away': row['away_odds'],
                    'draw': row['draw_odds']
                },
                'reason': reason,
                'timestamp': row['collected_at']
            }
            
            signals.append(signal)
        
        logger.info(f"[{self.name}] Généré {len(signals)} signaux")
        
        return signals
    
    def evaluate_performance(self, historical_signals, actual_results):
        """
        Évalue la performance de l'agent sur données historiques
        
        Returns:
            Dict avec métriques de performance
        """
        # TODO: Implémenter après avoir les résultats des matchs
        return {
            'agent': self.name,
            'total_signals': len(historical_signals),
            'roi': 0.0,
            'win_rate': 0.0,
            'avg_odds': 0.0
        }
