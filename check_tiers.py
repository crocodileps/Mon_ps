#!/usr/bin/env python3
import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("VÉRIFICATION TIERS - TEAM_CLASS")
print("="*70)

# Colonnes disponibles
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'team_class' ORDER BY ordinal_position
""")
cols = [r[0] for r in cur.fetchall()]
print(f"Colonnes: {cols}")

# Liverpool et Sunderland
print("\nLIVERPOOL & SUNDERLAND:")
cur.execute("""
    SELECT team_name, tier FROM team_class 
    WHERE LOWER(team_name) LIKE '%liverpool%' OR LOWER(team_name) LIKE '%sunderland%'
""")
for r in cur.fetchall():
    print(f"   {r['team_name']}: Tier {r['tier']}")

print("\nTOP TIERS S:")
cur.execute("SELECT team_name, tier FROM team_class WHERE tier = 'S' LIMIT 10")
for r in cur.fetchall():
    print(f"   {r['team_name']}")

print("\nTIERS C/D (équipes faibles):")
cur.execute("SELECT team_name, tier FROM team_class WHERE tier IN ('C', 'D') LIMIT 10")
for r in cur.fetchall():
    print(f"   {r['team_name']}: {r['tier']}")

cur.close()
conn.close()
