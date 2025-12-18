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


def get_team_statistics(team_name: str, season: str, session: requests.Session) -> dict:
    """
    Récupère les statistiques d'une équipe via l'API (post 8 décembre 2025).

    Args:
        team_name: Nom de l'équipe (ex: "Liverpool", "Manchester_United")
        season: Année de début saison (2025 pour 2025-26)
        session: Session requests avec cookies

    Returns:
        Dict avec gameState, timing, attackSpeed, situation
    """
    try:
        # Appeler API équipe
        time.sleep(random.uniform(0.5, 1))
        response = session.get(
            f"https://understat.com/getTeamData/{team_name}/{season}",
            headers={'Referer': f'https://understat.com/team/{team_name}/{season}'}
        )

        if response.status_code != 200:
            logger.error(f"   ❌ Erreur API équipe {team_name}: HTTP {response.status_code}")
            return {}

        data = response.json()
        return data.get('statistics', {})

    except Exception as e:
        logger.error(f"   ❌ Erreur get_team_statistics {team_name}: {e}")
        return {}


def get_league_teams_from_api(league_code: str, season: str, session: requests.Session) -> list:
    """
    Récupère la liste des équipes d'une ligue depuis l'API (post 8 décembre 2025).

    Returns:
        Liste de dicts avec 'id', 'title' (nom équipe), 'url_name' (pour API)
    """
    try:
        # Appeler API ligue
        response = session.get(
            f"https://understat.com/getLeagueData/{league_code}/{season}",
            headers={'Referer': f'https://understat.com/league/{league_code}/{season}'}
        )

        if response.status_code != 200:
            logger.error(f"   ❌ Erreur API ligue {league_code}: HTTP {response.status_code}")
            return []

        data = response.json()
        teams = data.get('teams', {})

        result = []
        for team_id, team_data in teams.items():
            title = team_data.get('title', '')
            # Convertir nom en format URL (espaces → underscores)
            url_name = title.replace(' ', '_')
            result.append({
                'id': team_id,
                'title': title,
                'url_name': url_name
            })

        return result

    except Exception as e:
        logger.error(f"   ❌ Erreur get_league_teams_from_api {league_code}: {e}")
        return []


def parse_statistics_to_gamestate(team_name: str, stats: dict, league: str, season: str) -> dict:
    """
    Parse les statistics de l'API vers le format team_gamestate_stats.

    MAPPING:
    - gameState["Goal diff 0"] → gs_drawing_*
    - gameState["Goal diff +1"] + ["Goal diff > +1"] → gs_leading_*
    - gameState["Goal diff -1"] + ["Goal diff < -1"] → gs_trailing_*
    - timing["1-15"], etc. → timing_*_goals
    - attackSpeed["Fast"] → fast_attack_*
    - situation["SetPiece"] → set_piece_*
    """
    gameState = stats.get('gameState', {})
    timing = stats.get('timing', {})
    attackSpeed = stats.get('attackSpeed', {})
    situation = stats.get('situation', {})

    # Helper pour extraire avec défaut
    def get_stat(data, key, field, default=0):
        return data.get(key, {}).get(field, default)

    def get_against(data, key, field, default=0):
        return data.get(key, {}).get('against', {}).get(field, default)

    # Game State - Drawing (égalité)
    drawing = gameState.get('Goal diff 0', {})

    # Game State - Leading (mène: +1 et >+1 combinés)
    lead1 = gameState.get('Goal diff +1', {})
    lead_more = gameState.get('Goal diff > +1', {})

    # Game State - Trailing (mené: -1 et <-1 combinés)
    trail1 = gameState.get('Goal diff -1', {})
    trail_more = gameState.get('Goal diff < -1', {})

    # Fast Attack
    fast = attackSpeed.get('Fast', {})

    # Set Piece
    set_piece = situation.get('SetPiece', {})
    set_piece_goals = set_piece.get('goals', 0)
    set_piece_xg = set_piece.get('xG', 0)

    return {
        'team_name': team_name,
        'league': league,
        'season': season,

        # Drawing
        'gs_drawing_time': drawing.get('time', 0),
        'gs_drawing_shots': drawing.get('shots', 0),
        'gs_drawing_goals': drawing.get('goals', 0),
        'gs_drawing_xg': drawing.get('xG', 0),
        'gs_drawing_conceded_goals': drawing.get('against', {}).get('goals', 0),
        'gs_drawing_conceded_xg': drawing.get('against', {}).get('xG', 0),

        # Leading (somme +1 et >+1)
        'gs_leading_time': lead1.get('time', 0) + lead_more.get('time', 0),
        'gs_leading_shots': lead1.get('shots', 0) + lead_more.get('shots', 0),
        'gs_leading_goals': lead1.get('goals', 0) + lead_more.get('goals', 0),
        'gs_leading_xg': lead1.get('xG', 0) + lead_more.get('xG', 0),
        'gs_leading_conceded_goals': lead1.get('against', {}).get('goals', 0) + lead_more.get('against', {}).get('goals', 0),
        'gs_leading_conceded_xg': lead1.get('against', {}).get('xG', 0) + lead_more.get('against', {}).get('xG', 0),

        # Trailing (somme -1 et <-1)
        'gs_trailing_time': trail1.get('time', 0) + trail_more.get('time', 0),
        'gs_trailing_shots': trail1.get('shots', 0) + trail_more.get('shots', 0),
        'gs_trailing_goals': trail1.get('goals', 0) + trail_more.get('goals', 0),
        'gs_trailing_xg': trail1.get('xG', 0) + trail_more.get('xG', 0),
        'gs_trailing_conceded_goals': trail1.get('against', {}).get('goals', 0) + trail_more.get('against', {}).get('goals', 0),
        'gs_trailing_conceded_xg': trail1.get('against', {}).get('xG', 0) + trail_more.get('against', {}).get('xG', 0),

        # Timing
        'timing_1_15_goals': timing.get('1-15', {}).get('goals', 0),
        'timing_16_30_goals': timing.get('16-30', {}).get('goals', 0),
        'timing_31_45_goals': timing.get('31-45', {}).get('goals', 0),
        'timing_46_60_goals': timing.get('46-60', {}).get('goals', 0),
        'timing_61_75_goals': timing.get('61-75', {}).get('goals', 0),
        'timing_76_90_goals': timing.get('76+', {}).get('goals', 0),

        # Fast Attack
        'fast_attack_goals': fast.get('goals', 0),
        'fast_attack_xg': fast.get('xG', 0),
        'fast_attack_conceded': fast.get('against', {}).get('goals', 0),
        'fast_attack_conceded_xg': fast.get('against', {}).get('xG', 0),

        # Set Piece
        'set_piece_goals': set_piece_goals,
        'set_piece_xg': set_piece_xg,
        'set_piece_luck': set_piece_goals - set_piece_xg,
    }


def save_gamestate_stats_from_api(data: dict) -> bool:
    """
    Sauvegarde les stats game state depuis le format API parsé.

    Args:
        data: Dict retourné par parse_statistics_to_gamestate()

    Returns:
        True si sauvegarde réussie, False sinon
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Calculer les profils
    gs_leading_time = data['gs_leading_time']
    gs_drawing_time = data['gs_drawing_time']
    gs_leading_xg = data['gs_leading_xg']
    gs_drawing_xg = data['gs_drawing_xg']

    # is_killer: continue d'attaquer quand il mène
    if gs_leading_time > 0 and gs_drawing_time > 0:
        leading_xg_per_min = gs_leading_xg / gs_leading_time * 90
        drawing_xg_per_min = gs_drawing_xg / gs_drawing_time * 90
        is_killer = leading_xg_per_min > drawing_xg_per_min * 0.7
    else:
        is_killer = False

    # is_fast_vulnerable: concède beaucoup en contre-attaque rapide
    fast_conceded = data['fast_attack_conceded']
    fast_conceded_xg = data['fast_attack_conceded_xg']
    is_fast_vulnerable = fast_conceded >= fast_conceded_xg + 1

    # Timing profiles
    timing_goals = [
        data['timing_1_15_goals'],
        data['timing_16_30_goals'],
        data['timing_31_45_goals'],
        data['timing_46_60_goals'],
        data['timing_61_75_goals'],
        data['timing_76_90_goals']
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
                gs_drawing_time = EXCLUDED.gs_drawing_time,
                gs_drawing_shots = EXCLUDED.gs_drawing_shots,
                gs_drawing_goals = EXCLUDED.gs_drawing_goals,
                gs_drawing_xg = EXCLUDED.gs_drawing_xg,
                gs_drawing_conceded_goals = EXCLUDED.gs_drawing_conceded_goals,
                gs_drawing_conceded_xg = EXCLUDED.gs_drawing_conceded_xg,
                gs_leading_time = EXCLUDED.gs_leading_time,
                gs_leading_shots = EXCLUDED.gs_leading_shots,
                gs_leading_goals = EXCLUDED.gs_leading_goals,
                gs_leading_xg = EXCLUDED.gs_leading_xg,
                gs_leading_conceded_goals = EXCLUDED.gs_leading_conceded_goals,
                gs_leading_conceded_xg = EXCLUDED.gs_leading_conceded_xg,
                gs_trailing_time = EXCLUDED.gs_trailing_time,
                gs_trailing_shots = EXCLUDED.gs_trailing_shots,
                gs_trailing_goals = EXCLUDED.gs_trailing_goals,
                gs_trailing_xg = EXCLUDED.gs_trailing_xg,
                gs_trailing_conceded_goals = EXCLUDED.gs_trailing_conceded_goals,
                gs_trailing_conceded_xg = EXCLUDED.gs_trailing_conceded_xg,
                timing_1_15_goals = EXCLUDED.timing_1_15_goals,
                timing_16_30_goals = EXCLUDED.timing_16_30_goals,
                timing_31_45_goals = EXCLUDED.timing_31_45_goals,
                timing_46_60_goals = EXCLUDED.timing_46_60_goals,
                timing_61_75_goals = EXCLUDED.timing_61_75_goals,
                timing_76_90_goals = EXCLUDED.timing_76_90_goals,
                fast_attack_goals = EXCLUDED.fast_attack_goals,
                fast_attack_xg = EXCLUDED.fast_attack_xg,
                fast_attack_conceded = EXCLUDED.fast_attack_conceded,
                fast_attack_conceded_xg = EXCLUDED.fast_attack_conceded_xg,
                set_piece_goals = EXCLUDED.set_piece_goals,
                set_piece_xg = EXCLUDED.set_piece_xg,
                set_piece_luck = EXCLUDED.set_piece_luck,
                is_killer = EXCLUDED.is_killer,
                is_manager = EXCLUDED.is_manager,
                is_fast_vulnerable = EXCLUDED.is_fast_vulnerable,
                is_slow_starter = EXCLUDED.is_slow_starter,
                is_strong_finisher = EXCLUDED.is_strong_finisher,
                updated_at = NOW()
        """, (
            data['team_name'], data['league'], data['season'],
            data['gs_drawing_time'], data['gs_drawing_shots'], data['gs_drawing_goals'], data['gs_drawing_xg'],
            data['gs_drawing_conceded_goals'], data['gs_drawing_conceded_xg'],
            data['gs_leading_time'], data['gs_leading_shots'], data['gs_leading_goals'], data['gs_leading_xg'],
            data['gs_leading_conceded_goals'], data['gs_leading_conceded_xg'],
            data['gs_trailing_time'], data['gs_trailing_shots'], data['gs_trailing_goals'], data['gs_trailing_xg'],
            data['gs_trailing_conceded_goals'], data['gs_trailing_conceded_xg'],
            data['timing_1_15_goals'], data['timing_16_30_goals'], data['timing_31_45_goals'],
            data['timing_46_60_goals'], data['timing_61_75_goals'], data['timing_76_90_goals'],
            data['fast_attack_goals'], data['fast_attack_xg'],
            data['fast_attack_conceded'], data['fast_attack_conceded_xg'],
            data['set_piece_goals'], data['set_piece_xg'], data['set_piece_luck'],
            is_killer, not is_killer, is_fast_vulnerable, is_slow_starter, is_strong_finisher
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"   ❌ Erreur sauvegarde {data['team_name']}: {e}")
        conn.close()
        return False


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

        # 2. Scraper game state PAR ÉQUIPE via nouvelle API
        logger.info(f"   Scraping game state par équipe (API)...")

        # Créer session partagée pour toutes les équipes de la ligue
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        })

        # Obtenir cookies en visitant la page de la ligue
        time.sleep(random.uniform(0.5, 1))
        session.get(f"https://understat.com/league/{league_code}/{SEASON}")

        # Récupérer liste des équipes via API
        teams = get_league_teams_from_api(league_code, SEASON, session)
        logger.info(f"   {len(teams)} équipes trouvées")

        for team in teams:
            team_name = team['title']
            url_name = team['url_name']

            # Récupérer statistics via API
            stats = get_team_statistics(url_name, SEASON, session)

            if stats:
                # Parser vers format DB
                gamestate_data = parse_statistics_to_gamestate(
                    team_name, stats, league_name, f'{SEASON}-{int(SEASON)+1}'
                )

                # Sauvegarder
                if save_gamestate_stats_from_api(gamestate_data):
                    logger.info(f"   ✅ {team_name}")
                else:
                    logger.warning(f"   ⚠️ {team_name}: erreur sauvegarde")
            else:
                logger.warning(f"   ⚠️ {team_name}: pas de statistics")

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
