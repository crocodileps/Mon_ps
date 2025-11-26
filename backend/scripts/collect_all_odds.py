#!/usr/bin/env python3
"""
�� Collecteur de cotes complet - Version 2.0
Collecte: h2h (1X2), totals (2.5), alternate_totals (1.5, 3.5), btts
Priorité: Pinnacle > Tous bookmakers
"""
import requests
import psycopg2
from datetime import datetime
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
API_KEY = os.environ.get('ODDS_API_KEY', '')
BASE_URL = "https://api.the-odds-api.com/v4"

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'monps_postgres'),
    'port': int(os.environ.get('DB_PORT', 5432)),
    'database': os.environ.get('DB_NAME', 'monps_db'),
    'user': os.environ.get('DB_USER', 'monps_user'),
    'password': os.environ.get('DB_PASSWORD', 'monps_secure_password_2024')
}

# Ligues à collecter
SPORTS = [
    'soccer_uefa_champs_league',
    'soccer_uefa_europa_league',
    'soccer_germany_bundesliga',
    'soccer_epl',
    'soccer_spain_la_liga',
    'soccer_france_ligue_one',
    'soccer_italy_serie_a',
    'soccer_netherlands_eredivisie',
    'soccer_portugal_primeira_liga',
    'soccer_belgium_first_div',
    'soccer_turkey_super_league',
]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_btts_table(conn):
    """Créer la table odds_btts si elle n'existe pas"""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS odds_btts (
            id SERIAL PRIMARY KEY,
            match_id VARCHAR(255) NOT NULL,
            sport VARCHAR(100) NOT NULL,
            home_team VARCHAR(255) NOT NULL,
            away_team VARCHAR(255) NOT NULL,
            commence_time TIMESTAMP NOT NULL,
            bookmaker VARCHAR(100) NOT NULL,
            btts_yes_odds DECIMAL(10,2),
            btts_no_odds DECIMAL(10,2),
            collected_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(match_id, bookmaker, collected_at)
        );
        CREATE INDEX IF NOT EXISTS idx_btts_match_id ON odds_btts(match_id);
    """)
    conn.commit()
    cur.close()
    logger.info("✅ Table odds_btts vérifiée")

def collect_h2h(conn, sport: str) -> int:
    """Collecter les cotes 1X2"""
    cur = conn.cursor()
    count = 0
    
    try:
        response = requests.get(
            f"{BASE_URL}/sports/{sport}/odds",
            params={'apiKey': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'},
            timeout=15
        )
        if response.status_code != 200:
            logger.warning(f"  h2h: Erreur {response.status_code}")
            return 0
        
        for match in response.json():
            for bk in match.get('bookmakers', []):
                for market in bk.get('markets', []):
                    if market['key'] == 'h2h':
                        outcomes = {o['name']: o.get('price', 0) for o in market['outcomes']}
                        cur.execute("""
                            INSERT INTO odds_history 
                            (match_id, sport, home_team, away_team, commence_time, bookmaker, home_odds, draw_odds, away_odds, collected_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (match_id, bookmaker, collected_at) DO NOTHING
                        """, (
                            match['id'], sport, match['home_team'], match['away_team'],
                            match['commence_time'], bk['title'],
                            outcomes.get(match['home_team'], 0),
                            outcomes.get('Draw', 0),
                            outcomes.get(match['away_team'], 0),
                            datetime.now()
                        ))
                        count += 1
        conn.commit()
        remaining = response.headers.get('x-requests-remaining', '?')
        logger.info(f"  h2h: {count} lignes (remaining: {remaining})")
    except Exception as e:
        logger.error(f"  h2h: {e}")
        conn.rollback()
    
    cur.close()
    return count

def collect_totals(conn, sport: str) -> int:
    """Collecter les cotes Over/Under (toutes lignes)"""
    cur = conn.cursor()
    count = 0
    
    try:
        # Collecter totals standard + alternate
        for market_type in ['totals', 'alternate_totals']:
            response = requests.get(
                f"{BASE_URL}/sports/{sport}/odds",
                params={'apiKey': API_KEY, 'regions': 'eu', 'markets': market_type, 'oddsFormat': 'decimal'},
                timeout=15
            )
            if response.status_code != 200:
                continue
            
            for match in response.json():
                for bk in match.get('bookmakers', []):
                    for market in bk.get('markets', []):
                        if 'totals' in market['key']:
                            outcomes = {o['name']: o for o in market['outcomes']}
                            over = outcomes.get('Over', {})
                            under = outcomes.get('Under', {})
                            line = over.get('point', 2.5)
                            
                            cur.execute("""
                                INSERT INTO odds_totals 
                                (match_id, sport, home_team, away_team, commence_time, bookmaker, line, over_odds, under_odds, collected_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (
                                match['id'], sport, match['home_team'], match['away_team'],
                                match['commence_time'], bk['title'], line,
                                over.get('price', 0), under.get('price', 0), datetime.now()
                            ))
                            count += 1
            conn.commit()
            remaining = response.headers.get('x-requests-remaining', '?')
            logger.info(f"  {market_type}: +{count} (remaining: {remaining})")
    except Exception as e:
        logger.error(f"  totals: {e}")
        conn.rollback()
    
    cur.close()
    return count

def collect_btts(conn, sport: str) -> int:
    """Collecter les cotes BTTS (Both Teams To Score)"""
    cur = conn.cursor()
    count = 0
    
    try:
        response = requests.get(
            f"{BASE_URL}/sports/{sport}/odds",
            params={'apiKey': API_KEY, 'regions': 'eu', 'markets': 'btts', 'oddsFormat': 'decimal'},
            timeout=15
        )
        if response.status_code != 200:
            logger.warning(f"  btts: Erreur {response.status_code}")
            return 0
        
        for match in response.json():
            for bk in match.get('bookmakers', []):
                for market in bk.get('markets', []):
                    if market['key'] == 'btts':
                        outcomes = {o['name']: o.get('price', 0) for o in market['outcomes']}
                        cur.execute("""
                            INSERT INTO odds_btts 
                            (match_id, sport, home_team, away_team, commence_time, bookmaker, btts_yes_odds, btts_no_odds, collected_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (match_id, bookmaker, collected_at) DO NOTHING
                        """, (
                            match['id'], sport, match['home_team'], match['away_team'],
                            match['commence_time'], bk['title'],
                            outcomes.get('Yes', 0), outcomes.get('No', 0), datetime.now()
                        ))
                        count += 1
        conn.commit()
        remaining = response.headers.get('x-requests-remaining', '?')
        logger.info(f"  btts: {count} lignes (remaining: {remaining})")
    except Exception as e:
        logger.error(f"  btts: {e}")
        conn.rollback()
    
    cur.close()
    return count

def main():
    if not API_KEY:
        logger.error("❌ ODDS_API_KEY non définie!")
        sys.exit(1)
    
    logger.info("🚀 Collecte des cotes - Démarrage")
    
    conn = get_db_connection()
    ensure_btts_table(conn)
    
    total_h2h = 0
    total_totals = 0
    total_btts = 0
    
    for sport in SPORTS:
        logger.info(f"📊 {sport}")
        total_h2h += collect_h2h(conn, sport)
        total_totals += collect_totals(conn, sport)
        total_btts += collect_btts(conn, sport)
    
    conn.close()
    
    logger.info("=" * 50)
    logger.info(f"✅ COLLECTE TERMINÉE")
    logger.info(f"   1X2 (h2h):    {total_h2h} lignes")
    logger.info(f"   Over/Under:   {total_totals} lignes")
    logger.info(f"   BTTS:         {total_btts} lignes")
    logger.info(f"   TOTAL:        {total_h2h + total_totals + total_btts} lignes")

if __name__ == "__main__":
    main()
