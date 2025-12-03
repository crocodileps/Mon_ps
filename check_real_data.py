#!/usr/bin/env python3
"""Vérifier les vraies données disponibles"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("DONNÉES RÉELLES DISPONIBLES")
print("="*70)

# 1. Structure market_traps
print("\n1. COLONNES market_traps:")
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'market_traps' ORDER BY ordinal_position
""")
cols = [r[0] for r in cur.fetchall()]
print(f"   {cols}")

# 2. Exemple de market_traps
print("\n2. EXEMPLE market_traps:")
cur.execute("SELECT * FROM market_traps LIMIT 3")
for r in cur.fetchall():
    print(f"   {dict(r)}")

# 3. Traps pour équipes espagnoles
print("\n3. TRAPS équipes espagnoles:")
cur.execute("""
    SELECT * FROM market_traps 
    WHERE LOWER(team_name) LIKE '%madrid%' 
       OR LOWER(team_name) LIKE '%barcelona%'
       OR LOWER(team_name) LIKE '%athletic%'
    LIMIT 5
""")
rows = cur.fetchall()
print(f"   Trouvé: {len(rows)}")
for r in rows:
    print(f"   {dict(r)}")

# 4. Odds history pour La Liga
print("\n4. ODDS_HISTORY La Liga (récent):")
cur.execute("""
    SELECT home_team, away_team, bookmaker, home_odds, draw_odds, away_odds, collected_at
    FROM odds_history
    WHERE LOWER(home_team) LIKE '%athletic%' 
       OR LOWER(home_team) LIKE '%bilbao%'
       OR LOWER(away_team) LIKE '%real madrid%'
    ORDER BY collected_at DESC
    LIMIT 5
""")
rows = cur.fetchall()
print(f"   Trouvé: {len(rows)}")
for r in rows:
    print(f"   {r['home_team']} vs {r['away_team']} @ {r['bookmaker']}: {r['home_odds']}/{r['draw_odds']}/{r['away_odds']}")

# 5. Voir le calcul Kelly actuel dans V10
print("\n5. KELLY ACTUEL dans V10:")
import subprocess
result = subprocess.run(
    ["grep", "-A10", "def _calculate_kelly", "/home/Mon_ps/backend/agents/clv_tracker/orchestrator_v10_quant_engine.py"],
    capture_output=True, text=True
)
print(result.stdout)

cur.close()
conn.close()
