#!/usr/bin/env python3
"""Debug xG Liverpool vs Sunderland"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("DEBUG xG - LIVERPOOL vs SUNDERLAND")
print("="*70)

# Liverpool (HOME)
cur.execute("""
    SELECT team_name, home_goals_scored_avg, home_goals_conceded_avg,
           away_goals_scored_avg, away_goals_conceded_avg
    FROM team_intelligence WHERE LOWER(team_name) LIKE '%liverpool%'
""")
liv = dict(cur.fetchone())

# Sunderland (AWAY)
cur.execute("""
    SELECT team_name, home_goals_scored_avg, home_goals_conceded_avg,
           away_goals_scored_avg, away_goals_conceded_avg
    FROM team_intelligence WHERE LOWER(team_name) LIKE '%sunderland%'
""")
sun = dict(cur.fetchone())

print(f"\n📊 DONNÉES BRUTES:")
print(f"\nLiverpool (HOME):")
print(f"   Marqués à domicile: {liv['home_goals_scored_avg']}")
print(f"   Encaissés à domicile: {liv['home_goals_conceded_avg']}")

print(f"\nSunderland (AWAY):")
print(f"   Marqués à l'extérieur: {sun['away_goals_scored_avg']}")
print(f"   Encaissés à l'extérieur: {sun['away_goals_conceded_avg']}")

# Calcul V10.1
print(f"\n" + "="*70)
print("CALCUL xG V10.1:")
print("="*70)

liv_attack = float(liv['home_goals_scored_avg'] or 1.3)
sun_defense = float(sun['away_goals_conceded_avg'] or 1.3)
liv_xg = (liv_attack * 0.6) + (sun_defense * 0.4)

sun_attack = float(sun['away_goals_scored_avg'] or 1.1)
liv_defense = float(liv['home_goals_conceded_avg'] or 1.1)
sun_xg = (sun_attack * 0.6) + (liv_defense * 0.4)

print(f"\nLiverpool xG = ({liv_attack:.2f} × 0.6) + ({sun_defense:.2f} × 0.4) = {liv_xg:.2f}")
print(f"Sunderland xG = ({sun_attack:.2f} × 0.6) + ({liv_defense:.2f} × 0.4) = {sun_xg:.2f}")
print(f"\n📍 TOTAL xG = {liv_xg + sun_xg:.2f}")

# Probabilités
import math
def poisson_prob(lam, k):
    return (lam**k * math.exp(-lam)) / math.factorial(k)

over25_prob = 0
for h in range(10):
    for a in range(10):
        if h + a > 2:
            over25_prob += poisson_prob(liv_xg, h) * poisson_prob(sun_xg, a)

print(f"\n📊 PROBABILITÉS POISSON:")
print(f"   OVER 2.5: {over25_prob*100:.1f}%")
print(f"   UNDER 2.5: {(1-over25_prob)*100:.1f}%")

print(f"\n⚠️  PROBLÈME IDENTIFIÉ:")
print(f"   Liverpool encaisse {liv['home_goals_conceded_avg']} à domicile (élevé!)")
print(f"   Sunderland n'encaisse que {sun['away_goals_conceded_avg']} à l'extérieur")
print(f"   → Le modèle voit un match plus serré qu'attendu")

cur.close()
conn.close()
