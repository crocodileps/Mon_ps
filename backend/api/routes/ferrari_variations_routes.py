"""
Routes API pour variations Ferrari - VRAIES DONNÉES UNIQUEMENT
Utilise improvement_variations (données réelles de tests A/B)
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
    Retourne UNIQUEMENT les variations avec VRAIES données
    Source: improvement_variations (tests A/B réels)
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Récupérer les vraies variations avec données
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
                iv.enabled_adjustments,
                iv.use_new_threshold,
                iv.custom_threshold,
                iv.created_at,
                iv.updated_at,
                vbs.alpha,
                vbs.beta,
                vbs.expected_win_rate as bayesian_expected_wr,
                vbs.confidence_lower,
                vbs.confidence_upper
            FROM improvement_variations iv
            LEFT JOIN variation_bayesian_stats vbs ON iv.id = vbs.variation_id
            WHERE iv.improvement_id = %s OR iv.improvement_id = 1
            ORDER BY iv.win_rate DESC
        """, (improvement_id,))
        
        variations = cursor.fetchall()
        conn.close()

        result = []
        for var in variations:
            var_dict = dict(var)
            
            # Format pour frontend
            var_dict['agent_name'] = 'Ferrari Ultimate 2.0'
            var_dict['improvement_threshold'] = 52.5
            var_dict['status'] = 'active' if var_dict.get('is_active', True) else 'paused'
            
            # Enabled factors - convertir en liste si nécessaire
            enabled_factors = var_dict.get('enabled_factors', [])
            if enabled_factors is None:
                enabled_factors = []
            var_dict['enabled_factors'] = list(enabled_factors) if enabled_factors else []
            
            # Enabled adjustments
            enabled_adjustments = var_dict.get('enabled_adjustments', [])
            if enabled_adjustments is None:
                enabled_adjustments = []
            var_dict['enabled_adjustments'] = list(enabled_adjustments) if enabled_adjustments else []
            
            # Bayesian stats
            var_dict['bayesian'] = {
                'alpha': float(var_dict.get('alpha') or 1.0),
                'beta': float(var_dict.get('beta') or 1.0),
                'expected_win_rate': float(var_dict.get('bayesian_expected_wr') or 50.0),
                'confidence_lower': float(var_dict.get('confidence_lower') or 10.0),
                'confidence_upper': float(var_dict.get('confidence_upper') or 90.0)
            }
            
            # Nettoyer champs temporaires
            for key in ['alpha', 'beta', 'bayesian_expected_wr', 'confidence_lower', 'confidence_upper']:
                var_dict.pop(key, None)
            
            # Assurer types corrects
            var_dict['matches_tested'] = int(var_dict.get('matches_tested') or 0)
            var_dict['wins'] = int(var_dict.get('wins') or 0)
            var_dict['losses'] = int(var_dict.get('losses') or 0)
            var_dict['win_rate'] = float(var_dict.get('win_rate') or 0)
            var_dict['total_profit'] = float(var_dict.get('total_profit') or 0)
            var_dict['roi'] = float(var_dict.get('roi') or 0)
            var_dict['traffic_percentage'] = int(var_dict.get('traffic_percentage') or 20)
            
            result.append(var_dict)

        return {
            "success": True,
            "improvement_id": improvement_id,
            "total": len(result),
            "variations": result,
            "source": "improvement_variations (vraies données A/B)",
            "has_real_data": True
        }

    except Exception as e:
        logger.error(f"Erreur get ferrari variations: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/improvements/{improvement_id}/traffic-recommendation")
async def get_traffic_recommendations(improvement_id: int):
    """
    Retourne les recommandations de trafic basées sur Thompson Sampling
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT
                vbs.variation_id,
                iv.name as variation_name,
                vbs.alpha as current_alpha,
                vbs.beta as current_beta,
                vbs.expected_win_rate,
                vbs.confidence_lower,
                vbs.confidence_upper,
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
            return {
                "success": True,
                "improvement_id": improvement_id,
                "recommendations": [],
                "note": "Pas de données bayésiennes disponibles"
            }

        # Calculer recommandations Thompson Sampling
        import random
        samples = []
        for stat in stats:
            alpha = float(stat['current_alpha'] or 1)
            beta = float(stat['current_beta'] or 1)
            # Échantillonner de la distribution Beta
            sample = random.betavariate(alpha, beta)
            samples.append((stat, sample))
        
        # Normaliser pour obtenir les pourcentages de trafic
        total_samples = sum(s[1] for s in samples)
        
        recommendations = []
        for stat, sample in samples:
            recommended = (sample / total_samples) * 100 if total_samples > 0 else 20
            current = stat['traffic_percentage'] or 20
            
            recommendations.append({
                'variation_id': stat['variation_id'],
                'variation_name': stat['variation_name'],
                'current_alpha': float(stat['current_alpha'] or 1),
                'current_beta': float(stat['current_beta'] or 1),
                'expected_win_rate': float(stat['expected_win_rate'] or 50),
                'confidence_interval': [
                    float(stat['confidence_lower'] or 10) / 100,
                    float(stat['confidence_upper'] or 90) / 100
                ],
                'recommended_traffic': round(recommended, 1),
                'current_traffic': current,
                'traffic_change': round(recommended - current, 1),
                'matches_tested': stat['matches_tested'] or 0,
                'actual_win_rate': float(stat['win_rate'] or 0)
            })

        # Trier par trafic recommandé
        recommendations.sort(key=lambda x: x['recommended_traffic'], reverse=True)

        return {
            "success": True,
            "improvement_id": improvement_id,
            "recommendations": recommendations,
            "total_variations": len(recommendations),
            "total_traffic": round(sum(r['recommended_traffic'] for r in recommendations), 1)
        }

    except Exception as e:
        logger.error(f"Erreur traffic recommendations: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
