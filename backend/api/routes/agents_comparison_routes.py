from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from api.services.database import get_db

router = APIRouter(prefix="/agents", tags=["agents_comparison"])

@router.get("/comparison")
async def get_agents_comparison(
    agent1: Optional[str] = None,
    agent2: Optional[str] = None,
    sport: Optional[str] = None,
    min_edge: Optional[float] = 0.0,
    days: Optional[int] = 90
) -> Dict[str, Any]:
    """Comparaison détaillée entre agents avec toutes les métriques"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            date_filter = datetime.now() - timedelta(days=days)
            
            query = """
                WITH agent_stats AS (
                    SELECT 
                        ar.agent_name,
                        COUNT(*) as total_signals,
                        ROUND(AVG(ar.confidence_score)::numeric, 1) as avg_confidence,
                        ROUND(AVG(ar.edge_percent)::numeric, 1) as avg_edge,
                        ROUND(AVG(ar.kelly_fraction)::numeric, 4) as avg_kelly,
                        COUNT(CASE WHEN ar.bet_placed THEN 1 END) as bets_placed,
                        COUNT(CASE WHEN ar.actual_result = 'won' THEN 1 END) as wins,
                        COUNT(CASE WHEN ar.actual_result = 'lost' THEN 1 END) as losses,
                        COUNT(CASE WHEN ar.actual_result = 'pending' THEN 1 END) as pending,
                        ROUND(
                            COUNT(CASE WHEN ar.actual_result = 'won' THEN 1 END)::numeric * 100 / 
                            NULLIF(COUNT(CASE WHEN ar.actual_result IN ('won', 'lost') THEN 1 END), 0), 
                            1
                        ) as win_rate,
                        ARRAY_AGG(DISTINCT ar.recommended_outcome) as outcomes
                    FROM agent_recommendations ar
                    LEFT JOIN odds_history oh ON ar.match_id = oh.match_id
                    WHERE ar.detected_at >= %s
                        AND (%s IS NULL OR ar.agent_name = %s)
                        AND (%s IS NULL OR oh.sport = %s)
                        AND ar.edge_percent >= %s
                    GROUP BY ar.agent_name
                )
                SELECT * FROM agent_stats
                ORDER BY total_signals DESC;
            """
            
            cursor.execute(query, (date_filter, agent1, agent1, sport, sport, min_edge))
            agents = cursor.fetchall()
            
            result = []
            for agent in agents:
                roi = calculate_roi(cursor, agent['agent_name'], date_filter)
                perf_3m = calculate_perf_3m(cursor, agent['agent_name'])
                strengths, weaknesses = analyze_agent_performance(
                    cursor, agent['agent_name'], agent['win_rate'], agent['avg_edge']
                )
                recent_bets = get_recent_bets(cursor, agent['agent_name'], limit=10)
                
                result.append({
                    **dict(agent),
                    'roi': roi,
                    'perf_3m': perf_3m,
                    'strengths': strengths,
                    'weaknesses': weaknesses,
                    'recent_bets': recent_bets
                })
            
            return {"agents": result, "filters": {"sport": sport, "min_edge": min_edge, "days": days}}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def calculate_roi(cursor, agent_name: str, date_filter: datetime) -> float:
    """Calcule le ROI de l'agent (simplifié car pas de colonnes profit)"""
    return 0.0  # À calculer quand on aura les données de profit réelles


def calculate_perf_3m(cursor, agent_name: str) -> str:
    """Performance sur 3 mois"""
    three_months_ago = datetime.now() - timedelta(days=90)
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN actual_result = 'won' THEN 1 END) as wins,
            COUNT(CASE WHEN actual_result IN ('won', 'lost') THEN 1 END) as total
        FROM agent_recommendations
        WHERE agent_name = %s AND bet_placed = true AND detected_at >= %s
    """, (agent_name, three_months_ago))
    
    result = cursor.fetchone()
    if result and result['total'] > 0:
        win_rate = (result['wins'] / result['total']) * 100
        return f"+{win_rate:.1f}%" if win_rate > 50 else f"{win_rate:.1f}%"
    return "N/A"


def analyze_agent_performance(cursor, agent_name: str, win_rate: float, avg_edge: float) -> tuple:
    """Analyse forces et faiblesses"""
    strengths = []
    weaknesses = []
    
    cursor.execute("""
        SELECT recommended_outcome, COUNT(CASE WHEN actual_result = 'won' THEN 1 END) as wins,
               COUNT(CASE WHEN actual_result IN ('won', 'lost') THEN 1 END) as total
        FROM agent_recommendations
        WHERE agent_name = %s AND bet_placed = true
        GROUP BY recommended_outcome
        HAVING COUNT(*) >= 3
    """, (agent_name,))
    
    outcomes = cursor.fetchall()
    for outcome in outcomes:
        if outcome['total'] > 0:
            outcome_wr = (outcome['wins'] / outcome['total']) * 100
            if outcome_wr > 65:
                strengths.append(f"Excellent sur {outcome['recommended_outcome']} ({outcome_wr:.0f}%)")
            elif outcome_wr < 45:
                weaknesses.append(f"Faible sur {outcome['recommended_outcome']} ({outcome_wr:.0f}%)")
    
    if avg_edge and avg_edge > 40:
        strengths.append(f"Edge élevé ({avg_edge:.1f}%)")
    elif avg_edge and avg_edge < 20:
        weaknesses.append(f"Edge faible ({avg_edge:.1f}%)")
    
    cursor.execute("SELECT COUNT(*) as total FROM agent_recommendations WHERE agent_name = %s", (agent_name,))
    volume = cursor.fetchone()['total']
    
    if volume > 20:
        strengths.append(f"Volume élevé ({volume} signaux)")
    elif volume < 10:
        weaknesses.append(f"Volume faible ({volume} signaux)")
    
    return strengths or ["Performance stable"], weaknesses or ["Aucune faiblesse majeure"]


def get_recent_bets(cursor, agent_name: str, limit: int = 10) -> List[Dict]:
    """Derniers paris"""
    cursor.execute("""
        SELECT ar.match_id, oh.sport, ar.recommended_outcome, ar.confidence_score, ar.edge_percent,
               ar.bet_placed, ar.actual_result, ar.detected_at, ar.recommended_odds
        FROM agent_recommendations ar
        LEFT JOIN odds_history oh ON ar.match_id = oh.match_id
        WHERE ar.agent_name = %s
        ORDER BY ar.detected_at DESC
        LIMIT %s
    """, (agent_name, limit))
    
    bets = cursor.fetchall()
    return [dict(bet) for bet in bets]
