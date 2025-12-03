#!/usr/bin/env python3
import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

# 1. Vérifier si mapping existe déjà
print("1. Vérification mappings existants:")
cur.execute("SELECT * FROM team_name_mapping WHERE source_name LIKE '%Athletic%' OR source_name LIKE '%Bilbao%'")
existing = cur.fetchall()
for r in existing:
    print(f"   {r['source_name']} -> {r['canonical_name']}")

# 2. Ajouter si n'existe pas
print("\n2. Ajout mapping Athletic Bilbao...")
cur.execute("SELECT COUNT(*) FROM team_name_mapping WHERE source_name = 'Athletic Bilbao'")
if cur.fetchone()[0] == 0:
    cur.execute("""
        INSERT INTO team_name_mapping (source_name, canonical_name)
        VALUES ('Athletic Bilbao', 'Athletic Club')
    """)
    conn.commit()
    print("   OK - Athletic Bilbao ajouté")
else:
    print("   Déjà existant")

# 3. Vérifier H2H pour Athletic Club vs Real Madrid
print("\n3. H2H Athletic Club vs Real Madrid:")
cur.execute("""
    SELECT team_a, team_b, total_matches, btts_pct, over_25_pct
    FROM team_head_to_head
    WHERE (LOWER(team_a) LIKE '%athletic%' AND LOWER(team_b) LIKE '%real madrid%')
       OR (LOWER(team_a) LIKE '%real madrid%' AND LOWER(team_b) LIKE '%athletic%')
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"   {r['team_a']} vs {r['team_b']}: {r['total_matches']} matches, btts={r['btts_pct']}%")
else:
    print("   Aucun H2H trouvé")

cur.close()
conn.close()
