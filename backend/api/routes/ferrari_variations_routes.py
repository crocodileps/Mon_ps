"""
Routes API pour variations Ferrari - Données réelles uniquement
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

DB_CONFIG = {
    'host': 'monps_postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

@router.get("/improvements/{improvement_id}/ferrari-variations")
async def get_ferrari_real_variations(improvement_id: int):
    """
    Retourne les VRAIES variations Ferrari depuis agent_b_variations
    avec leurs stats réelles depuis variation_stats
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Récupérer variations + stats réelles
        cursor.execute("""
            SELECT
                v.id,
                v.variation_name as name,
                v.description,
                v.config,
                v.status,
                v.created_at,
                v.updated_at,
                -- Stats réelles depuis variation_stats
                COUNT(DISTINCT vs.match_id) as matches_tested,
                COUNT(DISTINCT CASE WHEN vs.is_winner THEN vs.match_id END) as wins,
                COUNT(DISTINCT CASE WHEN NOT vs.is_winner THEN vs.match_id END) as losses,
                COALESCE(
                    ROUND(100.0 * COUNT(DISTINCT CASE WHEN vs.is_winner THEN vs.match_id END) / 
                    NULLIF(COUNT(DISTINCT vs.match_id), 0), 1), 
                    0
                ) as win_rate,
                COALESCE(SUM(vs.profit), 0) as total_profit,
                COALESCE(AVG(vs.roi) * 100, 0) as roi,
                -- Facteurs activés depuis config
                v.config->'api_boost' as enabled_factors,
                (v.config->>'use_api_football')::boolean as use_api_football,
                (v.config->>'confidence_threshold')::float as custom_threshold,
                -- Variation contrôle
                (v.variation_name LIKE '%Baseline%' OR v.variation_name LIKE '%Contrôle%') as is_control,
                (v.status = 'active' OR v.status = 'testing') as is_active
            FROM agent_b_variations v
            LEFT JOIN variation_stats vs ON v.id = vs.variation_id
            WHERE v.improvement_id = %s
            GROUP BY v.id, v.variation_name, v.description, v.config, v.status, v.created_at, v.updated_at
            ORDER BY 
                (v.variation_name LIKE '%%Baseline%%' OR v.variation_name LIKE '%%Contrôle%%') DESC,
                v.id ASC
        """, (improvement_id,))

        variations = cursor.fetchall()
        
        # Nettoyer les données pour JSON
        result = []
        for var in variations:
            var_dict = dict(var)
            # Extraire facteurs du config
            config = var_dict.get('config', {})
            api_boost = config.get('api_boost', {}) if isinstance(config, dict) else {}
            var_dict['enabled_factors'] = list(api_boost.keys()) if api_boost else []
            var_dict['traffic_percentage'] = 20  # Par défaut, à ajuster avec Thompson Sampling
            result.append(var_dict)

        conn.close()

        return {
            "success": True,
            "improvement_id": improvement_id,
            "total": len(result),
            "variations": result,
            "source": "agent_b_variations (real data)"
        }
        
    except Exception as e:
        logger.error(f"Erreur get ferrari variations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
