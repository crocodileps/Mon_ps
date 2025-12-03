#!/usr/bin/env python3
"""
Corriger les tiers des équipes Championship (D2 anglaise)
Championship = Tier C minimum, bas de tableau = Tier D
"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("CORRECTION TIERS CHAMPIONSHIP (D2)")
print("="*70)

# 1. Identifier les équipes Championship dans team_class
print("\n1. ÉQUIPES CHAMPIONSHIP ACTUELLES:")
championship_teams = [
    'Sunderland', 'Leeds', 'Sheffield United', 'Norwich', 'West Brom',
    'Middlesbrough', 'Blackburn', 'Burnley', 'Watford', 'Coventry',
    'Bristol City', 'Millwall', 'Stoke', 'Preston', 'Queens Park Rangers',
    'Hull', 'Swansea', 'Cardiff', 'Plymouth', 'Derby', 'Luton', 'Portsmouth',
    'Sheffield Wednesday', 'Oxford United'
]

# Vérifier leur tier actuel
for team in championship_teams:
    cur.execute("""
        SELECT team_name, tier, league FROM team_class 
        WHERE LOWER(team_name) LIKE %s
    """, (f"%{team.lower()}%",))
    rows = cur.fetchall()
    for r in rows:
        print(f"   {r['team_name']}: Tier {r['tier']} ({r['league']})")

# 2. Mettre à jour les tiers Championship -> C ou D
print("\n2. MISE À JOUR DES TIERS:")

# Équipes Championship milieu/haut de tableau -> Tier C
tier_c_teams = ['Leeds', 'Burnley', 'Sheffield United', 'Sunderland', 'Middlesbrough', 
                'West Brom', 'Norwich', 'Watford', 'Blackburn', 'Coventry']

# Équipes Championship bas de tableau -> Tier D  
tier_d_teams = ['Plymouth', 'Hull', 'Cardiff', 'Oxford', 'Portsmouth', 'Preston',
                'Stoke', 'Millwall', 'Queens Park Rangers', 'Derby', 'Sheffield Wednesday']

updated_c = 0
updated_d = 0

for team in tier_c_teams:
    cur.execute("""
        UPDATE team_class SET tier = 'C', updated_at = NOW()
        WHERE LOWER(team_name) LIKE %s AND tier NOT IN ('C', 'D')
    """, (f"%{team.lower()}%",))
    if cur.rowcount > 0:
        updated_c += cur.rowcount
        print(f"   ✅ {team} -> Tier C")

for team in tier_d_teams:
    cur.execute("""
        UPDATE team_class SET tier = 'D', updated_at = NOW()
        WHERE LOWER(team_name) LIKE %s AND tier NOT IN ('D')
    """, (f"%{team.lower()}%",))
    if cur.rowcount > 0:
        updated_d += cur.rowcount
        print(f"   ✅ {team} -> Tier D")

conn.commit()
print(f"\n   Total: {updated_c} équipes -> Tier C, {updated_d} équipes -> Tier D")

# 3. Vérifier Sunderland spécifiquement
print("\n3. VÉRIFICATION SUNDERLAND:")
cur.execute("SELECT team_name, tier, league FROM team_class WHERE LOWER(team_name) LIKE '%sunderland%'")
for r in cur.fetchall():
    print(f"   {r['team_name']}: Tier {r['tier']}")

cur.close()
conn.close()
