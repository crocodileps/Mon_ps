#!/usr/bin/env python3
"""
Version 2 avec fuzzy matching et logs détaillés
"""
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging
import time
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_TOKEN = "d40eee7eea3342179f16636ce9806fff"

DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

LEAGUES = {
    'Premier League': 'PL',
    'Ligue 1': 'FL1',
    'Serie A': 'SA',
    'La Liga': 'PD',
    'Bundesliga': 'BL1'
}

# Mapping noms communs (pour aider le matching)
TEAM_ALIASES = {
    'Paris Saint Germain': ['PSG', 'Paris SG'],
    'Manchester City': ['Man City'],
    'Manchester United': ['Man United', 'Man Utd'],
    'Tottenham Hotspur': ['Tottenham', 'Spurs'],
    'West Ham United': ['West Ham'],
    'Newcastle United': ['Newcastle'],
    'Brighton & Hove Albion': ['Brighton'],
    'Nottingham Forest': ["Nott'm Forest"],
    'Wolverhampton Wanderers': ['Wolves'],
}

def normalize_team_name(name):
    """Normalise nom d'équipe pour matching"""
    # Enlever espaces multiples, accents, casse
    normalized = name.lower().strip()
    normalized = normalized.replace('  ', ' ')
    
    # Enlever suffixes communs
    suffixes = [' fc', ' afc', ' united', ' city']
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()
    
    return normalized

def similarity_score(str1, str2):
    """Calcule similarité entre 2 strings"""
    return SequenceMatcher(None, normalize_team_name(str1), normalize_team_name(str2)).ratio()

def get_pending_matches():
    """Récupère matchs pending"""
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
    """Récupère matchs d'une ligue"""
    url = f"https://api.football-data.org/v4/competitions/{league_code}/matches"
    
    headers = {"X-Auth-Token": API_TOKEN}
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
            logger.info(f"✅ {league_code}: {len(matches)} matchs")
            return matches
        else:
            logger.warning(f"⚠️ {league_code}: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"❌ {league_code}: {e}")
        return []

def match_teams(api_match, pending_matches):
    """Trouve correspondance avec fuzzy matching"""
    api_home = api_match['homeTeam']['name']
    api_away = api_match['awayTeam']['name']
    
    best_match = None
    best_score = 0
    
    for pending in pending_matches:
        # Calculer similarité pour home et away
        home_sim = similarity_score(api_home, pending['home_team'])
        away_sim = similarity_score(api_away, pending['away_team'])
        
        # Score combiné
        combined_score = (home_sim + away_sim) / 2
        
        # Seuil de confiance : 0.7 (70% de similarité)
        if combined_score > 0.7 and combined_score > best_score:
            best_score = combined_score
            best_match = pending
    
    if best_match:
        logger.info(f"🎯 Match trouvé ({best_score:.0%}): {api_home} vs {api_away} → {best_match['home_team']} vs {best_match['away_team']}")
    else:
        logger.debug(f"⚠️ Pas de match: {api_home} vs {api_away}")
    
    return best_match

def save_result_and_analyze(conn, api_match, pending_match):
    """Sauvegarde résultat et analyse"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    home_team = api_match['homeTeam']['name']
    away_team = api_match['awayTeam']['name']
    score = api_match['score']['fullTime']
    score_home = score['home']
    score_away = score['away']
    
    if score_home > score_away:
        outcome = 'home'
    elif score_away > score_home:
        outcome = 'away'
    else:
        outcome = 'draw'
    
    try:
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
        
        # Analyser prédictions
        cursor.execute("""
            SELECT * FROM agent_predictions
            WHERE match_id = %s AND was_correct IS NULL
        """, (pending_match['match_id'],))
        
        predictions = cursor.fetchall()
        
        for pred in predictions:
            was_correct = (pred['predicted_outcome'] == outcome)
            
            cursor.execute("""
                UPDATE agent_predictions SET was_correct = %s WHERE id = %s
            """, (was_correct, pred['id']))
            
            insights = [f"{'✅ Correct' if was_correct else '❌ Incorrect'}: {pred['predicted_outcome']} → {outcome}"]
            
            cursor.execute("""
                INSERT INTO agent_feedback
                (prediction_id, match_id, agent_name, predicted_outcome, actual_outcome, 
                 was_correct, confidence_at_prediction, insights, recommendations)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (pred['id'], pending_match['match_id'], pred['agent_name'], 
                  pred['predicted_outcome'], outcome, was_correct, pred['confidence'], 
                  insights, []))
        
        conn.commit()
        logger.info(f"✅ {home_team} {score_home}-{score_away} {away_team} ({outcome})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        conn.rollback()
        return False

def main():
    logger.info("🚀 Démarrage (v2 - fuzzy matching)...")
    
    pending_matches = get_pending_matches()
    if not pending_matches:
        logger.info("✅ Aucun match pending")
        return
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    date_to = datetime.now().strftime('%Y-%m-%d')
    date_from = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    
    logger.info(f"📅 Période: {date_from} → {date_to}")
    
    processed = 0
    
    for league_name, league_code in LEAGUES.items():
        logger.info(f"🔍 {league_name}...")
        
        matches = fetch_league_matches(league_code, date_from, date_to)
        
        for api_match in matches:
            pending = match_teams(api_match, pending_matches)
            
            if pending:
                if save_result_and_analyze(conn, api_match, pending):
                    processed += 1
        
        time.sleep(7)
    
    conn.close()
    logger.info(f"✅ {processed} matchs traités")
    
    # Stats
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM agent_learning_stats ORDER BY win_rate_pct DESC")
    stats = cursor.fetchall()
    
    if stats:
        logger.info("\n" + "="*60)
        logger.info("📊 STATISTIQUES LEARNING")
        logger.info("="*60)
        for stat in stats:
            logger.info(f"{stat['agent_name']}: {stat['win_rate_pct']}% | {stat['correct_predictions']}/{stat['total_predictions']}")
        logger.info("="*60)
    
    conn.close()

if __name__ == "__main__":
    main()
