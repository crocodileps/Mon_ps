#!/usr/bin/env python3
"""Debug V10 - Pourquoi certains layers retournent 0"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

# Charger mappings
source_to_canonical = {}
canonical_to_sources = {}

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

print("="*70)
print("🔍 DEBUG V10 - LAYERS")
print("="*70)

teams = ["Liverpool", "Manchester City"]

for team in teams:
    print(f"\n{'='*70}")
    print(f"TEAM: {team}")
    print(f"{'='*70}")
    
    variants = resolve(team)
    print(f"Variantes générées: {variants[:5]}...")
    
    # Build WHERE clause
    conds = " OR ".join([f"LOWER(team_name) = '{v.lower()}'" for v in variants[:8]])
    
    # 1. team_intelligence
    print(f"\n1. TEAM_INTELLIGENCE:")
    cur.execute(f"SELECT team_name, current_style, btts_tendency, xg_for_avg FROM team_intelligence WHERE {conds} LIMIT 1")
    r = cur.fetchone()
    if r:
        print(f"   ✅ TROUVÉ: {r['team_name']} - style={r['current_style']}, btts={r['btts_tendency']}, xg={r['xg_for_avg']}")
    else:
        print(f"   ❌ PAS TROUVÉ")
    
    # 2. team_momentum
    print(f"\n2. TEAM_MOMENTUM:")
    cur.execute(f"SELECT team_name, momentum_score FROM team_momentum WHERE {conds} LIMIT 1")
    r = cur.fetchone()
    if r:
        print(f"   ✅ TROUVÉ: {r['team_name']} - momentum={r['momentum_score']}")
    else:
        print(f"   ❌ PAS TROUVÉ")
        # Chercher ce qui existe
        cur.execute("SELECT team_name FROM team_momentum WHERE LOWER(team_name) LIKE '%liver%' OR LOWER(team_name) LIKE '%city%' LIMIT 5")
        print(f"   Existant: {[r[0] for r in cur.fetchall()]}")
    
    # 3. team_class
    print(f"\n3. TEAM_CLASS:")
    cur.execute(f"SELECT team_name, tier, playing_style FROM team_class WHERE {conds} LIMIT 1")
    r = cur.fetchone()
    if r:
        print(f"   ✅ TROUVÉ: {r['team_name']} - tier={r['tier']}, style={r['playing_style']}")
    else:
        print(f"   ❌ PAS TROUVÉ")

# 4. Tactical matrix
print(f"\n{'='*70}")
print("4. TACTICAL_MATRIX (balanced vs balanced):")
cur.execute("SELECT style_a, style_b, btts_probability, over_25_probability FROM tactical_matrix WHERE style_a='balanced' AND style_b='balanced'")
r = cur.fetchone()
if r:
    print(f"   ✅ TROUVÉ: btts={r['btts_probability']}%, over25={r['over_25_probability']}%")
else:
    print(f"   ❌ PAS TROUVÉ")

# 5. Referee
print(f"\n5. REFEREE (Michael Oliver):")
cur.execute("SELECT referee_name, avg_goals_per_game, under_over_tendency FROM referee_intelligence WHERE LOWER(referee_name) LIKE '%oliver%'")
r = cur.fetchone()
if r:
    print(f"   ✅ TROUVÉ: {r['referee_name']} - goals={r['avg_goals_per_game']}, tendency={r['under_over_tendency']}")
else:
    print(f"   ❌ PAS TROUVÉ")

# 6. H2H
print(f"\n6. HEAD_TO_HEAD (Liverpool vs Manchester City):")
liv_vars = resolve("Liverpool")[:5]
city_vars = resolve("Manchester City")[:5]

found_h2h = False
for lv in liv_vars:
    for cv in city_vars:
        cur.execute("""
            SELECT team_a, team_b, btts_pct, over_25_pct, total_matches 
            FROM team_head_to_head 
            WHERE (LOWER(team_a)=%s AND LOWER(team_b)=%s)
               OR (LOWER(team_a)=%s AND LOWER(team_b)=%s)
            LIMIT 1
        """, (lv.lower(), cv.lower(), cv.lower(), lv.lower()))
        r = cur.fetchone()
        if r:
            print(f"   ✅ TROUVÉ: {r['team_a']} vs {r['team_b']} - btts={r['btts_pct']}%, matches={r['total_matches']}")
            found_h2h = True
            break
    if found_h2h:
        break

if not found_h2h:
    print(f"   ❌ PAS TROUVÉ")
    cur.execute("SELECT team_a, team_b FROM team_head_to_head WHERE LOWER(team_a) LIKE '%liver%' OR LOWER(team_b) LIKE '%liver%' LIMIT 3")
    print(f"   Existant: {[(r[0], r[1]) for r in cur.fetchall()]}")

cur.close()
conn.close()
print(f"\n✅ Debug terminé")
