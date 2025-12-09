#!/usr/bin/env python3
"""
🔬 VÉRIFICATION SCIENTIFIQUE: Les données sont-elles vraiment 2025/2026 ?
"""

import requests
import json
import re
from datetime import datetime

def fetch_page(url: str) -> str:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers, timeout=30)
    return response.text if response.status_code == 200 else ""

def extract_json_var(html: str, var_name: str):
    pattern = rf"var {var_name}\s*=\s*JSON\.parse\('(.+?)'\)"
    match = re.search(pattern, html)
    if match:
        json_str = match.group(1).encode().decode('unicode_escape')
        return json.loads(json_str)
    return None

def verify_team_matches(team_url: str, team_name: str):
    """Vérifie les dates des matchs d'une équipe"""
    url = f"https://understat.com/team/{team_url}/2025"
    html = fetch_page(url)
    
    if not html:
        return None
    
    matches = extract_json_var(html, 'datesData')
    if not matches:
        return None
    
    # Analyser les dates
    dates = []
    for match in matches:
        if match.get('isResult'):
            date_str = match.get('datetime', '')
            if date_str:
                dates.append(date_str)
    
    if dates:
        dates.sort()
        return {
            'team': team_name,
            'first_match': dates[0],
            'last_match': dates[-1],
            'total_matches': len(dates)
        }
    return None

# Équipes suspectes à vérifier
suspicious_teams = [
    # EPL - Devraient être en Championship
    ('Leeds', 'Leeds'),
    ('Sunderland', 'Sunderland'),
    ('Burnley', 'Burnley'),
    
    # La Liga - Devraient être en Segunda
    ('Levante', 'Levante'),
    ('Elche', 'Elche'),
    ('Real_Oviedo', 'Real Oviedo'),
    
    # Bundesliga - Devraient être en 2. Bundesliga
    ('Hamburger_SV', 'Hamburger SV'),
    ('FC_Cologne', 'FC Cologne'),
    
    # Serie A - Devraient être en Serie B
    ('Cremonese', 'Cremonese'),
    ('Pisa', 'Pisa'),
    
    # Ligue 1 - Devraient être en Ligue 2
    ('Paris_FC', 'Paris FC'),
    ('Metz', 'Metz'),
    ('Lorient', 'Lorient'),
]

# Équipes légitimes 2025/2026 pour comparaison
legitimate_teams = [
    ('Liverpool', 'Liverpool'),
    ('Arsenal', 'Arsenal'),
    ('Real_Madrid', 'Real Madrid'),
    ('Bayern_Munich', 'Bayern Munich'),
    ('Inter', 'Inter'),
    ('Paris_Saint_Germain', 'PSG'),
]

print("=" * 80)
print("🔬 VÉRIFICATION DES DATES DE MATCHS - SAISON 2025/2026")
print("=" * 80)
print("\nLa saison 2025/2026 commence en AOÛT 2025")
print("Si les matchs sont de 2024 ou avant → MAUVAISE SAISON\n")

print("=" * 80)
print("📊 ÉQUIPES LÉGITIMES (TOP DIVISION 2025/2026)")
print("=" * 80)
for team_url, team_name in legitimate_teams:
    result = verify_team_matches(team_url, team_name)
    if result:
        print(f"   ✅ {result['team']:20} | Premier: {result['first_match'][:10]} | Dernier: {result['last_match'][:10]} | {result['total_matches']} matchs")

print("\n" + "=" * 80)
print("🔍 ÉQUIPES SUSPECTES (Possiblement mauvaise division/saison)")
print("=" * 80)
for team_url, team_name in suspicious_teams:
    result = verify_team_matches(team_url, team_name)
    if result:
        first_year = result['first_match'][:4]
        # Vérifier si c'est bien 2025
        if first_year == '2025':
            status = "✅"
            note = "Dates 2025 OK"
        else:
            status = "❌"
            note = f"MAUVAISE ANNÉE: {first_year}"
        print(f"   {status} {result['team']:20} | Premier: {result['first_match'][:10]} | Dernier: {result['last_match'][:10]} | {note}")
    else:
        print(f"   ❌ {team_name:20} | Pas de données")

# Vérifier la structure de la ligue sur Understat
print("\n" + "=" * 80)
print("🔍 VÉRIFICATION: Que contient Understat pour 'EPL' saison 2025?")
print("=" * 80)

url = "https://understat.com/league/EPL/2025"
html = fetch_page(url)
teams_data = extract_json_var(html, 'teamsData')

if teams_data:
    print(f"\n   Understat EPL/2025 contient {len(teams_data)} équipes:")
    for team_id, data in sorted(teams_data.items(), key=lambda x: x[1]['title']):
        print(f"   • {data['title']}")

# Vérifier quelle est la VRAIE saison actuelle selon Understat
print("\n" + "=" * 80)
print("🔍 QUELLE SAISON EST DISPONIBLE SUR UNDERSTAT?")
print("=" * 80)

for season in ['2024', '2025']:
    url = f"https://understat.com/league/EPL/{season}"
    html = fetch_page(url)
    if html and 'teamsData' in html:
        teams_data = extract_json_var(html, 'teamsData')
        if teams_data:
            # Vérifier les dates
            sample_team = list(teams_data.values())[0]['title'].replace(' ', '_')
            result = verify_team_matches(sample_team, sample_team)
            if result:
                print(f"   Season={season}: {len(teams_data)} équipes | Matchs: {result['first_match'][:10]} → {result['last_match'][:10]}")

