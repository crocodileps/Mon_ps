#!/usr/bin/env python3
import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

# 1. Voir les colonnes de team_name_mapping
print("1. Colonnes de team_name_mapping:")
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'team_name_mapping'
""")
cols = [r[0] for r in cur.fetchall()]
print(f"   {cols}")

# 2. Ajouter mapping Athletic Bilbao (sans colonne source)
print("\n2. Ajout mapping Athletic Bilbao...")
try:
    cur.execute("""
        INSERT INTO team_name_mapping (source_name, canonical_name)
        VALUES ('Athletic Bilbao', 'Athletic Club')
        ON CONFLICT (source_name) DO NOTHING
    """)
    cur.execute("""
        INSERT INTO team_name_mapping (source_name, canonical_name)
        VALUES ('Athletic Club Bilbao', 'Athletic Club')
        ON CONFLICT (source_name) DO NOTHING
    """)
    conn.commit()
    print("   OK - Mappings ajoutés")
except Exception as e:
    print(f"   Erreur: {e}")
    conn.rollback()

# 3. Vérifier
print("\n3. Vérification:")
cur.execute("SELECT * FROM team_name_mapping WHERE canonical_name = 'Athletic Club'")
for r in cur.fetchall():
    print(f"   {r['source_name']} -> {r['canonical_name']}")

cur.close()
conn.close()
