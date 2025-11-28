#!/usr/bin/env python3
"""
🎯 Collecte des scores via The Odds API
"""
import requests
import psycopg2
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger('ScoresCollector')

ODDS_API_KEY = os.getenv('ODDS_API_KEY', '0ded7830ebf698618017c92e51cfcffc')
ODDS_API_BASE = 'https://api.the-odds-api.com/v4'

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

SPORTS = [
    'soccer_uefa_europa_league',
    'soccer_uefa_europa_conference_league',
    'soccer_uefa_champions_league',
    'soccer_epl',
    'soccer_france_ligue_one',
    'soccer_germany_bundesliga',
    'soccer_italy_serie_a',
    'soccer_spain_la_liga',
]

def fetch_scores(sport, days_from=3):
    url = f"{ODDS_API_BASE}/sports/{sport}/scores/"
    params = {'apiKey': ODDS_API_KEY, 'daysFrom': days_from, 'dateFormat': 'iso'}
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        logger.warning(f"API {sport}: {response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Erreur {sport}: {e}")
        return []

def update_match_results(conn, matches, sport_key):
    cur = conn.cursor()
    updated = 0
    
    for match in matches:
        if not match.get('completed') or not match.get('scores'):
            continue
            
        match_id = match.get('id', '')
        home_team = match.get('home_team', '')
        away_team = match.get('away_team', '')
        scores = match.get('scores', [])
        
        home_score = away_score = None
        for s in scores:
            if s.get('name') == home_team:
                home_score = int(s.get('score', 0))
            elif s.get('name') == away_team:
                away_score = int(s.get('score', 0))
        
        if home_score is None or away_score is None:
            continue
        
        commence_time = match.get('commence_time', '')
        
        # Déterminer outcome
        if home_score > away_score:
            outcome = 'home'
        elif away_score > home_score:
            outcome = 'away'
        else:
            outcome = 'draw'
        
        # Upsert via match_id
        cur.execute("""
            INSERT INTO match_results (match_id, home_team, away_team, score_home, score_away, commence_time, sport, outcome, is_finished, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, NOW())
            ON CONFLICT (match_id) 
            DO UPDATE SET score_home = EXCLUDED.score_home, 
                          score_away = EXCLUDED.score_away,
                          outcome = EXCLUDED.outcome,
                          is_finished = true,
                          last_updated = NOW()
        """, (match_id, home_team, away_team, home_score, away_score, commence_time, sport_key, outcome))
        
        updated += 1
        logger.info(f"  ✅ {home_team} {home_score}-{away_score} {away_team}")
    
    conn.commit()
    cur.close()
    return updated

def main():
    logger.info("🚀 Collecte scores via The Odds API")
    
    conn = psycopg2.connect(**DB_CONFIG)
    total = 0
    
    for sport in SPORTS:
        logger.info(f"\n📊 {sport}")
        matches = fetch_scores(sport, days_from=3)
        completed = [m for m in matches if m.get('completed')]
        logger.info(f"  {len(completed)} matchs terminés")
        
        if completed:
            total += update_match_results(conn, completed, sport)
    
    conn.close()
    logger.info(f"\n✅ TOTAL: {total} résultats mis à jour")

if __name__ == "__main__":
    main()
