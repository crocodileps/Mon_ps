#!/usr/bin/env python3
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 80)
print("    EXPLORATION DES DONNÉES EXISTANTES")
print("=" * 80)

# 1. match_xg_stats (719 entrées!)
print("\n1️⃣ TABLE match_xg_stats - Structure:")
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'match_xg_stats'
    ORDER BY ordinal_position
""")
for c in cur.fetchall():
    print(f"   {c['column_name']:30} | {c['data_type']}")

print("\n   Exemple (1 match):")
cur.execute("SELECT * FROM match_xg_stats LIMIT 1")
row = cur.fetchone()
if row:
    for k, v in row.items():
        print(f"      {k}: {v}")

# 2. match_advanced_stats (719 entrées!)
print("\n" + "=" * 80)
print("\n2️⃣ TABLE match_advanced_stats - Structure:")
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'match_advanced_stats'
    ORDER BY ordinal_position
""")
for c in cur.fetchall():
    print(f"   {c['column_name']:30} | {c['data_type']}")

print("\n   Exemple (1 match):")
cur.execute("SELECT * FROM match_advanced_stats LIMIT 1")
row = cur.fetchone()
if row:
    for k, v in row.items():
        print(f"      {k}: {v}")

# 3. team_xg_tendencies
print("\n" + "=" * 80)
print("\n3️⃣ TABLE team_xg_tendencies - Structure:")
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'team_xg_tendencies'
    ORDER BY ordinal_position
""")
for c in cur.fetchall():
    print(f"   {c['column_name']:30} | {c['data_type']}")

# 4. Vérifier si on peut matcher avec match_results
print("\n" + "=" * 80)
print("\n4️⃣ JOINTURE POSSIBLE match_results <-> match_xg_stats:")
cur.execute("""
    SELECT 
        mr.home_team, mr.away_team, mr.score_home, mr.score_away,
        mxg.*
    FROM match_results mr
    LEFT JOIN match_xg_stats mxg ON mr.match_id = mxg.match_id
    WHERE mr.is_finished = true
    LIMIT 3
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"\n   {row['home_team']} vs {row['away_team']} ({row['score_home']}-{row['score_away']})")
        print(f"      xG Home: {row.get('home_xg', 'NULL')} | xG Away: {row.get('away_xg', 'NULL')}")
else:
    print("   ❌ Pas de jointure possible - clés différentes?")

conn.close()
print("\n" + "=" * 80)
