#!/usr/bin/env python3
"""
RÉSOLUTION AUTOMATIQUE DES PICKS TRACKING CLV
Vérifie les matchs terminés et met à jour les picks
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

# Mapping des marchés vers les colonnes de résultat
MARKET_RESOLUTION = {
    'over_15': lambda h, a: (h + a) > 1,
    'over_25': lambda h, a: (h + a) > 2,
    'over_35': lambda h, a: (h + a) > 3,
    'under_15': lambda h, a: (h + a) < 2,
    'under_25': lambda h, a: (h + a) < 3,
    'under_35': lambda h, a: (h + a) < 4,
    'btts_yes': lambda h, a: h > 0 and a > 0,
    'btts_no': lambda h, a: h == 0 or a == 0,
    'dc_1x': lambda h, a, outcome: outcome in ('home', 'draw'),
    'dc_x2': lambda h, a, outcome: outcome in ('draw', 'away'),
    'dc_12': lambda h, a, outcome: outcome in ('home', 'away'),
    'dnb_home': lambda h, a, outcome: outcome == 'home',
    'dnb_away': lambda h, a, outcome: outcome == 'away',
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

def resolve_pick(market_type: str, home_score: int, away_score: int, outcome: str) -> bool:
    """Détermine si un pick est gagnant"""
    market_key = market_type.lower().replace(' ', '_').replace('.', '_')
    
    # Normaliser les noms de marché
    normalization = {
        'o15': 'over_15', 'o25': 'over_25', 'o35': 'over_35',
        'u15': 'under_15', 'u25': 'under_25', 'u35': 'under_35',
        'btts': 'btts_yes', 'btts_oui': 'btts_yes', 'btts_non': 'btts_no',
        'over15': 'over_15', 'over25': 'over_25', 'over35': 'over_35',
        'under15': 'under_15', 'under25': 'under_25', 'under35': 'under_35',
    }
    market_key = normalization.get(market_key, market_key)
    
    resolver = MARKET_RESOLUTION.get(market_key)
    if not resolver:
        print(f"  ⚠️ Marché non supporté: {market_type} -> {market_key}")
        return None
    
    # Certains marchés ont besoin de l'outcome
    if market_key.startswith('dc_') or market_key.startswith('dnb_'):
        return resolver(home_score, away_score, outcome)
    else:
        return resolver(home_score, away_score)

def main():
    print(f"\n{'='*60}")
    print(f"🎯 RÉSOLUTION PICKS TRACKING CLV - {datetime.now()}")
    print(f"{'='*60}\n")
    
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Récupérer les picks non résolus
    cur.execute("""
        SELECT id, match_id, match_name, market_type, odds_taken, stake
        FROM tracking_clv_picks
        WHERE is_resolved = false
        AND match_id IS NOT NULL
    """)
    pending_picks = cur.fetchall()
    print(f"📋 {len(pending_picks)} picks en attente de résolution\n")
    
    if not pending_picks:
        print("✅ Aucun pick à résoudre")
        conn.close()
        return
    
    resolved_count = 0
    wins = 0
    losses = 0
    
    for pick in pending_picks:
        match_id = pick['match_id']
        
        # 2. Chercher le résultat du match
        cur.execute("""
            SELECT score_home, score_away, outcome, is_finished
            FROM match_results
            WHERE match_id = %s AND is_finished = true
        """, (match_id,))
        result = cur.fetchone()
        
        if not result:
            # Essayer dans fg_match_results
            cur.execute("""
                SELECT home_score as score_home, away_score as score_away, result_1x2 as outcome
                FROM fg_match_results
                WHERE match_id = %s
            """, (match_id,))
            result = cur.fetchone()
        
        if not result:
            continue
        
        home_score = result['score_home']
        away_score = result['score_away']
        outcome = result.get('outcome', '')
        
        # 3. Résoudre le pick
        is_winner = resolve_pick(pick['market_type'], home_score, away_score, outcome)
        
        if is_winner is None:
            continue
        
        # 4. Calculer profit/loss
        stake = float(pick['stake'] or 1)
        odds = float(pick['odds_taken'] or 1)
        
        if is_winner:
            profit_loss = stake * (odds - 1)
            wins += 1
        else:
            profit_loss = -stake
            losses += 1
        
        # 5. Mettre à jour le pick
        cur.execute("""
            UPDATE tracking_clv_picks
            SET 
                is_resolved = true,
                is_winner = %s,
                profit_loss = %s,
                score_home = %s,
                score_away = %s,
                resolved_at = NOW()
            WHERE id = %s
        """, (is_winner, profit_loss, home_score, away_score, pick['id']))
        
        resolved_count += 1
        status = "✅ WIN" if is_winner else "❌ LOSS"
        print(f"  {status} | {pick['match_name']} | {pick['market_type']} | {home_score}-{away_score}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"📊 RÉSUMÉ:")
    print(f"   Résolus: {resolved_count}")
    print(f"   Gagnés: {wins}")
    print(f"   Perdus: {losses}")
    if resolved_count > 0:
        print(f"   Win Rate: {wins/resolved_count*100:.1f}%")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
