#!/usr/bin/env python3
"""
DIAGNOSTIC: Trouver les noms exacts des équipes qui ont échoué
"""

import requests
import re
import json

def test_team_url(team_name: str, season: str = '2025'):
    """Test si une URL d'équipe fonctionne"""
    url = f"https://understat.com/team/{team_name}/{season}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            # Vérifier si on a des données
            if 'datesData' in response.text:
                return True, "OK - Data found"
            else:
                return False, "Page exists but no data"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def get_all_teams_from_league(league: str, season: str = '2025'):
    """Récupère la liste des équipes d'une ligue depuis Understat"""
    url = f"https://understat.com/league/{league}/{season}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            # Extraire teamsData
            pattern = r"var teamsData\s*=\s*JSON\.parse\('(.+?)'\)"
            match = re.search(pattern, response.text)
            if match:
                json_str = match.group(1).encode().decode('unicode_escape')
                teams_data = json.loads(json_str)
                return {team_id: data['title'] for team_id, data in teams_data.items()}
        return {}
    except Exception as e:
        print(f"Error: {e}")
        return {}

# Équipes qui ont échoué
failed_teams = [
    ('Valladolid', 'La_Liga'),
    ('FC_Koln', 'Bundesliga'),
    ('Heidenheim', 'Bundesliga'),
    ('AS_Roma', 'Serie_A'),
]

print("=" * 70)
print("🔬 DIAGNOSTIC DES ÉQUIPES QUI ONT ÉCHOUÉ")
print("=" * 70)

# Test des noms actuels
print("\n📊 TEST DES NOMS ACTUELS:")
for team, league in failed_teams:
    success, msg = test_team_url(team, '2025')
    status = "✅" if success else "❌"
    print(f"   {status} {team}: {msg}")

# Récupérer les vrais noms depuis Understat
print("\n📊 RÉCUPÉRATION DES VRAIS NOMS DEPUIS UNDERSTAT:")

leagues_to_check = {
    'La_Liga': 'La_liga',
    'Bundesliga': 'Bundesliga', 
    'Serie_A': 'Serie_A'
}

for league_key, league_url in leagues_to_check.items():
    print(f"\n🔍 {league_key}:")
    teams = get_all_teams_from_league(league_url, '2025')
    if teams:
        for team_id, team_name in sorted(teams.items(), key=lambda x: x[1]):
            # Convertir en format URL
            url_name = team_name.replace(' ', '_')
            print(f"   • {team_name} → {url_name}")
    else:
        print(f"   ❌ Impossible de récupérer les équipes")

# Test des variantes possibles
print("\n📊 TEST DES VARIANTES POSSIBLES:")
variants = [
    # Valladolid
    ('Real_Valladolid', 'La_Liga'),
    ('Valladolid', 'La_Liga'),
    # Koln
    ('FC_Koln', 'Bundesliga'),
    ('Koln', 'Bundesliga'),
    ('FC_Cologne', 'Bundesliga'),
    ('Cologne', 'Bundesliga'),
    # Heidenheim
    ('Heidenheim', 'Bundesliga'),
    ('FC_Heidenheim', 'Bundesliga'),
    ('1._FC_Heidenheim', 'Bundesliga'),
    # Roma
    ('AS_Roma', 'Serie_A'),
    ('Roma', 'Serie_A'),
]

for team, league in variants:
    success, msg = test_team_url(team, '2025')
    status = "✅" if success else "❌"
    print(f"   {status} {team}: {msg}")

