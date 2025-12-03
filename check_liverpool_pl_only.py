#!/usr/bin/env python3
"""Stats Liverpool - Premier League uniquement"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*70)
print("LIVERPOOL - STATS PAR COMPÉTITION")
print("="*70)

# Stats par compétition
print("\n1. MATCHS À DOMICILE PAR COMPÉTITION:")
cur.execute("""
    SELECT league, 
           COUNT(*) as matchs,
           AVG(score_home) as avg_scored,
           AVG(score_away) as avg_conceded,
           SUM(CASE WHEN score_away = 0 THEN 1 ELSE 0 END) as clean_sheets
    FROM match_results 
    WHERE LOWER(home_team) LIKE '%liverpool%'
      AND is_finished = TRUE
    GROUP BY league
    ORDER BY matchs DESC
""")
for r in cur.fetchall():
    cs_pct = (r['clean_sheets'] / r['matchs'] * 100) if r['matchs'] > 0 else 0
    print(f"\n   {r['league']}:")
    print(f"      Matchs: {r['matchs']}")
    print(f"      Marqués: {float(r['avg_scored']):.2f}")
    print(f"      Encaissés: {float(r['avg_conceded']):.2f}")
    print(f"      Clean sheets: {r['clean_sheets']} ({cs_pct:.0f}%)")

# Premier League uniquement
print("\n" + "="*70)
print("2. DÉTAIL PREMIER LEAGUE (HOME):")
print("="*70)
cur.execute("""
    SELECT home_team, away_team, score_home, score_away, commence_time
    FROM match_results 
    WHERE LOWER(home_team) LIKE '%liverpool%'
      AND (LOWER(league) LIKE '%premier%' OR LOWER(league) LIKE '%epl%')
      AND is_finished = TRUE
    ORDER BY commence_time DESC
    LIMIT 10
""")
total_conceded = 0
count = 0
for r in cur.fetchall():
    print(f"   {r['commence_time'].strftime('%Y-%m-%d')}: Liverpool {r['score_home']}-{r['score_away']} {r['away_team']}")
    total_conceded += r['score_away']
    count += 1

if count > 0:
    print(f"\n   📊 VRAIE moyenne PL: {total_conceded/count:.2f} encaissés sur {count} matchs")

cur.close()
conn.close()
