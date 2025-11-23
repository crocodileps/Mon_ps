#!/usr/bin/env python3
"""
Récupération résultats depuis football-data.org (API officielle gratuite)
Token: 10 requêtes/minute = Largement suffisant
"""
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
API_TOKEN = "d40eee7eea3342179f16636ce9806fff"

DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Mapping ligues (codes officiels football-data.org)
LEAGUES = {
    'Premier League': 'PL',
    'Ligue 1': 'FL1',
    'Serie A': 'SA',
    'La Liga': 'PD',
    'Bundesliga': 'BL1'
}

def get_pending_matches():
    """Récupère les matchs analysés sans résultat"""
    try:
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
        """)
        
        matches = cursor.fetchall()
        conn.close()
        logger.info(f"📊 {len(matches)} matchs pending")
        return matches
        
    except Exception as e:
        logger.error(f"❌ Erreur DB: {e}")
        return []

def fetch_league_matches(league_code, date_from, date_to):
    """Récupère les matchs terminés d'une ligue"""
    url = f"https://api.football-data.org/v4/competitions/{league_code}/matches"
    
    headers = {
        "X-Auth-Token": API_TOKEN
    }
    
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
        "status": "FINISHED"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            logger.info(f"✅ {league_code}: {len(matches)} matchs terminés")
            return matches
        elif response.status_code == 429:
            logger.warning(f"⚠️ Rate limit atteint, pause 60s...")
            time.sleep(60)
            return []
        else:
            logger.warning(f"⚠️ {league_code}: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"❌ {league_code}: {e}")
        return []

def match_teams(api_match, pending_matches):
    """Trouve correspondance entre match API et match pending"""
    home = api_match['homeTeam']['name']
    away = api_match['awayTeam']['name']
    
    # Chercher correspondance exacte
    for pending in pending_matches:
        if pending['home_team'] == home and pending['away_team'] == away:
            return pending
    
    # Chercher correspondance approximative (ignorer casse, espaces)
    home_clean = home.lower().replace(' ', '')
    away_clean = away.lower().replace(' ', '')
    
    for pending in pending_matches:
        pending_home = pending['home_team'].lower().replace(' ', '')
        pending_away = pending['away_team'].lower().replace(' ', '')
        
        if pending_home == home_clean and pending_away == away_clean:
            return pending
    
    return None

def save_result_and_analyze(conn, api_match, pending_match):
    """Sauvegarde résultat et analyse prédictions"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    home_team = api_match['homeTeam']['name']
    away_team = api_match['awayTeam']['name']
    score = api_match['score']['fullTime']
    score_home = score['home']
    score_away = score['away']
    
    # Déterminer outcome
    if score_home > score_away:
        outcome = 'home'
    elif score_away > score_home:
        outcome = 'away'
    else:
        outcome = 'draw'
    
    try:
        # Sauvegarder résultat
        cursor.execute("""
            INSERT INTO match_results 
            (match_id, home_team, away_team, sport, league, score_home, score_away, outcome, is_finished, commence_time)
            VALUES (%s, %s, %s, 'soccer', %s, %s, %s, %s, TRUE, %s)
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
            home_team,
            away_team,
            api_match['competition']['name'],
            score_home,
            score_away,
            outcome,
            api_match['utcDate']
        ))
        
        result_id = cursor.fetchone()['id']
        
        # Analyser prédictions associées
        cursor.execute("""
            SELECT * FROM agent_predictions
            WHERE match_id = %s
            AND was_correct IS NULL
        """, (pending_match['match_id'],))
        
        predictions = cursor.fetchall()
        analyzed = 0
        
        for pred in predictions:
            was_correct = (pred['predicted_outcome'] == outcome)
            
            # Update prediction
            cursor.execute("""
                UPDATE agent_predictions
                SET was_correct = %s
                WHERE id = %s
            """, (was_correct, pred['id']))
            
            # Create feedback
            insights = []
            recommendations = []
            
            if was_correct:
                insights.append(f"✅ Prédiction correcte: {pred['predicted_outcome']}")
                if pred['confidence'] >= 70:
                    insights.append("🎯 Haute confiance justifiée")
            else:
                insights.append(f"❌ Prédiction incorrecte: {pred['predicted_outcome']} → {outcome}")
                recommendations.append(f"🔍 Analyser facteurs: Score réel {score_home}-{score_away}")
                
                if pred['confidence'] >= 70:
                    recommendations.append("⚠️ Réduire confiance sur matchs similaires")
            
            cursor.execute("""
                INSERT INTO agent_feedback
                (prediction_id, match_id, agent_name, predicted_outcome, actual_outcome, 
                 was_correct, confidence_at_prediction, insights, recommendations)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                pred['id'],
                pending_match['match_id'],
                pred['agent_name'],
                pred['predicted_outcome'],
                outcome,
                was_correct,
                pred['confidence'],
                insights,
                recommendations
            ))
            
            analyzed += 1
        
        conn.commit()
        
        logger.info(f"✅ {home_team} {score_home}-{score_away} {away_team} ({outcome}) | {analyzed} prédictions analysées")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde: {e}")
        conn.rollback()
        return False

def main():
    """Main function"""
    logger.info("🚀 Démarrage récupération résultats (football-data.org)...")
    
    # Récupérer matchs pending
    pending_matches = get_pending_matches()
    
    if not pending_matches:
        logger.info("✅ Aucun match à traiter")
        return
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Récupérer résultats des 3 derniers jours pour toutes les ligues
    date_to = datetime.now().strftime('%Y-%m-%d')
    date_from = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    
    logger.info(f"📅 Période: {date_from} → {date_to}")
    
    processed = 0
    
    for league_name, league_code in LEAGUES.items():
        logger.info(f"🔍 {league_name} ({league_code})...")
        
        matches = fetch_league_matches(league_code, date_from, date_to)
        
        for api_match in matches:
            # Chercher correspondance avec nos matchs pending
            pending = match_teams(api_match, pending_matches)
            
            if pending:
                if save_result_and_analyze(conn, api_match, pending):
                    processed += 1
        
        # Pause entre ligues (rate limit: 10 req/min)
        time.sleep(7)  # ~8-9 requêtes/min max
    
    conn.close()
    
    logger.info(f"✅ {processed} matchs traités avec succès")
    
    # Afficher statistiques learning
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT * FROM agent_learning_stats ORDER BY win_rate_pct DESC")
    stats = cursor.fetchall()
    
    if stats:
        logger.info("\n" + "="*60)
        logger.info("📊 STATISTIQUES LEARNING")
        logger.info("="*60)
        for stat in stats:
            logger.info(f"  {stat['agent_name']}: {stat['win_rate_pct']}% | {stat['correct_predictions']}/{stat['total_predictions']} correct")
        logger.info("="*60)
    
    conn.close()

if __name__ == "__main__":
    main()
