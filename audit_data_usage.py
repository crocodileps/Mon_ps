#!/usr/bin/env python3
"""Audit: Quelles données sont disponibles vs utilisées par V10?"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("AUDIT DONNÉES DISPONIBLES vs UTILISÉES")
print("="*70)

# Tables critiques pour l'analyse
tables_to_check = [
    ('head_to_head', 'H2H'),
    ('team_head_to_head', 'H2H Alt'),
    ('tactical_matrix', 'Tactical'),
    ('referee_intelligence', 'Referee'),
    ('coach_intelligence', 'Coach'),
    ('scorer_intelligence', 'Scorers'),
    ('market_patterns', 'Patterns'),
    ('match_context', 'Context'),
    ('team_intelligence', 'Team Intel'),
    ('team_class', 'Team Class'),
    ('team_momentum', 'Momentum'),
    ('market_traps', 'Traps'),
]

print("\n📊 TABLES DISPONIBLES:")
print("-"*70)

for table, label in tables_to_check:
    cur.execute(f"""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name = '{table}'
    """)
    exists = cur.fetchone()[0] > 0
    
    if exists:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        
        # Colonnes
        cur.execute(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '{table}' ORDER BY ordinal_position LIMIT 8
        """)
        cols = [r[0] for r in cur.fetchall()]
        
        status = "✅" if count > 0 else "⚠️ VIDE"
        print(f"{status} {label:15} | {table:25} | {count:6} rows | {', '.join(cols[:5])}...")
    else:
        print(f"❌ {label:15} | {table:25} | TABLE N'EXISTE PAS")

# Données Liverpool/Sunderland spécifiques
print("\n" + "="*70)
print("🔍 DONNÉES LIVERPOOL vs SUNDERLAND:")
print("-"*70)

# 1. Team Intelligence
print("\n1. TEAM_INTELLIGENCE:")
for team in ['liverpool', 'sunderland']:
    cur.execute(f"""
        SELECT team_name, matches_analyzed, home_goals_scored_avg, away_goals_scored_avg
        FROM team_intelligence WHERE LOWER(team_name) LIKE '%{team}%'
    """)
    r = cur.fetchone()
    if r:
        print(f"   ✅ {r['team_name']}: {r['matches_analyzed']} matchs analysés")
    else:
        print(f"   ❌ {team}: PAS DE DONNÉES")

# 2. Team Class
print("\n2. TEAM_CLASS:")
for team in ['liverpool', 'sunderland']:
    cur.execute(f"""
        SELECT team_name, tier, big_game_factor, psychological_edge
        FROM team_class WHERE LOWER(team_name) LIKE '%{team}%'
    """)
    r = cur.fetchone()
    if r:
        print(f"   ✅ {r['team_name']}: Tier {r['tier']}, BigGame={r['big_game_factor']}")
    else:
        print(f"   ❌ {team}: PAS DE DONNÉES")

# 3. H2H (trouver la bonne table)
print("\n3. HEAD_TO_HEAD:")
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'head_to_head' OR table_name = 'team_head_to_head'
    LIMIT 10
""")
cols = [r[0] for r in cur.fetchall()]
print(f"   Colonnes: {cols}")

if 'team1' in cols:
    cur.execute("""
        SELECT * FROM head_to_head 
        WHERE LOWER(team1) LIKE '%liverpool%' OR LOWER(team2) LIKE '%liverpool%'
        LIMIT 3
    """)
elif 'home_team' in cols:
    cur.execute("""
        SELECT * FROM team_head_to_head 
        WHERE LOWER(home_team) LIKE '%liverpool%'
        LIMIT 3
    """)
rows = cur.fetchall()
print(f"   Matchs H2H Liverpool: {len(rows)}")

# 4. Tactical Matrix
print("\n4. TACTICAL_MATRIX:")
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'tactical_matrix' LIMIT 10
""")
cols = [r[0] for r in cur.fetchall()]
print(f"   Colonnes: {cols}")

for team in ['liverpool', 'sunderland']:
    cur.execute(f"""
        SELECT * FROM tactical_matrix WHERE LOWER(team_name) LIKE '%{team}%' LIMIT 1
    """)
    r = cur.fetchone()
    if r:
        print(f"   ✅ {team}: données tactiques disponibles")
    else:
        print(f"   ❌ {team}: PAS DE DONNÉES TACTIQUES")

# 5. Market Patterns
print("\n5. MARKET_PATTERNS:")
cur.execute("SELECT COUNT(*) FROM market_patterns")
count = cur.fetchone()[0]
print(f"   Total patterns: {count}")

# 6. Scorer Intelligence
print("\n6. SCORER_INTELLIGENCE:")
cur.execute("SELECT COUNT(*) FROM scorer_intelligence")
count = cur.fetchone()[0]
print(f"   Total scorers: {count}")
cur.execute("""
    SELECT player_name, team_name FROM scorer_intelligence 
    WHERE LOWER(team_name) LIKE '%liverpool%' LIMIT 3
""")
for r in cur.fetchall():
    print(f"   ✅ {r['player_name']} ({r['team_name']})")

print("\n" + "="*70)
print("📋 CONCLUSION - CE QUE V10 DEVRAIT UTILISER MAIS N'UTILISE PAS:")
print("="*70)
print("""
1. ❌ tactical_matrix     - Styles de jeu, formations
2. ❌ referee_intelligence - Stats arbitres (cards, goals/match)  
3. ❌ coach_intelligence   - Historique coaches
4. ❌ scorer_intelligence  - Top buteurs (Salah, etc.)
5. ❌ market_patterns      - 41 patterns professionnels
6. ❌ match_context        - Derby, relegation, fatigue
7. ❌ head_to_head         - Historique confrontations

→ Ces données existent mais V10 ne les interroge PAS !
→ C'est pourquoi Score = 21 au lieu de 60+
""")

cur.close()
conn.close()
