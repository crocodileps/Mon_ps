#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
UNDERSTAT ALL LEAGUES SCRAPER - xG + Game State + Big Chances
═══════════════════════════════════════════════════════════════════════════════

Scrape toutes les ligues européennes majeures:
- Premier League (EPL)
- La Liga (Espagne)
- Bundesliga (Allemagne)
- Serie A (Italie)
- Ligue 1 (France)
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
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

SEASON = '2025'

# Toutes les ligues supportées par Understat
LEAGUES = {
    'EPL': {
        'name': 'Premier League',
        'country': 'England'
    },
    'La_Liga': {
        'name': 'La Liga',
        'country': 'Spain'
    },
    'Bundesliga': {
        'name': 'Bundesliga',
        'country': 'Germany'
    },
    'Serie_A': {
        'name': 'Serie A',
        'country': 'Italy'
    },
    'Ligue_1': {
        'name': 'Ligue 1',
        'country': 'France'
    }
}


def get_understat_matches(league: str, season: str) -> list:
    """
    Récupère les matchs Understat via la nouvelle API (post 8 décembre 2025).

    CHANGEMENT ARCHITECTURE:
    - Avant: Scraping HTML avec BeautifulSoup + regex pour extraire datesData
    - Après: API directe getLeagueData/{league}/{season} retourne JSON

    Args:
        league: Code ligue (EPL, La_Liga, Bundesliga, Serie_A, Ligue_1)
        season: Année de début saison (2025 pour 2025-26)

    Returns:
        Liste des matchs avec xG, goals, datetime, isResult, etc.
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    })

    try:
        # 1. Obtenir les cookies en visitant la page de la ligue
        logger.info(f"   Obtention cookies pour {league}...")
        time.sleep(random.uniform(1, 2))
        session.get(f"https://understat.com/league/{league}/{season}")

        # 2. Appeler l'API avec les cookies
        logger.info(f"   Appel API getLeagueData/{league}/{season}...")
        time.sleep(random.uniform(0.5, 1))
        response = session.get(
            f"https://understat.com/getLeagueData/{league}/{season}",
            headers={'Referer': f'https://understat.com/league/{league}/{season}'}
        )

        if response.status_code != 200:
            logger.error(f"   ❌ Erreur API Understat: HTTP {response.status_code} pour {league}")
            return []

        data = response.json()
        matches = data.get('dates', [])
        logger.info(f"   ✅ {len(matches)} matchs récupérés depuis API")
        return matches

    except Exception as e:
        logger.error(f"   ❌ Erreur get_understat_matches pour {league}: {e}")
        return []


def get_league_teams(league_code):
    """Récupère toutes les équipes d'une ligue depuis Understat"""
    url = f"https://understat.com/league/{league_code}/{SEASON}"
    
    try:
        time.sleep(random.uniform(1, 2))
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code} for {league_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup.find_all('script'):
            script_text = str(script)
            if 'teamsData' in script_text:
                match = re.search(r"var teamsData\s*=\s*JSON\.parse\('(.+?)'\)", script_text)
                if match:
                    decoded = match.group(1).encode().decode('unicode_escape')
                    teams_data = json.loads(decoded)
                    
                    teams = []
                    for team_id, team_info in teams_data.items():
                        team_name = team_info.get('title', '')
                        # Convertir pour URL (espaces -> underscores)
                        team_url = team_name.replace(' ', '_')
                        teams.append({
                            'id': team_id,
                            'name': team_name,
                            'url_name': team_url
                        })
                    
                    return teams
        
        return []
        
    except Exception as e:
        logger.error(f"Error getting teams for {league_code}: {e}")
        return []


def scrape_team_data(team_url_name, league_code, league_name):
    """Scrape toutes les données d'une équipe"""
    url = f"https://understat.com/team/{team_url_name}/{SEASON}"
    
    try:
        time.sleep(random.uniform(1.5, 2.5))
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            return None, None, None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        dates_data = None
        stats_data = None
        
        for script in soup.find_all('script'):
            script_text = str(script)
            
            # datesData = matchs avec xG
            if 'datesData' in script_text and dates_data is None:
                match = re.search(r"var datesData\s*=\s*JSON\.parse\('(.+?)'\)", script_text)
                if match:
                    decoded = match.group(1).encode().decode('unicode_escape')
                    dates_data = json.loads(decoded)
            
            # statisticsData = game state, timing, etc.
            if 'statisticsData' in script_text and stats_data is None:
                match = re.search(r"var statisticsData\s*=\s*JSON\.parse\('(.+?)'\)", script_text)
                if match:
                    decoded = match.group(1).encode().decode('unicode_escape')
                    stats_data = json.loads(decoded)
        
        return dates_data, stats_data, team_url_name.replace('_', ' ')
        
    except Exception as e:
        logger.error(f"Error scraping {team_url_name}: {e}")
        return None, None, None


def save_xg_matches(matches, league_name):
    """Sauvegarde les matchs xG"""
    if not matches:
        return 0
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    saved = 0
    for m in matches:
        if not m.get('isResult'):
            continue
            
        match_id = m.get('id')
        home_team = m.get('h', {}).get('title', '')
        away_team = m.get('a', {}).get('title', '')
        home_goals = int(m.get('goals', {}).get('h', 0))
        away_goals = int(m.get('goals', {}).get('a', 0))
        home_xg = float(m.get('xG', {}).get('h', 0) or 0)
        away_xg = float(m.get('xG', {}).get('a', 0) or 0)
        match_date = m.get('datetime', '')[:10]
        
        total_xg = home_xg + away_xg
        home_perf = home_goals - home_xg
        away_perf = away_goals - away_xg
        
        if total_xg < 1.5:
            profile = 'defensive'
        elif total_xg < 2.5:
            profile = 'balanced'
        elif total_xg < 4:
            profile = 'open'
        else:
            profile = 'crazy'
        
        try:
            cur.execute("""
                INSERT INTO match_xg_stats 
                (match_id, match_date, home_team, away_team, home_goals, away_goals,
                 home_xg, away_xg, total_xg, home_performance, away_performance,
                 match_profile, xg_diff, btts_expected, over25_expected, league, season)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id) DO NOTHING
            """, (
                match_id, match_date, home_team, away_team, home_goals, away_goals,
                home_xg, away_xg, total_xg, round(home_perf, 2), round(away_perf, 2),
                profile, round(abs(home_xg - away_xg), 2),
                home_xg > 0.8 and away_xg > 0.8, total_xg > 2.5,
                league_name, f'{SEASON}-{int(SEASON)+1}'
            ))
            saved += 1
        except:
            pass
    
    conn.commit()
    conn.close()
    return saved


def save_gamestate_stats(team_name, stats, league_name):
    """Sauvegarde les stats game state"""
    if not stats:
        return False
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Game State
    gs = stats.get('gameState', {})
    drawing = gs.get('Goal diff 0', {})
    leading = gs.get('Goal diff +1', {})
    trailing = gs.get('Goal diff -1', {})
    
    # Timing
    timing = stats.get('timing', {})
    
    # Attack Speed
    attack = stats.get('attackSpeed', {})
    fast = attack.get('Fast', {})
    
    # Set Pieces
    situation = stats.get('situation', {})
    set_piece_goals = 0
    set_piece_xg = 0
    for sit_type in ['FromCorner', 'SetPiece', 'DirectFreekick']:
        sit = situation.get(sit_type, {})
        set_piece_goals += sit.get('goals', 0)
        set_piece_xg += float(sit.get('xG', 0))
    
    # Calculate profiles
    gs_leading_time = leading.get('time', 0)
    gs_drawing_time = drawing.get('time', 0)
    gs_leading_xg = float(leading.get('xG', 0))
    gs_drawing_xg = float(drawing.get('xG', 0))
    
    if gs_leading_time > 0 and gs_drawing_time > 0:
        leading_xg_per_min = gs_leading_xg / gs_leading_time * 90
        drawing_xg_per_min = gs_drawing_xg / gs_drawing_time * 90
        is_killer = leading_xg_per_min > drawing_xg_per_min * 0.7
    else:
        is_killer = False
    
    fast_conceded = fast.get('against', {}).get('goals', 0)
    fast_conceded_xg = float(fast.get('against', {}).get('xG', 0))
    is_fast_vulnerable = fast_conceded >= fast_conceded_xg + 1
    
    timing_goals = [
        timing.get('1-15', {}).get('goals', 0),
        timing.get('16-30', {}).get('goals', 0),
        timing.get('31-45', {}).get('goals', 0),
        timing.get('46-60', {}).get('goals', 0),
        timing.get('61-75', {}).get('goals', 0),
        timing.get('76-90', {}).get('goals', 0)
    ]
    total_goals = sum(timing_goals)
    is_slow_starter = timing_goals[0] < total_goals * 0.1 if total_goals > 0 else False
    is_strong_finisher = timing_goals[5] > total_goals * 0.2 if total_goals > 0 else False
    
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
                gs_leading_goals = EXCLUDED.gs_leading_goals,
                is_killer = EXCLUDED.is_killer,
                is_fast_vulnerable = EXCLUDED.is_fast_vulnerable,
                updated_at = NOW()
        """, (
            team_name, league_name, f'{SEASON}-{int(SEASON)+1}',
            drawing.get('time', 0), drawing.get('shots', 0), drawing.get('goals', 0), float(drawing.get('xG', 0)),
            drawing.get('against', {}).get('goals', 0), float(drawing.get('against', {}).get('xG', 0)),
            leading.get('time', 0), leading.get('shots', 0), leading.get('goals', 0), float(leading.get('xG', 0)),
            leading.get('against', {}).get('goals', 0), float(leading.get('against', {}).get('xG', 0)),
            trailing.get('time', 0), trailing.get('shots', 0), trailing.get('goals', 0), float(trailing.get('xG', 0)),
            trailing.get('against', {}).get('goals', 0), float(trailing.get('against', {}).get('xG', 0)),
            timing_goals[0], timing_goals[1], timing_goals[2],
            timing_goals[3], timing_goals[4], timing_goals[5],
            fast.get('goals', 0), float(fast.get('xG', 0)),
            fast_conceded, fast_conceded_xg,
            set_piece_goals, round(set_piece_xg, 2), round(set_piece_goals - set_piece_xg, 2),
            is_killer, not is_killer, is_fast_vulnerable, is_slow_starter, is_strong_finisher
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving {team_name}: {e}")
        conn.close()
        return False


def main():
    print("═══════════════════════════════════════════════════════════════════")
    print("UNDERSTAT ALL LEAGUES SCRAPER")
    print("═══════════════════════════════════════════════════════════════════")
    
    total_teams = 0
    total_matches = 0
    
    for league_code, league_info in LEAGUES.items():
        league_name = league_info['name']
        print(f"\n{'='*70}")
        print(f"�� {league_name} ({league_info['country']})")
        print('='*70)
        
        # NOUVELLE ARCHITECTURE (post 8 décembre 2025):
        # 1. Scraper TOUS les matchs de la ligue via API (1 seule requête)
        logger.info(f"   Scraping matchs xG via API...")
        matches = get_understat_matches(league_code, SEASON)
        league_matches = save_xg_matches(matches, league_name)
        total_matches += league_matches
        logger.info(f"   📊 {league_matches} matchs xG sauvegardés")

        # 2. Scraper game state PAR ÉQUIPE (garde ancienne méthode HTML)
        logger.info(f"   Scraping game state par équipe...")
        teams = get_league_teams(league_code)
        logger.info(f"   {len(teams)} équipes trouvées")

        for team in teams:
            # On ne récupère plus dates_data ici (déjà fait avec API ci-dessus)
            # On récupère SEULEMENT stats_data (game state, timing, etc.)
            dates_data, stats_data, team_name = scrape_team_data(
                team['url_name'], league_code, league_name
            )

            if stats_data:
                save_gamestate_stats(team_name, stats_data, league_name)
                logger.info(f"   ✅ {team_name}")

            total_teams += 1
    
    # Résumé final
    print("\n" + "="*70)
    print("RÉSUMÉ FINAL")
    print("="*70)
    print(f"   🏆 {len(LEAGUES)} ligues scrapées")
    print(f"   👥 {total_teams} équipes analysées")
    print(f"   ⚽ {total_matches} matchs xG")
    
    # Stats par ligue
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("\n" + "="*70)
    print("KILLERS PAR LIGUE (continuent d'attaquer)")
    print("="*70)
    
    for league_code, league_info in LEAGUES.items():
        cur.execute("""
            SELECT team_name FROM team_gamestate_stats
            WHERE league = %s AND is_killer = true
            ORDER BY team_name
        """, (league_info['name'],))
        killers = [r[0] for r in cur.fetchall()]
        print(f"\n   {league_info['name']}:")
        for k in killers[:5]:
            print(f"      - {k}")
        if len(killers) > 5:
            print(f"      ... et {len(killers)-5} autres")
    
    conn.close()
    print("\n✅ SCRAPING MULTI-LIGUES TERMINÉ!")


if __name__ == "__main__":
    main()
