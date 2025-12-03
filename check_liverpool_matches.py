#!/usr/bin/env python3
"""Vérifier les matchs Liverpool"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("MATCHS LIVERPOOL - SOURCE DES DONNÉES")
print("="*70)

# 1. Colonnes de match_results
print("\n1. COLONNES match_results:")
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'match_results' ORDER BY ordinal_position
""")
cols = [r[0] for r in cur.fetchall()]
print(f"   {cols}")

# 2. Exemple de données
print("\n2. EXEMPLE match_results Liverpool:")
cur.execute("""
    SELECT * FROM match_results 
    WHERE LOWER(home_team) LIKE '%liverpool%'
    ORDER BY id DESC LIMIT 3
""")
for r in cur.fetchall():
    print(f"   {dict(r)}")

cur.close()
conn.close()
