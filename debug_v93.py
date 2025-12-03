#!/usr/bin/env python3
"""Debug V9.3 - Pourquoi les layers retournent 0"""

import psycopg2
import psycopg2.extras
import os

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("🔍 DEBUG V9.3 - RÉSOLUTION DE NOMS")
print("="*70)

# Test team_name_mapping
print("\n1. TEAM_NAME_MAPPING - Liverpool:")
cur.execute("""
    SELECT source_name, canonical_name, normalized_name 
    FROM team_name_mapping 
    WHERE LOWER(source_name) LIKE '%liverpool%' 
       OR LOWER(canonical_name) LIKE '%liverpool%'
""")
for r in cur.fetchall():
    print(f"   {r['source_name']} → {r['canonical_name']} ({r['normalized_name']})")

# Test ce que retourne _resolve_team_name
print("\n2. VARIANTES GÉNÉRÉES pour 'Liverpool':")
team = "Liverpool"
variants = [team, team.lower(), team + ' FC', team.lower() + ' fc']
for v in variants:
    print(f"   • {v}")

# Test direct sur team_momentum
print("\n3. TEAM_MOMENTUM - Recherche 'Liverpool':")
for v in variants:
    cur.execute("SELECT team_name, momentum_score FROM team_momentum WHERE LOWER(team_name) = %s", (v.lower(),))
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"   ✅ TROUVÉ avec '{v}': {r['team_name']} = {r['momentum_score']}")
    else:
        print(f"   ❌ Pas trouvé avec: '{v}'")

# Voir le vrai nom dans team_momentum
print("\n4. NOMS EXACTS dans team_momentum (LIKE '%liver%'):")
cur.execute("SELECT team_name FROM team_momentum WHERE LOWER(team_name) LIKE '%liver%'")
for r in cur.fetchall():
    print(f"   → '{r['team_name']}' (len={len(r['team_name'])})")
    # Afficher les caractères
    print(f"      Bytes: {[hex(ord(c)) for c in r['team_name']]}")

# Test direct sur team_intelligence
print("\n5. TEAM_INTELLIGENCE - Recherche 'Liverpool':")
for v in variants:
    cur.execute("SELECT team_name, current_style, btts_tendency FROM team_intelligence WHERE LOWER(team_name) = %s", (v.lower(),))
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"   ✅ TROUVÉ avec '{v}': {r['team_name']} - style={r['current_style']}")
    else:
        print(f"   ❌ Pas trouvé avec: '{v}'")

print("\n6. NOMS EXACTS dans team_intelligence (LIKE '%liver%'):")
cur.execute("SELECT team_name FROM team_intelligence WHERE LOWER(team_name) LIKE '%liver%'")
for r in cur.fetchall():
    print(f"   → '{r['team_name']}' (len={len(r['team_name'])})")

# Test team_class
print("\n7. TEAM_CLASS - Recherche 'Liverpool':")
cur.execute("SELECT team_name, tier, playing_style FROM team_class WHERE LOWER(team_name) LIKE '%liver%'")
for r in cur.fetchall():
    print(f"   → '{r['team_name']}' - Tier={r['tier']}, Style={r['playing_style']}")

# Test referee
print("\n8. REFEREE_INTELLIGENCE - 'Michael Oliver':")
cur.execute("SELECT referee_name, league, avg_goals_per_game FROM referee_intelligence WHERE LOWER(referee_name) LIKE '%oliver%'")
for r in cur.fetchall():
    print(f"   → '{r['referee_name']}' - {r['league']} - {r['avg_goals_per_game']} buts/match")

# Test H2H
print("\n9. TEAM_HEAD_TO_HEAD - Liverpool vs Manchester:")
cur.execute("""
    SELECT team_a, team_b, btts_pct 
    FROM team_head_to_head 
    WHERE (LOWER(team_a) LIKE '%liverpool%' AND LOWER(team_b) LIKE '%manchester%')
       OR (LOWER(team_a) LIKE '%manchester%' AND LOWER(team_b) LIKE '%liverpool%')
""")
for r in cur.fetchall():
    print(f"   → {r['team_a']} vs {r['team_b']} - BTTS={r['btts_pct']}%")

# Test tactical_matrix
print("\n10. TACTICAL_MATRIX - styles disponibles:")
cur.execute("SELECT DISTINCT style_a FROM tactical_matrix LIMIT 10")
styles = [r['style_a'] for r in cur.fetchall()]
print(f"   Styles: {', '.join(styles)}")

# Test avec 'balanced'
print("\n11. TACTICAL_MATRIX - 'balanced vs balanced':")
cur.execute("SELECT style_a, style_b, btts_probability FROM tactical_matrix WHERE style_a = 'balanced' AND style_b = 'balanced'")
for r in cur.fetchall():
    print(f"   → {r['style_a']} vs {r['style_b']} - BTTS={r['btts_probability']}%")

cur.close()
conn.close()
print("\n✅ Debug terminé")
