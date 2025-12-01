#!/usr/bin/env python3
"""
Agent Coach V5 - Utilise coach_team_mapping (donnees fiables)
Plus d'API Football-Data.org corrompue!
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

conn = psycopg2.connect(
    host='postgres', port=5432, database='monps_db',
    user='monps_user', password='monps_secure_password_2024'
)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("="*70)
print("AGENT COACH V5 - MAPPING FIABLE")
print("="*70)

# 1. Date max
cur.execute("SELECT MAX(commence_time)::date as max FROM match_results WHERE is_finished = true")
max_date = cur.fetchone()['max']
data_start = max_date - timedelta(days=180)
print(f"Periode: {data_start} -> {max_date}")

# 2. Charger le mapping FIABLE
cur.execute("SELECT team_name, coach_name, league, contract_start FROM coach_team_mapping WHERE is_verified = true")
coaches = []
for r in cur.fetchall():
    coaches.append({
        'name': r['coach_name'],
        'team': r['team_name'],
        'league': r['league'],
        'contract_start': r['contract_start']
    })
print(f"Coaches charges: {len(coaches)}")

# 3. Calculer stats pour chaque coach
enriched = 0
new_mgr = 0
all_stats = []

for c in coaches:
    team = c['team']
    start = data_start
    is_new = False
    
    if c['contract_start']:
        cs = c['contract_start']
        if cs > data_start:
            start = cs
        if (max_date - cs).days < 45:
            is_new = True
            new_mgr += 1
    
    # Stats HOME
    cur.execute("""
        SELECT COUNT(*) as m,
            SUM(CASE WHEN outcome='home' THEN 1 ELSE 0 END) as w,
            SUM(CASE WHEN outcome='draw' THEN 1 ELSE 0 END) as d,
            AVG(score_home) as gf, AVG(score_away) as ga,
            SUM(CASE WHEN score_home>0 AND score_away>0 THEN 1 ELSE 0 END) as btts,
            SUM(CASE WHEN score_home+score_away>2.5 THEN 1 ELSE 0 END) as o25,
            SUM(CASE WHEN score_away=0 THEN 1 ELSE 0 END) as cs
        FROM match_results
        WHERE is_finished = true
        AND home_team ILIKE %s
        AND commence_time::date BETWEEN %s AND %s
    """, (f'%{team}%', start, max_date))
    home = cur.fetchone()
    
    # Stats AWAY
    cur.execute("""
        SELECT COUNT(*) as m,
            SUM(CASE WHEN outcome='away' THEN 1 ELSE 0 END) as w,
            SUM(CASE WHEN outcome='draw' THEN 1 ELSE 0 END) as d,
            AVG(score_away) as gf, AVG(score_home) as ga,
            SUM(CASE WHEN score_home>0 AND score_away>0 THEN 1 ELSE 0 END) as btts,
            SUM(CASE WHEN score_home+score_away>2.5 THEN 1 ELSE 0 END) as o25,
            SUM(CASE WHEN score_home=0 THEN 1 ELSE 0 END) as cs
        FROM match_results
        WHERE is_finished = true
        AND away_team ILIKE %s
        AND commence_time::date BETWEEN %s AND %s
    """, (f'%{team}%', start, max_date))
    away = cur.fetchone()
    
    hm = int(home['m'] or 0)
    am = int(away['m'] or 0)
    total = hm + am
    
    if total == 0:
        c['stats'] = None
        continue
    
    enriched += 1
    
    def sf(v):
        try: return float(v) if v else 0.0
        except: return 0.0
    
    wins = int(home['w'] or 0) + int(away['w'] or 0)
    draws = int(home['d'] or 0) + int(away['d'] or 0)
    goals = (sf(home['gf'])*hm + sf(away['gf'])*am) / total
    conceded = (sf(home['ga'])*hm + sf(away['ga'])*am) / total
    btts = int(home['btts'] or 0) + int(away['btts'] or 0)
    o25 = int(home['o25'] or 0) + int(away['o25'] or 0)
    cs = int(home['cs'] or 0) + int(away['cs'] or 0)
    
    c['stats'] = {
        'matches': total, 'wins': wins, 'draws': draws, 'losses': total-wins-draws,
        'win_rate': round(wins/total*100, 1),
        'goals_avg': round(goals, 2),
        'conceded_avg': round(conceded, 2),
        'btts_rate': round(btts/total*100, 1),
        'over25_rate': round(o25/total*100, 1),
        'clean_sheet_rate': round(cs/total*100, 1) if total else 0,
        'home_matches': hm,
        'home_win_rate': round(int(home['w'] or 0)/hm*100, 1) if hm else 0,
        'away_matches': am,
        'away_win_rate': round(int(away['w'] or 0)/am*100, 1) if am else 0,
        'is_new': is_new
    }
    all_stats.append(c['stats'])

print(f"Enrichis: {enriched} | New Managers: {new_mgr}")

# 4. Calculer PERCENTILES
if all_stats:
    gf_values = sorted([s['goals_avg'] for s in all_stats])
    ga_values = sorted([s['conceded_avg'] for s in all_stats])
    cs_values = sorted([s['clean_sheet_rate'] for s in all_stats])
    
    n = len(gf_values)
    p25_gf = gf_values[n//4]
    p50_gf = gf_values[n//2]
    p75_gf = gf_values[3*n//4]
    p25_ga = ga_values[n//4]
    p50_ga = ga_values[n//2]
    p75_ga = ga_values[3*n//4]
    p75_cs = cs_values[3*n//4]
    
    print(f"\nPercentiles GF: P25={p25_gf:.2f} P50={p50_gf:.2f} P75={p75_gf:.2f}")
    print(f"Percentiles GA: P25={p25_ga:.2f} P50={p50_ga:.2f} P75={p75_ga:.2f}")

# 5. Classifier avec percentiles
for c in coaches:
    s = c.get('stats')
    if not s: continue
    
    g = s['goals_avg']
    ga = s['conceded_avg']
    cs = s['clean_sheet_rate']
    
    if g >= p75_gf and ga <= p25_ga:
        style = 'dominant_offensive'
    elif ga <= p25_ga and cs >= p75_cs:
        style = 'ultra_defensive'
    elif ga <= p50_ga and cs >= 35:
        style = 'defensive'
    elif g >= p75_gf and ga >= p75_ga:
        style = 'high_risk_offensive'
    elif g >= p75_gf:
        style = 'offensive'
    elif g >= p50_gf and ga <= p50_ga:
        style = 'balanced_offensive'
    elif g <= p25_gf and ga <= p50_ga:
        style = 'balanced_defensive'
    else:
        style = 'balanced'
    
    total_g = g + ga
    avg_total = p50_gf + p50_ga
    if total_g > avg_total * 1.3: pace = 'high_pace'
    elif total_g > avg_total * 1.1: pace = 'medium_high_pace'
    elif total_g < avg_total * 0.7: pace = 'low_pace'
    else: pace = 'medium_pace'
    
    s['style'] = style
    s['pace'] = pace
    s['reliable'] = s['matches'] >= 5 and not s['is_new']

# 6. Vider et repeupler coach_intelligence avec les bonnes donnees
cur.execute("DELETE FROM coach_intelligence")
conn.commit()
print("\nTable coach_intelligence videe")

saved = 0
for c in coaches:
    s = c.get('stats') or {}
    if not s.get('matches'): continue
    
    try:
        cur.execute("""
            INSERT INTO coach_intelligence (
                coach_name, coach_name_normalized, current_team,
                tactical_style, pressing_style,
                career_matches, career_wins, career_draws, career_losses,
                career_win_rate, avg_goals_per_match, avg_goals_conceded_per_match,
                clean_sheet_rate, btts_rate, over25_rate,
                home_matches, home_win_rate, away_matches, away_win_rate,
                data_quality_score, is_reliable, matches_analyzed,
                job_security, last_computed_at, computation_version
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 'v5.0'
            )
        """, (
            c['name'],
            c['name'].lower().replace(' ', '_'),
            c['team'],
            s.get('style', 'unknown'),
            s.get('pace', 'medium_pace'),
            s.get('matches', 0),
            s.get('wins', 0),
            s.get('draws', 0),
            s.get('losses', 0),
            s.get('win_rate', 0),
            s.get('goals_avg', 0),
            s.get('conceded_avg', 0),
            s.get('clean_sheet_rate', 0),
            s.get('btts_rate', 50),
            s.get('over25_rate', 50),
            s.get('home_matches', 0),
            s.get('home_win_rate', 0),
            s.get('away_matches', 0),
            s.get('away_win_rate', 0),
            min(100, s.get('matches', 0) * 5),
            s.get('reliable', False),
            s.get('matches', 0),
            'NEW_MANAGER' if s.get('is_new') else 'stable',
        ))
        saved += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erreur {c['name']}: {e}")

print(f"Sauvegardes: {saved}")

# 7. Afficher resultats
print("\n" + "="*110)
print("TOP 25 COACHES - DONNEES FIABLES V5")
print("="*110)
print(f"{'Coach':<22} {'Equipe':<20} {'Style':<20} {'Pace':<12} {'M':>2} {'WR':>5} {'GF':>4} {'GA':>4} {'CS':>4}")
print("-"*110)

cur.execute("""
    SELECT coach_name, current_team, tactical_style, pressing_style, 
           career_matches, career_win_rate, avg_goals_per_match, avg_goals_conceded_per_match, clean_sheet_rate
    FROM coach_intelligence WHERE career_matches > 0
    ORDER BY career_win_rate DESC LIMIT 25
""")
for r in cur.fetchall():
    print(f"{r['coach_name'][:21]:<22} {(r['current_team'] or '')[:19]:<20} {(r['tactical_style'] or '?'):<20} {(r['pressing_style'] or '?'):<12} {r['career_matches'] or 0:>2} {float(r['career_win_rate'] or 0):>5.1f} {float(r['avg_goals_per_match'] or 0):>4.1f} {float(r['avg_goals_conceded_per_match'] or 0):>4.1f} {float(r['clean_sheet_rate'] or 0):>4.0f}")

# Distribution
print("\n" + "="*50)
print("DISTRIBUTION DES STYLES")
print("="*50)
cur.execute("""
    SELECT tactical_style, COUNT(*) as n 
    FROM coach_intelligence WHERE career_matches > 0
    GROUP BY tactical_style ORDER BY n DESC
""")
for r in cur.fetchall():
    bar = "*" * r['n']
    print(f"  {r['tactical_style']:<20}: {r['n']:>2} {bar}")

# Verification cles
print("\n" + "="*50)
print("VERIFICATION COACHES CLES")
print("="*50)
cur.execute("""
    SELECT coach_name, current_team, tactical_style, career_matches, avg_goals_per_match, avg_goals_conceded_per_match
    FROM coach_intelligence 
    WHERE current_team IN ('Real Madrid', 'Atalanta BC', 'Inter Milan', 'Atletico Madrid', 'Napoli', 'Bayern Munich')
    ORDER BY current_team
""")
for r in cur.fetchall():
    print(f"  {r['current_team']:<18}: {r['coach_name']:<22} | {r['tactical_style']:<18} | GF:{float(r['avg_goals_per_match'] or 0):.1f} GA:{float(r['avg_goals_conceded_per_match'] or 0):.1f}")

cur.close()
conn.close()
print("\nDONE!")
