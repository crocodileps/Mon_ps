#!/usr/bin/env python3
"""Vérifier d'où viennent les données Liverpool"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("AUDIT DONNÉES LIVERPOOL")
print("="*70)

# 1. Données team_intelligence
print("\n1. TEAM_INTELLIGENCE Liverpool:")
cur.execute("""
    SELECT team_name, matches_analyzed, data_sources,
           home_goals_scored_avg, home_goals_conceded_avg,
           away_goals_scored_avg, away_goals_conceded_avg,
           home_win_rate, home_clean_sheet_rate
    FROM team_intelligence 
    WHERE LOWER(team_name) LIKE '%liverpool%'
""")
row = cur.fetchone()
if row:
    print(f"   Matchs analysés: {row['matches_analyzed']}")
    print(f"   Sources: {row['data_sources']}")
    print(f"   HOME: {row['home_goals_scored_avg']} marqués / {row['home_goals_conceded_avg']} encaissés")
    print(f"   AWAY: {row['away_goals_scored_avg']} marqués / {row['away_goals_conceded_avg']} encaissés")
    print(f"   Win rate HOME: {row['home_win_rate']}%")
    print(f"   Clean sheet HOME: {row['home_clean_sheet_rate']}%")

# 2. Comparer avec autres top teams
print("\n2. COMPARAISON TOP TEAMS (buts encaissés à domicile):")
cur.execute("""
    SELECT team_name, home_goals_conceded_avg, home_clean_sheet_rate, matches_analyzed
    FROM team_intelligence 
    WHERE team_name IN ('Liverpool', 'Arsenal', 'Manchester City', 'Real Madrid', 'Barcelona', 'Bayern Munich')
    ORDER BY home_goals_conceded_avg
""")
for r in cur.fetchall():
    print(f"   {r['team_name']}: {r['home_goals_conceded_avg']} encaissés (CS: {r['home_clean_sheet_rate']}%, {r['matches_analyzed']} matchs)")

# 3. Vérifier les résultats réels de Liverpool à domicile
print("\n3. DERNIERS RÉSULTATS LIVERPOOL (si disponibles):")
cur.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_name LIKE '%match%' OR table_name LIKE '%result%'
""")
tables = [r[0] for r in cur.fetchall()]
print(f"   Tables disponibles: {tables}")

# 4. Le problème probable
print("\n" + "="*70)
print("⚠️  DIAGNOSTIC:")
print("="*70)
print("""
Les données Liverpool semblent incorrectes:
- 1.56 buts encaissés à domicile est TRÈS élevé
- Liverpool a la meilleure défense de PL (0.4-0.6 en réalité)
- Clean sheet rate de seulement {cs}% confirme le problème

CAUSE PROBABLE:
- Petit échantillon (9 matchs seulement)
- Inclut peut-être des matchs de coupe contre des équipes fortes
- Ou données pas à jour

SOLUTION: Appliquer la régression vers la moyenne de la ligue
""".format(cs=row['home_clean_sheet_rate'] if row else 'N/A'))

cur.close()
conn.close()
