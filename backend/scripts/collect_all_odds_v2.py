#!/usr/bin/env python3
"""
Collecteur de cotes OPTIMISÉ V2 - Mon_PS
36 ligues, 3 marchés, régions eu+uk, Pinnacle prioritaire
"""
import requests
import psycopg2
from datetime import datetime
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

API_KEY = os.environ.get('ODDS_API_KEY', '')
BASE_URL = "https://api.the-odds-api.com/v4"

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'monps_postgres'),
    'port': int(os.environ.get('DB_PORT', 5432)),
    'database': os.environ.get('DB_NAME', 'monps_db'),
    'user': os.environ.get('DB_USER', 'monps_user'),
    'password': os.environ.get('DB_PASSWORD', 'monps_secure_password_2024')
}

# 25 LIGUES PRIORITAIRES (sur 36 disponibles)
SPORTS = [
    # TIER 1 - Top 5 Europe
    'soccer_epl', 'soccer_spain_la_liga', 'soccer_germany_bundesliga',
    'soccer_italy_serie_a', 'soccer_france_ligue_one',
    # TIER 2 - Coupes Europe
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league',
    'soccer_uefa_europa_conference_league',
    # TIER 3 - Europe secondaire
    'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga',
    'soccer_belgium_first_div', 'soccer_turkey_super_league',
    'soccer_austria_bundesliga', 'soccer_denmark_superliga',
    'soccer_greece_super_league', 'soccer_switzerland_superleague',
    'soccer_poland_ekstraklasa', 'soccer_spl',
    # TIER 4 - Divisions 2
    'soccer_efl_champ', 'soccer_germany_bundesliga2',
    'soccer_france_ligue_two', 'soccer_italy_serie_b',
    'soccer_spain_segunda_division',
    # TIER 5 - Monde
    'soccer_brazil_campeonato', 'soccer_usa_mls',
]

REGIONS = 'eu,uk'  # Plus de bookmakers
MARKETS = ['h2h', 'totals', 'spreads']

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_spreads_table(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS odds_spreads (
            id SERIAL PRIMARY KEY,
            match_id VARCHAR(255) NOT NULL,
            sport VARCHAR(100) NOT NULL,
            home_team VARCHAR(255) NOT NULL,
            away_team VARCHAR(255) NOT NULL,
            commence_time TIMESTAMP NOT NULL,
            bookmaker VARCHAR(100) NOT NULL,
            team VARCHAR(255),
            spread_point DECIMAL(5,2),
            spread_odds DECIMAL(10,2),
            collected_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_spreads_match ON odds_spreads(match_id);
    """)
    conn.commit()
    cur.close()
    logger.info("✅ Table odds_spreads vérifiée")

def collect_odds(conn, sport, market):
    cur = conn.cursor()
    count = 0
    try:
        response = requests.get(
            f"{BASE_URL}/sports/{sport}/odds",
            params={'apiKey': API_KEY, 'regions': REGIONS, 'markets': market, 'oddsFormat': 'decimal'},
            timeout=15
        )
        if response.status_code != 200:
            logger.warning(f"  {market}: Erreur {response.status_code}")
            return 0
        
        remaining = response.headers.get('x-requests-remaining', '?')
        
        for match in response.json():
            for bk in match.get('bookmakers', []):
                for mkt in bk.get('markets', []):
                    if mkt['key'] == market:
                        if market == 'h2h':
                            outcomes = {o['name']: o.get('price', 0) for o in mkt['outcomes']}
                            cur.execute("""
                                INSERT INTO odds_history (match_id, sport, home_team, away_team, 
                                    commence_time, bookmaker, home_odds, draw_odds, away_odds, collected_at)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                ON CONFLICT (match_id, bookmaker, collected_at) DO NOTHING
                            """, (match['id'], sport, match['home_team'], match['away_team'],
                                  match['commence_time'], bk['title'],
                                  outcomes.get(match['home_team'], 0),
                                  outcomes.get('Draw', 0),
                                  outcomes.get(match['away_team'], 0),
                                  datetime.now()))
                            count += 1
                        elif market == 'totals':
                            outcomes = {o['name']: o for o in mkt['outcomes']}
                            over = outcomes.get('Over', {})
                            under = outcomes.get('Under', {})
                            cur.execute("""
                                INSERT INTO odds_totals (match_id, sport, home_team, away_team,
                                    commence_time, bookmaker, line, over_odds, under_odds, collected_at)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                ON CONFLICT DO NOTHING
                            """, (match['id'], sport, match['home_team'], match['away_team'],
                                  match['commence_time'], bk['title'],
                                  over.get('point', 2.5), over.get('price', 0), under.get('price', 0),
                                  datetime.now()))
                            count += 1
                        elif market == 'spreads':
                            for o in mkt['outcomes']:
                                cur.execute("""
                                    INSERT INTO odds_spreads (match_id, sport, home_team, away_team,
                                        commence_time, bookmaker, team, spread_point, spread_odds, collected_at)
                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                    ON CONFLICT DO NOTHING
                                """, (match['id'], sport, match['home_team'], match['away_team'],
                                      match['commence_time'], bk['title'],
                                      o['name'], o.get('point', 0), o.get('price', 0),
                                      datetime.now()))
                                count += 1
        conn.commit()
        logger.info(f"  {market}: {count} lignes (remaining: {remaining})")
    except Exception as e:
        logger.error(f"  {market}: {e}")
        conn.rollback()
    cur.close()
    return count

def main():
    if not API_KEY:
        logger.error("❌ ODDS_API_KEY manquante!")
        sys.exit(1)
    
    logger.info(f"🚀 Collecte V2 - {len(SPORTS)} ligues × {len(MARKETS)} marchés")
    conn = get_db_connection()
    ensure_spreads_table(conn)
    
    totals = {m: 0 for m in MARKETS}
    for sport in SPORTS:
        logger.info(f"📊 {sport}")
        for market in MARKETS:
            totals[market] += collect_odds(conn, sport, market)
    
    conn.close()
    logger.info("=" * 50)
    logger.info("✅ COLLECTE V2 TERMINÉE")
    for m, c in totals.items():
        logger.info(f"   {m}: {c}")
    logger.info(f"   TOTAL: {sum(totals.values())}")

if __name__ == "__main__":
    main()
