#!/usr/bin/env python3
"""Vérifier les vraies colonnes des tables"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

tables = ['team_momentum', 'team_class', 'tactical_matrix', 'referee_intelligence', 'team_head_to_head']

print("="*70)
print("COLONNES REELLES DES TABLES")
print("="*70)

for table in tables:
    print(f"\n{table.upper()}:")
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    cols = [r[0] for r in cur.fetchall()]
    print(f"   {', '.join(cols)}")

cur.close()
conn.close()
