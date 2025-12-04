#!/usr/bin/env python3
"""
Investigation: Pourquoi team_class donne toujours 0?
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
sys.path.insert(0, '/home/Mon_ps')
from orchestrator_v11_3_full_analysis import OrchestratorV11_3

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

print("=" * 80)
print("    INVESTIGATION LAYER TEAM_CLASS")
print("=" * 80)

# 1. Vérifier les données dans team_class
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("\n1️⃣ ÉCHANTILLON TEAM_CLASS (top clubs):")
cur.execute("""
    SELECT team_name, tier, calculated_power_index, historical_strength, big_game_factor
    FROM team_class
    WHERE team_name ILIKE ANY(ARRAY['%manchester%', '%barcelona%', '%real madrid%', 
                                     '%liverpool%', '%bayern%', '%psg%', '%arsenal%'])
    ORDER BY calculated_power_index DESC NULLS LAST
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"   {row['team_name'][:30]:30} | Tier:{row['tier']:3} | Power:{row['calculated_power_index'] or 'NULL':>5} | Hist:{row['historical_strength'] or 'NULL'}")

# 2. Charger l'orchestrator et tester un match connu
print("\n2️⃣ TEST ANALYSE MATCH (Arsenal vs Liverpool):")
orch = OrchestratorV11_3()

# Voir le cache team_class
print(f"\n   Cache team_class: {len(orch.cache.get('team_class', {}))} équipes")

# Chercher Arsenal et Liverpool dans le cache
arsenal_found = None
liverpool_found = None
for name, data in orch.cache.get('team_class', {}).items():
    if 'arsenal' in name.lower():
        arsenal_found = (name, data)
    if 'liverpool' in name.lower():
        liverpool_found = (name, data)

print(f"\n   Arsenal dans cache: {arsenal_found[0] if arsenal_found else 'NON TROUVÉ'}")
if arsenal_found:
    print(f"      → {arsenal_found[1]}")
print(f"\n   Liverpool dans cache: {liverpool_found[0] if liverpool_found else 'NON TROUVÉ'}")
if liverpool_found:
    print(f"      → {liverpool_found[1]}")

# 3. Analyser le match
print("\n3️⃣ ANALYSE DÉTAILLÉE:")
result = orch.analyze_match("Arsenal FC", "Liverpool FC", "over_25")
print(f"   Score total: {result['score']:.1f}")
print(f"   Action: {result['action']}")
print(f"   Layers détail:")
for layer, score in result.get('layer_scores', {}).items():
    print(f"      {layer}: {score:.2f}")

# 4. Regarder le code du layer team_class
print("\n4️⃣ VÉRIFICATION DU CODE:")
print("   Cherchons comment team_class est calculé dans l'orchestrator...")

# Chercher la méthode _analyze_team_class
import inspect
source = inspect.getsource(orch._analyze_team_class)
print("\n   Code de _analyze_team_class:")
for i, line in enumerate(source.split('\n')[:30]):
    print(f"   {i+1:3}: {line}")

conn.close()
print("\n" + "=" * 80)
