#!/usr/bin/env python3
"""
Corriger les statistiques team_intelligence avec correspondance flexible des noms
"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("CORRECTION STATS AVEC CORRESPONDANCE FLEXIBLE")
print("="*70)

# Récupérer toutes les équipes de team_intelligence
cur.execute("SELECT DISTINCT team_name FROM team_intelligence")
teams = [r['team_name'] for r in cur.fetchall()]

print(f"\n{len(teams)} équipes à traiter...")

updated = 0
details = []

for team in teams:
    # Créer pattern de recherche flexible
    # "Liverpool" -> "%liverpool%"
    pattern = f"%{team.lower()}%"
    
    # Stats HOME (PL uniquement)
    cur.execute("""
        SELECT 
            AVG(score_home) as home_scored,
            AVG(score_away) as home_conceded,
            COUNT(*) as matches
        FROM match_results
        WHERE LOWER(home_team) LIKE %s 
        AND league = 'Premier League'
        AND is_finished = true
    """, (pattern,))
    home = cur.fetchone()
    
    # Stats AWAY (PL uniquement)
    cur.execute("""
        SELECT 
            AVG(score_away) as away_scored,
            AVG(score_home) as away_conceded,
            COUNT(*) as matches
        FROM match_results
        WHERE LOWER(away_team) LIKE %s
        AND league = 'Premier League'
        AND is_finished = true
    """, (pattern,))
    away = cur.fetchone()
    
    home_matches = home['matches'] or 0
    away_matches = away['matches'] or 0
    total = home_matches + away_matches
    
    if total >= 2:
        home_scored = float(home['home_scored']) if home['home_scored'] else None
        home_conceded = float(home['home_conceded']) if home['home_conceded'] else None
        away_scored = float(away['away_scored']) if away['away_scored'] else None
        away_conceded = float(away['away_conceded']) if away['away_conceded'] else None
        
        if home_scored is not None:
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
                details.append({
                    'team': team,
                    'home_scored': home_scored,
                    'home_conceded': home_conceded,
                    'away_scored': away_scored,
                    'away_conceded': away_conceded,
                    'matches': total
                })

conn.commit()

print(f"\n{updated} équipes mises à jour:")
print("-"*70)

# Afficher les équipes importantes
important = ['Liverpool', 'Arsenal', 'Manchester', 'Chelsea', 'Tottenham', 'City', 'Sunderland']
for d in details:
    if any(imp.lower() in d['team'].lower() for imp in important):
        print(f"   {d['team']} ({d['matches']} matchs):")
        print(f"      Home: scored={d['home_scored']:.2f}, conceded={d['home_conceded']:.2f}")
        print(f"      Away: scored={d['away_scored']:.2f}, conceded={d['away_conceded']:.2f}")

# Vérification finale
print("\n" + "="*70)
print("VERIFICATION FINALE:")
print("="*70)

for team in ['Liverpool', 'Sunderland', 'Arsenal', 'Chelsea']:
    cur.execute("""
        SELECT team_name, home_goals_scored_avg, home_goals_conceded_avg,
               away_goals_scored_avg, away_goals_conceded_avg
        FROM team_intelligence 
        WHERE LOWER(team_name) LIKE %s
    """, (f"%{team.lower()}%",))
    for r in cur.fetchall():
        print(f"\n   {r['team_name']}:")
        print(f"      Home: scored={r['home_goals_scored_avg']}, conceded={r['home_goals_conceded_avg']}")
        print(f"      Away: scored={r['away_goals_scored_avg']}, conceded={r['away_goals_conceded_avg']}")

cur.close()
conn.close()
