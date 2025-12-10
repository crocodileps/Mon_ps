#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🚀 UNDERSTAT API SCRAPER V2.0 - DIRECT API ACCESS                          ║
║  API découverte: /getLeagueData/{league}/{season}                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
from pathlib import Path
from datetime import datetime
import time

# Headers CRITIQUES - doivent inclure X-Requested-With
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://understat.com/'
}

DATA_DIR = Path('/home/Mon_ps/data/quantum_v2')
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Noms EXACTS des ligues Understat
LEAGUES = {
    'EPL': 'Premier League',
    'La_liga': 'La Liga', 
    'Bundesliga': 'Bundesliga',
    'Serie_A': 'Serie A',
    'Ligue_1': 'Ligue 1'
}

SEASON = '2025'  # 2025 = saison 2025/2026

def fetch_league_data(league: str) -> dict:
    """Fetch toutes les données d'une ligue via l'API directe"""
    url = f"https://understat.com/getLeagueData/{league}/{SEASON}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200 and len(response.text) > 1000:
            return response.json()
        else:
            print(f"   ⚠️ {league}: Status {response.status_code}, Size {len(response.text)}")
            return None
    except Exception as e:
        print(f"   ❌ Erreur {league}: {e}")
        return None

def build_teams_context_dna(all_data: dict) -> dict:
    """Construit le teams_context_dna enrichi"""
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
            
            # Stats agrégées
            total_xg = sum(float(m.get('xG', 0)) for m in history)
            total_xga = sum(float(m.get('xGA', 0)) for m in history)
            total_npxg = sum(float(m.get('npxG', 0)) for m in history)
            total_npxga = sum(float(m.get('npxGA', 0)) for m in history)
            total_deep = sum(int(m.get('deep', 0)) for m in history)
            total_scored = sum(int(m.get('scored', 0)) for m in history)
            total_missed = sum(int(m.get('missed', 0)) for m in history)  # conceded
            total_wins = sum(1 for m in history if m.get('result') == 'w')
            total_draws = sum(1 for m in history if m.get('result') == 'd')
            total_losses = sum(1 for m in history if m.get('result') == 'l')
            total_pts = sum(int(m.get('pts', 0)) for m in history)
            
            # PPDA (Passes Per Defensive Action) 
            ppda_att = sum(float(m.get('ppda', {}).get('att', 0)) for m in history)
            ppda_def = sum(float(m.get('ppda', {}).get('def', 1)) for m in history)
            ppda = ppda_att / ppda_def if ppda_def > 0 else 10
            
            # Classification pressing
            if ppda < 8:
                pressing_style = "GEGENPRESSING"
            elif ppda < 10:
                pressing_style = "HIGH_PRESS"
            elif ppda < 12:
                pressing_style = "MEDIUM_PRESS"
            else:
                pressing_style = "LOW_BLOCK"
            
            # Momentum (last 5)
            last_5 = history[-5:] if len(history) >= 5 else history
            form = ''.join('W' if m.get('result') == 'w' else 'D' if m.get('result') == 'd' else 'L' for m in last_5)
            
            # xG over/under performance
            xg_diff = total_scored - total_xg
            xga_diff = total_missed - total_xga
            
            teams_dna[team_name] = {
                'team_id': team_id,
                'league': LEAGUES.get(league, league),
                'matches': matches,
                'record': {
                    'wins': total_wins,
                    'draws': total_draws,
                    'losses': total_losses,
                    'points': total_pts,
                    'goals_for': total_scored,
                    'goals_against': total_missed
                },
                'history': {
                    'xg': round(total_xg, 2),
                    'xga': round(total_xga, 2),
                    'npxg': round(total_npxg, 2),
                    'npxga': round(total_npxga, 2),
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
                'updated_at': datetime.now().isoformat()
            }
    
    return teams_dna

def build_players_impact_dna(all_data: dict) -> list:
    """Construit le players_impact_dna"""
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
                'npg': int(player.get('npg', 0)),
                'key_passes': int(player.get('key_passes', 0)),
                'shots': int(player.get('shots', 0)),
            })
    
    return sorted(players, key=lambda x: x['xG'], reverse=True)

def main():
    print("=" * 70)
    print("🚀 UNDERSTAT API SCRAPER V2.0")
    print(f"   Season: {SEASON} | Leagues: {len(LEAGUES)}")
    print(f"   Output: {DATA_DIR}")
    print("=" * 70)
    
    all_data = {}
    
    # 1. Fetch toutes les ligues
    for league_code, league_name in LEAGUES.items():
        print(f"\n📥 {league_name} ({league_code})...")
        data = fetch_league_data(league_code)
        
        if data:
            teams_count = len(data.get('teams', {}))
            players_count = len(data.get('players', []))
            matches_count = len(data.get('dates', []))
            print(f"   ✅ {teams_count} teams | {players_count} players | {matches_count} matches")
            all_data[league_code] = data
        else:
            print(f"   ❌ Failed")
        
        time.sleep(2)  # Rate limit respectueux
    
    # 2. Construire les DNAs
    print("\n" + "=" * 70)
    print("🧬 CONSTRUCTION DES DNA...")
    
    teams_dna = build_teams_context_dna(all_data)
    players_dna = build_players_impact_dna(all_data)
    
    print(f"   ✅ Teams DNA: {len(teams_dna)} équipes")
    print(f"   ✅ Players DNA: {len(players_dna)} joueurs")
    
    # 3. Sauvegarder
    print("\n💾 SAUVEGARDE...")
    
    # Backup ancien fichier
    old_file = DATA_DIR / 'teams_context_dna.json'
    if old_file.exists():
        backup = DATA_DIR / f'teams_context_dna_backup_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
        old_file.rename(backup)
        print(f"   📦 Backup: {backup.name}")
    
    with open(DATA_DIR / 'teams_context_dna.json', 'w') as f:
        json.dump(teams_dna, f, indent=2, default=str)
    print(f"   ✅ teams_context_dna.json ({len(teams_dna)} teams)")
    
    with open(DATA_DIR / 'players_impact_dna.json', 'w') as f:
        json.dump(players_dna, f, indent=2)
    print(f"   ✅ players_impact_dna.json ({len(players_dna)} players)")
    
    with open(DATA_DIR / 'understat_raw_api.json', 'w') as f:
        json.dump(all_data, f)
    print(f"   ✅ understat_raw_api.json (raw backup)")
    
    # 4. Stats finales
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ PAR LIGUE:")
    for league, data in all_data.items():
        if data:
            print(f"   {LEAGUES.get(league, league):15} | {len(data.get('teams', {})):2} teams | {len(data.get('players', [])):4} players")
    
    print("\n🎉 MISE À JOUR TERMINÉE!")
    print("=" * 70)

if __name__ == "__main__":
    main()
