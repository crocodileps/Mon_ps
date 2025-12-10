#!/usr/bin/env python3
"""
UNDERSTAT SHOTS SCRAPER V2.0
============================
Collecte tous les tirs contre chaque équipe via l'API /getMatchData/
Génère: all_shots_against_2025.json
"""

import requests
import json
import time
import os
from datetime import datetime
from collections import defaultdict

# Configuration
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://understat.com/'
}

LEAGUES = {
    'EPL': 'Premier League',
    'La_liga': 'La Liga', 
    'Bundesliga': 'Bundesliga',
    'Serie_A': 'Serie A',
    'Ligue_1': 'Ligue 1'
}

SEASON = '2025'
BASE_URL = 'https://understat.com'
OUTPUT_DIR = '/home/Mon_ps/data/goalkeeper_dna'

def fetch_json(url, retries=3):
    """Fetch JSON avec retry"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
    return None

def get_played_match_ids(league, season):
    """Récupère les match IDs des matchs joués depuis /getLeagueData/"""
    url = f"{BASE_URL}/getLeagueData/{league}/{season}"
    data = fetch_json(url)
    
    if not data:
        return []
    
    match_ids = []
    dates = data.get('dates', [])
    
    for match in dates:
        # Seulement les matchs joués (isResult=true)
        if match.get('isResult') == True:
            match_ids.append(match['id'])
    
    return match_ids

def get_match_shots(match_id):
    """Récupère les shots d'un match via /getMatchData/"""
    url = f"{BASE_URL}/getMatchData/{match_id}"
    data = fetch_json(url)
    
    if not data or 'shots' not in data:
        return None
    
    return data['shots']

def main():
    print("🎯 UNDERSTAT SHOTS SCRAPER V2.0")
    print("=" * 60)
    print(f"   Season: {SEASON}")
    print(f"   Leagues: {len(LEAGUES)}")
    print(f"   Output: {OUTPUT_DIR}/all_shots_against_{SEASON}.json")
    print()
    
    # Structure: {team_name: [shots against]}
    all_shots_against = defaultdict(list)
    
    # Statistiques
    total_matches = 0
    total_shots = 0
    processed_matches = set()
    
    for league_code, league_name in LEAGUES.items():
        print(f"📥 {league_name}...")
        
        # 1. Récupérer tous les match IDs joués
        match_ids = get_played_match_ids(league_code, SEASON)
        new_matches = [m for m in match_ids if m not in processed_matches]
        
        print(f"   Matchs joués: {len(match_ids)} ({len(new_matches)} nouveaux)")
        
        # 2. Pour chaque match, récupérer les shots
        for i, match_id in enumerate(new_matches):
            shots_data = get_match_shots(match_id)
            
            if not shots_data:
                continue
            
            # Identifier les équipes depuis les shots
            home_team = None
            away_team = None
            
            if shots_data.get('h') and len(shots_data['h']) > 0:
                home_team = shots_data['h'][0].get('h_team')
                away_team = shots_data['h'][0].get('a_team')
            elif shots_data.get('a') and len(shots_data['a']) > 0:
                home_team = shots_data['a'][0].get('h_team')
                away_team = shots_data['a'][0].get('a_team')
            
            if not home_team or not away_team:
                continue
            
            # Shots CONTRE home = shots de away (shots.a)
            for shot in shots_data.get('a', []):
                shot['against_team'] = home_team
                shot['league'] = league_name
                all_shots_against[home_team].append(shot)
                total_shots += 1
            
            # Shots CONTRE away = shots de home (shots.h)
            for shot in shots_data.get('h', []):
                shot['against_team'] = away_team
                shot['league'] = league_name
                all_shots_against[away_team].append(shot)
                total_shots += 1
            
            processed_matches.add(match_id)
            total_matches += 1
            
            # Progress
            if (i + 1) % 50 == 0:
                print(f"      Processed: {i+1}/{len(new_matches)} matchs ({total_shots} tirs)")
            
            # Rate limiting
            time.sleep(0.3)
        
        print(f"   ✅ {league_name}: {len(new_matches)} matchs traités")
    
    # 3. Sauvegarder
    print()
    print("💾 SAUVEGARDE...")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = f"{OUTPUT_DIR}/all_shots_against_{SEASON}.json"
    
    # Convertir en dict standard
    output_data = dict(all_shots_against)
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    file_size = os.path.getsize(output_file) / (1024 * 1024)
    
    print()
    print("=" * 60)
    print("📊 RÉSUMÉ")
    print(f"   Équipes: {len(output_data)}")
    print(f"   Matchs traités: {total_matches}")
    print(f"   Tirs collectés: {total_shots}")
    print(f"   Fichier: {output_file}")
    print(f"   Taille: {file_size:.2f} MB")
    print()
    
    # Top équipes par tirs encaissés
    if output_data:
        print("📋 Top 5 équipes (tirs contre):")
        sorted_teams = sorted(output_data.items(), key=lambda x: len(x[1]), reverse=True)
        for team, shots in sorted_teams[:5]:
            total_xg = sum(float(s.get('xG', 0)) for s in shots)
            print(f"   {team}: {len(shots)} tirs, xG against: {total_xg:.2f}")
    
    print()
    print("🎉 TERMINÉ!")

if __name__ == '__main__':
    main()
