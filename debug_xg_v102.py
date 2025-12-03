#!/usr/bin/env python3
"""Debug xG V10.2 - Vérifier le filtrage compétition"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("DEBUG xG V10.2 - LIVERPOOL vs SUNDERLAND")
print("="*70)

# Stats team_intelligence (polluées CL)
print("\n1. TEAM_INTELLIGENCE (toutes compétitions):")
cur.execute("""
    SELECT team_name, home_goals_scored_avg, home_goals_conceded_avg
    FROM team_intelligence WHERE LOWER(team_name) LIKE '%liverpool%'
""")
r = cur.fetchone()
print(f"   Liverpool: {r['home_goals_scored_avg']} scored / {r['home_goals_conceded_avg']} conceded")

cur.execute("""
    SELECT team_name, away_goals_scored_avg, away_goals_conceded_avg
    FROM team_intelligence WHERE LOWER(team_name) LIKE '%sunderland%'
""")
r = cur.fetchone()
print(f"   Sunderland: {r['away_goals_scored_avg']} scored / {r['away_goals_conceded_avg']} conceded")

# Stats filtrées Premier League
print("\n2. MATCH_RESULTS (Premier League uniquement):")
cur.execute("""
    SELECT AVG(score_home) as scored, AVG(score_away) as conceded, COUNT(*) as n
    FROM match_results
    WHERE LOWER(home_team) LIKE '%liverpool%' AND is_finished = TRUE
      AND LOWER(league) LIKE '%premier%'
""")
r = cur.fetchone()
print(f"   Liverpool HOME (PL): {float(r['scored']):.2f} scored / {float(r['conceded']):.2f} conceded ({r['n']} matchs)")

cur.execute("""
    SELECT AVG(score_away) as scored, AVG(score_home) as conceded, COUNT(*) as n
    FROM match_results
    WHERE LOWER(away_team) LIKE '%sunderland%' AND is_finished = TRUE
      AND LOWER(league) LIKE '%premier%'
""")
r = cur.fetchone()
if r['n']:
    print(f"   Sunderland AWAY (PL): {float(r['scored']):.2f} scored / {float(r['conceded']):.2f} conceded ({r['n']} matchs)")
else:
    print(f"   Sunderland AWAY (PL): Pas de données (Championship!)")

# Calcul xG
print("\n" + "="*70)
print("3. CALCUL xG V10.2:")
print("="*70)

# Liverpool utilise stats PL
liv_attack = 1.67  # PL home scored
liv_defense = 1.33  # PL home conceded

# Sunderland - pas de données PL, fallback team_intelligence
cur.execute("""
    SELECT away_goals_scored_avg, away_goals_conceded_avg
    FROM team_intelligence WHERE LOWER(team_name) LIKE '%sunderland%'
""")
r = cur.fetchone()
sun_attack = float(r['away_goals_scored_avg'] or 0.5)
sun_defense = float(r['away_goals_conceded_avg'] or 1.0)

# xG V10.2
liv_xg = (liv_attack * 0.6) + (sun_defense * 0.4)
sun_xg = (sun_attack * 0.6) + (liv_defense * 0.4)

print(f"\n   Liverpool xG = ({liv_attack:.2f} × 0.6) + ({sun_defense:.2f} × 0.4) = {liv_xg:.2f}")
print(f"   Sunderland xG = ({sun_attack:.2f} × 0.6) + ({liv_defense:.2f} × 0.4) = {sun_xg:.2f}")
print(f"\n   📍 TOTAL xG = {liv_xg + sun_xg:.2f}")

# Proba Poisson
import math
def poisson(lam, k):
    return (lam**k * math.exp(-lam)) / math.factorial(k)

over25 = 0
for h in range(10):
    for a in range(10):
        if h + a > 2:
            over25 += poisson(liv_xg, h) * poisson(sun_xg, a)

print(f"\n   📊 OVER 2.5: {over25*100:.1f}%")
print(f"   📊 UNDER 2.5: {(1-over25)*100:.1f}%")

cur.close()
conn.close()
