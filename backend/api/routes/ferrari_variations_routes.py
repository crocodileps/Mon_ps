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
    avec leurs stats réelles depuis variation_stats (VIEW)
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # variation_stats est une VIEW avec stats déjà agrégées
        cursor.execute("""
            SELECT
                v.id,
                v.variation_name as name,
                v.description,
                v.config,
                v.status,
                v.created_at,
                v.updated_at,
                -- Stats depuis la VIEW (déjà calculées)
                COALESCE(vs.total_bets, 0) as matches_tested,
                COALESCE(vs.wins, 0) as wins,
                COALESCE(vs.losses, 0) as losses,
                COALESCE(vs.win_rate, 0) as win_rate,
                COALESCE(vs.total_profit, 0) as total_profit,
                COALESCE(vs.roi, 0) as roi
            FROM agent_b_variations v
            LEFT JOIN variation_stats vs ON v.id = vs.variation_id
            WHERE v.improvement_id = %s OR v.improvement_id IS NULL
            ORDER BY v.id ASC
        """, (improvement_id,))

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
                var_dict['use_new_threshold'] = config.get('use_api_football', False)
            else:
                var_dict['enabled_factors'] = []
                var_dict['use_api_football'] = False
                var_dict['custom_threshold'] = None
                var_dict['use_new_threshold'] = False
            
            # Déterminer si contrôle
            name_lower = var_dict.get('name', '').lower()
            var_dict['is_control'] = 'baseline' in name_lower or 'contrôle' in name_lower or 'control' in name_lower
            
            # Status actif
            var_dict['is_active'] = var_dict.get('status') in ['active', 'testing']
            
            # Traffic par défaut (sera ajusté par Thompson Sampling)
            var_dict['traffic_percentage'] = 20
            
            # Enabled adjustments
            var_dict['enabled_adjustments'] = []
            
            # Assurer types corrects
            var_dict['matches_tested'] = int(var_dict.get('matches_tested', 0))
            var_dict['wins'] = int(var_dict.get('wins', 0))
            var_dict['losses'] = int(var_dict.get('losses', 0))
            var_dict['win_rate'] = float(var_dict.get('win_rate', 0))
            var_dict['total_profit'] = float(var_dict.get('total_profit', 0))
            var_dict['roi'] = float(var_dict.get('roi', 0))
            
            # Ajouter agent_name et improvement_threshold (pour compatibilité frontend)
            var_dict['agent_name'] = 'Ferrari Ultimate 2.0'
            var_dict['improvement_threshold'] = 52.5
            
            result.append(var_dict)

        conn.close()

        return {
            "success": True,
            "improvement_id": improvement_id,
            "total": len(result),
            "variations": result,
            "source": "agent_b_variations + variation_stats VIEW",
            "note": "Stats will populate as Ferrari generates real signals"
        }
        
    except Exception as e:
        logger.error(f"Erreur get ferrari variations: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
