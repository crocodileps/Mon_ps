#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
UNDERSTAT ADVANCED SCRAPER - Big Chances & Shot Quality
═══════════════════════════════════════════════════════════════════════════════

Scrape detailed shot data from Understat to calculate:
- Big Chances (xG > 0.30)
- Shot quality (avg xG per shot)
- Inside/Outside box ratio
- Set piece vs Open play
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import psycopg2
import psycopg2.extras
import time
import random
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

BIG_CHANCE_THRESHOLD = 0.30  # xG > 0.30 = Big Chance

class UnderstatAdvancedScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
    def _smart_delay(self):
        time.sleep(random.uniform(1.5, 3))
    
    def get_match_shots(self, match_id):
        """Récupère les données de tirs détaillées pour un match"""
        url = f"https://understat.com/match/{match_id}"
        
        try:
            self._smart_delay()
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for script in soup.find_all('script'):
                script_text = str(script)
                if 'shotsData' in script_text:
                    match = re.search(r"var shotsData\s*=\s*JSON\.parse\('(.+?)'\)", script_text)
                    if match:
                        decoded = match.group(1).encode().decode('unicode_escape')
                        shots_data = json.loads(decoded)
                        return shots_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting shots for match {match_id}: {e}")
            return None
    
    def analyze_shots(self, shots_list):
        """Analyse une liste de tirs et retourne les métriques"""
        if not shots_list:
            return {
                'shots': 0, 'shots_on_target': 0,
                'big_chances': 0, 'big_chances_scored': 0, 'big_chances_missed': 0,
                'shots_inside_box': 0, 'shots_outside_box': 0,
                'set_piece_shots': 0, 'open_play_shots': 0,
                'total_xg': 0, 'shot_quality': 0
            }
        
        stats = {
            'shots': len(shots_list),
            'shots_on_target': 0,
            'big_chances': 0,
            'big_chances_scored': 0,
            'big_chances_missed': 0,
            'shots_inside_box': 0,
            'shots_outside_box': 0,
            'set_piece_shots': 0,
            'open_play_shots': 0,
            'total_xg': 0
        }
        
        for shot in shots_list:
            xg = float(shot.get('xG', 0))
            result = shot.get('result', '')
            situation = shot.get('situation', '')
            
            stats['total_xg'] += xg
            
            # Shot on target
            if result in ('Goal', 'SavedShot'):
                stats['shots_on_target'] += 1
            
            # Big Chance (xG > 0.30)
            if xg >= BIG_CHANCE_THRESHOLD:
                stats['big_chances'] += 1
                if result == 'Goal':
                    stats['big_chances_scored'] += 1
                else:
                    stats['big_chances_missed'] += 1
            
            # Position (inside/outside box based on xG and situation)
            # High xG shots are typically inside box
            if xg >= 0.10 or situation in ('Penalty', 'FromCorner'):
                stats['shots_inside_box'] += 1
            else:
                stats['shots_outside_box'] += 1
            
            # Situation
            if situation in ('SetPiece', 'FromCorner', 'Penalty', 'DirectFreekick'):
                stats['set_piece_shots'] += 1
            else:
                stats['open_play_shots'] += 1
        
        # Calculate shot quality
        stats['shot_quality'] = round(stats['total_xg'] / stats['shots'], 3) if stats['shots'] > 0 else 0
        
        return stats


def get_match_ids_from_db():
    """Récupère les match_ids depuis match_xg_stats"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT match_id, match_date, home_team, away_team 
        FROM match_xg_stats 
        WHERE match_id NOT IN (SELECT match_id FROM match_advanced_stats WHERE match_id IS NOT NULL)
        ORDER BY match_date DESC
        LIMIT 100
    """)
    
    matches = cur.fetchall()
    conn.close()
    return matches


def save_advanced_stats(match_info, home_stats, away_stats):
    """Sauvegarde les stats avancées"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    match_id, match_date, home_team, away_team = match_info
    
    # Calculate conversions
    home_bc_conv = round(home_stats['big_chances_scored'] / home_stats['big_chances'] * 100, 1) if home_stats['big_chances'] > 0 else 0
    away_bc_conv = round(away_stats['big_chances_scored'] / away_stats['big_chances'] * 100, 1) if away_stats['big_chances'] > 0 else 0
    
    total_bc = home_stats['big_chances'] + away_stats['big_chances']
    
    # Match intensity based on big chances
    if total_bc >= 8:
        intensity = 'crazy'
    elif total_bc >= 5:
        intensity = 'high'
    elif total_bc >= 3:
        intensity = 'medium'
    else:
        intensity = 'low'
    
    try:
        cur.execute("""
            INSERT INTO match_advanced_stats 
            (match_id, match_date, home_team, away_team,
             home_shots, home_shots_on_target, home_big_chances, home_big_chances_scored,
             home_big_chances_missed, home_shots_inside_box, home_shots_outside_box,
             home_set_piece_shots, home_open_play_shots,
             away_shots, away_shots_on_target, away_big_chances, away_big_chances_scored,
             away_big_chances_missed, away_shots_inside_box, away_shots_outside_box,
             away_set_piece_shots, away_open_play_shots,
             home_bc_conversion, away_bc_conversion, home_shot_quality, away_shot_quality,
             total_big_chances, match_intensity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (match_id) DO UPDATE SET
                home_big_chances = EXCLUDED.home_big_chances,
                away_big_chances = EXCLUDED.away_big_chances,
                scraped_at = NOW()
        """, (
            match_id, match_date, home_team, away_team,
            home_stats['shots'], home_stats['shots_on_target'], home_stats['big_chances'],
            home_stats['big_chances_scored'], home_stats['big_chances_missed'],
            home_stats['shots_inside_box'], home_stats['shots_outside_box'],
            home_stats['set_piece_shots'], home_stats['open_play_shots'],
            away_stats['shots'], away_stats['shots_on_target'], away_stats['big_chances'],
            away_stats['big_chances_scored'], away_stats['big_chances_missed'],
            away_stats['shots_inside_box'], away_stats['shots_outside_box'],
            away_stats['set_piece_shots'], away_stats['open_play_shots'],
            home_bc_conv, away_bc_conv, home_stats['shot_quality'], away_stats['shot_quality'],
            total_bc, intensity
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving stats: {e}")
        return False
    finally:
        conn.close()


def calculate_team_tendencies():
    """Calcule les tendances Big Chances par équipe"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Get all teams
    cur.execute("""
        SELECT DISTINCT home_team FROM match_advanced_stats
        UNION SELECT DISTINCT away_team FROM match_advanced_stats
    """)
    teams = [r[0] for r in cur.fetchall()]
    
    for team in teams:
        # Home stats
        cur.execute("""
            SELECT home_big_chances as bc, home_big_chances_scored as bc_scored,
                   home_big_chances_missed as bc_missed, home_shot_quality as sq,
                   home_shots_inside_box as inside, home_shots as total_shots,
                   home_set_piece_shots as sp, home_open_play_shots as op,
                   away_big_chances as bc_conceded, away_big_chances_scored as bc_conceded_scored
            FROM match_advanced_stats WHERE home_team = %s
        """, (team,))
        home_matches = cur.fetchall()
        
        # Away stats
        cur.execute("""
            SELECT away_big_chances as bc, away_big_chances_scored as bc_scored,
                   away_big_chances_missed as bc_missed, away_shot_quality as sq,
                   away_shots_inside_box as inside, away_shots as total_shots,
                   away_set_piece_shots as sp, away_open_play_shots as op,
                   home_big_chances as bc_conceded, home_big_chances_scored as bc_conceded_scored
            FROM match_advanced_stats WHERE away_team = %s
        """, (team,))
        away_matches = cur.fetchall()
        
        all_matches = list(home_matches) + list(away_matches)
        
        if len(all_matches) < 3:
            continue
        
        n = len(all_matches)
        
        # Calculate averages
        avg_bc = sum(m['bc'] or 0 for m in all_matches) / n
        avg_bc_conceded = sum(m['bc_conceded'] or 0 for m in all_matches) / n
        avg_bc_scored = sum(m['bc_scored'] or 0 for m in all_matches) / n
        avg_bc_missed = sum(m['bc_missed'] or 0 for m in all_matches) / n
        
        total_bc = sum(m['bc'] or 0 for m in all_matches)
        total_bc_scored = sum(m['bc_scored'] or 0 for m in all_matches)
        bc_conversion = round(total_bc_scored / total_bc * 100, 1) if total_bc > 0 else 0
        
        total_bc_conceded = sum(m['bc_conceded'] or 0 for m in all_matches)
        total_bc_conceded_scored = sum(m['bc_conceded_scored'] or 0 for m in all_matches)
        bc_conceded_conv = round(total_bc_conceded_scored / total_bc_conceded * 100, 1) if total_bc_conceded > 0 else 0
        
        # Shot quality
        avg_sq = sum(m['sq'] or 0 for m in all_matches) / n
        
        # Inside box rate
        total_inside = sum(m['inside'] or 0 for m in all_matches)
        total_shots = sum(m['total_shots'] or 0 for m in all_matches)
        inside_rate = round(total_inside / total_shots * 100, 1) if total_shots > 0 else 0
        
        # Set piece dependency
        total_sp = sum(m['sp'] or 0 for m in all_matches)
        sp_rate = round(total_sp / total_shots * 100, 1) if total_shots > 0 else 0
        
        # Luck factor (actual goals vs expected from BC)
        # Expected = BC * 0.40 (average BC conversion)
        expected_goals = total_bc * 0.40
        actual_goals = total_bc_scored
        luck_factor = round(actual_goals - expected_goals, 2)
        
        is_overperf = luck_factor > 1
        is_underperf = luck_factor < -1
        
        cur.execute("""
            INSERT INTO team_big_chances_tendencies
            (team_name, league, season, avg_bc_created, avg_bc_conceded, avg_bc_scored,
             avg_bc_missed, bc_conversion_rate, bc_conceded_conversion, avg_shot_quality,
             shots_inside_box_rate, set_piece_dependency, open_play_rate, bc_luck_factor,
             is_overperforming, is_underperforming, matches_analyzed, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (team_name, league, season) DO UPDATE SET
                avg_bc_created = EXCLUDED.avg_bc_created,
                bc_conversion_rate = EXCLUDED.bc_conversion_rate,
                bc_luck_factor = EXCLUDED.bc_luck_factor,
                is_overperforming = EXCLUDED.is_overperforming,
                is_underperforming = EXCLUDED.is_underperforming,
                matches_analyzed = EXCLUDED.matches_analyzed,
                updated_at = NOW()
        """, (
            team, 'Premier League', '2025-2026',
            round(avg_bc, 2), round(avg_bc_conceded, 2), round(avg_bc_scored, 2),
            round(avg_bc_missed, 2), bc_conversion, bc_conceded_conv, round(avg_sq, 3),
            inside_rate, sp_rate, round(100 - sp_rate, 1), luck_factor,
            is_overperf, is_underperf, n
        ))
    
    conn.commit()
    logger.info(f"Tendances Big Chances calculées pour {len(teams)} équipes")
    conn.close()


def main():
    print("═══════════════════════════════════════════════════════════════════")
    print("UNDERSTAT ADVANCED SCRAPER - Big Chances")
    print("═══════════════════════════════════════════════════════════════════")
    
    scraper = UnderstatAdvancedScraper()
    
    # Get matches to process
    matches = get_match_ids_from_db()
    logger.info(f"\n📊 {len(matches)} matchs à analyser")
    
    processed = 0
    for match_info in matches:
        match_id = match_info[0]
        
        shots_data = scraper.get_match_shots(match_id)
        
        if shots_data:
            home_stats = scraper.analyze_shots(shots_data.get('h', []))
            away_stats = scraper.analyze_shots(shots_data.get('a', []))
            
            if save_advanced_stats(match_info, home_stats, away_stats):
                processed += 1
                
                if processed % 10 == 0:
                    logger.info(f"   Processed {processed}/{len(matches)} matchs")
    
    logger.info(f"\n✅ {processed} matchs avec stats avancées sauvegardés")
    
    # Calculate tendencies
    logger.info("\n📈 Calcul des tendances Big Chances...")
    calculate_team_tendencies()
    
    # Display results
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    print("\n" + "="*70)
    print("TOP 5 CRÉATEURS DE BIG CHANCES")
    print("="*70)
    cur.execute("""
        SELECT team_name, avg_bc_created, bc_conversion_rate, matches_analyzed
        FROM team_big_chances_tendencies
        ORDER BY avg_bc_created DESC
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(f"  {r['team_name']}: {r['avg_bc_created']:.1f} BC/match, {r['bc_conversion_rate']:.0f}% conversion")
    
    print("\n" + "="*70)
    print("ÉQUIPES MALCHANCEUSES (sous-performent leurs BC)")
    print("="*70)
    cur.execute("""
        SELECT team_name, bc_luck_factor, avg_bc_missed, bc_conversion_rate
        FROM team_big_chances_tendencies
        WHERE bc_luck_factor < -0.5
        ORDER BY bc_luck_factor ASC
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(f"  {r['team_name']}: {r['bc_luck_factor']:+.1f} luck, {r['avg_bc_missed']:.1f} BC ratées/match")
    
    print("\n" + "="*70)
    print("ÉQUIPES CHANCEUSES (sur-performent leurs BC)")
    print("="*70)
    cur.execute("""
        SELECT team_name, bc_luck_factor, bc_conversion_rate
        FROM team_big_chances_tendencies
        WHERE bc_luck_factor > 0.5
        ORDER BY bc_luck_factor DESC
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(f"  {r['team_name']}: {r['bc_luck_factor']:+.1f} luck, {r['bc_conversion_rate']:.0f}% conversion")
    
    conn.close()
    print("\n✅ SCRAPING AVANCÉ TERMINÉ!")


if __name__ == "__main__":
    main()
