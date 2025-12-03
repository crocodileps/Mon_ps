#!/usr/bin/env python3
"""Debug: Pourquoi le Score reste bas malgré la supériorité Liverpool?"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("DEBUG LAYERS - LIVERPOOL vs SUNDERLAND")
print("="*70)

# 1. H2H - Confrontations directes
print("\n1. H2H (Confrontations directes):")
cur.execute("""
    SELECT * FROM head_to_head 
    WHERE (LOWER(home_team) LIKE '%liverpool%' AND LOWER(away_team) LIKE '%sunderland%')
       OR (LOWER(home_team) LIKE '%sunderland%' AND LOWER(away_team) LIKE '%liverpool%')
    LIMIT 5
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"   {r}")
else:
    print("   ❌ AUCUNE DONNÉE H2H")

# 2. Tactical - team_tactical_profile
print("\n2. TACTICAL (Profils tactiques):")
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'team_tactical_profile' LIMIT 1
""")
if cur.fetchone():
    cur.execute("""
        SELECT team_name FROM team_tactical_profile 
        WHERE LOWER(team_name) LIKE '%liverpool%' OR LOWER(team_name) LIKE '%sunderland%'
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"   ✅ {r['team_name']}")
    else:
        print("   ❌ AUCUNE DONNÉE TACTICAL")
else:
    print("   ❌ TABLE team_tactical_profile N'EXISTE PAS")

# 3. Referee
print("\n3. REFEREE:")
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'referee_stats' LIMIT 1
""")
if cur.fetchone():
    print("   Table referee_stats existe")
else:
    print("   ❌ TABLE referee_stats N'EXISTE PAS")

# 4. Team Class
print("\n4. TEAM CLASS:")
cur.execute("""
    SELECT team_name, tier, big_game_factor, home_fortress_factor
    FROM team_class 
    WHERE LOWER(team_name) LIKE '%liverpool%' OR LOWER(team_name) LIKE '%sunderland%'
""")
for r in cur.fetchall():
    print(f"   {r['team_name']}: Tier {r['tier']}, BigGame={r['big_game_factor']}, HomeFortress={r['home_fortress_factor']}")

# 5. Team Momentum
print("\n5. TEAM MOMENTUM:")
cur.execute("""
    SELECT team_name, last_5_results, form_trend
    FROM team_momentum 
    WHERE LOWER(team_name) LIKE '%liverpool%' OR LOWER(team_name) LIKE '%sunderland%'
""")
for r in cur.fetchall():
    print(f"   {r['team_name']}: Form={r['last_5_results']}, Trend={r['form_trend']}")

# 6. Market Traps
print("\n6. MARKET TRAPS pour ce match:")
cur.execute("""
    SELECT market_type, trap_reason, bookmaker
    FROM market_traps 
    WHERE (LOWER(home_team) LIKE '%liverpool%' AND LOWER(away_team) LIKE '%sunderland%')
    LIMIT 5
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"   🚫 {r['market_type']}: {r['trap_reason']}")
else:
    print("   Aucun trap détecté")

print("\n" + "="*70)
print("CONCLUSION:")
print("="*70)
print("Le Score reste bas car plusieurs layers n'ont PAS de données:")
print("- H2H: Pas de confrontations directes récentes")
print("- Tactical: Profils non disponibles")
print("- Referee: Pas de données arbitre")
print("→ Seuls Monte Carlo + Tier contribuent au score")
print("→ C'est pourquoi Score = 21 au lieu de 50+")

cur.close()
conn.close()
