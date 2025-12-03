#!/usr/bin/env python3
"""Test pour voir les exceptions cachées"""

import psycopg2
import psycopg2.extras
import logging

# Activer TOUS les logs
logging.basicConfig(level=logging.DEBUG)

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')

# Simuler exactement ce que fait V10
variants = ['liverpool fc', 'Liverpool', 'liverpool', 'Liverpool FC']
params = [v.lower() for v in variants]
where = "(LOWER(team_name) = %s OR LOWER(team_name) = %s OR LOWER(team_name) = %s OR LOWER(team_name) = %s)"

print("="*60)
print("TEST REQUETES DIRECTES")
print("="*60)

# Test 1: team_intelligence (fonctionne)
print("\n1. team_intelligence:")
try:
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(f"""
            SELECT team_name, current_style
            FROM team_intelligence
            WHERE {where}
            LIMIT 1
        """, params)
        row = cur.fetchone()
        print(f"   OK: {dict(row) if row else 'None'}")
except Exception as e:
    print(f"   ERREUR: {type(e).__name__}: {e}")

# Test 2: team_momentum (échoue)
print("\n2. team_momentum:")
try:
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(f"""
            SELECT team_name, momentum_score
            FROM team_momentum
            WHERE {where}
            LIMIT 1
        """, params)
        row = cur.fetchone()
        print(f"   OK: {dict(row) if row else 'None'}")
except Exception as e:
    print(f"   ERREUR: {type(e).__name__}: {e}")

# Test 3: team_class
print("\n3. team_class:")
try:
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(f"""
            SELECT team_name, tier
            FROM team_class
            WHERE {where}
            LIMIT 1
        """, params)
        row = cur.fetchone()
        print(f"   OK: {dict(row) if row else 'None'}")
except Exception as e:
    print(f"   ERREUR: {type(e).__name__}: {e}")

# Test 4: referee_intelligence
print("\n4. referee_intelligence:")
try:
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT referee_name, avg_goals_per_game
            FROM referee_intelligence
            WHERE LOWER(referee_name) LIKE %s
            LIMIT 1
        """, ('%michael oliver%',))
        row = cur.fetchone()
        print(f"   OK: {dict(row) if row else 'None'}")
except Exception as e:
    print(f"   ERREUR: {type(e).__name__}: {e}")

# Test 5: tactical_matrix
print("\n5. tactical_matrix:")
try:
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT style_a, style_b, btts_probability
            FROM tactical_matrix
            WHERE LOWER(style_a) = %s AND LOWER(style_b) = %s
            LIMIT 1
        """, ('balanced', 'offensive'))
        row = cur.fetchone()
        print(f"   OK: {dict(row) if row else 'None'}")
except Exception as e:
    print(f"   ERREUR: {type(e).__name__}: {e}")

# Test 6: Vérifier la connexion après erreurs
print("\n6. Etat connexion:")
print(f"   conn.closed: {conn.closed}")
print(f"   conn.status: {conn.status}")

conn.close()
print("\nDone")
