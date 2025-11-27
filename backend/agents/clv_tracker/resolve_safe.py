#!/usr/bin/env python3
"""
🔄 RÉSOLUTION SÉCURISÉE
Résout UNIQUEMENT les picks dont le match est terminé (par date + équipes)
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

def resolve_safe():
    """Résout les picks de manière sécurisée (avec vérification de date)"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("🔄 Résolution sécurisée...")
    now = datetime.now()
    
    # 1. Récupérer les picks non résolus avec leur date de match
    cur.execute("""
        SELECT DISTINCT 
            p.id, p.home_team, p.away_team, p.market_type, 
            p.odds_taken, p.stake, p.diamond_score, p.match_id,
            o.commence_time
        FROM tracking_clv_picks p
        JOIN odds_history o ON p.match_id = o.match_id
        WHERE p.is_resolved = false
        AND p.home_team IS NOT NULL
        AND o.commence_time IS NOT NULL
        ORDER BY o.commence_time
    """)
    pending = cur.fetchall()
    
    print(f"📋 {len(pending)} picks en attente")
    
    # Filtrer: ne garder que les matchs qui sont PASSÉS (+ 2h de marge)
    now_minus_2h = now - timedelta(hours=2)
    ready_picks = [p for p in pending if p['commence_time'] < now_minus_2h]
    
    print(f"⏰ {len(ready_picks)} picks avec match terminé (commence_time < {now_minus_2h})")
    
    if not ready_picks:
        print("✅ Aucun match terminé à résoudre. Les matchs sont encore à venir.")
        cur.close()
        conn.close()
        return
    
    # Grouper par match
    matches = {}
    for p in ready_picks:
        key = (p['home_team'].lower().strip(), p['away_team'].lower().strip(), 
               p['commence_time'].date())
        if key not in matches:
            matches[key] = {'picks': [], 'commence_time': p['commence_time']}
        matches[key]['picks'].append(p)
    
    print(f"🏟️ {len(matches)} matchs terminés à résoudre")
    
    resolved = 0
    wins = 0
    losses = 0
    
    for (home, away, match_date), data in matches.items():
        # Chercher le résultat avec la MÊME DATE
        cur.execute("""
            SELECT score_home, score_away, outcome, home_team, away_team
            FROM match_results
            WHERE is_finished = true
            AND DATE(match_date) = %s
            AND (
                LOWER(home_team) ILIKE %s 
                AND LOWER(away_team) ILIKE %s
            )
            LIMIT 1
        """, (
            match_date,
            f'%{home.split()[0]}%',
            f'%{away.split()[0]}%'
        ))
        
        result = cur.fetchone()
        
        if not result:
            # Essayer avec un matching plus large sur la date (±1 jour)
            cur.execute("""
                SELECT score_home, score_away, outcome, home_team, away_team
                FROM match_results
                WHERE is_finished = true
                AND match_date BETWEEN %s AND %s
                AND (
                    LOWER(home_team) ILIKE %s 
                    AND LOWER(away_team) ILIKE %s
                )
                LIMIT 1
            """, (
                match_date - timedelta(days=1),
                match_date + timedelta(days=1),
                f'%{home.split()[0]}%',
                f'%{away.split()[0]}%'
            ))
            result = cur.fetchone()
        
        if not result:
            print(f"  ⏳ {home} vs {away} ({match_date}): résultat non trouvé")
            continue
        
        home_score = result['score_home']
        away_score = result['score_away']
        outcome = result['outcome']
        
        print(f"  ✅ {home} vs {away}: {home_score}-{away_score}")
        
        # Résoudre chaque pick
        for pick in data['picks']:
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
        print(f"   Win Rate: {round(wins/(wins+losses)*100, 1)}%" if (wins+losses) > 0 else "   Win Rate: N/A")


if __name__ == "__main__":
    resolve_safe()
