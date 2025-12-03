#!/usr/bin/env python3
"""Debug V11 - Vérifier que les nouveaux layers fonctionnent"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("🔍 DEBUG V11 - LIVERPOOL vs SUNDERLAND")
print("="*70)

# 1. Récupérer les styles
print("\n1. STYLES DES ÉQUIPES:")
for team in ['Liverpool', 'Sunderland']:
    cur.execute("""
        SELECT current_style, current_pressing FROM team_intelligence 
        WHERE LOWER(team_name) LIKE %s
    """, (f"%{team.lower()}%",))
    ti = cur.fetchone()
    
    cur.execute("""
        SELECT playing_style FROM team_class 
        WHERE LOWER(team_name) LIKE %s
    """, (f"%{team.lower()}%",))
    tc = cur.fetchone()
    
    print(f"   {team}:")
    print(f"      team_intelligence.current_style: {ti['current_style'] if ti else 'N/A'}")
    print(f"      team_class.playing_style: {tc['playing_style'] if tc else 'N/A'}")

# 2. Tactical Matrix Matchup
print("\n2. TACTICAL MATRIX MATCHUP:")

# Liverpool = balanced, Sunderland = balanced_offensive -> attacking
matchups_to_test = [
    ('balanced', 'balanced'),
    ('balanced', 'attacking'),
    ('high_press', 'pressing'),
    ('high_press', 'balanced'),
]

for home_s, away_s in matchups_to_test:
    cur.execute("""
        SELECT btts_probability, over_25_probability, avg_goals_total
        FROM tactical_matrix
        WHERE style_a = %s AND style_b = %s
    """, (home_s, away_s))
    r = cur.fetchone()
    if r:
        print(f"   {home_s} vs {away_s}: BTTS={r['btts_probability']}%, Over25={r['over_25_probability']}%, Goals={r['avg_goals_total']}")
    else:
        print(f"   {home_s} vs {away_s}: ❌ Pas de données")

# 3. Team Class Factors
print("\n3. TEAM_CLASS FACTORS:")
for team in ['Liverpool', 'Sunderland']:
    cur.execute("""
        SELECT home_fortress_factor, away_weakness_factor, psychological_edge
        FROM team_class WHERE LOWER(team_name) LIKE %s
    """, (f"%{team.lower()}%",))
    r = cur.fetchone()
    if r:
        print(f"   {team}: HomeFort={r['home_fortress_factor']}, AwayWeak={r['away_weakness_factor']}, PsychEdge={r['psychological_edge']}")

# 4. VS Top/Bottom Teams
print("\n4. VS TOP/BOTTOM TEAMS:")
for team in ['Liverpool', 'Sunderland']:
    cur.execute("""
        SELECT vs_top_teams, vs_bottom_teams FROM team_intelligence 
        WHERE LOWER(team_name) LIKE %s
    """, (f"%{team.lower()}%",))
    r = cur.fetchone()
    if r:
        print(f"   {team}:")
        print(f"      vs_top_teams: {r['vs_top_teams']}")
        print(f"      vs_bottom_teams: {r['vs_bottom_teams']}")

# 5. Calcul xG attendu
print("\n5. CALCUL xG V11:")
print("-"*70)

# Liverpool HOME
cur.execute("""
    SELECT home_goals_scored_avg, current_style FROM team_intelligence 
    WHERE LOWER(team_name) LIKE '%liverpool%'
""")
liv = cur.fetchone()
liv_attack = float(liv['home_goals_scored_avg']) if liv else 1.5

# Sunderland AWAY défense
cur.execute("""
    SELECT away_goals_conceded_avg, current_style FROM team_intelligence 
    WHERE LOWER(team_name) LIKE '%sunderland%'
""")
sun = cur.fetchone()
sun_defense = float(sun['away_goals_conceded_avg']) if sun else 1.0

# xG base
liv_xg_base = (liv_attack * 0.6) + (sun_defense * 0.4)
print(f"   Liverpool xG base = ({liv_attack:.2f} × 0.6) + ({sun_defense:.2f} × 0.4) = {liv_xg_base:.2f}")

# Sunderland AWAY
cur.execute("""
    SELECT away_goals_scored_avg FROM team_intelligence 
    WHERE LOWER(team_name) LIKE '%sunderland%'
""")
sun2 = cur.fetchone()
sun_attack = float(sun2['away_goals_scored_avg']) if sun2 else 0.5

cur.execute("""
    SELECT home_goals_conceded_avg FROM team_intelligence 
    WHERE LOWER(team_name) LIKE '%liverpool%'
""")
liv2 = cur.fetchone()
liv_defense = float(liv2['home_goals_conceded_avg']) if liv2 else 1.0

sun_xg_base = (sun_attack * 0.6) + (liv_defense * 0.4)
print(f"   Sunderland xG base = ({sun_attack:.2f} × 0.6) + ({liv_defense:.2f} × 0.4) = {sun_xg_base:.2f}")

# Tier Adjustment (Liverpool A=4, Sunderland C=2, diff=2)
print(f"\n   Tier Adjustment: Liverpool(A) vs Sunderland(C) = diff 2")
print(f"   → Liverpool xG × 1.25 = {liv_xg_base * 1.25:.2f}")
print(f"   → Sunderland xG × 0.75 = {sun_xg_base * 0.75:.2f}")

total_xg = (liv_xg_base * 1.25) + (sun_xg_base * 0.75)
print(f"\n   TOTAL xG = {total_xg:.2f}")

# Poisson
import math
def poisson(lam, k):
    return (lam**k * math.exp(-lam)) / math.factorial(k)

over25 = 0
for h in range(10):
    for a in range(10):
        if h + a > 2:
            over25 += poisson(liv_xg_base * 1.25, h) * poisson(sun_xg_base * 0.75, a)

print(f"   📊 OVER 2.5 Poisson: {over25*100:.1f}%")

cur.close()
conn.close()
