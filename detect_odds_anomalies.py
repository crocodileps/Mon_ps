"""
DÉTECTEUR D'ANOMALIES DE COTES
==============================
Identifie les cotes suspectes dans la base de données
"""

import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

def detect_anomalies():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 80)
    print("🔍 DÉTECTION D'ANOMALIES - COTES SUSPECTES")
    print("=" * 80)
    
    # 1. Cotes absolues trop élevées
    print("\n📊 1. COTES > 10.0 (marchés illiquides):")
    print("-" * 80)
    
    cur.execute("""
        SELECT home_team, away_team, bookmaker, line, over_odds, under_odds
        FROM odds_totals
        WHERE over_odds > 10 OR under_odds > 10
        ORDER BY GREATEST(over_odds, under_odds) DESC
        LIMIT 20
    """)
    
    rows = cur.fetchall()
    print(f"   {len(rows)} entrées trouvées (max 20 affichées)\n")
    
    for r in rows:
        print(f"   {r['home_team'][:15]} vs {r['away_team'][:15]} | {r['bookmaker']}")
        print(f"      Line {r['line']}: Over {r['over_odds']:.2f} | Under {r['under_odds']:.2f}")
    
    # 2. Écart Pinnacle vs autres bookmakers
    print("\n\n📊 2. ÉCARTS SIGNIFICATIFS vs PINNACLE (> 50%):")
    print("-" * 80)
    
    cur.execute("""
        WITH pinnacle AS (
            SELECT home_team, away_team, line, over_odds as pin_over, under_odds as pin_under
            FROM odds_totals
            WHERE bookmaker = 'Pinnacle'
        )
        SELECT t.home_team, t.away_team, t.bookmaker, t.line,
               t.over_odds, p.pin_over,
               ABS(t.over_odds - p.pin_over) / p.pin_over * 100 as diff_pct
        FROM odds_totals t
        JOIN pinnacle p ON t.home_team = p.home_team 
                       AND t.away_team = p.away_team 
                       AND t.line = p.line
        WHERE t.bookmaker != 'Pinnacle'
          AND ABS(t.over_odds - p.pin_over) / p.pin_over > 0.5
        ORDER BY diff_pct DESC
        LIMIT 15
    """)
    
    rows = cur.fetchall()
    print(f"   {len(rows)} anomalies détectées\n")
    
    for r in rows:
        print(f"   {r['home_team'][:12]} vs {r['away_team'][:12]} | Line {r['line']}")
        print(f"      {r['bookmaker']}: {r['over_odds']:.2f} vs Pinnacle: {r['pin_over']:.2f} (+{r['diff_pct']:.0f}%)")
    
    # 3. Marges incohérentes
    print("\n\n📊 3. MARGES INCOHÉRENTES (< 0% ou > 20%):")
    print("-" * 80)
    
    cur.execute("""
        SELECT home_team, away_team, bookmaker, line, over_odds, under_odds,
               (1/over_odds + 1/under_odds - 1) * 100 as margin
        FROM odds_totals
        WHERE (1/over_odds + 1/under_odds - 1) < 0 
           OR (1/over_odds + 1/under_odds - 1) > 0.20
        ORDER BY ABS(1/over_odds + 1/under_odds - 1) DESC
        LIMIT 10
    """)
    
    rows = cur.fetchall()
    print(f"   {len(rows)} entrées avec marges suspectes\n")
    
    for r in rows:
        print(f"   {r['bookmaker']}: {r['home_team'][:12]} vs {r['away_team'][:12]} | Line {r['line']}")
        print(f"      Over {r['over_odds']:.2f} | Under {r['under_odds']:.2f} | Marge: {r['margin']:.1f}%")
    
    # 4. Résumé
    print("\n" + "=" * 80)
    print("📈 RÉSUMÉ")
    print("=" * 80)
    
    cur.execute("SELECT COUNT(*) FROM odds_totals WHERE over_odds > 10")
    high_odds = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) FROM odds_totals")
    total = cur.fetchone()['count']
    
    print(f"\n   Total entrées: {total:,}")
    print(f"   Cotes > 10.0: {high_odds} ({high_odds/total*100:.2f}%)")
    print(f"\n   💡 Recommandation: Filtrer les cotes > 10.0 dans l'analyse")
    
    conn.close()

if __name__ == "__main__":
    detect_anomalies()
