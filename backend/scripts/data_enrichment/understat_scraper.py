#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
UNDERSTAT SCRAPER - xG Intelligence System
═══════════════════════════════════════════════════════════════════════════════

Scrape xG data from Understat for all Premier League teams.
Calculates performance indicators and betting tendencies.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import psycopg2
import psycopg2.extras
import time
import random
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# Teams to scrape (Understat naming)
UNDERSTAT_TEAMS = [
    'Liverpool', 'Manchester_City', 'Arsenal', 'Chelsea', 'Manchester_United',
    'Tottenham', 'Newcastle_United', 'Aston_Villa', 'Brighton', 'West_Ham',
    'Brentford', 'Fulham', 'Bournemouth', 'Crystal_Palace', 'Everton',
    'Wolverhampton_Wanderers', 'Leicester', 'Nottingham_Forest', 'Ipswich', 'Burnley'
]

SEASON = '2025'  # Understat uses year of season start

class UnderstatScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
    def _smart_delay(self):
        time.sleep(random.uniform(1.5, 3))
    
    def get_team_matches(self, team_name):
        """Récupère tous les matchs d'une équipe avec xG"""
        url = f"https://understat.com/team/{team_name}/{SEASON}"
        
        try:
            self._smart_delay()
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code} for {team_name}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for script in soup.find_all('script'):
                script_text = str(script)
                if 'datesData' in script_text:
                    match = re.search(r"var datesData\s*=\s*JSON\.parse\('(.+?)'\)", script_text)
                    if match:
                        encoded_data = match.group(1)
                        decoded_data = encoded_data.encode().decode('unicode_escape')
                        matches = json.loads(decoded_data)
                        
                        processed = []
                        for m in matches:
                            if not m.get('isResult'):
                                continue  # Skip future matches
                                
                            processed.append({
                                'match_id': m.get('id'),
                                'date': m.get('datetime', '')[:10],
                                'home_team': m.get('h', {}).get('title', ''),
                                'away_team': m.get('a', {}).get('title', ''),
                                'home_goals': int(m.get('goals', {}).get('h', 0)),
                                'away_goals': int(m.get('goals', {}).get('a', 0)),
                                'home_xg': float(m.get('xG', {}).get('h', 0) or 0),
                                'away_xg': float(m.get('xG', {}).get('a', 0) or 0),
                            })
                        
                        logger.info(f"{team_name}: {len(processed)} matchs trouvés")
                        return processed
            
            return []
            
        except Exception as e:
            logger.error(f"Error scraping {team_name}: {e}")
            return []


def calculate_match_indicators(m):
    """Calcule les indicateurs pour un match"""
    home_xg = m['home_xg']
    away_xg = m['away_xg']
    total_xg = home_xg + away_xg
    
    # Performance (goals - xG)
    home_perf = m['home_goals'] - home_xg
    away_perf = m['away_goals'] - away_xg
    
    # Match profile
    if total_xg < 1.5:
        profile = 'defensive'
    elif total_xg < 2.5:
        profile = 'balanced'
    elif total_xg < 4:
        profile = 'open'
    else:
        profile = 'crazy'
    
    # Betting indicators
    btts_expected = home_xg > 0.8 and away_xg > 0.8
    over25_expected = total_xg > 2.5
    
    return {
        'total_xg': total_xg,
        'home_performance': round(home_perf, 2),
        'away_performance': round(away_perf, 2),
        'match_profile': profile,
        'xg_diff': round(abs(home_xg - away_xg), 2),
        'btts_expected': btts_expected,
        'over25_expected': over25_expected,
    }


def save_matches_to_db(matches):
    """Sauvegarde les matchs dans la base"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    saved = 0
    for m in matches:
        indicators = calculate_match_indicators(m)
        
        try:
            cur.execute("""
                INSERT INTO match_xg_stats 
                (match_id, match_date, home_team, away_team, home_goals, away_goals,
                 home_xg, away_xg, total_xg, home_performance, away_performance,
                 match_profile, xg_diff, btts_expected, over25_expected, league, season)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id) DO UPDATE SET
                    home_xg = EXCLUDED.home_xg,
                    away_xg = EXCLUDED.away_xg,
                    total_xg = EXCLUDED.total_xg,
                    home_performance = EXCLUDED.home_performance,
                    away_performance = EXCLUDED.away_performance,
                    match_profile = EXCLUDED.match_profile,
                    scraped_at = NOW()
            """, (
                m['match_id'], m['date'], m['home_team'], m['away_team'],
                m['home_goals'], m['away_goals'], m['home_xg'], m['away_xg'],
                indicators['total_xg'], indicators['home_performance'],
                indicators['away_performance'], indicators['match_profile'],
                indicators['xg_diff'], indicators['btts_expected'],
                indicators['over25_expected'], 'Premier League', f'{SEASON}-{int(SEASON)+1}'
            ))
            saved += 1
        except Exception as e:
            logger.debug(f"Error saving match {m['match_id']}: {e}")
    
    conn.commit()
    conn.close()
    return saved


def calculate_team_tendencies():
    """Calcule les tendances xG par équipe"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Obtenir toutes les équipes uniques
    cur.execute("SELECT DISTINCT home_team FROM match_xg_stats UNION SELECT DISTINCT away_team FROM match_xg_stats")
    teams = [r[0] for r in cur.fetchall()]
    
    for team in teams:
        # Stats comme équipe à domicile
        cur.execute("""
            SELECT home_xg as xg_for, away_xg as xg_against, home_performance as perf,
                   total_xg, match_profile, btts_expected, over25_expected
            FROM match_xg_stats WHERE home_team = %s
        """, (team,))
        home_matches = cur.fetchall()
        
        # Stats comme équipe à l'extérieur
        cur.execute("""
            SELECT away_xg as xg_for, home_xg as xg_against, away_performance as perf,
                   total_xg, match_profile, btts_expected, over25_expected
            FROM match_xg_stats WHERE away_team = %s
        """, (team,))
        away_matches = cur.fetchall()
        
        all_matches = list(home_matches) + list(away_matches)
        
        if len(all_matches) < 3:
            continue
        
        # Calculer les moyennes
        avg_xg_for = sum(m['xg_for'] for m in all_matches) / len(all_matches)
        avg_xg_against = sum(m['xg_against'] for m in all_matches) / len(all_matches)
        avg_total = sum(m['total_xg'] for m in all_matches) / len(all_matches)
        avg_perf = sum(m['perf'] for m in all_matches) / len(all_matches)
        
        overperf_count = sum(1 for m in all_matches if m['perf'] > 0)
        underperf_count = sum(1 for m in all_matches if m['perf'] < 0)
        
        defensive_count = sum(1 for m in all_matches if m['match_profile'] == 'defensive')
        open_count = sum(1 for m in all_matches if m['match_profile'] in ('open', 'crazy'))
        
        btts_xg_count = sum(1 for m in all_matches if m['btts_expected'])
        over25_xg_count = sum(1 for m in all_matches if m['over25_expected'])
        
        n = len(all_matches)
        
        # Recent form (last 5)
        recent = all_matches[-5:] if len(all_matches) >= 5 else all_matches
        recent_xg_for = sum(m['xg_for'] for m in recent) / len(recent)
        recent_xg_against = sum(m['xg_against'] for m in recent) / len(recent)
        recent_perf = sum(m['perf'] for m in recent) / len(recent)
        
        # Sauvegarder
        cur.execute("""
            INSERT INTO team_xg_tendencies 
            (team_name, league, season, avg_xg_for, avg_xg_against, avg_total_xg,
             avg_performance, overperform_rate, underperform_rate, defensive_rate,
             open_rate, btts_xg_rate, over25_xg_rate, recent_xg_for, recent_xg_against,
             recent_performance, matches_analyzed, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (team_name, league, season) DO UPDATE SET
                avg_xg_for = EXCLUDED.avg_xg_for,
                avg_xg_against = EXCLUDED.avg_xg_against,
                avg_total_xg = EXCLUDED.avg_total_xg,
                avg_performance = EXCLUDED.avg_performance,
                overperform_rate = EXCLUDED.overperform_rate,
                underperform_rate = EXCLUDED.underperform_rate,
                defensive_rate = EXCLUDED.defensive_rate,
                open_rate = EXCLUDED.open_rate,
                btts_xg_rate = EXCLUDED.btts_xg_rate,
                over25_xg_rate = EXCLUDED.over25_xg_rate,
                recent_xg_for = EXCLUDED.recent_xg_for,
                recent_xg_against = EXCLUDED.recent_xg_against,
                recent_performance = EXCLUDED.recent_performance,
                matches_analyzed = EXCLUDED.matches_analyzed,
                updated_at = NOW()
        """, (
            team, 'Premier League', f'{SEASON}-{int(SEASON)+1}',
            round(avg_xg_for, 2), round(avg_xg_against, 2), round(avg_total, 2),
            round(avg_perf, 2), round(overperf_count/n*100, 1), round(underperf_count/n*100, 1),
            round(defensive_count/n*100, 1), round(open_count/n*100, 1),
            round(btts_xg_count/n*100, 1), round(over25_xg_count/n*100, 1),
            round(recent_xg_for, 2), round(recent_xg_against, 2), round(recent_perf, 2), n
        ))
    
    conn.commit()
    logger.info(f"Tendances calculées pour {len(teams)} équipes")
    conn.close()


def main():
    print("═══════════════════════════════════════════════════════════════════")
    print("UNDERSTAT xG SCRAPER")
    print("═══════════════════════════════════════════════════════════════════")
    
    scraper = UnderstatScraper()
    all_matches = []
    
    for team in UNDERSTAT_TEAMS:
        matches = scraper.get_team_matches(team)
        all_matches.extend(matches)
    
    # Dédupliquer (chaque match apparaît 2 fois)
    unique_matches = {}
    for m in all_matches:
        if m['match_id'] not in unique_matches:
            unique_matches[m['match_id']] = m
    
    logger.info(f"\n📊 {len(unique_matches)} matchs uniques à sauvegarder")
    
    # Sauvegarder
    saved = save_matches_to_db(list(unique_matches.values()))
    logger.info(f"✅ {saved} matchs sauvegardés dans match_xg_stats")
    
    # Calculer les tendances
    logger.info("\n📈 Calcul des tendances par équipe...")
    calculate_team_tendencies()
    
    # Afficher un résumé
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    print("\n" + "="*70)
    print("TOP 5 SURPERFORMEURS (goals > xG)")
    print("="*70)
    cur.execute("""
        SELECT team_name, avg_performance, overperform_rate, matches_analyzed
        FROM team_xg_tendencies 
        ORDER BY avg_performance DESC
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(f"  {r['team_name']}: +{r['avg_performance']:.2f} goals/match ({r['overperform_rate']:.0f}% matchs)")
    
    print("\n" + "="*70)
    print("TOP 5 ÉQUIPES MATCHS OUVERTS (>4 xG)")
    print("="*70)
    cur.execute("""
        SELECT team_name, open_rate, avg_total_xg, over25_xg_rate
        FROM team_xg_tendencies 
        ORDER BY open_rate DESC
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(f"  {r['team_name']}: {r['open_rate']:.0f}% matchs ouverts, Over2.5 xG: {r['over25_xg_rate']:.0f}%")
    
    print("\n" + "="*70)
    print("TOP 5 ÉQUIPES DÉFENSIVES (<1.5 xG)")
    print("="*70)
    cur.execute("""
        SELECT team_name, defensive_rate, avg_total_xg, btts_xg_rate
        FROM team_xg_tendencies 
        ORDER BY defensive_rate DESC
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(f"  {r['team_name']}: {r['defensive_rate']:.0f}% matchs défensifs, BTTS xG: {r['btts_xg_rate']:.0f}%")
    
    conn.close()
    print("\n✅ SCRAPING UNDERSTAT TERMINÉ!")


if __name__ == "__main__":
    main()
