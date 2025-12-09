#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 QUANTUM DATA EXTRACTOR V2.0 - NIVEAU INSTITUTIONNEL                      ║
║  Extraction COMPLÈTE de toutes les données Understat                         ║
║                                                                              ║
║  NOUVELLES DIMENSIONS:                                                       ║
║  ├── Context DNA: gameState, formation, attackSpeed                          ║
║  ├── Player Impact DNA: xGChain, xGBuildup par joueur                        ║
║  ├── Attack Pattern DNA: lastAction, shotZone, X/Y positions                 ║
║  ├── Defender DNA: Stats défensives individuelles                            ║
║  └── Momentum DNA: History match-by-match                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
import re
import time
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import numpy as np

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

DATA_DIR = Path('/home/Mon_ps/data/quantum_v2')
DATA_DIR.mkdir(parents=True, exist_ok=True)

LEAGUES = {
    'EPL': 'EPL',
    'La_Liga': 'La_liga', 
    'Bundesliga': 'Bundesliga',
    'Serie_A': 'Serie_A',
    'Ligue_1': 'Ligue_1'
}

SEASON = '2025'  # 2025 = saison 2025/2026

def extract_json_var(html: str, var_name: str):
    """Extrait une variable JSON du HTML"""
    pattern = rf"var\s+{var_name}\s*=\s*JSON\.parse\('(.+?)'\)"
    match = re.search(pattern, html)
    if match:
        json_str = match.group(1).encode().decode('unicode_escape')
        return json.loads(json_str)
    return None

def fetch_page(url: str, retries: int = 3) -> str:
    """Fetch une page avec retry"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"   ❌ Erreur après {retries} tentatives: {e}")
                return None
    return None

def scrape_team_statistics(team_name: str, team_id: str) -> dict:
    """Scrape statisticsData complet d'une équipe"""
    url = f"https://understat.com/team/{team_name}/{SEASON}"
    html = fetch_page(url)
    
    if not html:
        return None
    
    statistics = extract_json_var(html, 'statisticsData')
    players = extract_json_var(html, 'playersData')
    dates = extract_json_var(html, 'datesData')
    
    return {
        'statistics': statistics,
        'players': players,
        'matches': dates
    }

def scrape_league_data(league: str) -> dict:
    """Scrape toutes les données d'une ligue"""
    url = f"https://understat.com/league/{league}/{SEASON}"
    html = fetch_page(url)
    
    if not html:
        return None
    
    teams_data = extract_json_var(html, 'teamsData')
    players_data = extract_json_var(html, 'playersData')
    dates_data = extract_json_var(html, 'datesData')
    
    return {
        'teams': teams_data,
        'players': players_data,
        'matches': dates_data
    }

def scrape_player_detailed(player_id: str) -> dict:
    """Scrape les données détaillées d'un joueur"""
    url = f"https://understat.com/player/{player_id}"
    html = fetch_page(url)
    
    if not html:
        return None
    
    groups = extract_json_var(html, 'groupsData')
    matches = extract_json_var(html, 'matchesData')
    shots = extract_json_var(html, 'shotsData')
    
    return {
        'groups': groups,
        'matches': matches,
        'shots': shots
    }

def calculate_context_dna(statistics: dict) -> dict:
    """Calcule le Context DNA depuis statisticsData"""
    if not statistics:
        return {}
    
    context_dna = {
        'gameState': {},
        'formation': {},
        'attackSpeed': {},
        'shotZone': {}
    }
    
    # === GAME STATE DNA ===
    # Comment l'équipe performe selon le score
    if 'gameState' in statistics:
        for state, data in statistics['gameState'].items():
            against = data.get('against', {})
            time_played = float(data.get('time', 1))
            
            # Normaliser par 90 minutes
            xG_for_90 = float(data.get('xG', 0)) / time_played * 90 if time_played > 0 else 0
            xG_against_90 = float(against.get('xG', 0)) / time_played * 90 if time_played > 0 else 0
            goals_for_90 = float(data.get('goals', 0)) / time_played * 90 if time_played > 0 else 0
            goals_against_90 = float(against.get('goals', 0)) / time_played * 90 if time_played > 0 else 0
            
            context_dna['gameState'][state] = {
                'time': time_played,
                'xG_for_90': round(xG_for_90, 3),
                'xG_against_90': round(xG_against_90, 3),
                'goals_for_90': round(goals_for_90, 3),
                'goals_against_90': round(goals_against_90, 3),
                'net_xG_90': round(xG_for_90 - xG_against_90, 3),
                'shots_for': int(data.get('shots', 0)),
                'shots_against': int(against.get('shots', 0))
            }
    
    # === FORMATION DNA ===
    # Performance par système tactique
    if 'formation' in statistics:
        for formation, data in statistics['formation'].items():
            against = data.get('against', {})
            time_played = float(data.get('time', 1))
            
            if time_played < 45:  # Ignorer formations avec peu de temps
                continue
            
            xG_for_90 = float(data.get('xG', 0)) / time_played * 90 if time_played > 0 else 0
            xG_against_90 = float(against.get('xG', 0)) / time_played * 90 if time_played > 0 else 0
            
            context_dna['formation'][formation] = {
                'time': time_played,
                'xG_for_90': round(xG_for_90, 3),
                'xG_against_90': round(xG_against_90, 3),
                'net_xG_90': round(xG_for_90 - xG_against_90, 3),
                'goals_for': int(data.get('goals', 0)),
                'goals_against': int(against.get('goals', 0)),
                'defensive_rating': round(2.0 - xG_against_90, 3)  # Plus c'est haut, meilleure est la défense
            }
    
    # === ATTACK SPEED DNA ===
    # Vulnérabilité par vitesse d'attaque
    if 'attackSpeed' in statistics:
        for speed, data in statistics['attackSpeed'].items():
            against = data.get('against', {})
            
            total_shots_against = int(against.get('shots', 0))
            total_goals_against = int(against.get('goals', 0))
            total_xG_against = float(against.get('xG', 0))
            
            context_dna['attackSpeed'][speed] = {
                'shots_for': int(data.get('shots', 0)),
                'shots_against': total_shots_against,
                'goals_for': int(data.get('goals', 0)),
                'goals_against': total_goals_against,
                'xG_for': round(float(data.get('xG', 0)), 3),
                'xG_against': round(total_xG_against, 3),
                'conversion_against': round(total_goals_against / total_shots_against * 100, 1) if total_shots_against > 0 else 0
            }
    
    # === SHOT ZONE DNA ===
    # Zones de vulnérabilité
    if 'shotZone' in statistics:
        for zone, data in statistics['shotZone'].items():
            against = data.get('against', {})
            
            context_dna['shotZone'][zone] = {
                'shots_for': int(data.get('shots', 0)),
                'shots_against': int(against.get('shots', 0)),
                'goals_for': int(data.get('goals', 0)),
                'goals_against': int(against.get('goals', 0)),
                'xG_for': round(float(data.get('xG', 0)), 3),
                'xG_against': round(float(against.get('xG', 0)), 3)
            }
    
    return context_dna

def calculate_player_impact_dna(players: list) -> dict:
    """Calcule le Player Impact DNA depuis playersData"""
    if not players:
        return {}
    
    player_impacts = {}
    
    for player in players:
        player_id = player.get('id')
        position = player.get('position', '')
        time_played = int(player.get('time', 0))
        
        if time_played < 200:  # Minimum 200 minutes
            continue
        
        # Métriques par 90 minutes
        games = float(player.get('games', 1))
        time_90 = time_played / 90
        
        player_impacts[player_id] = {
            'name': player.get('player_name'),
            'position': position,
            'games': int(games),
            'time': time_played,
            
            # Stats offensives
            'goals': int(player.get('goals', 0)),
            'xG': round(float(player.get('xG', 0)), 3),
            'npg': int(player.get('npg', 0)),  # Non-penalty goals
            'npxG': round(float(player.get('npxG', 0)), 3),
            'shots': int(player.get('shots', 0)),
            
            # Stats créatives
            'assists': int(player.get('assists', 0)),
            'xA': round(float(player.get('xA', 0)), 3),
            'key_passes': int(player.get('key_passes', 0)),
            
            # MÉTRIQUES AVANCÉES (PÉPITES!)
            'xGChain': round(float(player.get('xGChain', 0)), 3),  # Implication dans les actions de but
            'xGBuildup': round(float(player.get('xGBuildup', 0)), 3),  # Contribution au jeu construit
            
            # Par 90 minutes
            'goals_90': round(int(player.get('goals', 0)) / time_90, 3) if time_90 > 0 else 0,
            'xG_90': round(float(player.get('xG', 0)) / time_90, 3) if time_90 > 0 else 0,
            'xA_90': round(float(player.get('xA', 0)) / time_90, 3) if time_90 > 0 else 0,
            'xGChain_90': round(float(player.get('xGChain', 0)) / time_90, 3) if time_90 > 0 else 0,
            'xGBuildup_90': round(float(player.get('xGBuildup', 0)) / time_90, 3) if time_90 > 0 else 0,
            
            # Cartons
            'yellow_cards': int(player.get('yellow_cards', 0)),
            'red_cards': int(player.get('red_cards', 0)),
            
            # Ratios
            'goals_xG_ratio': round(int(player.get('goals', 0)) / float(player.get('xG', 0.001)), 2) if float(player.get('xG', 0)) > 0 else 0,
            'shot_accuracy': round(int(player.get('goals', 0)) / int(player.get('shots', 1)) * 100, 1) if int(player.get('shots', 0)) > 0 else 0
        }
        
        # Tags de profil
        tags = []
        
        # Attaquant
        if 'F' in position:
            if player_impacts[player_id]['goals_xG_ratio'] >= 1.2:
                tags.append('CLINICAL_FINISHER')
            elif player_impacts[player_id]['goals_xG_ratio'] <= 0.8:
                tags.append('UNDERPERFORMER')
            
            if player_impacts[player_id]['xG_90'] >= 0.5:
                tags.append('HIGH_VOLUME_SHOOTER')
        
        # Milieu/Créateur
        if 'M' in position or 'S' in position:
            if player_impacts[player_id]['xA_90'] >= 0.25:
                tags.append('ELITE_CREATOR')
            if player_impacts[player_id]['xGChain_90'] >= 0.6:
                tags.append('CHAIN_CONNECTOR')
            if player_impacts[player_id]['xGBuildup_90'] >= 0.4:
                tags.append('BUILDUP_MAESTRO')
        
        # Défenseur
        if 'D' in position:
            if player_impacts[player_id]['xGChain_90'] >= 0.2:
                tags.append('OFFENSIVE_DEFENDER')
            if player_impacts[player_id]['yellow_cards'] >= 5:
                tags.append('CARD_PRONE')
        
        player_impacts[player_id]['tags'] = tags
    
    return player_impacts

def calculate_momentum_dna(matches: list) -> dict:
    """Calcule le Momentum DNA depuis l'historique des matchs"""
    if not matches:
        return {}
    
    # Filtrer les matchs joués
    played_matches = [m for m in matches if m.get('isResult')]
    
    if len(played_matches) < 3:
        return {}
    
    # Calculer la forme récente (5 derniers matchs)
    recent = played_matches[:5]
    
    results = []
    xG_for = []
    xG_against = []
    goals_for = []
    goals_against = []
    
    for match in recent:
        result = match.get('result', 'd')
        results.append(result)
        
        side = match.get('side', 'h')
        goals = match.get('goals', {})
        xG = match.get('xG', {})
        
        if side == 'h':
            goals_for.append(int(goals.get('h', 0)))
            goals_against.append(int(goals.get('a', 0)))
            xG_for.append(float(xG.get('h', 0)))
            xG_against.append(float(xG.get('a', 0)))
        else:
            goals_for.append(int(goals.get('a', 0)))
            goals_against.append(int(goals.get('h', 0)))
            xG_for.append(float(xG.get('a', 0)))
            xG_against.append(float(xG.get('h', 0)))
    
    # Points forme
    form_points = sum([3 if r == 'w' else 1 if r == 'd' else 0 for r in results])
    max_points = len(results) * 3
    
    momentum_dna = {
        'form_last_5': ''.join(['W' if r == 'w' else 'D' if r == 'd' else 'L' for r in results]),
        'form_points': form_points,
        'form_percentage': round(form_points / max_points * 100, 1) if max_points > 0 else 0,
        
        'avg_goals_for': round(np.mean(goals_for), 2),
        'avg_goals_against': round(np.mean(goals_against), 2),
        'avg_xG_for': round(np.mean(xG_for), 2),
        'avg_xG_against': round(np.mean(xG_against), 2),
        
        'clean_sheets_last_5': sum(1 for g in goals_against if g == 0),
        'failed_to_score_last_5': sum(1 for g in goals_for if g == 0),
        
        # Tendance
        'trending': 'UP' if form_points >= 10 else 'STABLE' if form_points >= 6 else 'DOWN',
        
        # xG Performance
        'xG_overperformance': round(sum(goals_for) - sum(xG_for), 2),
        'xGA_overperformance': round(sum(xG_against) - sum(goals_against), 2)
    }
    
    return momentum_dna

def main():
    print("=" * 80)
    print("🧬 QUANTUM DATA EXTRACTOR V2.0 - NIVEAU INSTITUTIONNEL")
    print("   Extraction COMPLÈTE de toutes les données Understat")
    print("=" * 80)
    
    all_teams_data = {}
    all_players_data = {}
    
    for league_name, league_code in LEAGUES.items():
        print(f"\n{'='*60}")
        print(f"🏆 LIGUE: {league_name}")
        print(f"{'='*60}")
        
        # 1. Scraper les données de la ligue
        print(f"\n📥 Téléchargement données ligue...")
        league_data = scrape_league_data(league_code)
        
        if not league_data:
            print(f"   ❌ Impossible de récupérer {league_name}")
            continue
        
        teams = league_data.get('teams', {})
        players = league_data.get('players', [])
        
        print(f"   ✅ {len(teams)} équipes | {len(players)} joueurs")
        
        # Stocker les joueurs de la ligue
        for player in players:
            player_id = player.get('id')
            player['league'] = league_name
            all_players_data[player_id] = player
        
        # 2. Pour chaque équipe, récupérer statisticsData
        team_count = 0
        for team_id, team_info in teams.items():
            team_name = team_info.get('title', '')
            team_name_url = team_name.replace(' ', '_')
            
            print(f"\n   📊 {team_name}...", end=' ')
            
            team_data = scrape_team_statistics(team_name_url, team_id)
            time.sleep(0.5)  # Rate limiting
            
            if not team_data:
                print("❌")
                continue
            
            # Calculer les DNA
            statistics = team_data.get('statistics', {})
            team_players = team_data.get('players', [])
            matches = team_data.get('matches', [])
            
            context_dna = calculate_context_dna(statistics)
            player_impact_dna = calculate_player_impact_dna(team_players)
            momentum_dna = calculate_momentum_dna(matches)
            
            all_teams_data[team_name] = {
                'id': team_id,
                'league': league_name,
                'context_dna': context_dna,
                'player_impact_dna': player_impact_dna,
                'momentum_dna': momentum_dna,
                'raw_statistics': statistics,
                'history': team_info.get('history', [])
            }
            
            team_count += 1
            
            # Résumé rapide
            form = momentum_dna.get('form_last_5', '?????')
            best_formation = max(context_dna.get('formation', {}).items(), 
                               key=lambda x: x[1].get('net_xG_90', 0), default=('?', {}))
            
            print(f"✅ Forme: {form} | Best: {best_formation[0]}")
        
        print(f"\n   📊 {team_count} équipes traitées pour {league_name}")
    
    # 3. Sauvegarder les données
    print("\n" + "=" * 80)
    print("💾 SAUVEGARDE DES DONNÉES")
    print("=" * 80)
    
    # Teams Context DNA
    with open(DATA_DIR / 'teams_context_dna.json', 'w') as f:
        json.dump(all_teams_data, f, indent=2, ensure_ascii=False)
    print(f"   ✅ {DATA_DIR / 'teams_context_dna.json'} ({len(all_teams_data)} équipes)")
    
    # Players Impact DNA
    with open(DATA_DIR / 'players_impact_dna.json', 'w') as f:
        json.dump(all_players_data, f, indent=2, ensure_ascii=False)
    print(f"   ✅ {DATA_DIR / 'players_impact_dna.json'} ({len(all_players_data)} joueurs)")
    
    # 4. Rapport
    print("\n" + "=" * 80)
    print("📊 RAPPORT EXTRACTION")
    print("=" * 80)
    
    print(f"\n   📁 Total équipes: {len(all_teams_data)}")
    print(f"   📁 Total joueurs: {len(all_players_data)}")
    
    # Top joueurs par xGChain/90
    print("\n🔥 TOP 10 JOUEURS PAR xGChain/90 (Implication offensive):")
    sorted_players = sorted(
        [(p['player_name'], p.get('xGChain', 0) / (p.get('time', 1) / 90), p.get('team_title', ''))
         for p in all_players_data.values() if int(p.get('time', 0)) >= 500],
        key=lambda x: x[1], reverse=True
    )[:10]
    
    for i, (name, xgc90, team) in enumerate(sorted_players, 1):
        print(f"   {i:2}. {name:<25} ({team:<20}) | xGChain/90: {xgc90:.3f}")
    
    # Top équipes par forme
    print("\n🔥 TOP 10 ÉQUIPES PAR FORME RÉCENTE:")
    sorted_teams = sorted(
        [(name, data['momentum_dna'].get('form_percentage', 0), data['momentum_dna'].get('form_last_5', '?'))
         for name, data in all_teams_data.items() if data.get('momentum_dna')],
        key=lambda x: x[1], reverse=True
    )[:10]
    
    for i, (name, pct, form) in enumerate(sorted_teams, 1):
        print(f"   {i:2}. {name:<25} | {form} ({pct:.0f}%)")
    
    # Équipes vulnérables aux Fast attacks
    print("\n🎯 ÉQUIPES VULNÉRABLES AUX CONTRE-ATTAQUES (Fast):")
    fast_vulnerable = []
    for name, data in all_teams_data.items():
        fast = data.get('context_dna', {}).get('attackSpeed', {}).get('Fast', {})
        if fast.get('shots_against', 0) >= 5:
            conversion = fast.get('conversion_against', 0)
            fast_vulnerable.append((name, conversion, fast.get('goals_against', 0), fast.get('shots_against', 0)))
    
    fast_vulnerable.sort(key=lambda x: x[1], reverse=True)
    for name, conv, goals, shots in fast_vulnerable[:10]:
        print(f"   • {name:<25} | {conv:.1f}% conversion ({goals}/{shots})")
    
    print(f"\n{'='*80}")
    print(f"✅ QUANTUM DATA EXTRACTOR V2.0 COMPLET")
    print(f"   {len(all_teams_data)} équipes | {len(all_players_data)} joueurs")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
