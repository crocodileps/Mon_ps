from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import structlog
from api.services.database import get_db

logger = structlog.get_logger()
router = APIRouter(prefix="/agents", tags=["agents"])

class AgentStats(BaseModel):
    agent_name: str
    total_recommendations: int
    avg_confidence: float
    avg_edge: float
    outcomes: List[str]
    patron_scores: List[str]

class AgentComparison(BaseModel):
    stats: List[AgentStats]
    total_recommendations: int

@router.get("/stats/detailed")
async def get_agents_stats_detailed():
    """Statistiques détaillées avec taux de succès"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    agent_name,
                    COUNT(*) as total_reco,
                    ROUND(AVG(confidence_score)::numeric, 1) as avg_conf,
                    ROUND(AVG(edge_percent)::numeric, 1) as avg_edge,
                    ARRAY_AGG(DISTINCT recommended_outcome) as outcomes,
                    ARRAY_AGG(DISTINCT patron_score) as scores,
                    COUNT(CASE WHEN bet_placed THEN 1 END) as bets_placed,
                    COUNT(CASE WHEN actual_result = 'won' THEN 1 END) as wins,
                    COUNT(CASE WHEN actual_result = 'lost' THEN 1 END) as losses,
                    ROUND(COUNT(CASE WHEN actual_result = 'won' THEN 1 END)::numeric * 100 / 
                        NULLIF(COUNT(CASE WHEN actual_result IN ('won', 'lost') THEN 1 END), 0), 1) as win_rate
                FROM agent_recommendations
                GROUP BY agent_name
                ORDER BY total_reco DESC
            """)
            
            stats_list = []
            total = 0
            
            for row in cursor.fetchall():
                stats_list.append({
                    "agent_name": row[0],
                    "total_recommendations": row[1],
                    "avg_confidence": float(row[2]) if row[2] else 0,
                    "avg_edge": float(row[3]) if row[3] else 0,
                    "outcomes": row[4] if row[4] else [],
                    "patron_scores": row[5] if row[5] else [],
                    "bets_placed": row[6],
                    "wins": row[7],
                    "losses": row[8],
                    "win_rate": float(row[9]) if row[9] else 0
                })
                total += row[1]
            
            return {
                "stats": stats_list,
                "total_recommendations": total
            }
            
    except Exception as e:
        logger.error("get_agents_stats_detailed_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=AgentComparison)
async def get_agents_stats():
    """Statistiques comparatives des 4 agents ML"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    agent_name,
                    COUNT(*) as total_reco,
                    ROUND(AVG(confidence_score)::numeric, 1) as avg_conf,
                    ROUND(AVG(edge_percent)::numeric, 1) as avg_edge,
                    ARRAY_AGG(DISTINCT recommended_outcome) as outcomes,
                    ARRAY_AGG(DISTINCT patron_score) as scores
                FROM agent_recommendations
                GROUP BY agent_name
                ORDER BY total_reco DESC
            """)
            
            stats_list = []
            total = 0
            
            for row in cursor.fetchall():
                stats_list.append({
                    "agent_name": row[0],
                    "total_recommendations": row[1],
                    "avg_confidence": float(row[2]) if row[2] else 0,
                    "avg_edge": float(row[3]) if row[3] else 0,
                    "outcomes": row[4] if row[4] else [],
                    "patron_scores": row[5] if row[5] else []
                })
                total += row[1]
            
            return {
                "stats": stats_list,
                "total_recommendations": total
            }
            
    except Exception as e:
        logger.error("get_agents_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations")
async def get_agent_recommendations(agent_name: Optional[str] = None, limit: int = 50):
    """Liste des recommandations par agent"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    r.id, r.match_id, r.agent_name, r.recommended_outcome,
                    r.confidence_score, r.edge_percent, r.recommended_odds,
                    r.patron_score, r.detected_at, r.match_commence_time,
                    r.kelly_fraction, r.suggested_stake
                FROM agent_recommendations r
                WHERE 1=1
            """
            params = []
            
            if agent_name:
                query += " AND r.agent_name = %s"
                params.append(agent_name)
            
            query += " ORDER BY r.detected_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            
            recommendations = []
            for row in cursor.fetchall():
                recommendations.append({
                    "id": row[0],
                    "match_id": row[1],
                    "agent_name": row[2],
                    "recommended_outcome": row[3],
                    "confidence_score": float(row[4]) if row[4] else None,
                    "edge_percent": float(row[5]) if row[5] else None,
                    "recommended_odds": float(row[6]) if row[6] else None,
                    "patron_score": row[7],
                    "detected_at": row[8].isoformat() if row[8] else None,
                    "match_commence_time": row[9].isoformat() if row[9] else None,
                    "kelly_fraction": float(row[10]) if row[10] else None,
                    "suggested_stake": float(row[11]) if row[11] else None
                })
            
            return {
                "recommendations": recommendations,
                "count": len(recommendations)
            }
            
    except Exception as e:
        logger.error("get_agent_recommendations_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compare/{agent1}/{agent2}")
async def compare_two_agents(agent1: str, agent2: str):
    """Comparaison détaillée entre 2 agents"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Stats de chaque agent
            cursor.execute("""
                SELECT 
                    agent_name,
                    COUNT(*) as total,
                    ROUND(AVG(confidence_score)::numeric, 1) as avg_conf,
                    ROUND(AVG(edge_percent)::numeric, 1) as avg_edge,
                    COUNT(CASE WHEN edge_percent > 30 THEN 1 END) as high_edge_count,
                    ARRAY_AGG(DISTINCT recommended_outcome) as outcomes,
                    ARRAY_AGG(DISTINCT patron_score) as scores
                FROM agent_recommendations
                WHERE agent_name IN (%s, %s)
                GROUP BY agent_name
            """, (agent1, agent2))
            
            comparison = {}
            for row in cursor.fetchall():
                comparison[row[0]] = {
                    "total_signals": row[1],
                    "avg_confidence": float(row[2]) if row[2] else 0,
                    "avg_edge": float(row[3]) if row[3] else 0,
                    "high_edge_count": row[4],
                    "outcomes": row[5] if row[5] else [],
                    "patron_scores": row[6] if row[6] else []
                }
            
            return {"comparison": comparison}
            
    except Exception as e:
        logger.error("compare_agents_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
