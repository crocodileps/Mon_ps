#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
UNDERSTAT GAME STATE SCRAPER - Comportement selon score
═══════════════════════════════════════════════════════════════════════════════

Scrape statisticsData from Understat to get:
- Game State (comportement à 0-0, en menant, en perdant)
- Timing (performance par période)
- Attack Speed (vulnérabilité aux contres)
- Set Piece efficiency
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import psycopg2
import psycopg2.extras
import time
import random
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

UNDERSTAT_TEAMS = [
    'Liverpool', 'Manchester_City', 'Arsenal', 'Chelsea', 'Manchester_United',
    'Tottenham', 'Newcastle_United', 'Aston_Villa', 'Brighton', 'West_Ham',
    'Brentford', 'Fulham', 'Bournemouth', 'Crystal_Palace', 'Everton',
    'Wolverhampton_Wanderers', 'Leicester', 'Nottingham_Forest', 'Ipswich', 'Burnley'
]

SEASON = '2025'

def scrape_team_statistics(team_name):
    """Scrape statisticsData pour une équipe"""
    url = f"https://understat.com/team/{team_name}/{SEASON}"
    
    try:
        time.sleep(random.uniform(1.5, 2.5))
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code} for {team_name}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup.find_all('script'):
            script_text = str(script)
            if 'statisticsData' in script_text:
                match = re.search(r"var statisticsData\s*=\s*JSON\.parse\('(.+?)'\)", script_text)
                if match:
                    decoded = match.group(1).encode().decode('unicode_escape')
                    return json.loads(decoded)
        
        return None
        
    except Exception as e:
        logger.error(f"Error scraping {team_name}: {e}")
        return None


def process_team_stats(team_name, stats):
    """Process statisticsData et extrait les métriques clés"""
    result = {'team_name': team_name.replace('_', ' ')}
    
    # Game State
    gs = stats.get('gameState', {})
    
    # À 0-0
    drawing = gs.get('Goal diff 0', {})
    result['gs_drawing_time'] = drawing.get('time', 0)
    result['gs_drawing_shots'] = drawing.get('shots', 0)
    result['gs_drawing_goals'] = drawing.get('goals', 0)
    result['gs_drawing_xg'] = float(drawing.get('xG', 0))
    result['gs_drawing_conceded_goals'] = drawing.get('against', {}).get('goals', 0)
    result['gs_drawing_conceded_xg'] = float(drawing.get('against', {}).get('xG', 0))
    
    # Mène de 1
    leading = gs.get('Goal diff +1', {})
    result['gs_leading_time'] = leading.get('time', 0)
    result['gs_leading_shots'] = leading.get('shots', 0)
    result['gs_leading_goals'] = leading.get('goals', 0)
    result['gs_leading_xg'] = float(leading.get('xG', 0))
    result['gs_leading_conceded_goals'] = leading.get('against', {}).get('goals', 0)
    result['gs_leading_conceded_xg'] = float(leading.get('against', {}).get('xG', 0))
    
    # Perd de 1
    trailing = gs.get('Goal diff -1', {})
    result['gs_trailing_time'] = trailing.get('time', 0)
    result['gs_trailing_shots'] = trailing.get('shots', 0)
    result['gs_trailing_goals'] = trailing.get('goals', 0)
    result['gs_trailing_xg'] = float(trailing.get('xG', 0))
    result['gs_trailing_conceded_goals'] = trailing.get('against', {}).get('goals', 0)
    result['gs_trailing_conceded_xg'] = float(trailing.get('against', {}).get('xG', 0))
    
    # Timing
    timing = stats.get('timing', {})
    result['timing_1_15_goals'] = timing.get('1-15', {}).get('goals', 0)
    result['timing_16_30_goals'] = timing.get('16-30', {}).get('goals', 0)
    result['timing_31_45_goals'] = timing.get('31-45', {}).get('goals', 0)
    result['timing_46_60_goals'] = timing.get('46-60', {}).get('goals', 0)
    result['timing_61_75_goals'] = timing.get('61-75', {}).get('goals', 0)
    result['timing_76_90_goals'] = timing.get('76-90', {}).get('goals', 0)
    
    # Attack Speed
    attack = stats.get('attackSpeed', {})
    fast = attack.get('Fast', {})
    result['fast_attack_goals'] = fast.get('goals', 0)
    result['fast_attack_xg'] = float(fast.get('xG', 0))
    result['fast_attack_conceded'] = fast.get('against', {}).get('goals', 0)
    result['fast_attack_conceded_xg'] = float(fast.get('against', {}).get('xG', 0))
    
    # Set Pieces
    situation = stats.get('situation', {})
    set_piece_goals = 0
    set_piece_xg = 0
    for sit_type in ['FromCorner', 'SetPiece', 'DirectFreekick']:
        sit = situation.get(sit_type, {})
        set_piece_goals += sit.get('goals', 0)
        set_piece_xg += float(sit.get('xG', 0))
    
    result['set_piece_goals'] = set_piece_goals
    result['set_piece_xg'] = round(set_piece_xg, 2)
    result['set_piece_luck'] = round(set_piece_goals - set_piece_xg, 2)
    
    # Calculate profiles
    # Killer = continue à créer du xG quand mène
    if result['gs_leading_time'] > 0:
        leading_xg_per_min = result['gs_leading_xg'] / result['gs_leading_time'] * 90
        drawing_xg_per_min = result['gs_drawing_xg'] / result['gs_drawing_time'] * 90 if result['gs_drawing_time'] > 0 else 0
        result['is_killer'] = leading_xg_per_min > drawing_xg_per_min * 0.7  # Maintient 70%+ de son xG
    else:
        result['is_killer'] = False
    
    # Manager = baisse drastiquement quand mène
    result['is_manager'] = not result['is_killer']
    
    # Fast vulnerable = concède beaucoup sur contre-attaques
    result['is_fast_vulnerable'] = result['fast_attack_conceded'] >= result['fast_attack_conceded_xg'] + 1
    
    # Slow starter = peu de buts 1-15
    total_goals = sum([
        result['timing_1_15_goals'], result['timing_16_30_goals'],
        result['timing_31_45_goals'], result['timing_46_60_goals'],
        result['timing_61_75_goals'], result['timing_76_90_goals']
    ])
    result['is_slow_starter'] = result['timing_1_15_goals'] < total_goals * 0.1 if total_goals > 0 else False
    
    # Strong finisher = beaucoup de buts 76-90
    result['is_strong_finisher'] = result['timing_76_90_goals'] > total_goals * 0.2 if total_goals > 0 else False
    
    return result


def save_to_db(data):
    """Sauvegarde dans la base"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO team_gamestate_stats 
            (team_name, league, season,
             gs_drawing_time, gs_drawing_shots, gs_drawing_goals, gs_drawing_xg,
             gs_drawing_conceded_goals, gs_drawing_conceded_xg,
             gs_leading_time, gs_leading_shots, gs_leading_goals, gs_leading_xg,
             gs_leading_conceded_goals, gs_leading_conceded_xg,
             gs_trailing_time, gs_trailing_shots, gs_trailing_goals, gs_trailing_xg,
             gs_trailing_conceded_goals, gs_trailing_conceded_xg,
             timing_1_15_goals, timing_16_30_goals, timing_31_45_goals,
             timing_46_60_goals, timing_61_75_goals, timing_76_90_goals,
             fast_attack_goals, fast_attack_xg, fast_attack_conceded, fast_attack_conceded_xg,
             set_piece_goals, set_piece_xg, set_piece_luck,
             is_killer, is_manager, is_fast_vulnerable, is_slow_starter, is_strong_finisher,
             updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (team_name, league, season) DO UPDATE SET
                gs_drawing_goals = EXCLUDED.gs_drawing_goals,
                gs_leading_goals = EXCLUDED.gs_leading_goals,
                gs_trailing_goals = EXCLUDED.gs_trailing_goals,
                is_killer = EXCLUDED.is_killer,
                is_fast_vulnerable = EXCLUDED.is_fast_vulnerable,
                set_piece_luck = EXCLUDED.set_piece_luck,
                updated_at = NOW()
        """, (
            data['team_name'], 'Premier League', f'{SEASON}-{int(SEASON)+1}',
            data['gs_drawing_time'], data['gs_drawing_shots'], data['gs_drawing_goals'], data['gs_drawing_xg'],
            data['gs_drawing_conceded_goals'], data['gs_drawing_conceded_xg'],
            data['gs_leading_time'], data['gs_leading_shots'], data['gs_leading_goals'], data['gs_leading_xg'],
            data['gs_leading_conceded_goals'], data['gs_leading_conceded_xg'],
            data['gs_trailing_time'], data['gs_trailing_shots'], data['gs_trailing_goals'], data['gs_trailing_xg'],
            data['gs_trailing_conceded_goals'], data['gs_trailing_conceded_xg'],
            data['timing_1_15_goals'], data['timing_16_30_goals'], data['timing_31_45_goals'],
            data['timing_46_60_goals'], data['timing_61_75_goals'], data['timing_76_90_goals'],
            data['fast_attack_goals'], data['fast_attack_xg'], data['fast_attack_conceded'], data['fast_attack_conceded_xg'],
            data['set_piece_goals'], data['set_piece_xg'], data['set_piece_luck'],
            data['is_killer'], data['is_manager'], data['is_fast_vulnerable'],
            data['is_slow_starter'], data['is_strong_finisher']
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving {data['team_name']}: {e}")
        return False
    finally:
        conn.close()


def main():
    print("═══════════════════════════════════════════════════════════════════")
    print("UNDERSTAT GAME STATE SCRAPER")
    print("═══════════════════════════════════════════════════════════════════")
    
    processed = 0
    killers = []
    managers = []
    fast_vulnerable = []
    
    for team in UNDERSTAT_TEAMS:
        stats = scrape_team_statistics(team)
        
        if stats:
            data = process_team_stats(team, stats)
            if save_to_db(data):
                processed += 1
                logger.info(f"✅ {data['team_name']}")
                
                if data['is_killer']:
                    killers.append(data['team_name'])
                else:
                    managers.append(data['team_name'])
                    
                if data['is_fast_vulnerable']:
                    fast_vulnerable.append(data['team_name'])
    
    # Display results
    print("\n" + "="*70)
    print(f"✅ {processed} équipes analysées")
    print("="*70)
    
    print("\n🔪 KILLERS (continuent d'attaquer quand ils mènent):")
    for t in killers:
        print(f"   - {t}")
    
    print("\n🛡️ MANAGERS (gèrent le score quand ils mènent):")
    for t in managers:
        print(f"   - {t}")
    
    print("\n⚡ VULNÉRABLES AUX CONTRES:")
    for t in fast_vulnerable:
        print(f"   - {t}")
    
    # Query for more insights
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    print("\n" + "="*70)
    print("SET PIECE MALCHANCEUX (rebond attendu)")
    print("="*70)
    cur.execute("""
        SELECT team_name, set_piece_goals, set_piece_xg, set_piece_luck
        FROM team_gamestate_stats
        WHERE set_piece_luck < -1
        ORDER BY set_piece_luck ASC
        LIMIT 5
    """)
    for r in cur.fetchall():
        print(f"   {r['team_name']}: {r['set_piece_goals']} buts vs {r['set_piece_xg']:.1f} xG ({r['set_piece_luck']:+.1f})")
    
    print("\n" + "="*70)
    print("SLOW STARTERS (éviter 1er but avant 15min)")
    print("="*70)
    cur.execute("""
        SELECT team_name, timing_1_15_goals, is_slow_starter
        FROM team_gamestate_stats
        WHERE is_slow_starter = true
    """)
    for r in cur.fetchall():
        print(f"   {r['team_name']}: {r['timing_1_15_goals']} buts (1-15 min)")
    
    conn.close()
    print("\n✅ GAME STATE SCRAPING TERMINÉ!")


if __name__ == "__main__":
    main()
