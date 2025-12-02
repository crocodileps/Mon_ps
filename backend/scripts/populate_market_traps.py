#!/usr/bin/env python3
"""
Peuple market_traps à partir de team_intelligence.market_alerts
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger('PopulateMarketTraps')

DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

ALERT_LEVELS = {
    'TRAP': {'score': 90, 'emoji': '🚨', 'color': 'red'},
    'CAUTION': {'score': 60, 'emoji': '⚠️', 'color': 'orange'},
    'INFO': {'score': 30, 'emoji': 'ℹ️', 'color': 'blue'}
}

def populate_traps():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Récupérer toutes les équipes avec market_alerts
    cur.execute("""
        SELECT id, team_name, team_name_normalized, market_alerts
        FROM team_intelligence
        WHERE market_alerts IS NOT NULL
        AND market_alerts::text != '{}'
    """)
    
    teams = cur.fetchall()
    logger.info(f"📊 {len(teams)} équipes avec market_alerts")
    
    inserted = 0
    
    for team in teams:
        alerts = team['market_alerts']
        if not alerts:
            continue
            
        for market_type, alert_data in alerts.items():
            level = alert_data.get('level', 'INFO')
            level_info = ALERT_LEVELS.get(level, ALERT_LEVELS['INFO'])
            
            # Insérer dans market_traps
            cur.execute("""
                INSERT INTO market_traps (
                    team_name,
                    team_name_normalized,
                    team_intelligence_id,
                    market_type,
                    alert_level,
                    alert_level_score,
                    alert_emoji,
                    alert_color,
                    alert_reason,
                    alert_reason_short,
                    alternative_market,
                    historical_win_rate,
                    sample_size,
                    confidence_score,
                    is_reliable,
                    is_auto_generated,
                    generation_algorithm,
                    is_active,
                    created_at,
                    updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                )
                ON CONFLICT (team_name, market_type) DO UPDATE SET
                    alert_level = EXCLUDED.alert_level,
                    alert_level_score = EXCLUDED.alert_level_score,
                    alert_reason = EXCLUDED.alert_reason,
                    alternative_market = EXCLUDED.alternative_market,
                    updated_at = NOW()
            """, (
                team['team_name'],
                team['team_name_normalized'],
                team['id'],
                market_type,
                level,
                level_info['score'],
                level_info['emoji'],
                level_info['color'],
                alert_data.get('reason', ''),
                alert_data.get('reason', '')[:50],
                alert_data.get('alternative', ''),
                100 - alert_data.get('value', 50),  # Inverser pour win_rate
                20,  # Sample size par défaut
                80,  # Confidence score
                True,
                True,
                'team_intelligence_migration',
                True
            ))
            inserted += 1
            
    conn.commit()
    logger.info(f"✅ {inserted} market_traps insérés")
    
    # Stats finales
    cur.execute("SELECT COUNT(*) FROM market_traps")
    total = cur.fetchone()['count']
    logger.info(f"📊 Total market_traps: {total}")
    
    cur.execute("""
        SELECT alert_level, COUNT(*) as count
        FROM market_traps
        GROUP BY alert_level
        ORDER BY count DESC
    """)
    for row in cur.fetchall():
        logger.info(f"   {row['alert_level']}: {row['count']}")
    
    cur.close()
    conn.close()
    
    return inserted

if __name__ == "__main__":
    logger.info("🚀 Migration market_alerts → market_traps")
    populate_traps()
