#!/usr/bin/env python3
import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("RECHERCHE H2H BILBAO vs REAL MADRID")
print("="*70)

# Chercher toutes les variantes
cur.execute("""
    SELECT team_a, team_b, total_matches, btts_pct, over_25_pct
    FROM team_head_to_head
    WHERE LOWER(team_a) LIKE '%bilbao%' OR LOWER(team_b) LIKE '%bilbao%'
       OR LOWER(team_a) LIKE '%athletic%' OR LOWER(team_b) LIKE '%athletic%'
    LIMIT 10
""")
rows = cur.fetchall()
print(f"\nH2H avec Bilbao/Athletic ({len(rows)} trouvés):")
for r in rows:
    print(f"  {r['team_a']} vs {r['team_b']}: {r['total_matches']} matches, btts={r['btts_pct']}%")

# Chercher Real Madrid
cur.execute("""
    SELECT team_a, team_b, total_matches, btts_pct, over_25_pct
    FROM team_head_to_head
    WHERE LOWER(team_a) LIKE '%real madrid%' OR LOWER(team_b) LIKE '%real madrid%'
    LIMIT 10
""")
rows = cur.fetchall()
print(f"\nH2H avec Real Madrid ({len(rows)} trouvés):")
for r in rows:
    print(f"  {r['team_a']} vs {r['team_b']}: {r['total_matches']} matches, btts={r['btts_pct']}%")

# Voir le seuil tactical actuel
print("\n" + "="*70)
print("TACTICAL MATRIX - balanced_defensive vs offensive:")
cur.execute("""
    SELECT * FROM tactical_matrix 
    WHERE (style_a = 'balanced_defensive' AND style_b = 'offensive')
       OR (style_a = 'offensive' AND style_b = 'balanced_defensive')
""")
r = cur.fetchone()
if r:
    print(f"  btts_probability: {r['btts_probability']}%")
    print(f"  over_25_probability: {r['over_25_probability']}%")
else:
    print("  Non trouvé - essayons balanced vs offensive")
    cur.execute("SELECT * FROM tactical_matrix WHERE style_a = 'balanced' AND style_b = 'offensive'")
    r = cur.fetchone()
    if r:
        print(f"  btts_probability: {r['btts_probability']}%")
        print(f"  over_25_probability: {r['over_25_probability']}%")

cur.close()
conn.close()
