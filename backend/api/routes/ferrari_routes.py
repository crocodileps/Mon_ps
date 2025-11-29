from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import sys
sys.path.append('/app')
from ml.thompson_sampling import ThompsonSampling, SafeguardMonitor, chi_squared_test, bayesian_ab_test

router = APIRouter()
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# ============================================================================
# MODÈLES
# ============================================================================

class MatchAssignment(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    sport: str
    commence_time: str

class MatchResult(BaseModel):
    assignment_id: int
    outcome: str  # 'win', 'loss', 'void'
    profit: float
    stake: float
    odds: float

# ============================================================================
# ENDPOINT 1 : ASSIGNER MATCH À UNE VARIATION (THOMPSON SAMPLING)
# ============================================================================

@router.post("/improvements/{improvement_id}/assign-match")
async def assign_match_to_variation(improvement_id: int, match: MatchAssignment):
    """
    Assigne un match à une variation via Thompson Sampling
    Utilise Multi-Armed Bandit pour sélection optimale
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer variations actives
        cursor.execute("""
            SELECT v.*, bs.alpha, bs.beta
            FROM improvement_variations v
            JOIN variation_bayesian_stats bs ON v.id = bs.variation_id
            WHERE v.improvement_id = %s AND v.is_active = TRUE
        """, (improvement_id,))
        
        variations = cursor.fetchall()
        
        if not variations:
            conn.close()
            raise HTTPException(status_code=404, detail="Aucune variation active")
        
        # Initialiser Thompson Sampling
        ts = ThompsonSampling()
        for var in variations:
            ts.add_variation(var['id'], var['alpha'], var['beta'])
        
        # Sélectionner variation gagnante
        selected_variation_id = ts.select_variation()
        
        # Enregistrer assignation
        cursor.execute("""
            INSERT INTO variation_assignments (
                match_id, variation_id, improvement_id,
                home_team, away_team, sport, commence_time,
                assignment_method
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'thompson_sampling')
            RETURNING id, variation_id
        """, (
            match.match_id, selected_variation_id, improvement_id,
            match.home_team, match.away_team, match.sport, match.commence_time
        ))
        
        assignment = cursor.fetchone()
        
        # Sample pour logging
        cursor.execute("""
            UPDATE variation_bayesian_stats
            SET last_sample = %s, last_sampled_at = NOW(), total_samples = total_samples + 1
            WHERE variation_id = %s
        """, (ts.variations[selected_variation_id]['samples'][-1], selected_variation_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Match {match.match_id} assigné à variation {selected_variation_id}")
        
        return {
            "success": True,
            "assignment_id": assignment['id'],
            "variation_id": assignment['variation_id'],
            "match_id": match.match_id,
            "method": "thompson_sampling"
        }
        
    except Exception as e:
        logger.error(f"Erreur assign match: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 2 : ENREGISTRER RÉSULTAT (UPDATE BAYÉSIEN)
# ============================================================================

@router.post("/assignments/{assignment_id}/result")
async def record_match_result(assignment_id: int, result: MatchResult):
    """
    Enregistre résultat et met à jour stats Bayésiennes
    Update automatique Alpha/Beta selon outcome
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer assignation
        cursor.execute("""
            SELECT * FROM variation_assignments WHERE id = %s
        """, (assignment_id,))
        
        assignment = cursor.fetchone()
        if not assignment:
            conn.close()
            raise HTTPException(status_code=404, detail="Assignation non trouvée")
        
        variation_id = assignment['variation_id']
        
        # Mettre à jour assignation
        cursor.execute("""
            UPDATE variation_assignments
            SET outcome = %s, profit = %s, stake = %s, odds = %s, settled_at = NOW()
            WHERE id = %s
        """, (result.outcome, result.profit, result.stake, result.odds, assignment_id))
        
        # Update variation stats
        if result.outcome == 'win':
            cursor.execute("""
                UPDATE improvement_variations
                SET wins = wins + 1, matches_tested = matches_tested + 1,
                    total_profit = total_profit + %s,
                    win_rate = (wins + 1) * 100.0 / (matches_tested + 1),
                    roi = (total_profit + %s) / (SELECT SUM(stake) FROM variation_assignments WHERE variation_id = %s) * 100
                WHERE id = %s
            """, (result.profit, result.profit, variation_id, variation_id))
            
            # Update Bayesian alpha
            cursor.execute("""
                UPDATE variation_bayesian_stats
                SET alpha = alpha + 1,
                    expected_win_rate = (alpha + 1) / (alpha + 1 + beta),
                    updated_at = NOW()
                WHERE variation_id = %s
            """, (variation_id,))
            
        elif result.outcome == 'loss':
            cursor.execute("""
                UPDATE improvement_variations
                SET losses = losses + 1, matches_tested = matches_tested + 1,
                    total_profit = total_profit + %s,
                    win_rate = wins * 100.0 / (matches_tested + 1),
                    roi = (total_profit + %s) / (SELECT SUM(stake) FROM variation_assignments WHERE variation_id = %s) * 100
                WHERE id = %s
            """, (result.profit, result.profit, variation_id, variation_id))
            
            # Update Bayesian beta
            cursor.execute("""
                UPDATE variation_bayesian_stats
                SET beta = beta + 1,
                    expected_win_rate = alpha / (alpha + beta + 1),
                    updated_at = NOW()
                WHERE variation_id = %s
            """, (variation_id,))
        
        # Vérifier safeguards
        cursor.execute("""
            SELECT total_profit, win_rate, matches_tested
            FROM improvement_variations WHERE id = %s
        """, (variation_id,))
        
        var_stats = cursor.fetchone()
        
        monitor = SafeguardMonitor()
        events = monitor.check_variation(
            variation_id,
            var_stats['total_profit'],
            var_stats['win_rate'],
            var_stats['matches_tested']
        )
        
        # Enregistrer événements safeguard
        for event in events:
            cursor.execute("""
                INSERT INTO safeguard_events (
                    variation_id, event_type, severity, message,
                    trigger_value, threshold_value, action_taken
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                variation_id, event['type'], event['severity'], event['message'],
                event.get('trigger_value'), event.get('threshold_value'), event['action']
            ))
            
            # Appliquer action si critique
            if event['severity'] == 'critical' and event['action'] == 'pause_variation':
                cursor.execute("""
                    UPDATE improvement_variations SET is_active = FALSE WHERE id = %s
                """, (variation_id,))
                logger.warning(f"Variation {variation_id} PAUSÉE automatiquement: {event['message']}")
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "variation_id": variation_id,
            "outcome": result.outcome,
            "safeguard_events": len(events),
            "critical_events": sum(1 for e in events if e['severity'] == 'critical')
        }
        
    except Exception as e:
        logger.error(f"Erreur record result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 3 : RECOMMANDATIONS ALLOCATION TRAFIC
# ============================================================================

@router.get("/improvements/{improvement_id}/traffic-recommendation")
async def get_traffic_recommendation(improvement_id: int):
    """
    Calcule allocation trafic optimale via Thompson Sampling
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT v.id, v.name, bs.alpha, bs.beta
            FROM improvement_variations v
            JOIN variation_bayesian_stats bs ON v.id = bs.variation_id
            WHERE v.improvement_id = %s AND v.is_active = TRUE
        """, (improvement_id,))
        
        variations = cursor.fetchall()
        conn.close()
        
        if not variations:
            raise HTTPException(status_code=404, detail="Aucune variation active")
        
        ts = ThompsonSampling()
        for var in variations:
            ts.add_variation(var['id'], var['alpha'], var['beta'])
        
        # Calculer allocation optimale
        allocation = ts.calculate_traffic_allocation(min_traffic=0.05)
        
        recommendations = []
        for var in variations:
            var_id = var['id']
            recommendations.append({
                "variation_id": var_id,
                "variation_name": var['name'],
                "current_alpha": float(var['alpha']),
                "current_beta": float(var['beta']),
                "expected_win_rate": ts.get_expected_win_rate(var_id) * 100,
                "confidence_interval": ts.get_confidence_interval(var_id),
                "recommended_traffic": round(allocation[var_id] * 100, 2)
            })
        
        return {
            "success": True,
            "improvement_id": improvement_id,
            "recommendations": recommendations,
            "total_traffic": round(sum(r['recommended_traffic'] for r in recommendations), 2)
        }
        
    except Exception as e:
        logger.error(f"Erreur traffic recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 4 : TESTS STATISTIQUES
# ============================================================================

@router.get("/variations/compare/{var_a_id}/{var_b_id}")
async def compare_variations(var_a_id: int, var_b_id: int):
    """
    Compare 2 variations avec tests statistiques
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer stats
        cursor.execute("""
            SELECT v.*, bs.alpha, bs.beta
            FROM improvement_variations v
            JOIN variation_bayesian_stats bs ON v.id = bs.variation_id
            WHERE v.id IN (%s, %s)
        """, (var_a_id, var_b_id))
        
        variations = cursor.fetchall()
        
        if len(variations) != 2:
            conn.close()
            raise HTTPException(status_code=404, detail="Variations non trouvées")
        
        var_a = variations[0] if variations[0]['id'] == var_a_id else variations[1]
        var_b = variations[1] if variations[1]['id'] == var_b_id else variations[0]
        
        # Chi-squared
        chi2_result = chi_squared_test(
            var_a['wins'], var_a['losses'],
            var_b['wins'], var_b['losses']
        )
        
        # Bayesian A/B
        bayesian_result = bayesian_ab_test(
            var_a['alpha'], var_a['beta'],
            var_b['alpha'], var_b['beta']
        )
        
        # Enregistrer test
        cursor.execute("""
            INSERT INTO statistical_tests (
                improvement_id, variation_a_id, variation_b_id,
                test_type, test_statistic, p_value,
                is_significant, conclusion
            ) VALUES (%s, %s, %s, 'chi_squared', %s, %s, %s, %s)
        """, (
            var_a['improvement_id'], var_a_id, var_b_id,
            chi2_result['statistic'], chi2_result['p_value'],
            chi2_result['is_significant'], chi2_result['conclusion']
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "variation_a": {"id": var_a_id, "name": var_a['name'], "win_rate": float(var_a['win_rate'])},
            "variation_b": {"id": var_b_id, "name": var_b['name'], "win_rate": float(var_b['win_rate'])},
            "chi_squared_test": chi2_result,
            "bayesian_test": bayesian_result
        }
        
    except Exception as e:
        logger.error(f"Erreur compare variations: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ════════════════════════════════════════════════════════════
# ENDPOINTS POUR DASHBOARD FRONTEND
# ════════════════════════════════════════════════════════════

@router.get("/dashboard-stats")
async def get_dashboard_stats():
    """Stats globales pour le dashboard FERRARI"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        stats = {}
        
        # Count teams
        cur.execute("SELECT COUNT(*) FROM team_intelligence")
        stats['teams'] = cur.fetchone()['count']
        
        # Count scorers
        cur.execute("SELECT COUNT(*) FROM scorer_intelligence")
        stats['scorers'] = cur.fetchone()['count']
        
        # Count patterns
        cur.execute("SELECT COUNT(*) FROM market_patterns")
        stats['patterns'] = cur.fetchone()['count']
        
        # Count profitable patterns
        cur.execute("SELECT COUNT(*) FROM market_patterns WHERE is_profitable = true")
        stats['profitable_patterns'] = cur.fetchone()['count']
        
        # Value alerts (hardcoded for now)
        stats['value_alerts'] = 26
        
        cur.close()
        conn.close()
        
        return stats
        
    except Exception as e:
        return {"error": str(e)}


@router.get("/patterns/all")
async def get_all_patterns(limit: int = 50):
    """Tous les patterns avec filtres"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT pattern_name, pattern_code, market_type, league,
                   win_rate, roi, sample_size, recommendation, is_profitable
            FROM market_patterns
            ORDER BY roi DESC
            LIMIT %s
        """, (limit,))
        
        patterns = cur.fetchall()
        cur.close()
        conn.close()
        
        return {
            "patterns": patterns,
            "total": len(patterns)
        }
        
    except Exception as e:
        return {"error": str(e), "patterns": []}


@router.get("/scorers/top")
async def get_top_scorers(limit: int = 20):
    """Top buteurs"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT player_name, current_team, season_goals, 
                   goals_per_match, is_penalty_taker, tags
            FROM scorer_intelligence
            WHERE season_goals IS NOT NULL
            ORDER BY season_goals DESC
            LIMIT %s
        """, (limit,))
        
        scorers = cur.fetchall()
        cur.close()
        conn.close()
        
        # Parse tags JSON
        for s in scorers:
            if s['tags'] and isinstance(s['tags'], str):
                import json
                try:
                    s['tags'] = json.loads(s['tags'])
                except:
                    s['tags'] = []
        
        return {
            "scorers": scorers,
            "total": len(scorers)
        }
        
    except Exception as e:
        return {"error": str(e), "scorers": []}
