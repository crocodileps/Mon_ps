#!/usr/bin/env python3
"""
🧠 CRON: Synchronisation head_to_head depuis team_head_to_head
Copie les données H2H vers la table Reality Check

Usage:
    python3 update_h2h.py
    
Cron recommandé: 0 7 * * * (tous les jours à 7h)
"""

import os
import sys
import psycopg2
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}

SYNC_H2H_SQL = """
INSERT INTO head_to_head (
    team_a, team_b, total_matches, team_a_wins, team_b_wins, draws,
    avg_total_goals, btts_percentage, over_25_percentage,
    dominant_team, dominance_factor, always_goals, low_scoring, updated_at
)
SELECT 
    team_a,
    team_b,
    total_matches,
    team_a_wins,
    team_b_wins,
    draws,
    LEAST(9.99, avg_total_goals),
    COALESCE(btts_pct::integer, 0),
    COALESCE(over_25_pct::integer, 0),
    CASE 
        WHEN team_a_wins > team_b_wins * 1.5 THEN team_a
        WHEN team_b_wins > team_a_wins * 1.5 THEN team_b
        ELSE NULL
    END,
    LEAST(9.99, CASE 
        WHEN team_a_wins > team_b_wins AND team_b_wins > 0 THEN ROUND(team_a_wins::numeric / team_b_wins, 2)
        WHEN team_b_wins > team_a_wins AND team_a_wins > 0 THEN ROUND(team_b_wins::numeric / team_a_wins, 2)
        WHEN team_a_wins > 0 AND team_b_wins = 0 THEN 9.99
        WHEN team_b_wins > 0 AND team_a_wins = 0 THEN 9.99
        ELSE 1.0
    END),
    COALESCE(btts_pct, 0) > 60,
    avg_total_goals < 2.0,
    NOW()
FROM team_head_to_head
WHERE total_matches >= 1
ON CONFLICT (team_a, team_b) 
DO UPDATE SET
    total_matches = EXCLUDED.total_matches,
    team_a_wins = EXCLUDED.team_a_wins,
    team_b_wins = EXCLUDED.team_b_wins,
    draws = EXCLUDED.draws,
    avg_total_goals = EXCLUDED.avg_total_goals,
    btts_percentage = EXCLUDED.btts_percentage,
    over_25_percentage = EXCLUDED.over_25_percentage,
    dominant_team = EXCLUDED.dominant_team,
    dominance_factor = EXCLUDED.dominance_factor,
    always_goals = EXCLUDED.always_goals,
    low_scoring = EXCLUDED.low_scoring,
    updated_at = NOW();
"""


def sync_h2h():
    """Synchronise head_to_head depuis team_head_to_head"""
    logger.info("🚀 Démarrage sync H2H")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM head_to_head")
        before = cur.fetchone()[0]
        
        cur.execute(SYNC_H2H_SQL)
        updated = cur.rowcount
        
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM head_to_head")
        after = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        logger.info(f"✅ Sync terminée: {before} → {after} ({updated} màj)")
        return {'success': True, 'before': before, 'after': after}
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    result = sync_h2h()
    sys.exit(0 if result['success'] else 1)
