#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SCRAPE STANDINGS - REGIME DETECTOR                        ║
║                                                                              ║
║  Scrape les classements actuels depuis football-data.co.uk                   ║
║  et enrichit quantum.team_profiles.quantum_dna->'status_2025_2026'           ║
║                                                                              ║
║  Données calculées:                                                          ║
║  - rank, points, pts_to_leader, pts_to_relegation                           ║
║  - season_phase (EARLY/MID/LATE/FINAL)                                      ║
║  - motivation_zone (TITLE_RACE/EUROPE/MID_TABLE/RELEGATION)                 ║
║                                                                              ║
║  Usage: python3 scrape_standings.py                                          ║
║  Cron:  0 7 * * * python3 /home/Mon_ps/scripts/scrape_standings.py          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import pandas as pd
from io import StringIO
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from collections import defaultdict
import json
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

LEAGUES = {
    'E0': {'name': 'EPL', 'total_teams': 20, 'relegation_zone': 3, 'europe_spots': 6, 'total_matchdays': 38},
    'E1': {'name': 'Championship', 'total_teams': 24, 'relegation_zone': 3, 'europe_spots': 0, 'total_matchdays': 46},
    'D1': {'name': 'Bundesliga', 'total_teams': 18, 'relegation_zone': 3, 'europe_spots': 6, 'total_matchdays': 34},
    'I1': {'name': 'SerieA', 'total_teams': 20, 'relegation_zone': 3, 'europe_spots': 6, 'total_matchdays': 38},
    'SP1': {'name': 'LaLiga', 'total_teams': 20, 'relegation_zone': 3, 'europe_spots': 6, 'total_matchdays': 38},
    'F1': {'name': 'Ligue1', 'total_teams': 18, 'relegation_zone': 3, 'europe_spots': 5, 'total_matchdays': 34},
}

# Mapping football-data.co.uk → quantum.team_profiles
TEAM_MAPPING = {
    'Man United': 'Manchester United',
    'Man City': 'Manchester City',
    'Newcastle': 'Newcastle United',
    'Wolves': 'Wolverhampton Wanderers',
    "Nott'm Forest": 'Nottingham Forest',
    'Spurs': 'Tottenham',
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

def normalize_team(name: str) -> str:
    """Normalise le nom d'équipe vers le format quantum.team_profiles"""
    return TEAM_MAPPING.get(name, name)


# ═══════════════════════════════════════════════════════════════════════════════
# SCRAPING
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_league_data(code: str, season: str = '2526') -> pd.DataFrame:
    """Récupère les données d'une ligue depuis football-data.co.uk"""
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and len(r.text) > 100:
            text = r.text.replace('\ufeff', '')
            df = pd.read_csv(StringIO(text))
            df['league_code'] = code
            return df
    except Exception as e:
        print(f"   ⚠️ Erreur fetch {code}: {e}")
    return pd.DataFrame()


def calculate_standings(df: pd.DataFrame, league_config: dict) -> list:
    """Calcule le classement depuis les résultats"""
    if df.empty:
        return []
    
    standings = defaultdict(lambda: {
        'played': 0, 'wins': 0, 'draws': 0, 'losses': 0,
        'goals_for': 0, 'goals_against': 0, 'points': 0,
        'form': []  # Last 5 results
    })
    
    # Parcourir tous les matchs
    for _, row in df.iterrows():
        home = row.get('HomeTeam', '')
        away = row.get('AwayTeam', '')
        fthg = row.get('FTHG', 0)
        ftag = row.get('FTAG', 0)
        ftr = row.get('FTR', '')
        
        if not home or not away or pd.isna(ftr):
            continue
        
        # Home team
        standings[home]['played'] += 1
        standings[home]['goals_for'] += int(fthg) if pd.notna(fthg) else 0
        standings[home]['goals_against'] += int(ftag) if pd.notna(ftag) else 0
        
        # Away team
        standings[away]['played'] += 1
        standings[away]['goals_for'] += int(ftag) if pd.notna(ftag) else 0
        standings[away]['goals_against'] += int(fthg) if pd.notna(fthg) else 0
        
        # Results
        if ftr == 'H':
            standings[home]['wins'] += 1
            standings[home]['points'] += 3
            standings[home]['form'].append('W')
            standings[away]['losses'] += 1
            standings[away]['form'].append('L')
        elif ftr == 'A':
            standings[away]['wins'] += 1
            standings[away]['points'] += 3
            standings[away]['form'].append('W')
            standings[home]['losses'] += 1
            standings[home]['form'].append('L')
        else:  # Draw
            standings[home]['draws'] += 1
            standings[home]['points'] += 1
            standings[home]['form'].append('D')
            standings[away]['draws'] += 1
            standings[away]['points'] += 1
            standings[away]['form'].append('D')
    
    # Trier par points, goal diff, goals for
    sorted_teams = sorted(
        standings.items(),
        key=lambda x: (x[1]['points'], 
                      x[1]['goals_for'] - x[1]['goals_against'],
                      x[1]['goals_for']),
        reverse=True
    )
    
    # Construire le classement enrichi
    result = []
    leader_points = sorted_teams[0][1]['points'] if sorted_teams else 0
    
    # Points de relégation (17e ou 18e selon la ligue)
    relegation_rank = league_config['total_teams'] - league_config['relegation_zone']
    relegation_points = sorted_teams[relegation_rank][1]['points'] if len(sorted_teams) > relegation_rank else 0
    
    for rank, (team, stats) in enumerate(sorted_teams, 1):
        goal_diff = stats['goals_for'] - stats['goals_against']
        form_last_5 = ''.join(stats['form'][-5:])
        
        result.append({
            'team': normalize_team(team),
            'team_raw': team,
            'rank': rank,
            'played': stats['played'],
            'wins': stats['wins'],
            'draws': stats['draws'],
            'losses': stats['losses'],
            'goals_for': stats['goals_for'],
            'goals_against': stats['goals_against'],
            'goal_diff': goal_diff,
            'points': stats['points'],
            'pts_to_leader': leader_points - stats['points'],
            'pts_to_relegation': stats['points'] - relegation_points,
            'form_last_5': form_last_5,
        })
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# REGIME DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_season_phase(matchday: int, total_matchdays: int) -> str:
    """
    Détermine la phase de la saison
    EARLY: 0-25% (journées 1-9 sur 38)
    MID: 25-60% (journées 10-23)
    LATE: 60-85% (journées 24-32)
    FINAL: 85-100% (journées 33-38)
    """
    progress = matchday / total_matchdays
    
    if progress < 0.25:
        return "EARLY"
    elif progress < 0.60:
        return "MID"
    elif progress < 0.85:
        return "LATE"
    else:
        return "FINAL"


def calculate_motivation_zone(rank: int, pts_to_leader: int, pts_to_relegation: int, 
                              league_config: dict, season_phase: str) -> str:
    """
    Détermine la zone de motivation
    TITLE_RACE: Top 3 avec ≤6 pts du leader
    EUROPE: Positions 4-6 (ou 7 si Conference League)
    MID_TABLE: Safe, pas en course
    RELEGATION: Zone rouge ou ≤3 pts au-dessus
    """
    europe_spots = league_config['europe_spots']
    total_teams = league_config['total_teams']
    relegation_start = total_teams - league_config['relegation_zone'] + 1
    
    # Zone de relégation
    if rank >= relegation_start or pts_to_relegation <= 3:
        return "RELEGATION"
    
    # Course au titre (ajustée selon la phase)
    title_threshold = 6 if season_phase in ["EARLY", "MID"] else 9
    if rank <= 3 and pts_to_leader <= title_threshold:
        return "TITLE_RACE"
    
    # Course à l'Europe
    if rank <= europe_spots + 2:  # +2 pour Conference League potentielle
        return "EUROPE"
    
    return "MID_TABLE"


def calculate_reliability_multiplier(motivation_zone: str, form_last_5: str) -> float:
    """
    Calcule un multiplicateur de fiabilité basé sur la motivation
    TITLE_RACE + bonne forme = très fiable (1.2)
    RELEGATION + mauvaise forme = moins fiable (0.8)
    """
    base = {
        "TITLE_RACE": 1.15,
        "EUROPE": 1.05,
        "MID_TABLE": 0.95,
        "RELEGATION": 1.10  # Motivation desperate
    }.get(motivation_zone, 1.0)
    
    # Ajustement forme
    if form_last_5:
        wins = form_last_5.count('W')
        losses = form_last_5.count('L')
        
        if wins >= 4:
            base += 0.05
        elif losses >= 4:
            base -= 0.05
    
    return round(base, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE UPDATE
# ═══════════════════════════════════════════════════════════════════════════════

def update_team_status(conn, team_name: str, status_data: dict, league_name: str):
    """Met à jour status_2025_2026 dans quantum_dna"""
    cur = conn.cursor()
    try:
        # Récupérer le quantum_dna actuel
        cur.execute("""
            SELECT quantum_dna FROM quantum.team_profiles 
            WHERE team_name = %s
        """, (team_name,))
        
        row = cur.fetchone()
        if not row:
            print(f"   ⚠️ Équipe non trouvée: {team_name}")
            return False
        
        quantum_dna = row[0] or {}
        
        # Mettre à jour status_2025_2026
        quantum_dna['status_2025_2026'] = status_data
        
        # Sauvegarder
        cur.execute("""
            UPDATE quantum.team_profiles 
            SET quantum_dna = %s, updated_at = NOW()
            WHERE team_name = %s
        """, (Json(quantum_dna), team_name))
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"   ❌ Erreur update {team_name}: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║          REGIME DETECTOR - STANDINGS ENRICHMENT                 ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    total_updated = 0
    total_errors = 0
    
    for code, config in LEAGUES.items():
        league_name = config['name']
        print(f"\n📊 {league_name} ({code})...")
        
        # 1. Scraper les données
        df = fetch_league_data(code)
        if df.empty:
            print(f"   ⚠️ Pas de données pour {league_name}")
            continue
        
        print(f"   ✓ {len(df)} matchs récupérés")
        
        # 2. Calculer le classement
        standings = calculate_standings(df, config)
        if not standings:
            print(f"   ⚠️ Impossible de calculer le classement")
            continue
        
        # 3. Déterminer la journée actuelle (moyenne des matchs joués)
        avg_played = sum(t['played'] for t in standings) / len(standings)
        matchday = int(avg_played)
        
        # 4. Calculer la phase de saison
        season_phase = calculate_season_phase(matchday, config['total_matchdays'])
        
        print(f"   📅 Journée {matchday}/{config['total_matchdays']} - Phase: {season_phase}")
        
        # 5. Enrichir chaque équipe
        for team_data in standings:
            motivation_zone = calculate_motivation_zone(
                team_data['rank'],
                team_data['pts_to_leader'],
                team_data['pts_to_relegation'],
                config,
                season_phase
            )
            
            reliability_mult = calculate_reliability_multiplier(
                motivation_zone, 
                team_data['form_last_5']
            )
            
            status_data = {
                "matchday": matchday,
                "total_matchdays": config['total_matchdays'],
                "rank": team_data['rank'],
                "points": team_data['points'],
                "played": team_data['played'],
                "wins": team_data['wins'],
                "draws": team_data['draws'],
                "losses": team_data['losses'],
                "goals_for": team_data['goals_for'],
                "goals_against": team_data['goals_against'],
                "goal_diff": team_data['goal_diff'],
                "pts_to_leader": team_data['pts_to_leader'],
                "pts_to_relegation": team_data['pts_to_relegation'],
                "form_last_5": team_data['form_last_5'],
                "season_phase": season_phase,
                "motivation_zone": motivation_zone,
                "reliability_multiplier": reliability_mult,
                "league": league_name,
                "updated_at": datetime.now().isoformat()
            }
            
            success = update_team_status(conn, team_data['team'], status_data, league_name)
            if success:
                total_updated += 1
                # Afficher top 3 et zone de relégation
                if team_data['rank'] <= 3 or team_data['rank'] >= config['total_teams'] - 2:
                    zone_emoji = "🏆" if motivation_zone == "TITLE_RACE" else "🔴" if motivation_zone == "RELEGATION" else "🔵"
                    print(f"   {zone_emoji} {team_data['rank']:2}. {team_data['team'][:20]:20} {team_data['points']:2}pts ({motivation_zone})")
            else:
                total_errors += 1
    
    conn.close()
    
    print("\n" + "═" * 60)
    print(f"✅ {total_updated} équipes mises à jour")
    print(f"❌ {total_errors} erreurs")
    print("═" * 60)
    
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
