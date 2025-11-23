#!/usr/bin/env python3
"""
Debug : Afficher noms équipes API vs DB
"""
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

API_TOKEN = "d40eee7eea3342179f16636ce9806fff"

DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Récupérer matchs pending de notre DB
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor(cursor_factory=RealDictCursor)

cursor.execute("""
    SELECT DISTINCT home_team, away_team, analyzed_at
    FROM agent_analyses
    WHERE analyzed_at > NOW() - INTERVAL '3 days'
    ORDER BY analyzed_at DESC
    LIMIT 10
""")

db_matches = cursor.fetchall()
conn.close()

print("="*80)
print("📊 MATCHS DANS NOTRE DB (10 derniers)")
print("="*80)
for m in db_matches:
    print(f"{m['home_team']:30} vs {m['away_team']:30} | {m['analyzed_at']}")

# Récupérer matchs de l'API
print("\n" + "="*80)
print("🌐 MATCHS DE L'API FOOTBALL-DATA.ORG")
print("="*80)

date_to = datetime.now().strftime('%Y-%m-%d')
date_from = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')

leagues = {'Premier League': 'PL', 'Ligue 1': 'FL1'}

for league_name, league_code in leagues.items():
    url = f"https://api.football-data.org/v4/competitions/{league_code}/matches"
    
    headers = {"X-Auth-Token": API_TOKEN}
    params = {"dateFrom": date_from, "dateTo": date_to, "status": "FINISHED"}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        matches = response.json().get('matches', [])
        print(f"\n{league_name} ({league_code}): {len(matches)} matchs")
        print("-"*80)
        for m in matches[:5]:
            home = m['homeTeam']['name']
            away = m['awayTeam']['name']
            score = m['score']['fullTime']
            print(f"{home:30} vs {away:30} | {score['home']}-{score['away']}")

print("\n" + "="*80)
print("💡 ANALYSE")
print("="*80)
print("Compare les noms ci-dessus et identifie les différences !")
