#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
SMART TRANSFERMARKT SCRAPER V2 - Données Buteurs Réelles (Corrigé)
═══════════════════════════════════════════════════════════════════════════════
"""

import requests
from bs4 import BeautifulSoup
import psycopg2
import psycopg2.extras
import time
import random
import json
import os
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# Positions à ignorer pour le nom
POSITIONS = ['Goalkeeper', 'Defender', 'Midfielder', 'Forward', 'Centre-Forward', 
             'Left Winger', 'Right Winger', 'Central Midfield', 'Defensive Midfield',
             'Attacking Midfield', 'Right-Back', 'Left-Back', 'Centre-Back',
             'Second Striker', 'Left Midfield', 'Right Midfield']

TEAM_TM_MAPPING = {
    'Liverpool': {'tm_id': '31', 'tm_name': 'fc-liverpool'},
    'Arsenal': {'tm_id': '11', 'tm_name': 'fc-arsenal'},
    'Manchester City': {'tm_id': '281', 'tm_name': 'manchester-city'},
    'Chelsea': {'tm_id': '631', 'tm_name': 'fc-chelsea'},
    'Manchester United': {'tm_id': '985', 'tm_name': 'manchester-united'},
    'Tottenham': {'tm_id': '148', 'tm_name': 'tottenham-hotspur'},
    'Newcastle': {'tm_id': '762', 'tm_name': 'newcastle-united'},
    'Aston Villa': {'tm_id': '405', 'tm_name': 'aston-villa'},
    'Brighton': {'tm_id': '1237', 'tm_name': 'brighton-hove-albion'},
    'West Ham': {'tm_id': '379', 'tm_name': 'west-ham-united'},
    'Sunderland': {'tm_id': '289', 'tm_name': 'afc-sunderland'},
    'Brentford': {'tm_id': '1148', 'tm_name': 'fc-brentford'},
    'Fulham': {'tm_id': '931', 'tm_name': 'fc-fulham'},
    'Bournemouth': {'tm_id': '989', 'tm_name': 'afc-bournemouth'},
    'Crystal Palace': {'tm_id': '873', 'tm_name': 'crystal-palace'},
    'Everton': {'tm_id': '29', 'tm_name': 'fc-everton'},
    'Wolves': {'tm_id': '543', 'tm_name': 'wolverhampton-wanderers'},
    'Leicester': {'tm_id': '1003', 'tm_name': 'leicester-city'},
    'Nottingham Forest': {'tm_id': '703', 'tm_name': 'nottingham-forest'},
    'Ipswich': {'tm_id': '677', 'tm_name': 'ipswich-town'},
}

CACHE_DIR = '/home/Mon_ps/cache/transfermarkt'
CACHE_EXPIRY_HOURS = 12

class TransfermarktScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        os.makedirs(CACHE_DIR, exist_ok=True)
        
    def _get_cache_path(self, team_name, data_type):
        safe_name = team_name.lower().replace(' ', '_')
        return f"{CACHE_DIR}/{safe_name}_{data_type}.json"
    
    def _is_cache_valid(self, cache_path):
        if not os.path.exists(cache_path):
            return False
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
        return datetime.now() - mtime < timedelta(hours=CACHE_EXPIRY_HOURS)
    
    def _load_cache(self, cache_path):
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except:
            return None
    
    def _save_cache(self, cache_path, data):
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _smart_delay(self):
        time.sleep(random.uniform(2, 4))
    
    def _fetch_page(self, url):
        try:
            self._smart_delay()
            response = self.session.get(url, timeout=20)
            if response.status_code == 429:
                logger.warning("Rate limited! Waiting 60s...")
                time.sleep(60)
                return self._fetch_page(url)
            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code} for {url}")
                return None
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def get_team_injuries(self, team_name):
        """Récupère les blessures actuelles"""
        cache_path = self._get_cache_path(team_name, 'injuries')
        if self._is_cache_valid(cache_path):
            return self._load_cache(cache_path)
        
        if team_name not in TEAM_TM_MAPPING:
            return []
        
        tm_info = TEAM_TM_MAPPING[team_name]
        url = f"https://www.transfermarkt.com/{tm_info['tm_name']}/sperrenundverletzungen/verein/{tm_info['tm_id']}"
        
        logger.info(f"Scraping injuries for {team_name}...")
        html = self._fetch_page(url)
        if not html:
            return []
        
        injuries = []
        soup = BeautifulSoup(html, 'html.parser')
        injury_table = soup.find('table', class_='items')
        
        if injury_table:
            rows = injury_table.find_all('tr', class_=['odd', 'even'])
            for row in rows:
                try:
                    player_cell = row.find('td', class_='hauptlink')
                    if not player_cell:
                        continue
                    player_name = player_cell.get_text(strip=True)
                    
                    injury_cell = row.find('td', class_='zentriert')
                    injury_type = injury_cell.get_text(strip=True) if injury_cell else 'Unknown'
                    
                    injuries.append({
                        'player_name': player_name,
                        'injury_type': injury_type,
                        'scraped_at': datetime.now().isoformat()
                    })
                except:
                    continue
        
        self._save_cache(cache_path, injuries)
        logger.info(f"Found {len(injuries)} injuries for {team_name}")
        return injuries
    
    def get_team_scorers(self, team_name):
        """Récupère les buteurs avec stats - PARSING CORRIGÉ"""
        cache_path = self._get_cache_path(team_name, 'scorers_v2')
        if self._is_cache_valid(cache_path):
            return self._load_cache(cache_path)
        
        if team_name not in TEAM_TM_MAPPING:
            return []
        
        tm_info = TEAM_TM_MAPPING[team_name]
        url = f"https://www.transfermarkt.com/{tm_info['tm_name']}/leistungsdaten/verein/{tm_info['tm_id']}/plus/1"
        
        logger.info(f"Scraping scorers for {team_name}...")
        html = self._fetch_page(url)
        if not html:
            return []
        
        scorers = []
        soup = BeautifulSoup(html, 'html.parser')
        main_table = soup.find('table', class_='items')
        
        if main_table:
            tbody = main_table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr', class_=['odd', 'even'])
                
                for row in rows:
                    cells = row.find_all('td')
                    
                    # Extraire le nom (éviter les positions)
                    player_name = None
                    for cell in cells[:3]:
                        links = cell.find_all('a')
                        for link in links:
                            text = link.get_text(strip=True)
                            if text and len(text) > 3 and text not in POSITIONS:
                                player_name = text
                                break
                        if player_name:
                            break
                    
                    # Extraire les stats numériques
                    numeric_values = []
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        if text.isdigit():
                            numeric_values.append(int(text))
                        elif text == '-':
                            numeric_values.append(0)
                    
                    # Format: [#, age, in_squad, games, goals, assists, ...]
                    # Index 4 = goals, Index 5 = assists
                    if player_name and len(numeric_values) >= 6:
                        goals = numeric_values[4]
                        assists = numeric_values[5]
                        matches = numeric_values[3]
                        
                        if goals > 0 or assists > 0:
                            scorers.append({
                                'player_name': player_name,
                                'goals': goals,
                                'assists': assists,
                                'matches': matches,
                                'scraped_at': datetime.now().isoformat()
                            })
        
        scorers.sort(key=lambda x: (x['goals'], x['assists']), reverse=True)
        self._save_cache(cache_path, scorers)
        logger.info(f"Found {len(scorers)} scorers for {team_name}")
        return scorers


def update_database(scraper):
    """Met à jour scorer_intelligence avec les données scrapées"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    stats = {'injuries': 0, 'scorers': 0, 'hot_streaks': 0}
    
    for team_name in TEAM_TM_MAPPING.keys():
        logger.info(f"\n{'='*50}\nProcessing {team_name}\n{'='*50}")
        
        # 1. BLESSURES
        injuries = scraper.get_team_injuries(team_name)
        for injury in injuries:
            first_name = injury['player_name'].split()[0].lower()
            cur.execute("""
                UPDATE scorer_intelligence 
                SET is_injured = true
                WHERE LOWER(player_name) LIKE %s
                AND LOWER(current_team) LIKE %s
            """, (f"%{first_name}%", f"%{team_name.lower()}%"))
            stats['injuries'] += cur.rowcount
        
        # 2. BUTEURS - Mise à jour des stats réelles
        scorers = scraper.get_team_scorers(team_name)
        for scorer in scorers:
            first_name = scorer['player_name'].split()[0].lower()
            
            # Mettre à jour season_goals et assists depuis TM
            cur.execute("""
                UPDATE scorer_intelligence 
                SET season_goals = GREATEST(season_goals, %s),
                    season_assists = GREATEST(COALESCE(season_assists, 0), %s),
                    is_hot_streak = CASE WHEN %s >= 3 THEN true ELSE is_hot_streak END,
                    form_score = CASE WHEN %s > 0 THEN LEAST(100, 50 + %s * 10) ELSE form_score END
                WHERE LOWER(player_name) LIKE %s
                AND LOWER(current_team) LIKE %s
            """, (
                scorer['goals'], scorer['assists'],
                scorer['goals'],  # Hot streak si 3+ buts
                scorer['goals'], scorer['goals'],  # Form score boost
                f"%{first_name}%", f"%{team_name.lower()}%"
            ))
            stats['scorers'] += cur.rowcount
        
        # 3. KEY PLAYER = top scorer de l'équipe
        if scorers:
            top_scorer = scorers[0]['player_name'].split()[0].lower()
            cur.execute("""
                UPDATE scorer_intelligence 
                SET is_key_player = true
                WHERE LOWER(player_name) LIKE %s
                AND LOWER(current_team) LIKE %s
            """, (f"%{top_scorer}%", f"%{team_name.lower()}%"))
    
    conn.commit()
    
    # Résumé
    logger.info(f"\n{'='*60}\nRÉSUMÉ MISE À JOUR\n{'='*60}")
    logger.info(f"Blessures mises à jour: {stats['injuries']}")
    logger.info(f"Buteurs mis à jour: {stats['scorers']}")
    
    # Vérification
    cur.execute("""
        SELECT 
            COUNT(CASE WHEN is_injured = true THEN 1 END) as injured,
            COUNT(CASE WHEN is_hot_streak = true THEN 1 END) as hot,
            COUNT(CASE WHEN is_key_player = true THEN 1 END) as key_players
        FROM scorer_intelligence
    """)
    row = cur.fetchone()
    logger.info(f"Total blessés: {row['injured']}")
    logger.info(f"Total hot streaks: {row['hot']}")
    logger.info(f"Total key players: {row['key_players']}")
    
    # Exemple Liverpool
    logger.info("\n📊 Exemple Liverpool après update:")
    cur.execute("""
        SELECT player_name, season_goals, season_assists, is_injured, is_hot_streak, is_key_player, form_score
        FROM scorer_intelligence 
        WHERE LOWER(current_team) LIKE '%liverpool%'
        ORDER BY season_goals DESC
        LIMIT 5
    """)
    for row in cur.fetchall():
        flags = []
        if row['is_key_player']: flags.append('⭐')
        if row['is_hot_streak']: flags.append('🔥')
        if row['is_injured']: flags.append('🚑')
        logger.info(f"  {row['player_name']}: {row['season_goals']}G {row['season_assists'] or 0}A form={row['form_score']} {''.join(flags)}")
    
    conn.close()


def main():
    print("═══════════════════════════════════════════════════════════════════")
    print("TRANSFERMARKT SMART SCRAPER V2")
    print("═══════════════════════════════════════════════════════════════════")
    
    scraper = TransfermarktScraper()
    
    # Test Liverpool
    print("\n🔍 Test Liverpool...")
    injuries = scraper.get_team_injuries('Liverpool')
    print(f"   Blessés: {[i['player_name'] for i in injuries]}")
    
    scorers = scraper.get_team_scorers('Liverpool')
    print(f"   Top buteurs: {[(s['player_name'], f"{s['goals']}G {s['assists']}A") for s in scorers[:5]]}")
    
    # Mettre à jour la base
    print("\n📥 Mise à jour base de données...")
    update_database(scraper)
    
    print("\n✅ SCRAPING TERMINÉ!")


if __name__ == "__main__":
    main()
