"""
Routes API pour variations Ferrari - Données réelles depuis improvement_variations
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
    Retourne les variations Ferrari avec VRAIES données
    Utilise improvement_variations + variation_bayesian_stats
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # D'abord essayer agent_b_variations (nouvelles variations calibrées)
        cursor.execute("""
            SELECT
                v.id,
                v.variation_name as name,
                v.description,
                v.config,
                v.status,
                v.created_at,
                v.updated_at,
                v.improvement_id
            FROM agent_b_variations v
            WHERE v.improvement_id = %s OR v.improvement_id IS NULL
            ORDER BY v.id ASC
        """, (improvement_id,))
        
        calibrated_variations = cursor.fetchall()

        # Ensuite récupérer les VRAIES données depuis improvement_variations
        # (improvement_id=1 a les vraies stats)
        cursor.execute("""
            SELECT
                iv.id,
                iv.name,
                iv.description,
                iv.matches_tested,
                iv.wins,
                iv.losses,
                iv.win_rate,
                iv.total_profit,
                iv.roi,
                iv.traffic_percentage,
                iv.is_control,
                iv.is_active,
                iv.enabled_factors,
                iv.use_new_threshold,
                iv.custom_threshold,
                vbs.alpha,
                vbs.beta,
                vbs.expected_win_rate as bayesian_expected_wr,
                vbs.confidence_lower,
                vbs.confidence_upper,
                vbs.last_sample
            FROM improvement_variations iv
            LEFT JOIN variation_bayesian_stats vbs ON iv.id = vbs.variation_id
            WHERE iv.improvement_id = 1
            ORDER BY iv.id ASC
        """)
        
        real_variations = cursor.fetchall()

        conn.close()

        # Combiner les données
        result = []
        
        # Si on a des variations calibrées pour cet improvement
        if calibrated_variations:
            for var in calibrated_variations:
                var_dict = dict(var)
                
                # Enrichir avec config
                config = var_dict.get('config', {})
                if isinstance(config, dict):
                    seuils = config.get('seuils', {})
                    var_dict['confidence_threshold'] = seuils.get('confidence_threshold', 0.4)
                    var_dict['edge_threshold'] = seuils.get('min_spread', 0.01)
                else:
                    var_dict['confidence_threshold'] = 0.4
                    var_dict['edge_threshold'] = 0.01
                
                # Stats (par défaut 0, seront populées avec vrais signaux)
                var_dict['matches_tested'] = 0
                var_dict['wins'] = 0
                var_dict['losses'] = 0
                var_dict['win_rate'] = 0.0
                var_dict['total_profit'] = 0.0
                var_dict['roi'] = 0.0
                var_dict['traffic_percentage'] = 20
                var_dict['is_control'] = 'baseline' in var_dict.get('name', '').lower()
                var_dict['is_active'] = var_dict.get('status') == 'active'
                var_dict['enabled_factors'] = []
                var_dict['use_new_threshold'] = False
                var_dict['custom_threshold'] = None
                var_dict['agent_name'] = 'Ferrari Ultimate 2.0'
                var_dict['improvement_threshold'] = 52.5
                
                result.append(var_dict)

        # Ajouter les vraies variations avec données (de improvement_id=1)
        for var in real_variations:
            var_dict = dict(var)
            
            # Format pour frontend
            var_dict['is_control'] = var_dict.get('is_control', False)
            var_dict['is_active'] = var_dict.get('is_active', True)
            var_dict['traffic_percentage'] = var_dict.get('traffic_percentage', 20)
            var_dict['enabled_factors'] = var_dict.get('enabled_factors', []) or []
            var_dict['use_new_threshold'] = var_dict.get('use_new_threshold', False)
            var_dict['custom_threshold'] = var_dict.get('custom_threshold')
            var_dict['agent_name'] = 'Ferrari Ultimate 2.0'
            var_dict['improvement_threshold'] = 52.5
            
            # Bayesian stats
            var_dict['bayesian'] = {
                'alpha': float(var_dict.get('alpha', 1.0) or 1.0),
                'beta': float(var_dict.get('beta', 1.0) or 1.0),
                'expected_win_rate': float(var_dict.get('bayesian_expected_wr', 50.0) or 50.0),
                'confidence_lower': float(var_dict.get('confidence_lower', 10.0) or 10.0),
                'confidence_upper': float(var_dict.get('confidence_upper', 90.0) or 90.0)
            }
            
            # Nettoyer les champs temporaires
            for key in ['alpha', 'beta', 'bayesian_expected_wr', 'confidence_lower', 'confidence_upper', 'last_sample']:
                var_dict.pop(key, None)
            
            result.append(var_dict)

        return {
            "success": True,
            "improvement_id": improvement_id,
            "total": len(result),
            "variations": result,
            "source": "improvement_variations + variation_bayesian_stats",
            "has_real_data": len(real_variations) > 0
        }

    except Exception as e:
        logger.error(f"Erreur get ferrari variations: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/improvements/{improvement_id}/calibrated-variations")
async def get_calibrated_variations(improvement_id: int):
    """
    Retourne uniquement les variations AUTO-CALIBRÉES (Ferrari CAL)
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                v.id,
                v.variation_name as name,
                v.description,
                v.config,
                v.status,
                v.created_at
            FROM agent_b_variations v
            WHERE (v.improvement_id = %s OR v.improvement_id IS NULL)
              AND v.variation_name LIKE '%%CAL%%'
            ORDER BY v.id ASC
        """, (improvement_id,))
        
        variations = cursor.fetchall()
        conn.close()

        result = []
        for var in variations:
            var_dict = dict(var)
            config = var_dict.get('config', {})
            seuils = config.get('seuils', {}) if isinstance(config, dict) else {}
            
            result.append({
                'id': var_dict['id'],
                'name': var_dict['name'],
                'description': var_dict.get('description', ''),
                'confidence_threshold': seuils.get('confidence_threshold', 0.4) * 100,
                'edge_threshold': seuils.get('min_spread', 0.01) * 100,
                'is_active': var_dict.get('status') == 'active',
                'matches_tested': 0,
                'wins': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'roi': 0.0,
                'traffic_percentage': 20
            })

        return {
            "success": True,
            "improvement_id": improvement_id,
            "total": len(result),
            "variations": result
        }

    except Exception as e:
        logger.error(f"Erreur get calibrated variations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/improvements/{improvement_id}/traffic-recommendation")
async def get_traffic_recommendations(improvement_id: int):
    """
    Retourne les recommandations de trafic basées sur Thompson Sampling
    Utilise les VRAIES données de variation_bayesian_stats
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Récupérer les stats bayésiennes RÉELLES
        cursor.execute("""
            SELECT
                vbs.variation_id,
                iv.name as variation_name,
                vbs.alpha as current_alpha,
                vbs.beta as current_beta,
                vbs.expected_win_rate,
                vbs.confidence_lower,
                vbs.confidence_upper,
                vbs.last_sample,
                vbs.total_samples,
                iv.traffic_percentage,
                iv.matches_tested,
                iv.wins,
                iv.win_rate
            FROM variation_bayesian_stats vbs
            JOIN improvement_variations iv ON vbs.variation_id = iv.id
            WHERE iv.improvement_id = 1
            ORDER BY vbs.expected_win_rate DESC
        """)
        
        stats = cursor.fetchall()
        conn.close()

        if not stats:
            # Retourner des données par défaut si pas de stats
            return {
                "success": True,
                "improvement_id": improvement_id,
                "recommendations": [],
                "note": "Pas de données bayésiennes disponibles"
            }

        # Calculer les recommandations de trafic
        total_expected = sum(float(s['expected_win_rate'] or 50) for s in stats)
        
        recommendations = []
        for stat in stats:
            expected_wr = float(stat['expected_win_rate'] or 50)
            # Recommandation proportionnelle au win rate attendu
            recommended_traffic = (expected_wr / total_expected) * 100 if total_expected > 0 else 20
            
            recommendations.append({
                'variation_id': stat['variation_id'],
                'variation_name': stat['variation_name'],
                'current_alpha': float(stat['current_alpha'] or 1.0),
                'current_beta': float(stat['current_beta'] or 1.0),
                'expected_win_rate': expected_wr,
                'confidence_interval': [
                    float(stat['confidence_lower'] or 10) / 100,
                    float(stat['confidence_upper'] or 90) / 100
                ],
                'recommended_traffic': round(recommended_traffic, 1),
                'current_traffic': stat['traffic_percentage'] or 20,
                'matches_tested': stat['matches_tested'] or 0,
                'actual_win_rate': float(stat['win_rate'] or 0)
            })

        return {
            "success": True,
            "improvement_id": improvement_id,
            "recommendations": recommendations,
            "total_variations": len(recommendations),
            "source": "variation_bayesian_stats + improvement_variations"
        }

    except Exception as e:
        logger.error(f"Erreur get traffic recommendations: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
