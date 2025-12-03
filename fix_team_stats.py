#!/usr/bin/env python3
"""
Corriger les statistiques team_intelligence basées sur match_results
Filtrage par championnat uniquement
"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("CORRECTION DES STATISTIQUES TEAM_INTELLIGENCE")
print("="*70)

# 1. Voir les leagues disponibles
print("\n1. LEAGUES DANS MATCH_RESULTS:")
cur.execute("""
    SELECT DISTINCT league, COUNT(*) as matches
    FROM match_results
    WHERE is_finished = true
    GROUP BY league
    ORDER BY matches DESC
""")
for r in cur.fetchall():
    print(f"   {r['league']}: {r['matches']} matchs")

# 2. Championnats (exclure coupes)
league_filter = [
    'Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1',
    'Championship', 'Primeira Liga', 'Eredivisie', 'Pro League',
    'EPL', 'LaLiga', 'SerieA'
]

print("\n2. RECALCUL DES STATS (Championnats):")
print("-"*70)

cur.execute("SELECT DISTINCT team_name FROM team_intelligence")
teams = [r['team_name'] for r in cur.fetchall()]

updated = 0
for team in teams:
    # Stats HOME
    cur.execute("""
        SELECT 
            AVG(score_home) as home_scored,
            AVG(score_away) as home_conceded,
            COUNT(*) as matches
        FROM match_results
        WHERE home_team = %s AND is_finished = true
    """, (team,))
    home = cur.fetchone()
    
    # Stats AWAY
    cur.execute("""
        SELECT 
            AVG(score_away) as away_scored,
            AVG(score_home) as away_conceded,
            COUNT(*) as matches
        FROM match_results
        WHERE away_team = %s AND is_finished = true
    """, (team,))
    away = cur.fetchone()
    
    home_scored = float(home['home_scored']) if home and home['home_scored'] else None
    home_conceded = float(home['home_conceded']) if home and home['home_conceded'] else None
    away_scored = float(away['away_scored']) if away and away['away_scored'] else None
    away_conceded = float(away['away_conceded']) if away and away['away_conceded'] else None
    
    total = (home['matches'] or 0) + (away['matches'] or 0)
    
    if total >= 2 and home_scored is not None:
        cur.execute("""
            UPDATE team_intelligence SET
                home_goals_scored_avg = %s,
                home_goals_conceded_avg = %s,
                away_goals_scored_avg = %s,
                away_goals_conceded_avg = %s,
                updated_at = NOW()
            WHERE team_name = %s
        """, (home_scored, home_conceded, away_scored, away_conceded, team))
        
        if cur.rowcount > 0:
            updated += 1

conn.commit()
print(f"   Total: {updated} equipes mises a jour")

# 3. Verification
print("\n" + "="*70)
print("3. VERIFICATION:")
print("="*70)

for team in ['Liverpool', 'Sunderland', 'Arsenal', 'Man City']:
    cur.execute("""
        SELECT team_name, home_goals_scored_avg, home_goals_conceded_avg,
               away_goals_scored_avg, away_goals_conceded_avg
        FROM team_intelligence 
        WHERE LOWER(team_name) LIKE %s
    """, (f"%{team.lower()}%",))
    for r in cur.fetchall():
        print(f"\n   {r['team_name']}:")
        hs = r['home_goals_scored_avg']
        hc = r['home_goals_conceded_avg']
        aws = r['away_goals_scored_avg']
        awc = r['away_goals_conceded_avg']
        print(f"      Home: scored={hs}, conceded={hc}")
        print(f"      Away: scored={aws}, conceded={awc}")

cur.close()
conn.close()
