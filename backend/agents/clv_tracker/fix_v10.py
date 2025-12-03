#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor()

# 1. Ajouter mapping Athletic Bilbao
print("1. Ajout mapping Athletic Bilbao...")
try:
    cur.execute("""
        INSERT INTO team_name_mapping (source_name, canonical_name, source, confidence)
        VALUES ('Athletic Bilbao', 'Athletic Club', 'manual', 1.0)
        ON CONFLICT (source_name) DO NOTHING
    """)
    cur.execute("""
        INSERT INTO team_name_mapping (source_name, canonical_name, source, confidence)
        VALUES ('Athletic Club Bilbao', 'Athletic Club', 'manual', 1.0)
        ON CONFLICT (source_name) DO NOTHING
    """)
    conn.commit()
    print("   OK - Mappings ajoutés")
except Exception as e:
    print(f"   Erreur: {e}")
    conn.rollback()

# 2. Voir les styles disponibles dans tactical_matrix
print("\n2. Styles disponibles dans tactical_matrix:")
cur.execute("SELECT DISTINCT style_a FROM tactical_matrix ORDER BY style_a")
styles = [r[0] for r in cur.fetchall()]
print(f"   {styles}")

cur.close()
conn.close()
