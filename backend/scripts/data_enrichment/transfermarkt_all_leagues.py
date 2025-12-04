#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
TRANSFERMARKT ALL LEAGUES SCRAPER - Scorers & Injuries
═══════════════════════════════════════════════════════════════════════════════

Scrape buteurs et blessures pour:
- Premier League (Angleterre)
- La Liga (Espagne)
- Bundesliga (Allemagne)
- Serie A (Italie)
- Ligue 1 (France)
"""

import requests
from bs4 import BeautifulSoup
import psycopg2
import psycopg2.extras
import time
import random
import logging
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

CACHE_DIR = '/home/Mon_ps/cache/transfermarkt_all'
os.makedirs(CACHE_DIR, exist_ok=True)

# Mapping des équipes par ligue
LEAGUES_TEAMS = {
    'Premier League': {
        'Liverpool': {'tm_id': '31', 'tm_name': 'fc-liverpool'},
        'Arsenal': {'tm_id': '11', 'tm_name': 'fc-arsenal'},
        'Manchester City': {'tm_id': '281', 'tm_name': 'manchester-city'},
        'Chelsea': {'tm_id': '631', 'tm_name': 'fc-chelsea'},
        'Manchester United': {'tm_id': '985', 'tm_name': 'manchester-united'},
        'Tottenham': {'tm_id': '148', 'tm_name': 'tottenham-hotspur'},
        'Newcastle United': {'tm_id': '762', 'tm_name': 'newcastle-united'},
        'Aston Villa': {'tm_id': '405', 'tm_name': 'aston-villa'},
        'Brighton': {'tm_id': '1237', 'tm_name': 'brighton-amp-hove-albion'},
        'West Ham': {'tm_id': '379', 'tm_name': 'west-ham-united'},
        'Brentford': {'tm_id': '1148', 'tm_name': 'fc-brentford'},
        'Fulham': {'tm_id': '931', 'tm_name': 'fc-fulham'},
        'Bournemouth': {'tm_id': '989', 'tm_name': 'afc-bournemouth'},
        'Crystal Palace': {'tm_id': '873', 'tm_name': 'crystal-palace'},
        'Everton': {'tm_id': '29', 'tm_name': 'fc-everton'},
        'Wolverhampton Wanderers': {'tm_id': '543', 'tm_name': 'wolverhampton-wanderers'},
        'Leicester': {'tm_id': '1003', 'tm_name': 'leicester-city'},
        'Nottingham Forest': {'tm_id': '703', 'tm_name': 'nottingham-forest'},
        'Ipswich': {'tm_id': '677', 'tm_name': 'ipswich-town'},
        'Burnley': {'tm_id': '1132', 'tm_name': 'fc-burnley'},
    },
    'La Liga': {
        'Real Madrid': {'tm_id': '418', 'tm_name': 'real-madrid'},
        'Barcelona': {'tm_id': '131', 'tm_name': 'fc-barcelona'},
        'Atletico Madrid': {'tm_id': '13', 'tm_name': 'atletico-madrid'},
        'Sevilla': {'tm_id': '368', 'tm_name': 'fc-sevilla'},
        'Real Sociedad': {'tm_id': '681', 'tm_name': 'real-sociedad-san-sebastian'},
        'Real Betis': {'tm_id': '150', 'tm_name': 'real-betis-sevilla'},
        'Villarreal': {'tm_id': '1050', 'tm_name': 'villarreal-cf'},
        'Athletic Club': {'tm_id': '621', 'tm_name': 'athletic-bilbao'},
        'Valencia': {'tm_id': '1049', 'tm_name': 'fc-valencia'},
        'Girona': {'tm_id': '12321', 'tm_name': 'fc-girona'},
        'Celta Vigo': {'tm_id': '940', 'tm_name': 'celta-de-vigo'},
        'Osasuna': {'tm_id': '331', 'tm_name': 'ca-osasuna'},
        'Getafe': {'tm_id': '3709', 'tm_name': 'fc-getafe'},
        'Rayo Vallecano': {'tm_id': '367', 'tm_name': 'rayo-vallecano'},
        'Mallorca': {'tm_id': '237', 'tm_name': 'rcd-mallorca'},
        'Alaves': {'tm_id': '1108', 'tm_name': 'deportivo-alaves'},
        'Espanyol': {'tm_id': '714', 'tm_name': 'rcd-espanyol-barcelona'},
        'Valladolid': {'tm_id': '366', 'tm_name': 'real-valladolid'},
        'Las Palmas': {'tm_id': '472', 'tm_name': 'ud-las-palmas'},
        'Leganes': {'tm_id': '1244', 'tm_name': 'cd-leganes'},
    },
    'Bundesliga': {
        'Bayern Munich': {'tm_id': '27', 'tm_name': 'fc-bayern-munchen'},
        'Bayer Leverkusen': {'tm_id': '15', 'tm_name': 'bayer-04-leverkusen'},
        'Borussia Dortmund': {'tm_id': '16', 'tm_name': 'borussia-dortmund'},
        'RB Leipzig': {'tm_id': '23826', 'tm_name': 'rasenballsport-leipzig'},
        'Eintracht Frankfurt': {'tm_id': '24', 'tm_name': 'eintracht-frankfurt'},
        'VfB Stuttgart': {'tm_id': '79', 'tm_name': 'vfb-stuttgart'},
        'Freiburg': {'tm_id': '60', 'tm_name': 'sc-freiburg'},
        'Wolfsburg': {'tm_id': '82', 'tm_name': 'vfl-wolfsburg'},
        'Borussia M.Gladbach': {'tm_id': '18', 'tm_name': 'borussia-monchengladbach'},
        'Union Berlin': {'tm_id': '89', 'tm_name': '1-fc-union-berlin'},
        'Mainz 05': {'tm_id': '39', 'tm_name': '1-fsv-mainz-05'},
        'Werder Bremen': {'tm_id': '86', 'tm_name': 'sv-werder-bremen'},
        'Augsburg': {'tm_id': '167', 'tm_name': 'fc-augsburg'},
        'Hoffenheim': {'tm_id': '533', 'tm_name': 'tsg-1899-hoffenheim'},
        'FC Heidenheim': {'tm_id': '2036', 'tm_name': '1-fc-heidenheim-1846'},
        'St. Pauli': {'tm_id': '35', 'tm_name': 'fc-st-pauli'},
        'Holstein Kiel': {'tm_id': '522', 'tm_name': 'holstein-kiel'},
        'Bochum': {'tm_id': '80', 'tm_name': 'vfl-bochum'},
    },
    'Serie A': {
        'Inter': {'tm_id': '46', 'tm_name': 'inter-mailand'},
        'AC Milan': {'tm_id': '5', 'tm_name': 'ac-mailand'},
        'Juventus': {'tm_id': '506', 'tm_name': 'juventus-turin'},
        'Napoli': {'tm_id': '6195', 'tm_name': 'ssc-neapel'},
        'Roma': {'tm_id': '12', 'tm_name': 'as-rom'},
        'Lazio': {'tm_id': '398', 'tm_name': 'lazio-rom'},
        'Atalanta': {'tm_id': '800', 'tm_name': 'atalanta-bergamo'},
        'Fiorentina': {'tm_id': '430', 'tm_name': 'ac-florenz'},
        'Bologna': {'tm_id': '1025', 'tm_name': 'fc-bologna'},
        'Torino': {'tm_id': '416', 'tm_name': 'fc-turin'},
        'Udinese': {'tm_id': '410', 'tm_name': 'udinese-calcio'},
        'Genoa': {'tm_id': '252', 'tm_name': 'genua-cfc'},
        'Cagliari': {'tm_id': '1390', 'tm_name': 'cagliari-calcio'},
        'Parma': {'tm_id': '130', 'tm_name': 'fc-parma'},
        'Lecce': {'tm_id': '1005', 'tm_name': 'us-lecce'},
        'Verona': {'tm_id': '276', 'tm_name': 'hellas-verona'},
        'Como': {'tm_id': '1047', 'tm_name': 'como-1907'},
        'Empoli': {'tm_id': '749', 'tm_name': 'fc-empoli'},
        'Venezia': {'tm_id': '607', 'tm_name': 'fc-venedig'},
        'Monza': {'tm_id': '2919', 'tm_name': 'ac-monza'},
    },
    'Ligue 1': {
        'Paris Saint Germain': {'tm_id': '583', 'tm_name': 'fc-paris-saint-germain'},
        'Monaco': {'tm_id': '162', 'tm_name': 'as-monaco'},
        'Marseille': {'tm_id': '244', 'tm_name': 'olympique-marseille'},
        'Lyon': {'tm_id': '1041', 'tm_name': 'olympique-lyon'},
        'Lille': {'tm_id': '1082', 'tm_name': 'losc-lille'},
        'Nice': {'tm_id': '417', 'tm_name': 'ogc-nizza'},
        'Lens': {'tm_id': '826', 'tm_name': 'rc-lens'},
        'Rennes': {'tm_id': '273', 'tm_name': 'stade-rennes'},
        'Strasbourg': {'tm_id': '667', 'tm_name': 'rc-strasbourg-alsace'},
        'Toulouse': {'tm_id': '415', 'tm_name': 'fc-toulouse'},
        'Nantes': {'tm_id': '995', 'tm_name': 'fc-nantes'},
        'Brest': {'tm_id': '3911', 'tm_name': 'stade-brest-29'},
        'Reims': {'tm_id': '1421', 'tm_name': 'stade-reims'},
        'Montpellier': {'tm_id': '969', 'tm_name': 'montpellier-hsc'},
        'Le Havre': {'tm_id': '738', 'tm_name': 'le-havre-ac'},
        'Auxerre': {'tm_id': '290', 'tm_name': 'aj-auxerre'},
        'Angers': {'tm_id': '1420', 'tm_name': 'angers-sco'},
        'Saint-Etienne': {'tm_id': '618', 'tm_name': 'as-saint-etienne'},
    }
}


def get_team_scorers(tm_id, tm_name, team_name, league):
    """Récupère les buteurs d'une équipe"""
    url = f"https://www.transfermarkt.com/{tm_name}/leistungsdaten/verein/{tm_id}/plus/1"
    
    try:
        time.sleep(random.uniform(2, 4))
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='items')
        
        if not table:
            return []
        
        tbody = table.find('tbody')
        if not tbody:
            return []
        
        scorers = []
        rows = tbody.find_all('tr', class_=['odd', 'even'])
        
        for row in rows:
            try:
                # Nom du joueur
                name_cell = row.find('td', class_='hauptlink')
                if not name_cell:
                    continue
                player_name = name_cell.get_text(strip=True)
                
                # Récupérer toutes les valeurs numériques
                cells = row.find_all('td')
                numeric_values = []
                for cell in cells:
                    text = cell.get_text(strip=True)
                    text = text.replace("'", "").replace(",", "")
                    if text.isdigit():
                        numeric_values.append(int(text))
                
                # Skip si pas assez de données
                if len(numeric_values) < 6:
                    continue
                
                # Indices: [#, age, in_squad, games, goals, assists, ...]
                goals = numeric_values[4] if len(numeric_values) > 4 else 0
                assists = numeric_values[5] if len(numeric_values) > 5 else 0
                
                if goals > 0 or assists > 0:
                    scorers.append({
                        'name': player_name,
                        'team': team_name,
                        'league': league,
                        'goals': goals,
                        'assists': assists
                    })
                    
            except Exception as e:
                continue
        
        return scorers
        
    except Exception as e:
        logger.error(f"Error scraping {team_name}: {e}")
        return []


def get_team_injuries(tm_id, tm_name, team_name, league):
    """Récupère les blessés d'une équipe"""
    url = f"https://www.transfermarkt.com/{tm_name}/sperrenundverletzungen/verein/{tm_id}"
    
    try:
        time.sleep(random.uniform(1.5, 3))
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        injuries = []
        
        rows = soup.find_all('tr', class_=['odd', 'even'])
        
        for row in rows:
            try:
                name_cell = row.find('td', class_='hauptlink')
                if not name_cell:
                    continue
                    
                player_name = name_cell.get_text(strip=True)
                
                # Type de blessure
                injury_cell = row.find('td', class_='zentriert')
                injury_type = injury_cell.get_text(strip=True) if injury_cell else 'Unknown'
                
                injuries.append({
                    'name': player_name,
                    'team': team_name,
                    'league': league,
                    'injury_type': injury_type
                })
                
            except:
                continue
        
        return injuries
        
    except Exception as e:
        return []


def save_scorers_to_db(scorers):
    """Sauvegarde les buteurs dans la base"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    updated = 0
    for s in scorers:
        try:
            # Vérifier si le joueur existe
            cur.execute("""
                SELECT id FROM scorer_intelligence 
                WHERE LOWER(player_name) LIKE %s AND LOWER(current_team) LIKE %s
            """, (f"%{s['name'].lower().split()[0]}%", f"%{s['team'].lower()[:10]}%"))
            
            existing = cur.fetchone()
            
            if existing:
                # Update
                cur.execute("""
                    UPDATE scorer_intelligence 
                    SET season_goals = GREATEST(season_goals, %s),
                        season_assists = GREATEST(COALESCE(season_assists, 0), %s),
                        is_hot_streak = CASE WHEN %s >= 3 THEN true ELSE is_hot_streak END,
                        form_score = CASE WHEN %s > 0 THEN LEAST(100, 50 + %s * 10) ELSE form_score END
                    WHERE id = %s
                """, (s['goals'], s['assists'], s['goals'], s['goals'], s['goals'], existing[0]))
            else:
                # Insert
                cur.execute("""
                    INSERT INTO scorer_intelligence 
                    (player_name, current_team, league, season_goals, season_assists, 
                     is_hot_streak, form_score, is_key_player)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (s['name'], s['team'], s['league'], s['goals'], s['assists'],
                      s['goals'] >= 3, min(100, 50 + s['goals'] * 10), s['goals'] >= 5))
            
            updated += 1
        except Exception as e:
            pass
    
    conn.commit()
    conn.close()
    return updated


def save_injuries_to_db(injuries):
    """Marque les joueurs blessés"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    updated = 0
    for inj in injuries:
        try:
            cur.execute("""
                UPDATE scorer_intelligence 
                SET is_injured = true, injury_type = %s
                WHERE LOWER(player_name) LIKE %s AND LOWER(current_team) LIKE %s
            """, (inj['injury_type'], f"%{inj['name'].lower().split()[0]}%", 
                  f"%{inj['team'].lower()[:10]}%"))
            
            if cur.rowcount > 0:
                updated += 1
        except:
            pass
    
    conn.commit()
    conn.close()
    return updated


def main():
    print("═══════════════════════════════════════════════════════════════════")
    print("TRANSFERMARKT ALL LEAGUES SCRAPER")
    print("═══════════════════════════════════════════════════════════════════")
    
    all_scorers = []
    all_injuries = []
    
    for league, teams in LEAGUES_TEAMS.items():
        print(f"\n{'='*70}")
        print(f"🏆 {league}")
        print('='*70)
        
        league_scorers = []
        league_injuries = []
        
        for team_name, tm_info in teams.items():
            # Scorers
            scorers = get_team_scorers(tm_info['tm_id'], tm_info['tm_name'], team_name, league)
            if scorers:
                league_scorers.extend(scorers)
                logger.info(f"   ✅ {team_name}: {len(scorers)} buteurs")
            else:
                logger.info(f"   ⚠️ {team_name}: 0 buteurs")
            
            # Injuries (moins fréquent pour éviter rate limit)
            if random.random() < 0.5:  # 50% des équipes
                injuries = get_team_injuries(tm_info['tm_id'], tm_info['tm_name'], team_name, league)
                league_injuries.extend(injuries)
        
        all_scorers.extend(league_scorers)
        all_injuries.extend(league_injuries)
        
        logger.info(f"   📊 {league}: {len(league_scorers)} buteurs, {len(league_injuries)} blessés")
    
    # Save to DB
    print("\n" + "="*70)
    print("SAUVEGARDE EN BASE")
    print("="*70)
    
    scorers_saved = save_scorers_to_db(all_scorers)
    injuries_saved = save_injuries_to_db(all_injuries)
    
    print(f"\n✅ {scorers_saved} buteurs sauvegardés")
    print(f"✅ {injuries_saved} blessures marquées")
    
    # Summary
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    print("\n" + "="*70)
    print("TOP BUTEURS PAR LIGUE")
    print("="*70)
    
    for league in LEAGUES_TEAMS.keys():
        cur.execute("""
            SELECT player_name, current_team, season_goals
            FROM scorer_intelligence
            WHERE league = %s AND season_goals > 0
            ORDER BY season_goals DESC
            LIMIT 3
        """, (league,))
        results = cur.fetchall()
        
        if results:
            print(f"\n   {league}:")
            for r in results:
                print(f"      {r['player_name']} ({r['current_team']}): {r['season_goals']} buts")
    
    conn.close()
    print("\n✅ SCRAPING TRANSFERMARKT MULTI-LIGUES TERMINÉ!")


if __name__ == "__main__":
    main()
