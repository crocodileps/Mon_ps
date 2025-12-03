#!/usr/bin/env python3
"""Trouver un match testable avec données complètes"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("MATCHS TESTABLES (données complètes)")
print("="*70)

# 1. Équipes avec données complètes dans team_intelligence
print("\n1. TOP ÉQUIPES avec données complètes:")
cur.execute("""
    SELECT team_name, league,
           home_goals_scored_avg, home_goals_conceded_avg,
           away_goals_scored_avg, away_goals_conceded_avg,
           current_style
    FROM team_intelligence 
    WHERE home_goals_scored_avg IS NOT NULL 
      AND away_goals_conceded_avg IS NOT NULL
      AND matches_analyzed >= 10
    ORDER BY matches_analyzed DESC
    LIMIT 20
""")
teams = []
for r in cur.fetchall():
    teams.append(r['team_name'])
    print(f"   {r['team_name']} ({r['league']}): {r['current_style']}")
    print(f"      HOME: {r['home_goals_scored_avg']}/{r['home_goals_conceded_avg']} | AWAY: {r['away_goals_scored_avg']}/{r['away_goals_conceded_avg']}")

# 2. Vérifier H2H disponibles
print("\n2. H2H DISPONIBLES:")
cur.execute("""
    SELECT DISTINCT home_team, away_team, COUNT(*) as matches
    FROM head_to_head
    GROUP BY home_team, away_team
    HAVING COUNT(*) >= 3
    ORDER BY matches DESC
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"   {r['home_team']} vs {r['away_team']}: {r['matches']} matchs")

# 3. Odds récents
print("\n3. MATCHS avec ODDS RÉCENTS (dernières 24h):")
cur.execute("""
    SELECT DISTINCT home_team, away_team, MAX(collected_at) as last_update
    FROM odds_history
    WHERE collected_at > NOW() - INTERVAL '24 hours'
    GROUP BY home_team, away_team
    ORDER BY last_update DESC
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"   {r['home_team']} vs {r['away_team']} ({r['last_update']})")

# 4. Suggérer des matchs intéressants
print("\n" + "="*70)
print("MATCHS SUGGÉRÉS POUR TEST:")
print("="*70)

# Liverpool vs Man City si dispo
cur.execute("""
    SELECT team_name FROM team_intelligence 
    WHERE team_name ILIKE '%liverpool%' OR team_name ILIKE '%manchester city%'
""")
epl = [r['team_name'] for r in cur.fetchall()]
if len(epl) >= 2:
    print(f"\n🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League: {epl[0]} vs {epl[1]}")

# Barcelona vs Atletico
cur.execute("""
    SELECT team_name FROM team_intelligence 
    WHERE team_name ILIKE '%barcelona%' OR team_name ILIKE '%atletico%'
""")
laliga = [r['team_name'] for r in cur.fetchall()]
if len(laliga) >= 2:
    print(f"\n🇪🇸 La Liga: {laliga[0]} vs {laliga[1]}")

# Bayern vs Dortmund
cur.execute("""
    SELECT team_name FROM team_intelligence 
    WHERE team_name ILIKE '%bayern%' OR team_name ILIKE '%dortmund%'
""")
buli = [r['team_name'] for r in cur.fetchall()]
if len(buli) >= 2:
    print(f"\n🇩🇪 Bundesliga: {buli[0]} vs {buli[1]}")

# PSG vs Marseille
cur.execute("""
    SELECT team_name FROM team_intelligence 
    WHERE team_name ILIKE '%paris%' OR team_name ILIKE '%marseille%'
""")
ligue1 = [r['team_name'] for r in cur.fetchall()]
if len(ligue1) >= 2:
    print(f"\n🇫🇷 Ligue 1: {ligue1[0]} vs {ligue1[1]}")

cur.close()
conn.close()
