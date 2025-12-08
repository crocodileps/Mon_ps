#!/usr/bin/env python3
"""
Scraper Football-Data.co.uk pour Phase 2-5 - VERSION CORRIGÉE
"""

import requests
import pandas as pd
from io import StringIO
import psycopg2
from datetime import datetime
import time

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

LEAGUES = {
    'E0': ('Premier League', 'Premier League', 'england'),
    'E1': ('Championship', 'Championship', 'england'),
    'D1': ('Bundesliga', 'Bundesliga', 'germany'),
    'D2': ('2. Bundesliga', '2. Bundesliga', 'germany'),
    'I1': ('Serie A', 'Serie A', 'italy'),
    'I2': ('Serie B', 'Serie B', 'italy'),
    'SP1': ('La Liga', 'La Liga', 'spain'),
    'SP2': ('La Liga 2', 'La Liga 2', 'spain'),
    'F1': ('Ligue 1', 'Ligue 1', 'france'),
    'F2': ('Ligue 2', 'Ligue 2', 'france'),
}

TEAM_MAPPING = {
    'Man United': 'Manchester United',
    'Man City': 'Manchester City',
    'Newcastle': 'Newcastle United',
    'Wolves': 'Wolverhampton Wanderers',
    "Nott'm Forest": 'Nottingham Forest',
    'Spurs': 'Tottenham',
    'Tottenham': 'Tottenham',
    'Sheffield Utd': 'Sheffield United',
    'West Brom': 'West Bromwich Albion',
    'Leverkusen': 'Bayer Leverkusen',
    'Dortmund': 'Borussia Dortmund',
    "M'gladbach": 'Borussia M.Gladbach',
    'Ein Frankfurt': 'Eintracht Frankfurt',
    'RB Leipzig': 'RasenBallsport Leipzig',
    'FC Koln': 'FC Cologne',
    'Heidenheim': 'FC Heidenheim',
    'St Pauli': 'St. Pauli',
    'Parma': 'Parma Calcio 1913',
    'Ath Madrid': 'Atletico Madrid',
    'Ath Bilbao': 'Athletic Club',
    'Betis': 'Real Betis',
    'Sociedad': 'Real Sociedad',
    'Celta': 'Celta Vigo',
    'Vallecano': 'Rayo Vallecano',
    'Espanol': 'Espanyol',
    'Paris SG': 'Paris Saint Germain',
    'St Etienne': 'Saint-Etienne',
}

def normalize_team(name):
    return TEAM_MAPPING.get(name, name)

def parse_date(date_str):
    for fmt in ['%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d']:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    return None

def fetch_league(code, season='2526'):
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and len(r.text) > 100:
            text = r.text.replace('\ufeff', '')
            return pd.read_csv(StringIO(text))
    except Exception as e:
        print(f"Erreur fetch: {e}")
    return None

def safe_int(val):
    try:
        return int(val) if pd.notna(val) else None
    except:
        return None

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║  📥 SCRAPER FOOTBALL-DATA.CO.UK V2 - Corners, Cartons, Fautes                ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    conn = psycopg2.connect(**DB_CONFIG)
    total = 0
    
    for code, (fd_name, our_name, country) in LEAGUES.items():
        print(f"   🏟️ {our_name} ({code})... ", end='', flush=True)
        
        df = fetch_league(code, '2526')
        if df is None or len(df) == 0:
            print("❌ Non disponible")
            continue
        
        inserted = 0
        errors = 0
        
        for _, row in df.iterrows():
            match_date = parse_date(str(row.get('Date', '')))
            if not match_date:
                continue
            
            home = normalize_team(str(row.get('HomeTeam', '')))
            away = normalize_team(str(row.get('AwayTeam', '')))
            
            if not home or not away:
                continue
            
            # Match ID plus court et unique
            match_id = f"{match_date}_{home[:15]}_{away[:15]}".replace(' ', '_').lower()
            
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO match_stats_extended (
                        match_id, match_date, home_team, away_team, league, season,
                        home_goals, away_goals, ht_home_goals, ht_away_goals,
                        corners_home, corners_away,
                        yellow_cards_home, yellow_cards_away,
                        red_cards_home, red_cards_away,
                        fouls_home, fouls_away, source
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (match_id) DO UPDATE SET
                        corners_home = EXCLUDED.corners_home,
                        corners_away = EXCLUDED.corners_away,
                        yellow_cards_home = EXCLUDED.yellow_cards_home,
                        yellow_cards_away = EXCLUDED.yellow_cards_away,
                        updated_at = NOW()
                """, (
                    match_id, match_date, home, away, our_name, '2025-2026',
                    safe_int(row.get('FTHG')), safe_int(row.get('FTAG')),
                    safe_int(row.get('HTHG')), safe_int(row.get('HTAG')),
                    safe_int(row.get('HC')), safe_int(row.get('AC')),
                    safe_int(row.get('HY')), safe_int(row.get('AY')),
                    safe_int(row.get('HR')), safe_int(row.get('AR')),
                    safe_int(row.get('HF')), safe_int(row.get('AF')),
                    'football-data.co.uk'
                ))
                conn.commit()
                inserted += 1
            except Exception as e:
                conn.rollback()
                errors += 1
            finally:
                cur.close()
        
        print(f"✅ {len(df)} matchs, {inserted} insérés" + (f", {errors} erreurs" if errors else ""))
        total += inserted
        time.sleep(0.3)
    
    # Stats finales
    cur = conn.cursor()
    cur.execute("""
        SELECT league, COUNT(*) as n,
               ROUND(AVG(corners_home + corners_away)::numeric, 1) as corners,
               ROUND(AVG(yellow_cards_home + yellow_cards_away)::numeric, 1) as yellows
        FROM match_stats_extended WHERE season = '2025-2026'
        GROUP BY league ORDER BY n DESC
    """)
    
    print(f"\n{'='*60}")
    print(f"✅ TOTAL: {total} matchs insérés\n")
    print(f"{'Ligue':<20} {'Matchs':<8} {'Corners':<10} {'Jaunes'}")
    print("-"*50)
    for r in cur.fetchall():
        print(f"{r[0]:<20} {r[1]:<8} {r[2] or '-':<10} {r[3] or '-'}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
