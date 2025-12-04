#!/usr/bin/env python3
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 70)
print("    RECHERCHE DES DONNÉES STATISTIQUES DE MATCH")
print("=" * 70)

# 1. Tables avec stats
print("\n1️⃣ TABLES DISPONIBLES:")
cur.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND (table_name ILIKE '%stat%' 
         OR table_name ILIKE '%xg%' 
         OR table_name ILIKE '%fixture%'
         OR table_name ILIKE '%event%'
         OR table_name ILIKE '%shot%')
    ORDER BY table_name
""")
for t in cur.fetchall():
    print(f"   → {t['table_name']}")
    cur.execute(f"SELECT COUNT(*) as c FROM {t['table_name']}")
    print(f"      ({cur.fetchone()['c']} entrées)")

# 2. Colonnes dans team_intelligence (xG?)
print("\n2️⃣ COLONNES DANS team_intelligence:")
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'team_intelligence' 
    ORDER BY ordinal_position
""")
for c in cur.fetchall():
    if 'xg' in c['column_name'].lower() or 'shot' in c['column_name'].lower() or 'goal' in c['column_name'].lower():
        print(f"   → {c['column_name']}")

# 3. Exemple de données xG
print("\n3️⃣ EXEMPLE DONNÉES xG (team_intelligence):")
cur.execute("""
    SELECT team_name, xg_for_avg, xg_against_avg, shots_per_game, shots_on_target_per_game
    FROM team_intelligence
    WHERE xg_for_avg IS NOT NULL
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"   {row['team_name'][:25]:25} | xG For:{row['xg_for_avg'] or 'NULL':>5} | xG Ag:{row['xg_against_avg'] or 'NULL':>5} | Shots:{row['shots_per_game'] or 'NULL':>5}")

# 4. Chercher une table fixture_statistics
print("\n4️⃣ TABLE fixture_statistics (si existe):")
try:
    cur.execute("SELECT * FROM fixture_statistics LIMIT 1")
    row = cur.fetchone()
    if row:
        print("   Colonnes disponibles:")
        for k in row.keys():
            print(f"      → {k}")
except:
    print("   ❌ Table fixture_statistics non trouvée")

# 5. Alternative: API-Football stockées?
print("\n5️⃣ RECHERCHE AUTRES SOURCES:")
cur.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name ILIKE '%api%'
""")
tables = cur.fetchall()
if tables:
    for t in tables:
        print(f"   → {t['table_name']}")
else:
    print("   Aucune table API trouvée")

conn.close()
print("\n" + "=" * 70)
