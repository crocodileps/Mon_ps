#!/usr/bin/env python3
"""Diagnostic pour V10 Quant Engine"""
import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("🔬 DIAGNOSTIC QUANT ENGINE V10")
print("="*70)

# 1. odds_history
print("\n1. ODDS_HISTORY - Structure:")
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'odds_history'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"   • {r['column_name']}: {r['data_type']}")

cur.execute("SELECT COUNT(*) FROM odds_history")
print(f"   Total lignes: {cur.fetchone()[0]}")

print("\n   Exemple:")
cur.execute("SELECT * FROM odds_history LIMIT 1")
row = cur.fetchone()
if row:
    for key in row.keys():
        print(f"   {key}: {row[key]}")

# 2. Vérifier si on a des xG
print("\n2. XG DATA - Disponibilité:")
tables_with_xg = ['match_results', 'matches', 'team_intelligence']
for table in tables_with_xg:
    cur.execute(f"""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = '{table}' AND column_name LIKE '%xg%'
    """)
    cols = [r[0] for r in cur.fetchall()]
    if cols:
        print(f"   ✅ {table}: {', '.join(cols)}")

# 3. Star players data
print("\n3. STAR_PLAYERS - Exemple:")
cur.execute("SELECT team_name, star_players FROM team_class WHERE star_players IS NOT NULL LIMIT 2")
for r in cur.fetchall():
    print(f"   {r['team_name']}: {r['star_players']}")

cur.close()
conn.close()
print("\n✅ Diagnostic terminé")
