#!/usr/bin/env python3
"""Debug _get_team_momentum"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')

# Charger mappings comme V10
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

print("="*60)
print("DEBUG MOMENTUM STEP BY STEP")
print("="*60)

team = "Liverpool"

# Step 1: resolve
print(f"\n1. resolve('{team}'):")
variants = resolve(team)
print(f"   {variants}")

# Step 2: build_where  
print(f"\n2. build_where('team_name', '{team}'):")
where, params = build_where('team_name', team)
print(f"   WHERE: {where}")
print(f"   PARAMS: {params}")

# Step 3: Requête complète comme V10
print(f"\n3. Requête team_momentum:")
query = f"""
    SELECT 
        team_name, momentum_score,
        goals_scored_last_5, goals_conceded_last_5,
        form_last_5, win_streak, unbeaten_streak,
        key_player_absent, key_absence_impact
    FROM team_momentum
    WHERE {where}
    LIMIT 1
"""
print(f"   Query:\n{query}")
print(f"   Params: {params}")

try:
    cur.execute(query, params)
    row = cur.fetchone()
    print(f"\n   RESULTAT: {dict(row) if row else 'None'}")
except Exception as e:
    print(f"\n   ERREUR: {type(e).__name__}: {e}")

# Step 4: Comparer avec ce que fait V10
print(f"\n4. Importer et tester V10 directement:")
import sys
sys.path.insert(0, '/home/Mon_ps/backend/agents/clv_tracker')
from orchestrator_v10_quant_engine import OrchestratorV10Quant

orch = OrchestratorV10Quant()

# Voir les variantes V10
print(f"\n   V10 _resolve_team_name('{team}'):")
v10_variants = orch._resolve_team_name(team)
print(f"   {v10_variants}")

print(f"\n   V10 _build_name_where('team_name', '{team}'):")
v10_where, v10_params = orch._build_name_where('team_name', team)
print(f"   WHERE: {v10_where}")
print(f"   PARAMS: {v10_params}")

# Différences?
print(f"\n5. COMPARAISON:")
print(f"   Local params: {sorted(params)}")
print(f"   V10 params:   {sorted(v10_params)}")
print(f"   Identiques:   {sorted(params) == sorted(v10_params)}")

cur.close()
conn.close()
print("\nDone")
