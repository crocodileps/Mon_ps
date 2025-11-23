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

        # Récupérer variations + stats (sans match_id, utiliser id)
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
                COUNT(vs.id) as matches_tested,
                COUNT(CASE WHEN vs.is_winner THEN 1 END) as wins,
                COUNT(CASE WHEN NOT vs.is_winner THEN 1 END) as losses,
                COALESCE(
                    ROUND(100.0 * COUNT(CASE WHEN vs.is_winner THEN 1 END)::numeric / 
                    NULLIF(COUNT(vs.id), 0), 1), 
                    0
                ) as win_rate,
                COALESCE(SUM(vs.profit), 0) as total_profit,
                COALESCE(ROUND(AVG(vs.roi) * 100, 1), 0) as roi
            FROM agent_b_variations v
            LEFT JOIN variation_stats vs ON v.id = vs.variation_id
            GROUP BY v.id, v.variation_name, v.description, v.config, v.status, v.created_at, v.updated_at
            ORDER BY v.id ASC
        """)

        variations_raw = cursor.fetchall()
        
        # Nettoyer et enrichir les données
        result = []
        for var in variations_raw:
            var_dict = dict(var)
            
            # Extraire config
            config = var_dict.get('config', {})
            if isinstance(config, dict):
                api_boost = config.get('api_boost', {})
                var_dict['enabled_factors'] = list(api_boost.keys()) if api_boost else []
                var_dict['use_api_football'] = config.get('use_api_football', False)
                var_dict['custom_threshold'] = config.get('confidence_threshold')
            else:
                var_dict['enabled_factors'] = []
                var_dict['use_api_football'] = False
                var_dict['custom_threshold'] = None
            
            # Déterminer si contrôle
            name_lower = var_dict.get('name', '').lower()
            var_dict['is_control'] = 'baseline' in name_lower or 'contrôle' in name_lower
            
            # Status actif
            var_dict['is_active'] = var_dict.get('status') in ['active', 'testing']
            
            # Traffic par défaut
            var_dict['traffic_percentage'] = 20
            
            # Enabled adjustments
            var_dict['enabled_adjustments'] = []
            
            # Convertir en float si nécessaire
            var_dict['win_rate'] = float(var_dict.get('win_rate', 0))
            var_dict['total_profit'] = float(var_dict.get('total_profit', 0))
            var_dict['roi'] = float(var_dict.get('roi', 0))
            
            result.append(var_dict)

        conn.close()

        return {
            "success": True,
            "improvement_id": improvement_id,
            "total": len(result),
            "variations": result,
            "source": "agent_b_variations + variation_stats (real)",
            "note": "Stats will populate as Ferrari generates signals"
        }
        
    except Exception as e:
        logger.error(f"Erreur get ferrari variations: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
