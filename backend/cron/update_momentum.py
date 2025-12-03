#!/usr/bin/env python3
"""
🧠 CRON: Mise à jour automatique du team_momentum
Calcule le momentum des équipes basé sur les 5 derniers matchs

Usage:
    python3 update_momentum.py
    
Cron recommandé: 0 6 * * * (tous les jours à 6h)
"""

import os
import sys
import psycopg2
from datetime import datetime
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/monps/momentum_update.log', mode='a')
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

UPDATE_MOMENTUM_SQL = """
WITH team_last_5 AS (
    SELECT 
        team_name,
        array_agg(result ORDER BY match_date DESC) as results,
        SUM(points) as total_points,
        SUM(goals_for) as goals_scored,
        SUM(goals_against) as goals_conceded,
        COUNT(*) as matches_count,
        SUM(CASE WHEN goals_against = 0 THEN 1 ELSE 0 END) as clean_sheets,
        SUM(CASE WHEN goals_for = 0 THEN 1 ELSE 0 END) as failed_to_score
    FROM (
        -- Matchs à domicile
        SELECT 
            home_team as team_name,
            commence_time as match_date,
            CASE 
                WHEN outcome = 'home' THEN 'W'
                WHEN outcome = 'draw' THEN 'D'
                ELSE 'L'
            END as result,
            CASE 
                WHEN outcome = 'home' THEN 3
                WHEN outcome = 'draw' THEN 1
                ELSE 0
            END as points,
            score_home as goals_for,
            score_away as goals_against,
            ROW_NUMBER() OVER (PARTITION BY home_team ORDER BY commence_time DESC) as rn
        FROM match_results
        WHERE is_finished = true
        AND commence_time > NOW() - INTERVAL '60 days'
        
        UNION ALL
        
        -- Matchs à l'extérieur
        SELECT 
            away_team as team_name,
            commence_time as match_date,
            CASE 
                WHEN outcome = 'away' THEN 'W'
                WHEN outcome = 'draw' THEN 'D'
                ELSE 'L'
            END as result,
            CASE 
                WHEN outcome = 'away' THEN 3
                WHEN outcome = 'draw' THEN 1
                ELSE 0
            END as points,
            score_away as goals_for,
            score_home as goals_against,
            ROW_NUMBER() OVER (PARTITION BY away_team ORDER BY commence_time DESC) as rn
        FROM match_results
        WHERE is_finished = true
        AND commence_time > NOW() - INTERVAL '60 days'
    ) all_matches
    WHERE rn <= 5
    GROUP BY team_name
    HAVING COUNT(*) >= 3
)
INSERT INTO team_momentum (
    team_name, 
    last_5_results, 
    last_5_points, 
    momentum_status,
    momentum_score,
    goals_scored_last_5,
    goals_conceded_last_5,
    clean_sheets_last_5,
    failed_to_score_last_5,
    confidence_level,
    pressure_level,
    calculated_at,
    valid_until
)
SELECT 
    team_name,
    array_to_string(results[1:5], '') as last_5_results,
    total_points as last_5_points,
    CASE 
        WHEN total_points >= 12 THEN 'excellent'
        WHEN total_points >= 9 THEN 'good'
        WHEN total_points >= 6 THEN 'stable'
        WHEN total_points >= 3 THEN 'poor'
        ELSE 'crisis'
    END as momentum_status,
    LEAST(100, GREATEST(0, total_points * 6 + 10)) as momentum_score,
    goals_scored,
    goals_conceded,
    clean_sheets,
    failed_to_score,
    CASE 
        WHEN total_points >= 10 THEN 80
        WHEN total_points >= 7 THEN 60
        WHEN total_points >= 4 THEN 40
        ELSE 20
    END as confidence_level,
    CASE 
        WHEN total_points <= 3 THEN 80
        WHEN total_points <= 6 THEN 50
        ELSE 20
    END as pressure_level,
    NOW() as calculated_at,
    NOW() + INTERVAL '7 days' as valid_until
FROM team_last_5
ON CONFLICT (team_name) 
DO UPDATE SET
    last_5_results = EXCLUDED.last_5_results,
    last_5_points = EXCLUDED.last_5_points,
    momentum_status = EXCLUDED.momentum_status,
    momentum_score = EXCLUDED.momentum_score,
    goals_scored_last_5 = EXCLUDED.goals_scored_last_5,
    goals_conceded_last_5 = EXCLUDED.goals_conceded_last_5,
    clean_sheets_last_5 = EXCLUDED.clean_sheets_last_5,
    failed_to_score_last_5 = EXCLUDED.failed_to_score_last_5,
    confidence_level = EXCLUDED.confidence_level,
    pressure_level = EXCLUDED.pressure_level,
    calculated_at = NOW(),
    valid_until = NOW() + INTERVAL '7 days';
"""


def update_momentum():
    """Met à jour le momentum de toutes les équipes"""
    logger.info("🚀 Démarrage mise à jour team_momentum")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Compter avant
        cur.execute("SELECT COUNT(*) FROM team_momentum")
        before_count = cur.fetchone()[0]
        
        # Exécuter la mise à jour
        cur.execute(UPDATE_MOMENTUM_SQL)
        updated_count = cur.rowcount
        
        conn.commit()
        
        # Compter après
        cur.execute("SELECT COUNT(*) FROM team_momentum")
        after_count = cur.fetchone()[0]
        
        # Stats par status
        cur.execute("""
            SELECT momentum_status, COUNT(*) 
            FROM team_momentum 
            GROUP BY momentum_status 
            ORDER BY momentum_status
        """)
        stats = cur.fetchall()
        
        cur.close()
        conn.close()
        
        logger.info(f"✅ Mise à jour terminée")
        logger.info(f"   Équipes avant: {before_count}")
        logger.info(f"   Équipes après: {after_count}")
        logger.info(f"   Lignes affectées: {updated_count}")
        logger.info(f"   Stats: {dict(stats)}")
        
        return {
            'success': True,
            'before': before_count,
            'after': after_count,
            'updated': updated_count,
            'stats': dict(stats)
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def main():
    """Point d'entrée principal"""
    logger.info("=" * 60)
    logger.info("🧠 CRON: Update Team Momentum")
    logger.info(f"   Date: {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    result = update_momentum()
    
    if result['success']:
        logger.info("✅ Cron terminé avec succès")
        sys.exit(0)
    else:
        logger.error(f"❌ Cron échoué: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
