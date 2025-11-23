from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

class StrategyRanking(BaseModel):
    id: int
    agent_name: str
    strategy_name: str
    win_rate: Optional[float]
    roi: Optional[float]
    total_predictions: int
    tier: Optional[str]
    global_score: Optional[float]
    trend: Optional[str]
    has_improvement_test: bool

@router.get("/ranking")
async def get_strategies_ranking():
    """Récupère le ranking de toutes les stratégies"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM strategies_ranking
            ORDER BY global_score DESC NULLS LAST
        """)
        
        strategies = cursor.fetchall()
        conn.close()
        
        return {
            "success": True,
            "strategies": strategies,
            "total": len(strategies)
        }
        
    except Exception as e:
        logger.error(f"Erreur ranking: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/{strategy_id}")
async def get_strategy_performance(strategy_id: int, days: int = 30):
    """Historique de performance d'une stratégie"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                date,
                predictions_count,
                win_rate,
                roi
            FROM strategy_performance_log
            WHERE strategy_id = %s
            AND date >= NOW() - INTERVAL '%s days'
            ORDER BY date DESC
        """, (strategy_id, days))
        
        performance = cursor.fetchall()
        
        # Stats globales
        cursor.execute("""
            SELECT 
                agent_name,
                strategy_name,
                win_rate,
                roi,
                total_predictions,
                tier
            FROM strategies
            WHERE id = %s
        """, (strategy_id,))
        
        strategy_info = cursor.fetchone()
        conn.close()
        
        return {
            "success": True,
            "strategy": strategy_info,
            "performance_history": performance
        }
        
    except Exception as e:
        logger.error(f"Erreur performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/failures/{agent_name}")
async def get_recent_failures(agent_name: str, limit: int = 10):
    """Récupère les échecs récents d'un agent pour analyse LLM"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                ap.match_id,
                aa.home_team,
                aa.away_team,
                ap.predicted_outcome,
                mr.outcome as actual_outcome,
                ap.confidence,
                aa.factors,
                aa.reasoning
            FROM agent_predictions ap
            JOIN agent_analyses aa ON ap.match_id = aa.match_id 
                AND ap.agent_name = aa.agent_name
            JOIN match_results mr ON ap.match_id = mr.match_id
            WHERE ap.agent_name = %s
            AND ap.was_correct = FALSE
            AND mr.is_finished = TRUE
            ORDER BY ap.created_at DESC
            LIMIT %s
        """, (agent_name, limit))
        
        failures = cursor.fetchall()
        conn.close()
        
        return {
            "success": True,
            "agent_name": agent_name,
            "failures_count": len(failures),
            "failures": failures
        }
        
    except Exception as e:
        logger.error(f"Erreur failures: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/improvement/create")
async def create_improvement(
    strategy_id: int,
    failure_pattern: str,
    missing_factors: List[str],
    new_parameters: dict,
    llm_reasoning: str
):
    """Créer une amélioration suggérée par LLM"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer infos stratégie actuelle
        cursor.execute("""
            SELECT agent_name, strategy_name, win_rate, roi, total_predictions
            FROM strategies WHERE id = %s
        """, (strategy_id,))
        
        strategy = cursor.fetchone()
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Stratégie non trouvée")
        
        # Créer amélioration
        cursor.execute("""
            INSERT INTO strategy_improvements
            (strategy_id, agent_name, strategy_name, baseline_win_rate, 
             baseline_roi, baseline_samples, failure_pattern, missing_factors,
             new_parameters, llm_reasoning)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            strategy_id,
            strategy['agent_name'],
            strategy['strategy_name'],
            strategy['win_rate'],
            strategy['roi'],
            strategy['total_predictions'],
            failure_pattern,
            missing_factors,
            new_parameters,
            llm_reasoning
        ))
        
        improvement_id = cursor.fetchone()['id']
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "improvement_id": improvement_id,
            "message": "Amélioration créée"
        }
        
    except Exception as e:
        logger.error(f"Erreur création amélioration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/improvements")
async def get_all_improvements():
    """Récupère toutes les améliorations suggérées par GPT-4o"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                si.id,
                si.strategy_id,
                si.agent_name,
                si.strategy_name,
                si.baseline_win_rate,
                si.baseline_roi,
                si.baseline_samples,
                si.failure_pattern,
                si.missing_factors,
                si.recommended_adjustments,
                si.llm_reasoning,
                si.new_threshold,
                si.old_threshold,
                si.ab_test_active,
                si.ab_test_start,
                si.ab_test_matches_a,
                si.ab_test_matches_b,
                si.ab_test_wins_a,
                si.ab_test_wins_b,
                si.improvement_validated,
                si.improvement_applied,
                si.performance_gain,
                si.created_at,
                si.analyzed_at,
                -- Calculer win rate A/B test
                CASE 
                    WHEN si.ab_test_matches_a > 0 
                    THEN ROUND(100.0 * si.ab_test_wins_a / si.ab_test_matches_a, 2)
                    ELSE NULL
                END as ab_win_rate_a,
                CASE 
                    WHEN si.ab_test_matches_b > 0 
                    THEN ROUND(100.0 * si.ab_test_wins_b / si.ab_test_matches_b, 2)
                    ELSE NULL
                END as ab_win_rate_b
            FROM strategy_improvements si
            WHERE si.status != 'archived'
            ORDER BY si.created_at DESC
        """)
        
        improvements = cursor.fetchall()
        conn.close()
        
        return {
            "success": True,
            "improvements": improvements,
            "total": len(improvements)
        }
        
    except Exception as e:
        logger.error(f"Erreur improvements: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/improvements/{improvement_id}")
async def get_improvement_details(improvement_id: int):
    """Détails complets d'une amélioration"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                si.*,
                s.win_rate as current_win_rate,
                s.roi as current_roi,
                s.tier as current_tier,
                -- Stats A/B test
                CASE 
                    WHEN si.ab_test_matches_a > 0 
                    THEN ROUND(100.0 * si.ab_test_wins_a / si.ab_test_matches_a, 2)
                    ELSE NULL
                END as ab_win_rate_a,
                CASE 
                    WHEN si.ab_test_matches_b > 0 
                    THEN ROUND(100.0 * si.ab_test_wins_b / si.ab_test_matches_b, 2)
                    ELSE NULL
                END as ab_win_rate_b
            FROM strategy_improvements si
            JOIN strategies s ON si.strategy_id = s.id
            WHERE si.id = %s
        """, (improvement_id,))
        
        improvement = cursor.fetchone()
        conn.close()
        
        if not improvement:
            raise HTTPException(status_code=404, detail="Amélioration non trouvée")
        
        return {
            "success": True,
            "improvement": improvement
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur détails: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/improvements/{improvement_id}/activate-test")
async def activate_ab_test(improvement_id: int):
    """Active un A/B test pour une amélioration"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Vérifier que l'amélioration existe et n'est pas déjà en test
        cursor.execute("""
            SELECT id, ab_test_active, improvement_applied
            FROM strategy_improvements
            WHERE id = %s
        """, (improvement_id,))
        
        improvement = cursor.fetchone()
        
        if not improvement:
            raise HTTPException(status_code=404, detail="Amélioration non trouvée")
        
        if improvement['ab_test_active']:
            raise HTTPException(status_code=400, detail="A/B test déjà actif")
        
        if improvement['improvement_applied']:
            raise HTTPException(status_code=400, detail="Amélioration déjà appliquée")
        
        # Activer le test
        cursor.execute("""
            UPDATE strategy_improvements
            SET 
                ab_test_active = TRUE,
                ab_test_start = NOW(),
                ab_test_matches_a = 0,
                ab_test_matches_b = 0,
                ab_test_wins_a = 0,
                ab_test_wins_b = 0
            WHERE id = %s
            RETURNING id
        """, (improvement_id,))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "A/B test activé",
            "improvement_id": improvement_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur activation test: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/improvements/{improvement_id}/apply")
async def apply_improvement(improvement_id: int):
    """Applique définitivement une amélioration validée"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer amélioration
        cursor.execute("""
            SELECT 
                si.*,
                CASE 
                    WHEN si.ab_test_matches_b > 0 
                    THEN ROUND(100.0 * si.ab_test_wins_b / si.ab_test_matches_b, 2)
                    ELSE NULL
                END as ab_win_rate_b
            FROM strategy_improvements si
            WHERE id = %s
        """, (improvement_id,))
        
        improvement = cursor.fetchone()
        
        if not improvement:
            raise HTTPException(status_code=404, detail="Amélioration non trouvée")
        
        if improvement['improvement_applied']:
            raise HTTPException(status_code=400, detail="Déjà appliquée")
        
        # Calculer gain de performance
        performance_gain = None
        if improvement['ab_win_rate_b'] and improvement['baseline_win_rate']:
            performance_gain = improvement['ab_win_rate_b'] - improvement['baseline_win_rate']
        
        # Appliquer l'amélioration
        cursor.execute("""
            UPDATE strategy_improvements
            SET 
                improvement_applied = TRUE,
                improvement_validated = TRUE,
                ab_test_active = FALSE,
                ab_test_end = NOW(),
                performance_gain = %s
            WHERE id = %s
        """, (performance_gain, improvement_id))
        
        # TODO: Mettre à jour les paramètres de la stratégie dans le code de l'agent
        # Pour l'instant, c'est juste marqué comme appliqué
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Amélioration appliquée",
            "performance_gain": performance_gain
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur application: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/improvements/{improvement_id}")
async def reject_improvement(improvement_id: int):
    """Rejette une amélioration"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM strategy_improvements
            WHERE id = %s
            AND improvement_applied = FALSE
            RETURNING id
        """, (improvement_id,))
        
        deleted = cursor.fetchone()
        
        if not deleted:
            raise HTTPException(
                status_code=404, 
                detail="Amélioration non trouvée ou déjà appliquée"
            )
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Amélioration rejetée"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur rejet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/improvements/{improvement_id}/archive")
async def archive_improvement(
    improvement_id: int,
    reason: str = None
):
    """
    Archive une amélioration pour plus tard
    
    Args:
        improvement_id: ID de l'amélioration
        reason: Raison de l'archivage (optionnel)
    
    Returns:
        {"success": True, "improvement_id": X}
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Vérifier existence
        cursor.execute(
            "SELECT * FROM strategy_improvements WHERE id = %s",
            (improvement_id,)
        )
        improvement = cursor.fetchone()
        
        if not improvement:
            conn.close()
            raise HTTPException(
                status_code=404,
                detail="Amélioration non trouvée"
            )
        
        # Archiver
        cursor.execute("""
            UPDATE strategy_improvements
            SET 
                status = 'archived',
                archived_at = NOW(),
                archived_reason = %s,
                ab_test_active = FALSE
            WHERE id = %s
            RETURNING id, agent_name, status
        """, (reason, improvement_id))
        
        result = cursor.fetchone()
        conn.commit()
        conn.close()
        
        logger.info(f"Amélioration {improvement_id} archivée: {reason}")
        
        return {
            "success": True,
            "improvement_id": improvement_id,
            "agent_name": result['agent_name'],
            "status": result['status'],
            "reason": reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur archivage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/improvements/{improvement_id}/reactivate")
async def reactivate_improvement(improvement_id: int):
    """
    Réactive une amélioration archivée
    
    Args:
        improvement_id: ID de l'amélioration archivée
    
    Returns:
        {"success": True, "improvement_id": X}
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Vérifier que l'amélioration est archivée
        cursor.execute(
            "SELECT * FROM strategy_improvements WHERE id = %s",
            (improvement_id,)
        )
        improvement = cursor.fetchone()
        
        if not improvement:
            conn.close()
            raise HTTPException(
                status_code=404,
                detail="Amélioration non trouvée"
            )
        
        if improvement['status'] != 'archived':
            conn.close()
            raise HTTPException(
                status_code=400,
                detail="Amélioration n'est pas archivée"
            )
        
        # Réactiver
        cursor.execute("""
            UPDATE strategy_improvements
            SET 
                status = 'proposed',
                archived_at = NULL,
                archived_reason = NULL
            WHERE id = %s
            RETURNING id, agent_name, status
        """, (improvement_id,))
        
        result = cursor.fetchone()
        conn.commit()
        conn.close()
        
        logger.info(f"Amélioration {improvement_id} réactivée")
        
        return {
            "success": True,
            "improvement_id": improvement_id,
            "agent_name": result['agent_name'],
            "status": result['status']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur réactivation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
