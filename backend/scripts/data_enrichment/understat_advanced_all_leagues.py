#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
UNDERSTAT ADVANCED SCRAPER - ALL LEAGUES
Big Chances + Shot Quality pour toutes les ligues européennes
═══════════════════════════════════════════════════════════════════════════════
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

BIG_CHANCE_THRESHOLD = 0.30
SEASON = '2025'

LEAGUES = {
    'EPL': 'Premier League',
    'La_Liga': 'La Liga',
    'Bundesliga': 'Bundesliga',
    'Serie_A': 'Serie A',
    'Ligue_1': 'Ligue 1'
}


def get_match_ids_to_process():
    """Récupère les matchs sans stats avancées"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT m.match_id, m.match_date, m.home_team, m.away_team, m.league
        FROM match_xg_stats m
        WHERE m.match_id NOT IN (
            SELECT match_id FROM match_advanced_stats WHERE match_id IS NOT NULL
        )
        ORDER BY m.match_date DESC
    """)
    
    matches = cur.fetchall()
    conn.close()
    return matches


def get_match_shots(match_id):
    """Récupère les données de tirs détaillées"""
    url = f"https://understat.com/match/{match_id}"
    
    try:
        time.sleep(random.uniform(1, 2))
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup.find_all('script'):
            script_text = str(script)
            if 'shotsData' in script_text:
                match = re.search(r"var shotsData\s*=\s*JSON\.parse\('(.+?)'\)", script_text)
                if match:
                    decoded = match.group(1).encode().decode('unicode_escape')
                    return json.loads(decoded)
        
        return None
        
    except Exception as e:
        return None


def analyze_shots(shots_list):
    """Analyse les tirs et calcule les métriques"""
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
        
        if result in ('Goal', 'SavedShot'):
            stats['shots_on_target'] += 1
        
        if xg >= BIG_CHANCE_THRESHOLD:
            stats['big_chances'] += 1
            if result == 'Goal':
                stats['big_chances_scored'] += 1
            else:
                stats['big_chances_missed'] += 1
        
        if xg >= 0.10 or situation in ('Penalty', 'FromCorner'):
            stats['shots_inside_box'] += 1
        else:
            stats['shots_outside_box'] += 1
        
        if situation in ('SetPiece', 'FromCorner', 'Penalty', 'DirectFreekick'):
            stats['set_piece_shots'] += 1
        else:
            stats['open_play_shots'] += 1
    
    stats['shot_quality'] = round(stats['total_xg'] / stats['shots'], 3) if stats['shots'] > 0 else 0
    
    return stats


def save_advanced_stats(match_info, home_stats, away_stats):
    """Sauvegarde les stats avancées"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    match_id, match_date, home_team, away_team, league = match_info
    
    home_bc_conv = round(home_stats['big_chances_scored'] / home_stats['big_chances'] * 100, 1) if home_stats['big_chances'] > 0 else 0
    away_bc_conv = round(away_stats['big_chances_scored'] / away_stats['big_chances'] * 100, 1) if away_stats['big_chances'] > 0 else 0
    
    total_bc = home_stats['big_chances'] + away_stats['big_chances']
    
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
            ON CONFLICT (match_id) DO NOTHING
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
        return False
    finally:
        conn.close()


def calculate_all_tendencies():
    """Calcule les tendances Big Chances pour TOUTES les équipes"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Get all unique teams with their leagues
    cur.execute("""
        SELECT DISTINCT home_team as team, 
               (SELECT league FROM match_xg_stats WHERE home_team = mas.home_team LIMIT 1) as league
        FROM match_advanced_stats mas
        UNION
        SELECT DISTINCT away_team as team,
               (SELECT league FROM match_xg_stats WHERE away_team = mas.away_team LIMIT 1) as league
        FROM match_advanced_stats mas
    """)
    teams = cur.fetchall()
    
    updated = 0
    for team_row in teams:
        team = team_row['team']
        league = team_row['league'] or 'Unknown'
        
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
        
        avg_sq = sum(m['sq'] or 0 for m in all_matches) / n
        
        total_inside = sum(m['inside'] or 0 for m in all_matches)
        total_shots = sum(m['total_shots'] or 0 for m in all_matches)
        inside_rate = round(total_inside / total_shots * 100, 1) if total_shots > 0 else 0
        
        total_sp = sum(m['sp'] or 0 for m in all_matches)
        sp_rate = round(total_sp / total_shots * 100, 1) if total_shots > 0 else 0
        
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
            team, league, f'{SEASON}-{int(SEASON)+1}',
            round(avg_bc, 2), round(avg_bc_conceded, 2), round(avg_bc_scored, 2),
            round(avg_bc_missed, 2), bc_conversion, bc_conceded_conv, round(avg_sq, 3),
            inside_rate, sp_rate, round(100 - sp_rate, 1), luck_factor,
            is_overperf, is_underperf, n
        ))
        updated += 1
    
    conn.commit()
    conn.close()
    return updated


def calculate_all_xg_tendencies():
    """Calcule les tendances xG pour TOUTES les équipes"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Get all unique teams
    cur.execute("""
        SELECT DISTINCT home_team as team, league FROM match_xg_stats
        UNION
        SELECT DISTINCT away_team as team, league FROM match_xg_stats
    """)
    teams = cur.fetchall()
    
    updated = 0
    for team_row in teams:
        team = team_row['team']
        league = team_row['league']
        
        # Home matches
        cur.execute("""
            SELECT home_xg as xg_for, away_xg as xg_against, home_performance as perf,
                   total_xg, match_profile, btts_expected, over25_expected
            FROM match_xg_stats WHERE home_team = %s
        """, (team,))
        home_matches = cur.fetchall()
        
        # Away matches
        cur.execute("""
            SELECT away_xg as xg_for, home_xg as xg_against, away_performance as perf,
                   total_xg, match_profile, btts_expected, over25_expected
            FROM match_xg_stats WHERE away_team = %s
        """, (team,))
        away_matches = cur.fetchall()
        
        all_matches = list(home_matches) + list(away_matches)
        
        if len(all_matches) < 3:
            continue
        
        n = len(all_matches)
        
        avg_xg_for = sum(float(m['xg_for'] or 0) for m in all_matches) / n
        avg_xg_against = sum(float(m['xg_against'] or 0) for m in all_matches) / n
        avg_total = sum(float(m['total_xg'] or 0) for m in all_matches) / n
        avg_perf = sum(float(m['perf'] or 0) for m in all_matches) / n
        
        overperf_count = sum(1 for m in all_matches if float(m['perf'] or 0) > 0)
        underperf_count = sum(1 for m in all_matches if float(m['perf'] or 0) < 0)
        
        defensive_count = sum(1 for m in all_matches if m['match_profile'] == 'defensive')
        open_count = sum(1 for m in all_matches if m['match_profile'] in ('open', 'crazy'))
        
        btts_xg_count = sum(1 for m in all_matches if m['btts_expected'])
        over25_xg_count = sum(1 for m in all_matches if m['over25_expected'])
        
        # Recent form (last 5)
        recent = all_matches[-5:] if len(all_matches) >= 5 else all_matches
        recent_xg_for = sum(float(m['xg_for'] or 0) for m in recent) / len(recent)
        recent_xg_against = sum(float(m['xg_against'] or 0) for m in recent) / len(recent)
        recent_perf = sum(float(m['perf'] or 0) for m in recent) / len(recent)
        
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
                avg_performance = EXCLUDED.avg_performance,
                btts_xg_rate = EXCLUDED.btts_xg_rate,
                over25_xg_rate = EXCLUDED.over25_xg_rate,
                recent_xg_for = EXCLUDED.recent_xg_for,
                matches_analyzed = EXCLUDED.matches_analyzed,
                updated_at = NOW()
        """, (
            team, league, f'{SEASON}-{int(SEASON)+1}',
            round(avg_xg_for, 2), round(avg_xg_against, 2), round(avg_total, 2),
            round(avg_perf, 2), round(overperf_count/n*100, 1), round(underperf_count/n*100, 1),
            round(defensive_count/n*100, 1), round(open_count/n*100, 1),
            round(btts_xg_count/n*100, 1), round(over25_xg_count/n*100, 1),
            round(recent_xg_for, 2), round(recent_xg_against, 2), round(recent_perf, 2), n
        ))
        updated += 1
    
    conn.commit()
    conn.close()
    return updated


def main():
    print("═══════════════════════════════════════════════════════════════════")
    print("UNDERSTAT ADVANCED SCRAPER - ALL LEAGUES")
    print("═══════════════════════════════════════════════════════════════════")
    
    # Get matches to process
    matches = get_match_ids_to_process()
    logger.info(f"\n📊 {len(matches)} matchs à analyser pour Big Chances")
    
    processed = 0
    by_league = {}
    
    for match_info in matches:
        match_id = match_info[0]
        league = match_info[4]
        
        shots_data = get_match_shots(match_id)
        
        if shots_data:
            home_stats = analyze_shots(shots_data.get('h', []))
            away_stats = analyze_shots(shots_data.get('a', []))
            
            if save_advanced_stats(match_info, home_stats, away_stats):
                processed += 1
                by_league[league] = by_league.get(league, 0) + 1
                
                if processed % 50 == 0:
                    logger.info(f"   Processed {processed}/{len(matches)} matchs")
    
    logger.info(f"\n✅ {processed} matchs avec Big Chances sauvegardés")
    
    for league, count in by_league.items():
        logger.info(f"   {league}: {count} matchs")
    
    # Calculate tendencies
    logger.info("\n📈 Calcul des tendances Big Chances (toutes ligues)...")
    bc_updated = calculate_all_tendencies()
    logger.info(f"   {bc_updated} équipes mises à jour")
    
    logger.info("\n📈 Calcul des tendances xG (toutes ligues)...")
    xg_updated = calculate_all_xg_tendencies()
    logger.info(f"   {xg_updated} équipes mises à jour")
    
    # Summary
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    print("\n" + "="*70)
    print("MALCHANCEUX PAR LIGUE (rebond attendu)")
    print("="*70)
    
    for league_code, league_name in LEAGUES.items():
        cur.execute("""
            SELECT team_name, bc_luck_factor, bc_conversion_rate
            FROM team_big_chances_tendencies
            WHERE league = %s AND bc_luck_factor < -1
            ORDER BY bc_luck_factor ASC
            LIMIT 3
        """, (league_name,))
        results = cur.fetchall()
        if results:
            print(f"\n   {league_name}:")
            for r in results:
                print(f"      {r['team_name']}: {r['bc_luck_factor']:+.1f} luck")
    
    conn.close()
    print("\n✅ SCRAPING AVANCÉ MULTI-LIGUES TERMINÉ!")


if __name__ == "__main__":
    main()
