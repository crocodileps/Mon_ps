from fastapi import APIRouter, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

router = APIRouter()

DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

@router.get("/agents")  # ✅ CORRIGÉ : pas /stats/agents
async def get_agents_stats():
    """Statistiques des agents (analyses enregistrées)"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Total analyses par agent
        cursor.execute("""
            SELECT 
                agent_name,
                COUNT(*) as total_analyses,
                AVG(confidence_score) as avg_confidence,
                MAX(analyzed_at) as last_analysis
            FROM agent_analyses
            GROUP BY agent_name
            ORDER BY total_analyses DESC;
        """)
        agents_summary = cursor.fetchall()
        
        # Dernières analyses
        cursor.execute("""
            SELECT 
                agent_name,
                recommendation,
                confidence_score,
                home_team,
                away_team,
                analyzed_at
            FROM agent_analyses
            ORDER BY analyzed_at DESC
            LIMIT 20;
        """)
        recent_analyses = cursor.fetchall()
        
        # Prédictions
        cursor.execute("""
            SELECT 
                agent_name,
                predicted_outcome,
                confidence,
                strategy_used,
                was_correct,
                predicted_at
            FROM agent_predictions
            ORDER BY predicted_at DESC
            LIMIT 20;
        """)
        predictions = cursor.fetchall()
        
        conn.close()
        
        return {
            "agents_summary": [dict(row) for row in agents_summary],
            "recent_analyses": [dict(row) for row in recent_analyses],
            "predictions": [dict(row) for row in predictions]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
