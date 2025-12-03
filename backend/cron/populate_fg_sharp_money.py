#!/usr/bin/env python3
"""
💰 CRON: Détection des Steam Moves / Sharp Money
Analyse odds_history pour détecter les mouvements significatifs de cotes

Usage:
    python3 populate_fg_sharp_money.py

Cron recommandé: */30 * * * * (toutes les 30 minutes)
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/monps/sharp_money_detect.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Configuration DB
DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}

# Seuils de détection steam
SHARP_THRESHOLD_PCT = 3.0  # Mouvement >= 3% = sharp
STEAM_THRESHOLD_PCT = 5.0  # Mouvement >= 5% = steam move majeur

def detect_sharp_money():
    """Détecte les sharp moves depuis odds_history"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Analyser les mouvements de cotes par match (Pinnacle = référence sharp)
        cursor.execute("""
            WITH odds_movements AS (
                SELECT 
                    match_id,
                    bookmaker,
                    -- Opening odds (premier enregistrement)
                    FIRST_VALUE(home_odds) OVER (
                        PARTITION BY match_id, bookmaker 
                        ORDER BY collected_at
                    ) as opening_home,
                    FIRST_VALUE(draw_odds) OVER (
                        PARTITION BY match_id, bookmaker 
                        ORDER BY collected_at
                    ) as opening_draw,
                    FIRST_VALUE(away_odds) OVER (
                        PARTITION BY match_id, bookmaker 
                        ORDER BY collected_at
                    ) as opening_away,
                    -- Closing odds (dernier enregistrement)
                    LAST_VALUE(home_odds) OVER (
                        PARTITION BY match_id, bookmaker 
                        ORDER BY collected_at
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    ) as closing_home,
                    LAST_VALUE(draw_odds) OVER (
                        PARTITION BY match_id, bookmaker 
                        ORDER BY collected_at
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    ) as closing_draw,
                    LAST_VALUE(away_odds) OVER (
                        PARTITION BY match_id, bookmaker 
                        ORDER BY collected_at
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    ) as closing_away,
                    -- Current odds
                    home_odds as current_home,
                    draw_odds as current_draw,
                    away_odds as current_away,
                    collected_at
                FROM odds_history
                WHERE bookmaker = 'pinnacle'
            ),
            distinct_movements AS (
                SELECT DISTINCT ON (match_id)
                    match_id,
                    opening_home, opening_draw, opening_away,
                    closing_home, closing_draw, closing_away,
                    current_home, current_draw, current_away
                FROM odds_movements
                ORDER BY match_id, collected_at DESC
            )
            SELECT 
                match_id,
                opening_home, closing_home,
                opening_draw, closing_draw,
                opening_away, closing_away,
                ROUND(((closing_home - opening_home) / NULLIF(opening_home, 0) * 100)::numeric, 2) as home_move_pct,
                ROUND(((closing_draw - opening_draw) / NULLIF(opening_draw, 0) * 100)::numeric, 2) as draw_move_pct,
                ROUND(((closing_away - opening_away) / NULLIF(opening_away, 0) * 100)::numeric, 2) as away_move_pct
            FROM distinct_movements
            WHERE opening_home IS NOT NULL
        """)
        
        movements = cursor.fetchall()
        logger.info(f"📊 {len(movements)} matchs avec mouvements de cotes analysés")
        
        inserted = 0
        for mov in movements:
            match_id = mov['match_id']
            
            # Analyser chaque marché (home, draw, away)
            markets = [
                ('home', mov['opening_home'], mov['closing_home'], mov['home_move_pct']),
                ('draw', mov['opening_draw'], mov['closing_draw'], mov['draw_move_pct']),
                ('away', mov['opening_away'], mov['closing_away'], mov['away_move_pct'])
            ]
            
            for market_type, opening, closing, move_pct in markets:
                if move_pct is None or opening is None:
                    continue
                    
                abs_move = abs(float(move_pct))
                
                # Ne garder que les mouvements significatifs
                if abs_move < SHARP_THRESHOLD_PCT:
                    continue
                
                # Déterminer la direction
                if float(move_pct) < 0:
                    direction = 'shortening'  # Cote baisse = money entre
                else:
                    direction = 'drifting'  # Cote monte = money sort
                
                # Est-ce un sharp move ?
                is_sharp = abs_move >= SHARP_THRESHOLD_PCT
                
                # Vérifier si déjà enregistré
                cursor.execute("""
                    SELECT id FROM fg_sharp_money 
                    WHERE match_id = %s AND market_type = %s
                """, (match_id, market_type))
                
                if cursor.fetchone():
                    # Update
                    cursor.execute("""
                        UPDATE fg_sharp_money SET
                            opening_odds = %s,
                            closing_odds = %s,
                            current_odds = %s,
                            movement_pct = %s,
                            movement_direction = %s,
                            is_sharp_move = %s,
                            detected_at = NOW()
                        WHERE match_id = %s AND market_type = %s
                    """, (
                        opening, closing, closing, move_pct,
                        direction, is_sharp, match_id, market_type
                    ))
                else:
                    # Insert
                    cursor.execute("""
                        INSERT INTO fg_sharp_money (
                            match_id, market_type,
                            opening_odds, current_odds, closing_odds,
                            movement_pct, movement_direction, is_sharp_move,
                            detected_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        match_id, market_type,
                        opening, closing, closing,
                        move_pct, direction, is_sharp
                    ))
                    inserted += 1
        
        conn.commit()
        logger.info(f"✅ {inserted} nouveaux sharp moves détectés")
        
        # Stats finales
        cursor.execute("""
            SELECT 
                market_type,
                COUNT(*) as total,
                SUM(CASE WHEN is_sharp_move THEN 1 ELSE 0 END) as sharp_moves,
                ROUND(AVG(ABS(movement_pct))::numeric, 2) as avg_movement
            FROM fg_sharp_money
            GROUP BY market_type
            ORDER BY total DESC
        """)
        stats = cursor.fetchall()
        
        for s in stats:
            logger.info(f"   {s['market_type']}: {s['total']} mouvements, {s['sharp_moves']} sharp, avg {s['avg_movement']}%")
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    logger.info("🚀 Démarrage détection Sharp Money")
    detect_sharp_money()
    logger.info("✅ Terminé")
