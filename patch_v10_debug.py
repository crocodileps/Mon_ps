#!/usr/bin/env python3
"""Patch V10 - Ajouter debug dans prefetch"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')

# Charger mappings
source_to_canonical = {}
canonical_to_sources = {}

cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
cur.execute("SELECT source_name, canonical_name FROM team_name_mapping")
for r in cur.fetchall():
    src, can = r["source_name"], r["canonical_name"]
    source_to_canonical[src.lower()] = can
    if can.lower() not in canonical_to_sources:
        canonical_to_sources[can.lower()] = set()
    canonical_to_sources[can.lower()].add(src)
    canonical_to_sources[can.lower()].add(can)

def resolve(name):
    nl = name.lower().strip()
    variants = {name, nl}
    if nl in source_to_canonical:
        c = source_to_canonical[nl]
        variants.add(c)
        variants.add(c.lower())
    if nl in canonical_to_sources:
        variants.update(canonical_to_sources[nl])
    if nl.endswith(" fc"):
        variants.add(nl[:-3].strip())
    else:
        variants.add(nl + " fc")
        variants.add(name + " FC")
    return list(variants)

def build_where(col, name):
    vs = resolve(name)
    conds = [f"LOWER({col}) = %s" for _ in vs[:10]]
    return f"({' OR '.join(conds)})", [v.lower() for v in vs[:10]]

print("="*70)
print("🔧 TEST FETCH DIRECT (comme V10)")
print("="*70)

team = "Liverpool"
w, p = build_where("team_name", team)
print(f"\nWHERE clause: {w}")
print(f"Params: {p[:5]}...")

# Test momentum
print(f"\n--- TEST MOMENTUM ---")
try:
    cur.execute(f"SELECT team_name, momentum_score FROM team_momentum WHERE {w} LIMIT 1", p)
    r = cur.fetchone()
    print(f"Résultat: {dict(r) if r else 'None'}")
except Exception as e:
    print(f"ERREUR: {e}")

# Test avec requête simple
print(f"\n--- TEST MOMENTUM SIMPLE ---")
cur.execute("SELECT team_name, momentum_score FROM team_momentum WHERE LOWER(team_name) = 'liverpool fc' LIMIT 1")
r = cur.fetchone()
print(f"Résultat simple: {dict(r) if r else 'None'}")

# Vérifier les variantes
print(f"\n--- VARIANTES GÉNÉRÉES ---")
variants = resolve("Liverpool")
print(f"Liverpool: {variants}")

# Tester chaque variante
print(f"\n--- TEST CHAQUE VARIANTE ---")
for v in variants[:6]:
    cur.execute("SELECT team_name, momentum_score FROM team_momentum WHERE LOWER(team_name) = %s", (v.lower(),))
    r = cur.fetchone()
    status = f"✅ {dict(r)['momentum_score']}" if r else "❌"
    print(f"  '{v.lower()}': {status}")

cur.close()
conn.close()
print("\n✅ Test terminé")
