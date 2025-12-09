#!/usr/bin/env python3
"""
🔬 DIAGNOSTIC DEFENDER DNA
Vérifie les données réellement collectées
"""

import json
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path('/home/Mon_ps/data/defender_dna')

# Charger les données
with open(DATA_DIR / 'all_defenders_dna.json', 'r') as f:
    defenders = json.load(f)

with open(DATA_DIR / 'defensive_lines.json', 'r') as f:
    lines = json.load(f)

print("=" * 80)
print("🔬 DIAGNOSTIC DEFENDER DNA")
print("=" * 80)

# 1. Stats globales
print(f"\n📊 STATS GLOBALES:")
print(f"   Total défenseurs: {len(defenders)}")
print(f"   Total lignes: {len(lines)}")

# 2. Distribution par position
print(f"\n📊 DISTRIBUTION PAR POSITION:")
pos_counts = defaultdict(int)
for d in defenders:
    pos_counts[d.get('position_category', 'UNKNOWN')] += 1

for pos, count in sorted(pos_counts.items(), key=lambda x: -x[1]):
    print(f"   {pos}: {count}")

# 3. Vérifier les données d'impact
print(f"\n📊 DONNÉES D'IMPACT:")
has_impact = sum(1 for d in defenders if d.get('impact_goals_conceded', 0) != 0)
has_matches_with = sum(1 for d in defenders if d.get('matches_analyzed_with', 0) > 0)
has_matches_without = sum(1 for d in defenders if d.get('matches_analyzed_without', 0) > 0)

print(f"   Avec impact != 0: {has_impact}")
print(f"   Avec matches_with > 0: {has_matches_with}")
print(f"   Avec matches_without > 0: {has_matches_without}")

# 4. Exemple de défenseurs
print(f"\n📋 EXEMPLES DE DÉFENSEURS (Arsenal):")
arsenal_def = [d for d in defenders if d.get('team') == 'Arsenal']
for d in arsenal_def[:5]:
    print(f"\n   {d['name']} ({d['position']} → {d['position_category']})")
    print(f"      Temps: {d['time']} min | Games: {d['games']}")
    print(f"      xGChain/90: {d.get('xGChain_90', 0):.3f} | xA/90: {d.get('xA_90', 0):.3f}")
    print(f"      Matches WITH: {d.get('matches_analyzed_with', 0)} | WITHOUT: {d.get('matches_analyzed_without', 0)}")
    print(f"      Impact: {d.get('impact_goals_conceded', 0)}")
    print(f"      CS% with: {d.get('clean_sheet_rate_with', 0)}% | without: {d.get('clean_sheet_rate_without', 0)}%")
    print(f"      Tags: {d.get('tags', [])}")
    print(f"      Type: {d.get('defender_type', '?')}")

# 5. Vérifier les CB spécifiquement
print(f"\n📋 TOUS LES CB (Center Backs):")
cbs = [d for d in defenders if d.get('position_category') == 'CB']
print(f"   Total CB: {len(cbs)}")

if cbs:
    # Top par xGBuildup (contribution au jeu)
    cbs_sorted = sorted(cbs, key=lambda x: x.get('xGBuildup_90', 0), reverse=True)
    print(f"\n   TOP 10 CB par xGBuildup/90:")
    for cb in cbs_sorted[:10]:
        print(f"      {cb['name']:<25} ({cb['team']:<18}) | {cb.get('xGBuildup_90', 0):.3f}")

# 6. Vérifier les latéraux
print(f"\n📋 TOUS LES LATÉRAUX:")
fullbacks = [d for d in defenders if d.get('position_category') in ['LB', 'RB']]
print(f"   Total LB: {sum(1 for d in fullbacks if d.get('position_category') == 'LB')}")
print(f"   Total RB: {sum(1 for d in fullbacks if d.get('position_category') == 'RB')}")

if fullbacks:
    fb_sorted = sorted(fullbacks, key=lambda x: x.get('xGChain_90', 0) + x.get('xA_90', 0), reverse=True)
    print(f"\n   TOP 10 Latéraux par (xGChain + xA)/90:")
    for fb in fb_sorted[:10]:
        output = fb.get('xGChain_90', 0) + fb.get('xA_90', 0)
        print(f"      {fb['name']:<25} ({fb['team']:<18}) | xGC: {fb.get('xGChain_90', 0):.3f} | xA: {fb.get('xA_90', 0):.3f}")

# 7. Vérifier les lignes défensives
print(f"\n📋 EXEMPLE LIGNE DÉFENSIVE (Arsenal):")
if 'Arsenal' in lines:
    line = lines['Arsenal']
    print(f"   Charnière: {line.get('charniere', {})}")
    print(f"   Left Flank: {line.get('left_flank', {})}")
    print(f"   Right Flank: {line.get('right_flank', {})}")
    print(f"   Vulnérabilités: {line.get('vulnerabilities', [])}")
    print(f"   Defensive Score: {line.get('defensive_score', 0)}")

# 8. Problème identifié
print(f"\n" + "=" * 80)
print("🔴 PROBLÈMES IDENTIFIÉS:")
print("=" * 80)

if has_matches_without == 0:
    print("""
   ⚠️ AUCUN joueur n'a de matches "WITHOUT" (sans lui)
   
   CAUSE: Les titulaires jouent TOUS les matchs analysés (15 matchs max)
   
   SOLUTION: Le calcul d'impact WITH/WITHOUT ne fonctionne que si le joueur
   a manqué des matchs. Pour les titulaires indiscutables, on doit utiliser
   d'autres métriques:
   
   1. xGBuildup_90: Contribution au jeu construit
   2. xGChain_90: Implication dans les actions offensives
   3. Cards_90: Tendance aux cartons
   4. Clean Sheet rate global de l'équipe quand il joue
""")

print(f"\n💡 Les données OFFENSIVES des défenseurs sont correctes!")
print(f"   → xGChain, xGBuildup, xA, goals, assists")
print(f"\n⚠️ Les données d'IMPACT WITH/WITHOUT nécessitent plus de matchs")
print(f"   → ou des blessures/rotations dans l'échantillon")
