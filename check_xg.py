#!/usr/bin/env python3
"""Vérifier les données xG"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("DONNÉES XG DISPONIBLES")
print("="*70)

# Colonnes liées aux goals/xG dans team_intelligence
print("\n1. Colonnes goals/xG dans team_intelligence:")
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'team_intelligence'
      AND (column_name LIKE '%xg%' OR column_name LIKE '%goal%')
    ORDER BY column_name
""")
cols = [r[0] for r in cur.fetchall()]
print(f"   {cols}")

# Valeurs pour Liverpool et Man City
print("\n2. Valeurs Liverpool:")
cur.execute("""
    SELECT team_name, 
           xg_for_avg, xg_against_avg,
           home_goals_scored_avg, away_goals_scored_avg,
           home_goals_conceded_avg, away_goals_conceded_avg,
           goals_tendency
    FROM team_intelligence
    WHERE LOWER(team_name) = 'liverpool'
""")
r = cur.fetchone()
if r:
    for k in r.keys():
        print(f"   {k}: {r[k]}")

print("\n3. Valeurs Manchester City:")
cur.execute("""
    SELECT team_name, 
           xg_for_avg, xg_against_avg,
           home_goals_scored_avg, away_goals_scored_avg,
           home_goals_conceded_avg, away_goals_conceded_avg,
           goals_tendency
    FROM team_intelligence
    WHERE LOWER(team_name) = 'manchester city'
""")
r = cur.fetchone()
if r:
    for k in r.keys():
        print(f"   {k}: {r[k]}")

# Moyenne générale
print("\n4. Moyennes générales (Premier League):")
cur.execute("""
    SELECT 
        AVG(home_goals_scored_avg) as avg_home_scored,
        AVG(away_goals_scored_avg) as avg_away_scored,
        AVG(xg_for_avg) as avg_xg
    FROM team_intelligence
    WHERE home_goals_scored_avg IS NOT NULL
""")
r = cur.fetchone()
if r:
    for k in r.keys():
        print(f"   {k}: {r[k]}")

cur.close()
conn.close()
