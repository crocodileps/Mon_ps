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
                
                sharpe_ratio = calculate_sharpe_ratio(cursor, agent['agent_name'], date_filter)
                max_dd = calculate_max_drawdown(cursor, agent['agent_name'], date_filter)
                
                result.append({
                    **dict(agent),
                    'roi': roi,
                    'perf_3m': perf_3m,
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_dd,
                    'strengths': strengths,
                    'weaknesses': weaknesses,
                    'recent_bets': recent_bets
                })
            
            correlation = 0.0
            if agent1 and agent2 and len(result) >= 2:
                correlation = calculate_correlation(cursor, agent1, agent2, date_filter)
            
            return {
                "agents": result, 
                "filters": {"sport": sport, "min_edge": min_edge, "days": days},
                "correlation": correlation
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def calculate_roi(cursor, agent_name: str, date_filter: datetime) -> float:
    """Calcule le ROI de l'agent (simplifié car pas de colonnes profit)"""
    return 0.0  # À calculer quand on aura les données de profit réelles




def calculate_sharpe_ratio(cursor, agent_name: str, date_filter: datetime) -> float:
    """Calcule le Sharpe Ratio de l'agent"""
    cursor.execute("""
        WITH daily_returns AS (
            SELECT 
                DATE(detected_at) as day,
                SUM(CASE 
                    WHEN actual_result = 'won' THEN suggested_stake * (recommended_odds - 1)
                    WHEN actual_result = 'lost' THEN -suggested_stake
                    ELSE 0 
                END) as daily_pnl
            FROM agent_recommendations
            WHERE agent_name = %s 
                AND bet_placed = true
                AND actual_result IN ('won', 'lost')
                AND detected_at >= %s
            GROUP BY DATE(detected_at)
        )
        SELECT 
            AVG(daily_pnl) as avg_return,
            STDDEV(daily_pnl) as std_return
        FROM daily_returns
    """, (agent_name, date_filter))
    
    result = cursor.fetchone()
    if result and result['std_return'] and result['std_return'] > 0:
        sharpe = (result['avg_return'] / result['std_return']) * (252 ** 0.5)  # Annualisé
        return round(sharpe, 2)
    return 0.0


def calculate_max_drawdown(cursor, agent_name: str, date_filter: datetime) -> float:
    """Calcule le drawdown maximum"""
    cursor.execute("""
        WITH cumulative_pnl AS (
            SELECT 
                detected_at,
                SUM(CASE 
                    WHEN actual_result = 'won' THEN suggested_stake * (recommended_odds - 1)
                    WHEN actual_result = 'lost' THEN -suggested_stake
                    ELSE 0 
                END) OVER (ORDER BY detected_at) as running_pnl
            FROM agent_recommendations
            WHERE agent_name = %s 
                AND bet_placed = true
                AND actual_result IN ('won', 'lost')
                AND detected_at >= %s
        ),
        peaks AS (
            SELECT 
                detected_at,
                running_pnl,
                MAX(running_pnl) OVER (ORDER BY detected_at) as peak
            FROM cumulative_pnl
        )
        SELECT 
            MIN((running_pnl - peak) / NULLIF(peak, 0) * 100) as max_dd
        FROM peaks
    """, (agent_name, date_filter))
    
    result = cursor.fetchone()
    if result and result['max_dd']:
        return round(result['max_dd'], 1)
    return 0.0


def calculate_correlation(cursor, agent1: str, agent2: str, date_filter: datetime) -> float:
    """Calcule la corrélation entre 2 agents (overlap de matchs)"""
    cursor.execute("""
        WITH agent1_matches AS (
            SELECT DISTINCT match_id 
            FROM agent_recommendations 
            WHERE agent_name = %s AND detected_at >= %s
        ),
        agent2_matches AS (
            SELECT DISTINCT match_id 
            FROM agent_recommendations 
            WHERE agent_name = %s AND detected_at >= %s
        )
        SELECT 
            COUNT(DISTINCT a1.match_id) as total_agent1,
            COUNT(DISTINCT a2.match_id) as total_agent2,
            COUNT(DISTINCT CASE WHEN a1.match_id = a2.match_id THEN a1.match_id END) as overlap
        FROM agent1_matches a1
        FULL OUTER JOIN agent2_matches a2 ON a1.match_id = a2.match_id
    """, (agent1, date_filter, agent2, date_filter))
    
    result = cursor.fetchone()
    if result and result['total_agent1'] > 0:
        correlation = (result['overlap'] / result['total_agent1']) * 100
        return round(correlation, 1)
    return 0.0


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
