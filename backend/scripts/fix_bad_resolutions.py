#!/usr/bin/env python3
"""Corrige les picks mal résolus en recalculant avec les vrais scores"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'monps_postgres'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

def resolve_market(market_type, home_score, away_score, outcome):
    """Calcule si le pick est gagnant selon le vrai résultat"""
    total = home_score + away_score
    
    resolvers = {
        'home': outcome == 'home',
        'away': outcome == 'away',
        'draw': outcome == 'draw',
        'dc_1x': outcome in ('home', 'draw'),
        'dc_x2': outcome in ('draw', 'away'),
        'dc_12': outcome in ('home', 'away'),
        'btts_yes': home_score > 0 and away_score > 0,
        'btts_no': home_score == 0 or away_score == 0,
        'over_15': total > 1,
        'under_15': total < 2,
        'over_25': total > 2,
        'under_25': total < 3,
        'over_35': total > 3,
        'under_35': total < 4,
        'dnb_home': outcome == 'home',
        'dnb_away': outcome == 'away',
    }
    
    return resolvers.get(market_type)

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Trouver les picks à corriger
    cur.execute("""
        SELECT 
            t.id,
            t.home_team || ' vs ' || t.away_team as match,
            t.market_type,
            t.is_winner as current_winner,
            t.odds_taken,
            t.stake,
            m.score_home,
            m.score_away,
            m.outcome
        FROM tracking_clv_picks t
        JOIN match_results m ON t.match_id = m.match_id
        WHERE t.is_resolved = true
          AND t.resolved_at > NOW() - INTERVAL '30 days'
    """)
    
    picks = cur.fetchall()
    fixed = 0
    
    for pick in picks:
        should_win = resolve_market(
            pick['market_type'],
            pick['score_home'],
            pick['score_away'],
            pick['outcome']
        )
        
        if should_win is None:
            continue
            
        if pick['current_winner'] != should_win:
            # Recalculer profit/loss
            odds = float(pick['odds_taken'] or 1)
            stake = float(pick['stake'] or 1)
            
            if should_win:
                profit_loss = stake * (odds - 1)
            else:
                profit_loss = -stake
            
            # Corriger
            cur.execute("""
                UPDATE tracking_clv_picks
                SET is_winner = %s,
                    profit_loss = %s,
                    score_home = %s,
                    score_away = %s
                WHERE id = %s
            """, (should_win, profit_loss, pick['score_home'], pick['score_away'], pick['id']))
            
            old = "✅" if pick['current_winner'] else "❌"
            new = "✅" if should_win else "❌"
            print(f"  {old}→{new} | {pick['match']} | {pick['market_type']} | {pick['score_home']}-{pick['score_away']}")
            fixed += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"✅ {fixed} picks corrigés")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
