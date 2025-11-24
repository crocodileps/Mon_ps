"""
Routes Ferrari Monitoring - Métriques et Dashboard
"""
from fastapi import APIRouter, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'monps_postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

@router.get("/monitoring/overview")
async def get_ferrari_overview():
    """
    Vue d'ensemble Ferrari - Métriques depuis improvement_variations
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Compter variations
        cursor.execute("SELECT COUNT(*) as total, COUNT(CASE WHEN status = 'active' THEN 1 END) as active FROM agent_b_variations")
        var_counts = cursor.fetchone()
        
        # Stats depuis improvement_variations (vraies données)
        cursor.execute("""
            SELECT
                COUNT(*) as variations_tested,
                SUM(matches_tested) as total_signals,
                SUM(wins) as total_wins,
                AVG(win_rate) as avg_win_rate,
                AVG(roi) as avg_roi,
                SUM(total_profit) as total_profit
            FROM improvement_variations
            WHERE matches_tested > 0
        """)
        stats = cursor.fetchone()
        
        # Top variations
        cursor.execute("""
            SELECT id, name as variation_name, matches_tested as total_bets, wins, win_rate, roi, total_profit
            FROM improvement_variations
            WHERE matches_tested > 0
            ORDER BY win_rate DESC
            LIMIT 5
        """)
        top_vars = cursor.fetchall()
        
        conn.close()
        
        return {
            "success": True,
            "overview": {
                "total_variations": var_counts['total'] or 0,
                "active_variations": var_counts['active'] or 0,
                "variations_tested": stats['variations_tested'] or 0,
                "total_signals": int(stats['total_signals'] or 0),
                "total_wins": int(stats['total_wins'] or 0),
                "avg_win_rate": float(stats['avg_win_rate'] or 0),
                "avg_roi": float(stats['avg_roi'] or 0),
                "total_profit": float(stats['total_profit'] or 0)
            },
            "top_variations": [dict(v) for v in top_vars]
        }
        
    except Exception as e:
        logger.error(f"Erreur monitoring: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/daily-runs")
async def get_daily_runs(limit: int = 30):
    return {"success": True, "runs": []}


@router.get("/monitoring/performance-chart")
async def get_performance_chart():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT name, matches_tested, wins, win_rate, total_profit, roi
            FROM improvement_variations WHERE matches_tested > 0
            ORDER BY win_rate DESC
        """)
        data = cursor.fetchall()
        conn.close()
        return {"success": True, "chart_data": [dict(d) for d in data]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
