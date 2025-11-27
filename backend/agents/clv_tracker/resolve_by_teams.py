#!/usr/bin/env python3
"""
🔄 RÉSOLUTION PAR NOM D'ÉQUIPES
Résout les picks en matchant par home_team + away_team
(car les match_id ont des formats différents entre sources)
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

MARKET_RESOLVERS = {
    'btts_yes': lambda h, a, o: h > 0 and a > 0,
    'btts_no': lambda h, a, o: h == 0 or a == 0,
    'over15': lambda h, a, o: (h + a) > 1,
    'under15': lambda h, a, o: (h + a) < 2,
    'over25': lambda h, a, o: (h + a) > 2,
    'under25': lambda h, a, o: (h + a) < 3,
    'over35': lambda h, a, o: (h + a) > 3,
    'under35': lambda h, a, o: (h + a) < 4,
    'dc_1x': lambda h, a, o: o in ('home', 'draw'),
    'dc_x2': lambda h, a, o: o in ('draw', 'away'),
    'dc_12': lambda h, a, o: o in ('home', 'away'),
    'dnb_home': lambda h, a, o: o == 'home' if o != 'draw' else None,
    'dnb_away': lambda h, a, o: o == 'away' if o != 'draw' else None,
}

def resolve_by_teams():
    """Résout les picks en matchant par équipes"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("🔄 Résolution par nom d'équipes...")
    
    # Récupérer picks non résolus avec leurs équipes
    cur.execute("""
        SELECT DISTINCT p.id, p.home_team, p.away_team, p.market_type, 
               p.odds_taken, p.stake, p.diamond_score
        FROM tracking_clv_picks p
        WHERE p.is_resolved = false
        AND p.home_team IS NOT NULL
        AND p.away_team IS NOT NULL
    """)
    pending = cur.fetchall()
    print(f"📋 {len(pending)} picks en attente")
    
    # Grouper par match (home_team, away_team)
    matches = {}
    for p in pending:
        key = (p['home_team'].lower().strip(), p['away_team'].lower().strip())
        if key not in matches:
            matches[key] = []
        matches[key].append(p)
    
    print(f"🏟️ {len(matches)} matchs uniques")
    
    resolved = 0
    wins = 0
    losses = 0
    
    for (home, away), picks in matches.items():
        # Chercher le résultat dans match_results (matching fuzzy par nom)
        cur.execute("""
            SELECT score_home, score_away, outcome
            FROM match_results
            WHERE is_finished = true
            AND (
                (LOWER(home_team) LIKE %s OR LOWER(home_team) LIKE %s)
                AND (LOWER(away_team) LIKE %s OR LOWER(away_team) LIKE %s)
            )
            ORDER BY last_updated DESC
            LIMIT 1
        """, (
            f'%{home.split()[0]}%', f'%{home}%',
            f'%{away.split()[0]}%', f'%{away}%'
        ))
        
        result = cur.fetchone()
        
        if not result:
            continue
        
        home_score = result['score_home']
        away_score = result['score_away']
        outcome = result['outcome']
        
        print(f"  ✅ {home} vs {away}: {home_score}-{away_score}")
        
        # Résoudre chaque pick du match
        for pick in picks:
            resolver = MARKET_RESOLVERS.get(pick['market_type'])
            if not resolver:
                continue
            
            is_winner = resolver(home_score, away_score, outcome)
            
            if is_winner is None:
                profit = 0
            elif is_winner:
                stake = float(pick['stake'] or 1)
                odds = float(pick['odds_taken'] or 1)
                profit = stake * (odds - 1)
                wins += 1
            else:
                profit = -float(pick['stake'] or 1)
                losses += 1
            
            cur.execute("""
                UPDATE tracking_clv_picks
                SET is_resolved = true, is_winner = %s, profit_loss = %s,
                    score_home = %s, score_away = %s, resolved_at = NOW()
                WHERE id = %s
            """, (is_winner, profit, home_score, away_score, pick['id']))
            
            resolved += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n📊 RÉSUMÉ:")
    print(f"   Résolus: {resolved}")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    if resolved > 0:
        print(f"   Win Rate: {round(wins/resolved*100, 1)}%")

if __name__ == "__main__":
    resolve_by_teams()
