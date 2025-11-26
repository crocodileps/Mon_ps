"""
Service de récupération automatique des cotes
Priorité: Pinnacle > Moyenne des bookmakers
"""
import psycopg2
from typing import Dict
import logging

logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'monps_postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

def get_match_odds(match_id: str) -> Dict[str, float]:
    """
    Récupère les meilleures cotes pour un match
    Returns: dict avec odds_over15, odds_over25, odds_home, etc.
    """
    odds = {}
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 1. Over/Under odds (lignes 1.5, 2.5, 3.5)
        for line in [1.5, 2.5, 3.5]:
            # Pinnacle d'abord
            cur.execute("""
                SELECT over_odds, under_odds 
                FROM odds_totals 
                WHERE match_id = %s AND line = %s AND bookmaker = 'Pinnacle'
                ORDER BY collected_at DESC LIMIT 1
            """, (match_id, line))
            row = cur.fetchone()
            
            # Fallback: moyenne
            if not row:
                cur.execute("""
                    SELECT AVG(over_odds), AVG(under_odds)
                    FROM odds_totals 
                    WHERE match_id = %s AND line = %s
                """, (match_id, line))
                row = cur.fetchone()
            
            if row and row[0] is not None:
                line_key = str(line).replace('.', '')
                odds[f'odds_over{line_key}'] = float(row[0])
                odds[f'odds_under{line_key}'] = float(row[1])
        
        # 2. 1X2 odds depuis odds_history
        cur.execute("""
            SELECT home_odds, draw_odds, away_odds 
            FROM odds_history 
            WHERE match_id = %s AND bookmaker = 'Pinnacle'
            ORDER BY collected_at DESC LIMIT 1
        """, (match_id,))
        row = cur.fetchone()
        
        if not row:
            cur.execute("""
                SELECT AVG(home_odds), AVG(draw_odds), AVG(away_odds)
                FROM odds_history 
                WHERE match_id = %s
            """, (match_id,))
            row = cur.fetchone()
        
        if row and row[0] is not None:
            odds['odds_home'] = float(row[0])
            odds['odds_draw'] = float(row[1])
            odds['odds_away'] = float(row[2])
            
            # Calculer Double Chance
            odds['odds_dc_1x'] = round(1 / (1/odds['odds_home'] + 1/odds['odds_draw']), 2)
            odds['odds_dc_x2'] = round(1 / (1/odds['odds_draw'] + 1/odds['odds_away']), 2)
            odds['odds_dc_12'] = round(1 / (1/odds['odds_home'] + 1/odds['odds_away']), 2)
            
            # DNB approximatif
            odds['odds_dnb_home'] = round(odds['odds_home'] * 0.85, 2)
            odds['odds_dnb_away'] = round(odds['odds_away'] * 0.85, 2)
        
        # 3. BTTS approximatif (corrélation avec Over 2.5)
        if 'odds_over25' in odds:
            odds['odds_btts'] = round(odds['odds_over25'] * 0.95, 2)
            odds['odds_btts_no'] = round(odds['odds_under25'] * 0.95, 2)
        
        cur.close()
        conn.close()
        
        logger.info(f"✅ Odds récupérées pour {match_id}: {len(odds)} marchés")
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération odds: {e}")
    
    return odds
