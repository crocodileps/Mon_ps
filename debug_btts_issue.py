#!/usr/bin/env python3
"""Debug BTTS - Pourquoi Sunderland aurait 50% de chance de marquer?"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("🔍 DEBUG BTTS - LIVERPOOL vs SUNDERLAND")
print("="*70)

# Liverpool défense à domicile
cur.execute("""
    SELECT team_name, home_goals_conceded_avg, competition
    FROM team_intelligence 
    WHERE LOWER(team_name) LIKE '%liverpool%'
""")
for r in cur.fetchall():
    print(f"\n📊 {r['team_name']} ({r['competition']}):")
    print(f"   home_goals_conceded_avg = {r['home_goals_conceded_avg']}")

# Sunderland attaque à l'extérieur  
cur.execute("""
    SELECT team_name, away_goals_scored_avg, competition
    FROM team_intelligence 
    WHERE LOWER(team_name) LIKE '%sunderland%'
""")
for r in cur.fetchall():
    print(f"\n�� {r['team_name']} ({r['competition']}):")
    print(f"   away_goals_scored_avg = {r['away_goals_scored_avg']}")

# Calcul xG Sunderland
print("\n" + "="*70)
print("CALCUL xG SUNDERLAND (away):")
print("="*70)

# Formule: away_xg = (away_attack * 0.6) + (home_defense * 0.4)
sun_attack = 0.50  # away_goals_scored_avg
liv_defense = 1.56  # home_goals_conceded_avg (PROBLÈME ICI!)

sun_xg_base = (sun_attack * 0.6) + (liv_defense * 0.4)
print(f"   Sunderland attack = {sun_attack}")
print(f"   Liverpool defense = {liv_defense} ❌ TROP ÉLEVÉ!")
print(f"   Sunderland xG base = ({sun_attack} × 0.6) + ({liv_defense} × 0.4) = {sun_xg_base:.2f}")

# Après tier adjustment (×0.75)
sun_xg_adjusted = sun_xg_base * 0.75
print(f"   Après Tier Adjustment (×0.75) = {sun_xg_adjusted:.2f}")

# Poisson P(goals >= 1)
import math
def poisson(lam, k):
    return (lam**k * math.exp(-lam)) / math.factorial(k)

p_zero = poisson(sun_xg_adjusted, 0)
p_score = 1 - p_zero
print(f"\n   P(Sunderland marque) = 1 - P(0 buts) = 1 - {p_zero:.3f} = {p_score*100:.1f}%")

# Ce qu'il DEVRAIT être avec une défense Liverpool réaliste
print("\n" + "="*70)
print("CORRECTION ATTENDUE:")
print("="*70)

# Liverpool à domicile en PL concède ~0.8 buts/match (pas 1.56!)
liv_defense_realistic = 0.80
sun_xg_realistic = (sun_attack * 0.6) + (liv_defense_realistic * 0.4)
sun_xg_adj_real = sun_xg_realistic * 0.75

p_zero_real = poisson(sun_xg_adj_real, 0)
p_score_real = 1 - p_zero_real

print(f"   Si Liverpool defense = {liv_defense_realistic} (réaliste PL)")
print(f"   Sunderland xG = {sun_xg_adj_real:.2f}")
print(f"   P(Sunderland marque) = {p_score_real*100:.1f}%")
print(f"\n   → BTTS YES devrait être ~{p_score_real * 0.9 * 100:.0f}% (avec Liverpool qui marque)")

cur.close()
conn.close()
