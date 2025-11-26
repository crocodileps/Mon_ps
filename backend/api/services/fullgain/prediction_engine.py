"""
FULL GAIN 2.0 - Moteur de Prédiction Intelligent
Algorithme pondéré pour BTTS et Over/Under
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PredictionEngine:
    """
    Moteur de prédiction basé sur:
    - Stats équipes (global + domicile/extérieur)
    - Tendances récentes (5 derniers matchs)
    - Head-to-Head historique
    - Qualité des données
    """
    
    # Pondérations pour le calcul des scores
    WEIGHTS = {
        'btts': {
            'home_btts_global': 0.15,
            'away_btts_global': 0.15,
            'home_btts_home': 0.15,
            'away_btts_away': 0.15,
            'home_last5_btts': 0.10,
            'away_last5_btts': 0.10,
            'h2h_btts': 0.20,
        },
        'over25': {
            'home_over25_global': 0.15,
            'away_over25_global': 0.15,
            'home_over25_home': 0.15,
            'away_over25_away': 0.15,
            'home_last5_over25': 0.10,
            'away_last5_over25': 0.10,
            'h2h_over25': 0.20,
        }
    }
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', '127.0.0.1'),
            'port': 5432,
            'database': os.getenv('DB_NAME', 'monps_db'),
            'user': os.getenv('DB_USER', 'monps_user'),
            'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
        }
    
    def _get_conn(self):
        return psycopg2.connect(**self.db_config)
    
    def get_team_stats(self, team_name: str) -> Optional[Dict]:
        """Récupère les stats d'une équipe"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT * FROM team_statistics_live 
                WHERE team_name = %s
            """, (team_name,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close()
            conn.close()
    
    def get_h2h(self, team_a: str, team_b: str) -> Optional[Dict]:
        """Récupère le H2H entre deux équipes"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # H2H stocké avec team_a < team_b alphabétiquement
            t1, t2 = sorted([team_a, team_b])
            cur.execute("""
                SELECT * FROM team_head_to_head 
                WHERE team_a = %s AND team_b = %s
            """, (t1, t2))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close()
            conn.close()
    
    def calculate_btts_score(self, home_team: str, away_team: str) -> Dict:
        """
        Calcule le score BTTS (0-100)
        Plus le score est élevé, plus BTTS Yes est probable
        """
        home_stats = self.get_team_stats(home_team)
        away_stats = self.get_team_stats(away_team)
        h2h = self.get_h2h(home_team, away_team)
        
        if not home_stats or not away_stats:
            return {'score': None, 'confidence': 'low', 'error': 'Stats manquantes'}
        
        factors = {}
        weights = self.WEIGHTS['btts']
        
        # Stats globales
        factors['home_btts_global'] = float(home_stats.get('btts_pct') or 50)
        factors['away_btts_global'] = float(away_stats.get('btts_pct') or 50)
        
        # Stats domicile/extérieur spécifiques
        factors['home_btts_home'] = float(home_stats.get('home_btts_pct') or factors['home_btts_global'])
        factors['away_btts_away'] = float(away_stats.get('away_btts_pct') or factors['away_btts_global'])
        
        # Tendances récentes
        factors['home_last5_btts'] = float(home_stats.get('last5_btts_pct') or factors['home_btts_global'])
        factors['away_last5_btts'] = float(away_stats.get('last5_btts_pct') or factors['away_btts_global'])
        
        # H2H
        if h2h:
            factors['h2h_btts'] = float(h2h.get('btts_pct') or 50)
        else:
            # Sans H2H, redistribuer le poids
            factors['h2h_btts'] = (factors['home_btts_global'] + factors['away_btts_global']) / 2
        
        # Calcul du score pondéré
        score = sum(factors[k] * weights[k] for k in weights.keys())
        
        # Confidence basée sur la qualité des données
        home_dq = home_stats.get('data_quality_score', 50)
        away_dq = away_stats.get('data_quality_score', 50)
        avg_dq = (home_dq + away_dq) / 2
        
        if avg_dq >= 80:
            confidence = 'high'
        elif avg_dq >= 60:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        # Recommendation
        if score >= 65:
            recommendation = 'BTTS YES'
        elif score <= 35:
            recommendation = 'BTTS NO'
        else:
            recommendation = 'SKIP'
        
        return {
            'score': round(score, 1),
            'confidence': confidence,
            'recommendation': recommendation,
            'factors': factors,
            'home_stats': {
                'btts_global': factors['home_btts_global'],
                'btts_home': factors['home_btts_home'],
                'last5_btts': factors['home_last5_btts'],
                'form': home_stats.get('form'),
                'data_quality': home_dq
            },
            'away_stats': {
                'btts_global': factors['away_btts_global'],
                'btts_away': factors['away_btts_away'],
                'last5_btts': factors['away_last5_btts'],
                'form': away_stats.get('form'),
                'data_quality': away_dq
            },
            'h2h': {
                'btts_pct': h2h.get('btts_pct') if h2h else None,
                'total_matches': h2h.get('total_matches') if h2h else 0
            }
        }
    
    def calculate_over25_score(self, home_team: str, away_team: str) -> Dict:
        """
        Calcule le score Over 2.5 (0-100)
        """
        home_stats = self.get_team_stats(home_team)
        away_stats = self.get_team_stats(away_team)
        h2h = self.get_h2h(home_team, away_team)
        
        if not home_stats or not away_stats:
            return {'score': None, 'confidence': 'low', 'error': 'Stats manquantes'}
        
        factors = {}
        weights = self.WEIGHTS['over25']
        
        # Stats globales
        factors['home_over25_global'] = float(home_stats.get('over_25_pct') or 50)
        factors['away_over25_global'] = float(away_stats.get('over_25_pct') or 50)
        
        # Stats domicile/extérieur
        factors['home_over25_home'] = float(home_stats.get('home_over25_pct') or factors['home_over25_global'])
        factors['away_over25_away'] = float(away_stats.get('away_over25_pct') or factors['away_over25_global'])
        
        # Tendances
        factors['home_last5_over25'] = float(home_stats.get('last5_over25_pct') or factors['home_over25_global'])
        factors['away_last5_over25'] = float(away_stats.get('last5_over25_pct') or factors['away_over25_global'])
        
        # H2H
        if h2h:
            factors['h2h_over25'] = float(h2h.get('over_25_pct') or 50)
        else:
            factors['h2h_over25'] = (factors['home_over25_global'] + factors['away_over25_global']) / 2
        
        # Score
        score = sum(factors[k] * weights[k] for k in weights.keys())
        
        # Confidence
        home_dq = home_stats.get('data_quality_score', 50)
        away_dq = away_stats.get('data_quality_score', 50)
        avg_dq = (home_dq + away_dq) / 2
        
        confidence = 'high' if avg_dq >= 80 else 'medium' if avg_dq >= 60 else 'low'
        
        # Recommendation
        if score >= 65:
            recommendation = 'OVER 2.5'
        elif score <= 35:
            recommendation = 'UNDER 2.5'
        else:
            recommendation = 'SKIP'
        
        return {
            'score': round(score, 1),
            'confidence': confidence,
            'recommendation': recommendation,
            'factors': factors,
            'avg_goals_expected': round(
                float(home_stats.get('home_avg_scored') or 0) + 
                float(away_stats.get('away_avg_scored') or 0), 2
            )
        }
    
    def predict_match(self, home_team: str, away_team: str) -> Dict:
        """
        Prédiction complète pour un match
        """
        btts = self.calculate_btts_score(home_team, away_team)
        over25 = self.calculate_over25_score(home_team, away_team)
        
        # Value bet detection (score élevé = valeur potentielle)
        btts_value = btts.get('score', 0) >= 70 or btts.get('score', 100) <= 30
        over25_value = over25.get('score', 0) >= 70 or over25.get('score', 100) <= 30
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'btts': btts,
            'over25': over25,
            'value_bets': {
                'btts': btts_value,
                'over25': over25_value
            },
            'overall_confidence': btts.get('confidence', 'low'),
            'generated_at': datetime.now().isoformat()
        }
    
    def get_best_btts_predictions(self, limit: int = 20) -> List[Dict]:
        """
        Retourne les meilleures prédictions BTTS des matchs à venir
        """
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Matchs à venir avec cotes
            cur.execute("""
                SELECT DISTINCT home_team, away_team, commence_time
                FROM odds_history
                WHERE commence_time > NOW()
                ORDER BY commence_time
                LIMIT 50
            """)
            
            matches = cur.fetchall()
            predictions = []
            
            for match in matches:
                pred = self.predict_match(match['home_team'], match['away_team'])
                if pred['btts'].get('score'):
                    pred['commence_time'] = match['commence_time']
                    predictions.append(pred)
            
            # Trier par score BTTS
            predictions.sort(key=lambda x: x['btts'].get('score', 0), reverse=True)
            
            return predictions[:limit]
            
        finally:
            cur.close()
            conn.close()
