#!/usr/bin/env python3
"""
Script autonome pour récupérer résultats depuis API-Football
Alternative à n8n si problème
"""
import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
RAPIDAPI_KEY = "cac3fcc086msb2cc89f67315743ap1d5517jsn18b7640fa578"
RAPIDAPI_HOST = "api-football-v1.p.rapidapi.com"

DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

def get_pending_matches():
    """Récupère les matchs sans résultat"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT DISTINCT
            aa.match_id,
            aa.home_team,
            aa.away_team,
            aa.sport,
            aa.league,
            aa.analyzed_at
        FROM agent_analyses aa
        LEFT JOIN match_results mr ON aa.match_id = mr.match_id
        WHERE mr.id IS NULL
        AND aa.analyzed_at > NOW() - INTERVAL '7 days'
        ORDER BY aa.analyzed_at DESC
        LIMIT 20
    """)
    
    matches = cursor.fetchall()
    conn.close()
    return matches

def fetch_from_api_football(date):
    """Récupère résultats depuis API-Football pour une date"""
    url = f"https://{RAPIDAPI_HOST}/v3/fixtures"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }
    
    params = {
        "date": date,
        "status": "FT"  # Finished matches only
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data.get('response'):
            logger.info(f"✅ {len(data['response'])} matchs récupérés pour {date}")
            return data['response']
        else:
            logger.warning(f"⚠️ Aucun match pour {date}")
            return []
            
    except Exception as e:
        logger.error(f"❌ Erreur API Football: {e}")
        return []

def save_match_result(conn, match_data, pending_match):
    """Sauvegarde résultat + analyse prédictions"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Sauvegarder résultat
        cursor.execute("""
            INSERT INTO match_results 
            (match_id, home_team, away_team, sport, league, score_home, score_away, outcome, is_finished)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (match_id) 
            DO UPDATE SET
                score_home = EXCLUDED.score_home,
                score_away = EXCLUDED.score_away,
                outcome = EXCLUDED.outcome,
                is_finished = TRUE,
                last_updated = NOW()
            RETURNING id
        """, (
            pending_match['match_id'],
            match_data['teams']['home']['name'],
            match_data['teams']['away']['name'],
            'soccer',
            match_data['league']['name'],
            match_data['goals']['home'],
            match_data['goals']['away'],
            match_data['outcome']
        ))
        
        result_id = cursor.fetchone()['id']
        
        # Analyser prédictions
        cursor.execute("""
            SELECT * FROM agent_predictions
            WHERE match_id = %s
            AND was_correct IS NULL
        """, (pending_match['match_id'],))
        
        predictions = cursor.fetchall()
        
        for pred in predictions:
            was_correct = (pred['predicted_outcome'] == match_data['outcome'])
            
            # Update prediction
            cursor.execute("""
                UPDATE agent_predictions
                SET was_correct = %s
                WHERE id = %s
            """, (was_correct, pred['id']))
            
            # Create feedback
            insights = []
            if was_correct:
                insights.append(f"✅ Correct: {pred['predicted_outcome']}")
            else:
                insights.append(f"❌ Incorrect: {pred['predicted_outcome']} → {match_data['outcome']}")
            
            cursor.execute("""
                INSERT INTO agent_feedback
                (prediction_id, match_id, agent_name, predicted_outcome, actual_outcome, 
                 was_correct, confidence_at_prediction, insights)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                pred['id'],
                pending_match['match_id'],
                pred['agent_name'],
                pred['predicted_outcome'],
                match_data['outcome'],
                was_correct,
                pred['confidence'],
                insights
            ))
        
        conn.commit()
        logger.info(f"✅ {match_data['teams']['home']['name']} vs {match_data['teams']['away']['name']}: {match_data['goals']['home']}-{match_data['goals']['away']} ({match_data['outcome']})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde: {e}")
        conn.rollback()
        return False

def main():
    """Main function"""
    logger.info("🚀 Démarrage récupération résultats API-Football...")
    
    # Get pending matches
    pending = get_pending_matches()
    logger.info(f"📊 {len(pending)} matchs sans résultat")
    
    if not pending:
        logger.info("✅ Aucun match à traiter")
        return
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Récupérer résultats des 3 derniers jours
    processed = 0
    for days_ago in range(3):
        date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        logger.info(f"📅 Récupération {date}...")
        
        fixtures = fetch_from_api_football(date)
        
        for fixture in fixtures:
            # Chercher si on a analysé ce match
            home = fixture['teams']['home']['name']
            away = fixture['teams']['away']['name']
            
            matching = [m for m in pending if m['home_team'] == home and m['away_team'] == away]
            
            if matching and fixture['fixture']['status']['short'] == 'FT':
                # Déterminer outcome
                score_home = fixture['goals']['home']
                score_away = fixture['goals']['away']
                
                if score_home > score_away:
                    outcome = 'home'
                elif score_away > score_home:
                    outcome = 'away'
                else:
                    outcome = 'draw'
                
                fixture['outcome'] = outcome
                
                if save_match_result(conn, fixture, matching[0]):
                    processed += 1
        
        # Pause pour ne pas abuser de l'API
        time.sleep(2)
    
    conn.close()
    logger.info(f"✅ {processed} matchs traités")
    
    # Stats finales
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM agent_learning_stats")
    stats = cursor.fetchall()
    
    logger.info("\n�� STATS LEARNING:")
    for stat in stats:
        logger.info(f"  {stat['agent_name']}: {stat['win_rate_pct']}% ({stat['correct_predictions']}/{stat['total_predictions']})")
    
    conn.close()

if __name__ == "__main__":
    main()
