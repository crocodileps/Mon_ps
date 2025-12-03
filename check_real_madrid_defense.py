#!/usr/bin/env python3
"""Vérifier les vraies stats défensives Real Madrid"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("AUDIT REAL MADRID - DONNÉES DÉFENSIVES")
print("="*70)

# 1. Colonnes disponibles
print("\n1. COLONNES team_intelligence:")
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'team_intelligence' 
    ORDER BY ordinal_position
""")
cols = [r[0] for r in cur.fetchall()]
print(f"   {cols}")

# 2. Données Real Madrid
print("\n2. REAL MADRID - TOUTES LES DONNÉES:")
cur.execute("""
    SELECT * FROM team_intelligence 
    WHERE LOWER(team_name) LIKE '%real madrid%'
""")
row = cur.fetchone()
if row:
    d = dict(row)
    for key in sorted(d.keys()):
        if d[key] is not None:
            print(f"   {key}: {d[key]}")

# 3. D'où vient le 2.08 affiché ?
print("\n3. RECHERCHE DU 2.08 (buts encaissés):")
if row:
    d = dict(row)
    for key, val in d.items():
        if val and str(val) == '2.08':
            print(f"   ⚠️  TROUVÉ: {key} = {val}")

# 4. Vérifier away_goals_scored_avg
print("\n4. STATS OFFENSIVES/DÉFENSIVES:")
cur.execute("""
    SELECT team_name, 
           home_goals_scored_avg, home_goals_conceded_avg,
           away_goals_scored_avg, away_goals_conceded_avg
    FROM team_intelligence 
    WHERE LOWER(team_name) LIKE '%real madrid%'
""")
for r in cur.fetchall():
    print(f"   {r['team_name']}:")
    print(f"   HOME: {r['home_goals_scored_avg']} scored / {r['home_goals_conceded_avg']} conceded")
    print(f"   AWAY: {r['away_goals_scored_avg']} scored / {r['away_goals_conceded_avg']} conceded")

cur.close()
conn.close()
