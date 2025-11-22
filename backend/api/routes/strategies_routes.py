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
