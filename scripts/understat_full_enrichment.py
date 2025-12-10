#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 UNDERSTAT FULL ENRICHMENT V2.0                                           ║
║  Utilise /getTeamData/ pour récupérer TOUTES les statistiques détaillées     ║
║                                                                              ║
║  Données extraites:                                                          ║
║  ├── context_dna.formation (temps joué, xG par formation)                    ║
║  ├── context_dna.gameState (xG selon le score)                               ║
║  ├── context_dna.timing (xG par période 1-15, 16-30, etc.)                   ║
║  ├── context_dna.shotZone (zones de tir)                                     ║
║  ├── context_dna.attackSpeed (vitesse d'attaque)                             ║
║  └── context_dna.situation (OpenPlay, SetPiece, etc.)                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
from pathlib import Path
from datetime import datetime
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://understat.com/'
}

QUANTUM_DIR = Path('/home/Mon_ps/data/quantum_v2')
SEASON = '2025'

# Mapping équipes DB → Understat URL format
TEAM_URL_MAPPING = {
    # Premier League
    "Manchester City": "Manchester_City",
    "Manchester United": "Manchester_United",
    "Arsenal": "Arsenal",
    "Liverpool": "Liverpool",
    "Chelsea": "Chelsea",
    "Tottenham": "Tottenham",
    "Newcastle United": "Newcastle_United",
    "Brighton": "Brighton",
    "Aston Villa": "Aston_Villa",
    "West Ham": "West_Ham",
    "Brentford": "Brentford",
    "Fulham": "Fulham",
    "Crystal Palace": "Crystal_Palace",
    "Wolverhampton Wanderers": "Wolverhampton_Wanderers",
    "Everton": "Everton",
    "Nottingham Forest": "Nottingham_Forest",
    "Bournemouth": "Bournemouth",
    "Leicester": "Leicester",
    "Southampton": "Southampton",
    "Ipswich": "Ipswich",
    # La Liga
    "Barcelona": "Barcelona",
    "Real Madrid": "Real_Madrid",
    "Atletico Madrid": "Atletico_Madrid",
    "Athletic Club": "Athletic_Club",
    "Real Sociedad": "Real_Sociedad",
    "Real Betis": "Real_Betis",
    "Villarreal": "Villarreal",
    "Sevilla": "Sevilla",
    "Valencia": "Valencia",
    "Girona": "Girona",
    "Getafe": "Getafe",
    "Osasuna": "Osasuna",
    "Celta Vigo": "Celta_Vigo",
    "Mallorca": "Mallorca",
    "Las Palmas": "Las_Palmas",
    "Rayo Vallecano": "Rayo_Vallecano",
    "Alaves": "Alaves",
    "Espanyol": "Espanyol",
    "Valladolid": "Valladolid",
    "Leganes": "Leganes",
    # Serie A
    "Inter": "Inter",
    "AC Milan": "AC_Milan",
    "Juventus": "Juventus",
    "Napoli": "Napoli",
    "Lazio": "Lazio",
    "Roma": "Roma",
    "Atalanta": "Atalanta",
    "Fiorentina": "Fiorentina",
    "Bologna": "Bologna",
    "Torino": "Torino",
    "Monza": "Monza",
    "Udinese": "Udinese",
    "Empoli": "Empoli",
    "Cagliari": "Cagliari",
    "Verona": "Verona",
    "Lecce": "Lecce",
    "Genoa": "Genoa",
    "Como": "Como",
    "Parma": "Parma",
    "Venezia": "Venezia",
    # Bundesliga
    "Bayern Munich": "Bayern_Munich",
    "Bayer Leverkusen": "Bayer_Leverkusen",
    "Borussia Dortmund": "Borussia_Dortmund",
    "RB Leipzig": "RasenBallsport_Leipzig",
    "Eintracht Frankfurt": "Eintracht_Frankfurt",
    "VfB Stuttgart": "VfB_Stuttgart",
    "Freiburg": "Freiburg",
    "Wolfsburg": "Wolfsburg",
    "Borussia M.Gladbach": "Borussia_M.Gladbach",
    "Werder Bremen": "Werder_Bremen",
    "Mainz 05": "Mainz_05",
    "FC Augsburg": "Augsburg",
    "Hoffenheim": "Hoffenheim",
    "Union Berlin": "Union_Berlin",
    "Bochum": "Bochum",
    "St. Pauli": "St._Pauli",
    "Holstein Kiel": "Holstein_Kiel",
    "Heidenheim": "Heidenheim",
    # Ligue 1
    "Paris Saint Germain": "Paris_Saint_Germain",
    "Monaco": "Monaco",
    "Marseille": "Marseille",
    "Lille": "Lille",
    "Lyon": "Lyon",
    "Nice": "Nice",
    "Lens": "Lens",
    "Rennes": "Rennes",
    "Strasbourg": "Strasbourg",
    "Toulouse": "Toulouse",
    "Reims": "Reims",
    "Auxerre": "Auxerre",
    "Nantes": "Nantes",
    "Angers": "Angers",
    "Le Havre": "Le_Havre",
    "Montpellier": "Montpellier",
    "Saint-Etienne": "Saint-Etienne",
    "Brest": "Brest",
}

def fetch_team_data(team_url: str) -> dict:
    """Fetch données détaillées d'une équipe"""
    url = f"https://understat.com/getTeamData/{team_url}/{SEASON}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200 and len(response.text) > 100:
            return response.json()
    except Exception as e:
        pass
    return None

def process_statistics(stats: dict) -> dict:
    """Transforme les statistiques brutes en context_dna"""
    context_dna = {}
    
    # Formation DNA
    if 'formation' in stats:
        formations = {}
        for formation, data in stats['formation'].items():
            time_played = float(data.get('time', 0))
            xg = float(data.get('xG', 0))
            xga = float(data.get('against', {}).get('xG', 0))
            
            formations[formation] = {
                'time': int(time_played),
                'xG': round(xg, 3),
                'xGA': round(xga, 3),
                'xG_90': round(xg / time_played * 90, 3) if time_played > 0 else 0,
                'xGA_90': round(xga / time_played * 90, 3) if time_played > 0 else 0,
                'goals': int(data.get('goals', 0)),
                'conceded': int(data.get('against', {}).get('goals', 0)),
            }
        context_dna['formation'] = formations
    
    # GameState DNA
    if 'gameState' in stats:
        gamestates = {}
        for state, data in stats['gameState'].items():
            time_played = float(data.get('time', 0))
            xg = float(data.get('xG', 0))
            xga = float(data.get('against', {}).get('xG', 0))
            
            gamestates[state] = {
                'time': int(time_played),
                'xG': round(xg, 3),
                'xGA': round(xga, 3),
                'xG_90': round(xg / time_played * 90, 3) if time_played > 0 else 0,
                'xGA_90': round(xga / time_played * 90, 3) if time_played > 0 else 0,
            }
        context_dna['gameState'] = gamestates
    
    # Timing DNA
    if 'timing' in stats:
        timing = {}
        for period, data in stats['timing'].items():
            timing[period] = {
                'shots': int(data.get('shots', 0)),
                'goals': int(data.get('goals', 0)),
                'xG': round(float(data.get('xG', 0)), 3),
                'conceded': int(data.get('against', {}).get('goals', 0)),
                'xGA': round(float(data.get('against', {}).get('xG', 0)), 3),
            }
        context_dna['timing'] = timing
    
    # AttackSpeed DNA
    if 'attackSpeed' in stats:
        speeds = {}
        for speed, data in stats['attackSpeed'].items():
            speeds[speed] = {
                'shots': int(data.get('shots', 0)),
                'goals': int(data.get('goals', 0)),
                'xG': round(float(data.get('xG', 0)), 3),
            }
        context_dna['attackSpeed'] = speeds
    
    # ShotZone DNA
    if 'shotZone' in stats:
        zones = {}
        for zone, data in stats['shotZone'].items():
            zones[zone] = {
                'shots': int(data.get('shots', 0)),
                'goals': int(data.get('goals', 0)),
                'xG': round(float(data.get('xG', 0)), 3),
            }
        context_dna['shotZone'] = zones
    
    # Situation DNA
    if 'situation' in stats:
        situations = {}
        for situation, data in stats['situation'].items():
            situations[situation] = {
                'shots': int(data.get('shots', 0)),
                'goals': int(data.get('goals', 0)),
                'xG': round(float(data.get('xG', 0)), 3),
                'conceded': int(data.get('against', {}).get('goals', 0)),
                'xGA': round(float(data.get('against', {}).get('xG', 0)), 3),
            }
        context_dna['situation'] = situations
    
    return context_dna

def main():
    print("=" * 70)
    print("🧬 UNDERSTAT FULL ENRICHMENT V2.0")
    print(f"   Équipes: {len(TEAM_URL_MAPPING)} | Season: {SEASON}")
    print("=" * 70)
    
    # Charger le teams_context_dna existant
    teams_dna_path = QUANTUM_DIR / 'teams_context_dna.json'
    with open(teams_dna_path) as f:
        teams_dna = json.load(f)
    
    print(f"\n📥 Enrichissement de {len(teams_dna)} équipes...")
    
    enriched = 0
    failed = []
    
    for team_name in teams_dna.keys():
        # Trouver l'URL Understat
        team_url = TEAM_URL_MAPPING.get(team_name)
        
        if not team_url:
            # Essayer de deviner
            team_url = team_name.replace(' ', '_')
        
        print(f"   {team_name:25}", end=" → ")
        
        data = fetch_team_data(team_url)
        
        if data and 'statistics' in data:
            context_dna = process_statistics(data['statistics'])
            teams_dna[team_name]['context_dna'] = context_dna
            print(f"✅ {len(context_dna)} dimensions")
            enriched += 1
        else:
            print(f"❌ Failed")
            failed.append(team_name)
        
        time.sleep(0.5)  # Rate limiting
    
    # Sauvegarder
    print("\n" + "=" * 70)
    print("💾 SAUVEGARDE...")
    
    with open(teams_dna_path, 'w') as f:
        json.dump(teams_dna, f, indent=2, default=str)
    
    size = teams_dna_path.stat().st_size / 1024
    print(f"   ✅ teams_context_dna.json ({size:.1f} KB)")
    
    print(f"\n📊 RÉSULTATS:")
    print(f"   Enrichies: {enriched}/{len(teams_dna)}")
    print(f"   Échecs: {len(failed)}")
    
    if failed:
        print(f"\n⚠️ Équipes non enrichies:")
        for team in failed[:10]:
            print(f"      - {team}")
    
    print("\n🎉 ENRICHISSEMENT TERMINÉ!")
    print("=" * 70)

if __name__ == "__main__":
    main()
