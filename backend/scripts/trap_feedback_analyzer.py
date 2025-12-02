#!/usr/bin/env python3
"""
Trap Feedback Analyzer V2 - Avec logique HOME/AWAY correcte
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger('TrapFeedbackV2')

DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

def analyze_trap_feedback(days: int = 7):
    """Analyse les picks résolus avec logique HOME/AWAY"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT id, home_team, away_team, market_type, prediction, 
               is_winner, odds_taken, profit_loss, match_name
        FROM tracking_clv_picks
        WHERE is_resolved = true
        AND resolved_at > NOW() - INTERVAL '%s days'
    """, (days,))
    
    picks = cur.fetchall()
    logger.info(f"📊 {len(picks)} picks résolus dans les {days} derniers jours")
    
    trap_hits = 0
    trap_saves = 0
    trap_false_positives = 0
    
    for pick in picks:
        home = pick['home_team']
        away = pick['away_team']
        market = pick['market_type']
        is_winner = pick['is_winner']
        
        # Vérifier si un trap existe pour HOME team (avec applies_home = true)
        cur.execute("""
            SELECT id, team_name, alert_level, alert_reason
            FROM market_traps
            WHERE market_type = %s
            AND team_name ILIKE %s
            AND applies_home = true
            AND alert_level IN ('TRAP', 'CAUTION')
            AND is_active = true
        """, (market, f"%{home}%"))
        home_traps = cur.fetchall()
        
        # Vérifier si un trap existe pour AWAY team (avec applies_away = true)
        cur.execute("""
            SELECT id, team_name, alert_level, alert_reason
            FROM market_traps
            WHERE market_type = %s
            AND team_name ILIKE %s
            AND applies_away = true
            AND alert_level IN ('TRAP', 'CAUTION')
            AND is_active = true
        """, (market, f"%{away}%"))
        away_traps = cur.fetchall()
        
        all_traps = home_traps + away_traps
        
        if all_traps:
            for trap in all_traps:
                trap_id = trap['id']
                location = 'HOME' if trap in home_traps else 'AWAY'
                
                cur.execute("""
                    UPDATE market_traps 
                    SET times_triggered = times_triggered + 1, updated_at = NOW()
                    WHERE id = %s
                """, (trap_id,))
                
                trap_hits += 1
                
                if not is_winner:
                    cur.execute("""
                        UPDATE market_traps 
                        SET times_saved_user = times_saved_user + 1
                        WHERE id = %s
                    """, (trap_id,))
                    trap_saves += 1
                    logger.info(f"✅ TRAP CORRECT ({location}): {pick['match_name']} - {market}")
                else:
                    cur.execute("""
                        UPDATE market_traps 
                        SET false_positive_count = false_positive_count + 1
                        WHERE id = %s
                    """, (trap_id,))
                    trap_false_positives += 1
                    logger.info(f"⚠️ FAUX POSITIF ({location}): {pick['match_name']} - {market}")
    
    # Mettre à jour accuracy_rate
    cur.execute("""
        UPDATE market_traps
        SET accuracy_rate = CASE 
            WHEN times_triggered > 0 
            THEN ROUND((times_saved_user::numeric / times_triggered::numeric) * 100, 1)
            ELSE 0
        END
        WHERE times_triggered > 0
    """)
    
    conn.commit()
    
    logger.info(f"")
    logger.info(f"═══════════════════════════════════════")
    logger.info(f"📊 RÉSUMÉ ANALYSE TRAPS V2")
    logger.info(f"═══════════════════════════════════════")
    logger.info(f"Traps déclenchés: {trap_hits}")
    logger.info(f"Traps corrects: {trap_saves}")
    logger.info(f"Faux positifs: {trap_false_positives}")
    
    if trap_hits > 0:
        accuracy = (trap_saves / trap_hits) * 100
        logger.info(f"Précision globale: {accuracy:.1f}%")
    
    cur.execute("""
        SELECT team_name, market_type, times_triggered, accuracy_rate
        FROM market_traps
        WHERE times_triggered > 0
        ORDER BY times_triggered DESC
        LIMIT 10
    """)
    
    top = cur.fetchall()
    if top:
        logger.info(f"\n🏆 TOP TRAPS:")
        for t in top:
            logger.info(f"   {t['team_name']} - {t['market_type']}: {t['times_triggered']} triggers, {t['accuracy_rate'] or 0}% acc")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    logger.info(f"🚀 Analyse feedback traps V2 ({days} jours)")
    analyze_trap_feedback(days)
