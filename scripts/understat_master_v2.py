#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🚀 UNDERSTAT MASTER SCRAPER V2.0 - API DIRECTE                              ║
║  Génère TOUS les fichiers DNA depuis l'API /getLeagueData/                   ║
║                                                                              ║
║  Fichiers générés:                                                           ║
║  ├── quantum_v2/teams_context_dna.json                                       ║
║  ├── quantum_v2/players_impact_dna.json                                      ║
║  ├── quantum_v2/gamestate_insights.json                                      ║
║  ├── quantum_v2/action_analysis.json                                         ║
║  ├── quantum_v2/speed_insights.json                                          ║
║  ├── quantum_v2/zone_analysis.json                                           ║
║  ├── quantum_v2/team_exploit_profiles.json                                   ║
║  └── goal_analysis/all_goals_2025.json                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import time

# Headers CRITIQUES
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://understat.com/'
}

# Répertoires
QUANTUM_DIR = Path('/home/Mon_ps/data/quantum_v2')
GOAL_DIR = Path('/home/Mon_ps/data/goal_analysis')
QUANTUM_DIR.mkdir(parents=True, exist_ok=True)
GOAL_DIR.mkdir(parents=True, exist_ok=True)

LEAGUES = {
    'EPL': 'Premier League',
    'La_liga': 'La Liga', 
    'Bundesliga': 'Bundesliga',
    'Serie_A': 'Serie A',
    'Ligue_1': 'Ligue 1'
}

SEASON = '2025'

def fetch_league_data(league: str) -> dict:
    """Fetch via API directe"""
    url = f"https://understat.com/getLeagueData/{league}/{SEASON}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200 and len(response.text) > 1000:
            return response.json()
    except Exception as e:
        print(f"   ❌ Erreur {league}: {e}")
    return None

def fetch_team_data(team_name: str) -> dict:
    """Fetch données détaillées d'une équipe (statisticsData)"""
    # L'API team existe aussi
    url = f"https://understat.com/getTeamData/{team_name}/{SEASON}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200 and len(response.text) > 100:
            return response.json()
    except:
        pass
    return None

def fetch_match_shots(match_id: str) -> list:
    """Fetch tous les tirs d'un match"""
    url = f"https://understat.com/getMatchShots/{match_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get('h', []) + data.get('a', [])
    except:
        pass
    return []

# ═══════════════════════════════════════════════════════════════════════════════
# BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def build_teams_context_dna(all_data: dict) -> dict:
    """teams_context_dna.json avec PPDA, momentum, variance"""
    teams_dna = {}
    
    for league, data in all_data.items():
        if not data or 'teams' not in data:
            continue
            
        for team_id, team_info in data['teams'].items():
            team_name = team_info.get('title', 'Unknown')
            history = team_info.get('history', [])
            
            if not history:
                continue
            
            matches = len(history)
            
            # Agrégations
            total_xg = sum(float(m.get('xG', 0)) for m in history)
            total_xga = sum(float(m.get('xGA', 0)) for m in history)
            total_npxg = sum(float(m.get('npxG', 0)) for m in history)
            total_npxga = sum(float(m.get('npxGA', 0)) for m in history)
            total_deep = sum(int(m.get('deep', 0)) for m in history)
            total_scored = sum(int(m.get('scored', 0)) for m in history)
            total_missed = sum(int(m.get('missed', 0)) for m in history)
            total_wins = sum(1 for m in history if m.get('result') == 'w')
            total_draws = sum(1 for m in history if m.get('result') == 'd')
            total_losses = sum(1 for m in history if m.get('result') == 'l')
            total_pts = sum(int(m.get('pts', 0)) for m in history)
            
            # PPDA
            ppda_att = sum(float(m.get('ppda', {}).get('att', 0)) for m in history)
            ppda_def = sum(float(m.get('ppda', {}).get('def', 1)) for m in history)
            ppda = ppda_att / ppda_def if ppda_def > 0 else 10
            
            if ppda < 8:
                pressing_style = "GEGENPRESSING"
            elif ppda < 10:
                pressing_style = "HIGH_PRESS"
            elif ppda < 12:
                pressing_style = "MEDIUM_PRESS"
            else:
                pressing_style = "LOW_BLOCK"
            
            # Momentum
            last_5 = history[-5:] if len(history) >= 5 else history
            form = ''.join('W' if m.get('result') == 'w' else 'D' if m.get('result') == 'd' else 'L' for m in last_5)
            
            # Variance
            xg_diff = total_scored - total_xg
            xga_diff = total_missed - total_xga
            
            teams_dna[team_name] = {
                'team_id': team_id,
                'league': LEAGUES.get(league, league),
                'matches': matches,
                'record': {
                    'wins': total_wins, 'draws': total_draws, 'losses': total_losses,
                    'points': total_pts, 'goals_for': total_scored, 'goals_against': total_missed
                },
                'history': {
                    'xg': round(total_xg, 2), 'xga': round(total_xga, 2),
                    'npxg': round(total_npxg, 2), 'npxga': round(total_npxga, 2),
                    'xg_90': round(total_xg / matches, 3) if matches > 0 else 0,
                    'xga_90': round(total_xga / matches, 3) if matches > 0 else 0,
                    'deep': total_deep,
                    'deep_90': round(total_deep / matches, 2) if matches > 0 else 0,
                    'ppda': round(ppda, 2),
                    'pressing_style': pressing_style
                },
                'variance': {
                    'xg_overperformance': round(xg_diff, 2),
                    'xga_overperformance': round(xga_diff, 2),
                    'luck_index': round((xg_diff - xga_diff) / matches, 3) if matches > 0 else 0
                },
                'momentum_dna': {
                    'form_last_5': form,
                    'points_last_5': form.count('W') * 3 + form.count('D'),
                    'xg_last_5': round(sum(float(m.get('xG', 0)) for m in last_5), 2),
                    'xga_last_5': round(sum(float(m.get('xGA', 0)) for m in last_5), 2)
                },
                'raw_history': history,
                'updated_at': datetime.now().isoformat()
            }
    
    return teams_dna

def build_players_impact_dna(all_data: dict) -> list:
    """players_impact_dna.json"""
    players = []
    
    for league, data in all_data.items():
        if not data or 'players' not in data:
            continue
            
        for player in data['players']:
            players.append({
                'id': player.get('id'),
                'player_name': player.get('player_name'),
                'team': player.get('team_title'),
                'league': LEAGUES.get(league, league),
                'position': player.get('position'),
                'games': int(player.get('games', 0)),
                'time': int(player.get('time', 0)),
                'goals': int(player.get('goals', 0)),
                'assists': int(player.get('assists', 0)),
                'xG': round(float(player.get('xG', 0)), 3),
                'xA': round(float(player.get('xA', 0)), 3),
                'npxG': round(float(player.get('npxG', 0)), 3),
                'xGChain': round(float(player.get('xGChain', 0)), 3),
                'xGBuildup': round(float(player.get('xGBuildup', 0)), 3),
                'shots': int(player.get('shots', 0)),
                'key_passes': int(player.get('key_passes', 0)),
            })
    
    return sorted(players, key=lambda x: x['xG'], reverse=True)

def build_gamestate_insights(teams_dna: dict) -> dict:
    """gamestate_insights.json - Comment les équipes performent selon le score"""
    insights = {}
    
    for team_name, team_data in teams_dna.items():
        history = team_data.get('raw_history', [])
        if not history:
            continue
        
        # Analyser les matchs par gamestate
        gamestates = defaultdict(lambda: {'matches': 0, 'xg': 0, 'xga': 0, 'goals': 0, 'conceded': 0})
        
        for match in history:
            # Simplification: on utilise le résultat comme proxy
            result = match.get('result', 'd')
            xg = float(match.get('xG', 0))
            xga = float(match.get('xGA', 0))
            scored = int(match.get('scored', 0))
            missed = int(match.get('missed', 0))
            
            gamestates['all']['matches'] += 1
            gamestates['all']['xg'] += xg
            gamestates['all']['xga'] += xga
            gamestates['all']['goals'] += scored
            gamestates['all']['conceded'] += missed
            
            if result == 'w':
                gamestates['winning']['matches'] += 1
                gamestates['winning']['xg'] += xg
            elif result == 'l':
                gamestates['losing']['matches'] += 1
                gamestates['losing']['xg'] += xg
        
        insights[team_name] = {
            'league': team_data.get('league'),
            'gamestates': dict(gamestates),
            'avg_xg_when_winning': round(gamestates['winning']['xg'] / max(gamestates['winning']['matches'], 1), 3),
            'avg_xg_when_losing': round(gamestates['losing']['xg'] / max(gamestates['losing']['matches'], 1), 3),
        }
    
    return insights

def build_team_exploit_profiles(teams_dna: dict) -> dict:
    """team_exploit_profiles.json - Vulnérabilités exploitables"""
    profiles = {}
    
    for team_name, team_data in teams_dna.items():
        history = team_data.get('raw_history', [])
        if not history:
            continue
        
        # Analyser les patterns de vulnérabilité
        home_xga = []
        away_xga = []
        
        for match in history:
            xga = float(match.get('xGA', 0))
            if match.get('h_a') == 'h':
                home_xga.append(xga)
            else:
                away_xga.append(xga)
        
        avg_home_xga = sum(home_xga) / len(home_xga) if home_xga else 0
        avg_away_xga = sum(away_xga) / len(away_xga) if away_xga else 0
        
        # Identifier les vulnérabilités
        vulnerabilities = []
        if avg_away_xga > avg_home_xga * 1.3:
            vulnerabilities.append("WEAK_AWAY")
        if team_data['history']['ppda'] > 12:
            vulnerabilities.append("LOW_PRESS_VULNERABLE")
        if team_data['variance']['xga_overperformance'] < -2:
            vulnerabilities.append("LUCKY_DEFENSE")
        
        profiles[team_name] = {
            'league': team_data.get('league'),
            'pressing_style': team_data['history']['pressing_style'],
            'ppda': team_data['history']['ppda'],
            'home_xga_avg': round(avg_home_xga, 3),
            'away_xga_avg': round(avg_away_xga, 3),
            'vulnerabilities': vulnerabilities,
            'exploit_markets': [],
            'updated_at': datetime.now().isoformat()
        }
    
    return profiles

def build_all_goals(all_data: dict) -> list:
    """all_goals_2025.json - Tous les buts avec détails"""
    all_goals = []
    
    for league, data in all_data.items():
        if not data or 'dates' not in data:
            continue
        
        for match in data.get('dates', []):
            match_id = match.get('id')
            home_team = match.get('h', {}).get('title', 'Unknown')
            away_team = match.get('a', {}).get('title', 'Unknown')
            home_goals = int(match.get('h', {}).get('goals', 0))
            away_goals = int(match.get('a', {}).get('goals', 0))
            home_xg = float(match.get('h', {}).get('xG', 0))
            away_xg = float(match.get('a', {}).get('xG', 0))
            date = match.get('datetime', '')
            
            # Créer des entrées de buts simplifiées
            for i in range(home_goals):
                all_goals.append({
                    'match_id': match_id,
                    'date': date,
                    'league': LEAGUES.get(league, league),
                    'scoring_team': home_team,
                    'conceding_team': away_team,
                    'home_away': 'home',
                    'match_xg': home_xg,
                })
            
            for i in range(away_goals):
                all_goals.append({
                    'match_id': match_id,
                    'date': date,
                    'league': LEAGUES.get(league, league),
                    'scoring_team': away_team,
                    'conceding_team': home_team,
                    'home_away': 'away',
                    'match_xg': away_xg,
                })
    
    return all_goals

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("🚀 UNDERSTAT MASTER SCRAPER V2.0")
    print(f"   Season: {SEASON} | Leagues: {len(LEAGUES)}")
    print("=" * 70)
    
    all_data = {}
    
    # 1. Fetch toutes les ligues
    for league_code, league_name in LEAGUES.items():
        print(f"\n📥 {league_name}...")
        data = fetch_league_data(league_code)
        
        if data:
            teams = len(data.get('teams', {}))
            players = len(data.get('players', []))
            matches = len(data.get('dates', []))
            print(f"   ✅ {teams} teams | {players} players | {matches} matches")
            all_data[league_code] = data
        else:
            print(f"   ❌ Failed")
        
        time.sleep(2)
    
    # 2. Construire tous les DNA
    print("\n" + "=" * 70)
    print("🧬 CONSTRUCTION DES DNA...")
    
    teams_dna = build_teams_context_dna(all_data)
    players_dna = build_players_impact_dna(all_data)
    gamestate_insights = build_gamestate_insights(teams_dna)
    exploit_profiles = build_team_exploit_profiles(teams_dna)
    # [DÉSACTIVÉ 2025-12-23] Remplacé par GoalsIngestionService
    #     all_goals = build_all_goals(all_data)
    all_goals = []  # Placeholder - géré par GoalsIngestionService
    
    print(f"   ✅ Teams DNA: {len(teams_dna)} équipes")
    print(f"   ✅ Players DNA: {len(players_dna)} joueurs")
    print(f"   ✅ Gamestate Insights: {len(gamestate_insights)} équipes")
    print(f"   ✅ Exploit Profiles: {len(exploit_profiles)} équipes")
    # [DÉSACTIVÉ] print(f"   ✅ All Goals: {len(all_goals)} buts")
    # 3. Nettoyer raw_history avant sauvegarde (trop volumineux)
    teams_dna_clean = {}
    for team, data in teams_dna.items():
        clean_data = {k: v for k, v in data.items() if k != 'raw_history'}
        teams_dna_clean[team] = clean_data
    
    # 4. Sauvegarder
    print("\n💾 SAUVEGARDE...")
    
    files_to_save = [
        (QUANTUM_DIR / 'teams_context_dna.json', teams_dna_clean),
        (QUANTUM_DIR / 'players_impact_dna.json', players_dna),
        (QUANTUM_DIR / 'gamestate_insights.json', gamestate_insights),
        (QUANTUM_DIR / 'team_exploit_profiles.json', exploit_profiles),
        (QUANTUM_DIR / 'understat_raw_api.json', all_data),
        # [DÉSACTIVÉ] (GOAL_DIR / 'all_goals_2025.json', all_goals),  # Géré par GoalsIngestionService
    ]
    
    for filepath, data in files_to_save:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        size = filepath.stat().st_size / 1024
        print(f"   ✅ {filepath.name} ({size:.1f} KB)")
    
    print("\n" + "=" * 70)
    print("🎉 MISE À JOUR COMPLÈTE TERMINÉE!")
    print("=" * 70)
    
    return all_data

if __name__ == "__main__":
    main()
