#!/usr/bin/env python3
import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*60)
print("VÉRIFICATION STEAM & TRAPS")
print("="*60)

# 1. Market traps pour Bilbao/Madrid
print("\n1. MARKET_TRAPS:")
cur.execute("""
    SELECT team_name, trap_type, market, description 
    FROM market_traps 
    WHERE LOWER(team_name) LIKE '%bilbao%' 
       OR LOWER(team_name) LIKE '%athletic%'
       OR LOWER(team_name) LIKE '%madrid%'
    LIMIT 10
""")
rows = cur.fetchall()
print(f"   Trouvé: {len(rows)} traps")
for r in rows:
    print(f"   - {r['team_name']}: {r['trap_type']} ({r['market']})")

# 2. Odds history récent
print("\n2. ODDS_HISTORY (récent):")
cur.execute("""
    SELECT home_team, away_team, bookmaker, home_odds, away_odds, collected_at
    FROM odds_history
    WHERE LOWER(home_team) LIKE '%athletic%' OR LOWER(away_team) LIKE '%real madrid%'
    ORDER BY collected_at DESC
    LIMIT 5
""")
rows = cur.fetchall()
print(f"   Trouvé: {len(rows)} entrées")
for r in rows:
    print(f"   - {r['home_team']} vs {r['away_team']}: {r['home_odds']}/{r['away_odds']} ({r['collected_at']})")

# 3. Nombre total d'entrées odds_history
cur.execute("SELECT COUNT(*) FROM odds_history")
total = cur.fetchone()[0]
print(f"\n3. Total odds_history: {total} entrées")

cur.close()
conn.close()
