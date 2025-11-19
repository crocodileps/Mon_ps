"""
Script de calcul automatique du CLV (Closing Line Value)
Capture les dernières cotes avant chaque match et calcule le CLV
"""
import os
import sys
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'monps_db'),
    'user': os.getenv('DB_USER', 'monps_user'),
    'password': os.getenv('DB_PASSWORD', 'monps_password')
}

def get_closing_odds_from_db(match_id, outcome):
    """Récupère la dernière cote enregistrée pour un match"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Récupérer la dernière cote H2H pour ce match et outcome
    cursor.execute("""
        SELECT 
            CASE 
                WHEN %s = 'home' THEN home_odds
                WHEN %s = 'away' THEN away_odds
                WHEN %s = 'draw' THEN draw_odds
            END as closing_odd,
            collected_at
        FROM odds_h2h
        WHERE match_id = %s
        ORDER BY collected_at DESC
        LIMIT 1
    """, (outcome, outcome, outcome, match_id))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result

def calculate_clv(obtained_odds, closing_odds):
    """Calcule le CLV en pourcentage"""
    if not closing_odds or closing_odds == 0:
        return None
    
    clv = ((closing_odds / obtained_odds) - 1) * 100
    return round(clv, 2)

def update_bets_with_closing_odds():
    """Met à jour les paris avec closing odds et CLV"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Récupérer les paris sans closing_odds
    cursor.execute("""
        SELECT id, match_id, outcome, odds, commence_time
        FROM bets
        WHERE closing_odds IS NULL
        AND commence_time < NOW()
        ORDER BY commence_time DESC
    """)
    
    bets = cursor.fetchall()
    updated_count = 0
    
    for bet in bets:
        closing_data = get_closing_odds_from_db(bet['match_id'], bet['outcome'])
        
        if not closing_data:
            continue
        
        closing_odd = float(closing_data['closing_odd']) if closing_data['closing_odd'] else None
        
        if not closing_odd:
            continue
        
        clv_percent = calculate_clv(float(bet['odds']), closing_odd)
        
        if clv_percent is None:
            continue
        
        cursor.execute("""
            UPDATE bets
            SET closing_odds = %s, clv_percent = %s
            WHERE id = %s
        """, (closing_odd, clv_percent, bet['id']))
        
        updated_count += 1
        
        clv_sign = '+' if clv_percent >= 0 else ''
        print(f"  ✓ Bet #{bet['id']}: Odds {bet['odds']:.2f} → Closing {closing_odd:.2f} = CLV {clv_sign}{clv_percent}%")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return updated_count

def capture_closing_odds_for_upcoming():
    """Capture les closing odds pour les matchs qui commencent dans moins de 15min"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Matchs commençant dans 15 minutes
    soon = datetime.now() + timedelta(minutes=15)
    
    cursor.execute("""
        SELECT DISTINCT b.match_id, b.outcome, b.odds
        FROM bets b
        WHERE b.closing_odds IS NULL
        AND b.commence_time BETWEEN NOW() AND %s
    """, (soon,))
    
    bets = cursor.fetchall()
    captured_count = 0
    
    for bet in bets:
        closing_data = get_closing_odds_from_db(bet['match_id'], bet['outcome'])
        
        if closing_data and closing_data['closing_odd']:
            cursor.execute("""
                UPDATE bets
                SET closing_odds = %s
                WHERE match_id = %s AND outcome = %s AND closing_odds IS NULL
            """, (closing_data['closing_odd'], bet['match_id'], bet['outcome']))
            captured_count += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return captured_count

def main():
    print(f"[{datetime.now()}] Démarrage calcul CLV automatique...")
    
    # 1. Capturer closing odds pour matchs imminents
    captured = capture_closing_odds_for_upcoming()
    print(f"✓ {captured} closing odds capturées pour matchs imminents")
    
    # 2. Calculer CLV pour paris passés
    updated = update_bets_with_closing_odds()
    print(f"✓ {updated} paris mis à jour avec CLV")
    
    print(f"\n[{datetime.now()}] Terminé !")

if __name__ == '__main__':
    main()
