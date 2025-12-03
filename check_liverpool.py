import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print('MATCHS LIVERPOOL dans match_results:')
cur.execute("""
    SELECT home_team, away_team, score_home, score_away, league
    FROM match_results 
    WHERE LOWER(home_team) LIKE '%liverpool%' OR LOWER(away_team) LIKE '%liverpool%'
    ORDER BY commence_time DESC
    LIMIT 15
""")
for r in cur.fetchall():
    print(f"   {r['home_team']} {r['score_home']}-{r['score_away']} {r['away_team']} ({r['league']})")

print()
print('NOM EXACT LIVERPOOL dans match_results:')
cur.execute("SELECT DISTINCT home_team FROM match_results WHERE LOWER(home_team) LIKE '%liverpool%'")
for r in cur.fetchall():
    print(f"   '{r['home_team']}'")
    
print()
print('NOM EXACT LIVERPOOL dans team_intelligence:')
cur.execute("SELECT DISTINCT team_name FROM team_intelligence WHERE LOWER(team_name) LIKE '%liverpool%'")
for r in cur.fetchall():
    print(f"   '{r['team_name']}'")

cur.close()
conn.close()
