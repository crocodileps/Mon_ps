#!/usr/bin/env python3
"""
Script pour récupérer les résultats réels des matchs et analyser les prédictions
"""
import os
import sys
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_KEY = os.getenv('ODDS_API_KEY', '8f7318bea033cf7da9e08bc6bb3d0c48')
DB_CONFIG = {
    "host": os.getenv('DB_HOST', 'monps_postgres'),
    "database": os.getenv('DB_NAME', 'monps_db'),
    "user": os.getenv('DB_USER', 'monps_user'),
    "password": os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

SPORTS = ['soccer_epl', 'soccer_france_ligue_one', 'soccer_italy_serie_a', 
          'soccer_spain_la_liga', 'soccer_germany_bundesliga']

def get_match_scores(sport):
    """Récupère les scores des matchs terminés depuis l'API"""
    url = f'https://api.the-odds-api.com/v4/sports/{sport}/scores/'
    params = {
        'apiKey': API_KEY,
        'daysFrom': 3,  # Matchs des 3 derniers jours
        'completed': 'true'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Erreur API pour {sport}: {e}")
        return []

def save_match_result(conn, match_data):
    """Sauvegarde le résultat d'un match dans la DB"""
    cursor = conn.cursor()
    
    # Extraire les données
    match_id = match_data.get('id')
    home_team = match_data.get('home_team')
    away_team = match_data.get('away_team')
    sport = match_data.get('sport_key')
    
    # Scores
    scores = match_data.get('scores', [])
    score_home = None
    score_away = None
    
    for score in scores:
        if score.get('name') == home_team:
            score_home = int(score.get('score', 0))
        elif score.get('name') == away_team:
            score_away = int(score.get('score', 0))
    
    # Déterminer outcome
    outcome = None
    if score_home is not None and score_away is not None:
        if score_home > score_away:
            outcome = 'home'
        elif score_away > score_home:
            outcome = 'away'
        else:
            outcome = 'draw'
    
    # Insérer ou update
    try:
        cursor.execute("""
            INSERT INTO match_results 
            (match_id, home_team, away_team, sport, score_home, score_away, outcome, is_finished)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (match_id) 
            DO UPDATE SET
                score_home = EXCLUDED.score_home,
                score_away = EXCLUDED.score_away,
                outcome = EXCLUDED.outcome,
                is_finished = TRUE,
                last_updated = NOW()
        """, (match_id, home_team, away_team, sport, score_home, score_away, outcome))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erreur sauvegarde match {match_id}: {e}")
        conn.rollback()
        return False

def analyze_prediction(conn, prediction, match_result):
    """Analyse une prédiction par rapport au résultat réel"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    predicted_outcome = prediction['predicted_outcome']
    actual_outcome = match_result['outcome']
    was_correct = (predicted_outcome == actual_outcome)
    
    # Préparer insights
    insights = []
    recommendations = []
    
    if was_correct:
        insights.append(f"✅ Prédiction correcte: {predicted_outcome}")
        if prediction['confidence'] >= 70:
            insights.append("🎯 Haute confiance justifiée")
    else:
        insights.append(f"❌ Prédiction incorrecte: {predicted_outcome} → {actual_outcome}")
        
        # Analyse de l'erreur
        if prediction['confidence'] >= 70:
            recommendations.append("⚠️ Réduire confiance sur ce type de match")
        
        # Type d'erreur
        if predicted_outcome == 'home' and actual_outcome == 'away':
            recommendations.append("🔍 Analyser facteur away advantage sous-estimé")
        elif predicted_outcome == 'draw' and actual_outcome != 'draw':
            recommendations.append("⚡ Draw surévalué, favoriser outcomes clairs")
    
    # Sauvegarder feedback
    try:
        cursor.execute("""
            INSERT INTO agent_feedback
            (prediction_id, match_id, agent_name, predicted_outcome, actual_outcome, 
             was_correct, confidence_at_prediction, insights, recommendations)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            prediction['id'],
            match_result['match_id'],
            prediction['agent_name'],
            predicted_outcome,
            actual_outcome,
            was_correct,
            prediction['confidence'],
            insights,
            recommendations
        ))
        
        # Update prediction
        cursor.execute("""
            UPDATE agent_predictions
            SET was_correct = %s
            WHERE id = %s
        """, (was_correct, prediction['id']))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erreur analyse prédiction {prediction['id']}: {e}")
        conn.rollback()
        return False

def main():
    """Fonction principale"""
    logger.info("🚀 Démarrage fetch résultats matchs...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    total_processed = 0
    total_saved = 0
    
    # Récupérer scores pour chaque sport
    for sport in SPORTS:
        logger.info(f"📊 Récupération {sport}...")
        matches = get_match_scores(sport)
        
        for match in matches:
            if match.get('completed'):
                if save_match_result(conn, match):
                    total_saved += 1
                total_processed += 1
    
    logger.info(f"✅ {total_saved}/{total_processed} matchs sauvegardés")
    
    # Analyser prédictions
    logger.info("🔍 Analyse des prédictions...")
    
    cursor.execute("""
        SELECT p.*, mr.outcome as actual_outcome
        FROM agent_predictions p
        JOIN match_results mr ON p.match_id = mr.match_id
        WHERE mr.is_finished = TRUE
        AND p.was_correct IS NULL
    """)
    
    predictions = cursor.fetchall()
    analyzed = 0
    
    for pred in predictions:
        match_result = {
            'match_id': pred['match_id'],
            'outcome': pred['actual_outcome']
        }
        if analyze_prediction(conn, pred, match_result):
            analyzed += 1
    
    logger.info(f"✅ {analyzed} prédictions analysées")
    
    # Stats finales
    cursor.execute("SELECT * FROM agent_learning_stats")
    stats = cursor.fetchall()
    
    logger.info("\n📊 STATISTIQUES LEARNING:")
    for stat in stats:
        logger.info(f"  {stat['agent_name']}: {stat['win_rate_pct']}% ({stat['correct_predictions']}/{stat['total_predictions']})")
    
    conn.close()
    logger.info("✅ Terminé!")

if __name__ == "__main__":
    main()
