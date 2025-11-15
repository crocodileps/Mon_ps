"""
Routes API pour les Agents ML - Version Complète (4 Agents)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.append('/app/agents')

router = APIRouter(prefix="/agents", tags=["Agents ML"])

# Configuration DB
DB_CONFIG = {
    'host': 'monps_postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}


class AgentSignal(BaseModel):
    agent: str
    match: str
    sport: str
    direction: str
    confidence: float
    reason: str
    spread_pct: Optional[float] = None
    expected_value: Optional[float] = None
    kelly_fraction: Optional[float] = None
    recommended_stake_pct: Optional[float] = None
    bookmaker_count: Optional[int] = None
    pattern_type: Optional[str] = None


class AgentPerformance(BaseModel):
    agent_id: str
    agent_name: str
    total_signals: int
    avg_confidence: float
    avg_ev: float
    avg_kelly: float
    status: str
    top_signal: Optional[Dict[str, Any]] = None


class AgentHealth(BaseModel):
    status: str
    agents: List[str]
    db_connected: bool
    total_opportunities: int


@router.get("/signals", response_model=List[Dict[str, Any]])
async def get_all_agent_signals():
    """Récupère les signaux de tous les 4 agents ML"""
    all_signals = []
    
    # Agent A - Anomaly Detector
    try:
        from agent_anomaly import AnomalyDetectorAgent
        agent_a = AnomalyDetectorAgent(DB_CONFIG)
        signals_a = agent_a.generate_signals(top_n=10)
        all_signals.extend(signals_a)
    except Exception as e:
        print(f"Agent A error: {e}")
    
    # Agent B - Spread Optimizer (Kelly Criterion)
    try:
        from agent_spread import SpreadOptimizerAgent
        agent_b = SpreadOptimizerAgent(DB_CONFIG)
        signals_b = agent_b.generate_signals(top_n=10)
        all_signals.extend(signals_b)
    except Exception as e:
        print(f"Agent B error: {e}")
    
    # Agent C - Pattern Matcher
    try:
        from agent_pattern import PatternMatcherAgent
        agent_c = PatternMatcherAgent(DB_CONFIG)
        signals_c = agent_c.generate_signals(top_n=10)
        all_signals.extend(signals_c)
    except Exception as e:
        print(f"Agent C error: {e}")
    
    # Agent D - Backtest Engine (analyse historique)
    try:
        from agent_backtest import BacktestAgent
        agent_d = BacktestAgent(DB_CONFIG)
        # Agent D fournit des analyses, pas des signaux directs
        # On peut l'utiliser pour valider les autres signaux
    except Exception as e:
        print(f"Agent D error: {e}")
    
    return all_signals


@router.get("/performance", response_model=List[AgentPerformance])
async def get_agents_performance():
    """Récupère les performances comparatives des 4 agents"""
    performances = []
    
    # Agent A - Anomaly Detector
    try:
        from agent_anomaly import AnomalyDetectorAgent
        agent_a = AnomalyDetectorAgent(DB_CONFIG)
        signals = agent_a.generate_signals(top_n=20)
        
        if signals:
            avg_conf = sum(s.get('confidence', 0) for s in signals) / len(signals)
            performances.append({
                'agent_id': 'agent_a',
                'agent_name': 'Anomaly Detector',
                'total_signals': len(signals),
                'avg_confidence': round(avg_conf, 2),
                'avg_ev': 0,  # Anomaly detector ne calcule pas EV
                'avg_kelly': 0,
                'status': 'active',
                'top_signal': signals[0] if signals else None
            })
        else:
            performances.append({
                'agent_id': 'agent_a',
                'agent_name': 'Anomaly Detector',
                'total_signals': 0,
                'avg_confidence': 0,
                'avg_ev': 0,
                'avg_kelly': 0,
                'status': 'no_signals',
                'top_signal': None
            })
    except Exception as e:
        performances.append({
            'agent_id': 'agent_a',
            'agent_name': 'Anomaly Detector',
            'total_signals': 0,
            'avg_confidence': 0,
            'avg_ev': 0,
            'avg_kelly': 0,
            'status': f'error: {str(e)[:50]}',
            'top_signal': None
        })
    
    # Agent B - Spread Optimizer
    try:
        from agent_spread import SpreadOptimizerAgent
        agent_b = SpreadOptimizerAgent(DB_CONFIG)
        signals = agent_b.generate_signals(top_n=20)
        
        if signals:
            avg_conf = sum(s.get('confidence', 0) for s in signals) / len(signals)
            avg_ev = sum(s.get('expected_value', 0) for s in signals) / len(signals)
            avg_kelly = sum(s.get('kelly_fraction', 0) for s in signals) / len(signals)
            
            performances.append({
                'agent_id': 'agent_b',
                'agent_name': 'Spread Optimizer',
                'total_signals': len(signals),
                'avg_confidence': round(avg_conf, 2),
                'avg_ev': round(avg_ev, 2),
                'avg_kelly': round(avg_kelly * 100, 2),
                'status': 'active',
                'top_signal': signals[0] if signals else None
            })
    except Exception as e:
        performances.append({
            'agent_id': 'agent_b',
            'agent_name': 'Spread Optimizer',
            'total_signals': 0,
            'avg_confidence': 0,
            'avg_ev': 0,
            'avg_kelly': 0,
            'status': f'error: {str(e)[:50]}',
            'top_signal': None
        })
    
    # Agent C - Pattern Matcher
    try:
        from agent_pattern import PatternMatcherAgent
        agent_c = PatternMatcherAgent(DB_CONFIG)
        signals = agent_c.generate_signals(top_n=20)
        
        if signals:
            avg_conf = sum(s.get('confidence', 0) for s in signals) / len(signals)
            
            performances.append({
                'agent_id': 'agent_c',
                'agent_name': 'Pattern Matcher',
                'total_signals': len(signals),
                'avg_confidence': round(avg_conf, 2),
                'avg_ev': 0,
                'avg_kelly': 0,
                'status': 'active',
                'top_signal': signals[0] if signals else None
            })
    except Exception as e:
        performances.append({
            'agent_id': 'agent_c',
            'agent_name': 'Pattern Matcher',
            'total_signals': 0,
            'avg_confidence': 0,
            'avg_ev': 0,
            'avg_kelly': 0,
            'status': f'error: {str(e)[:50]}',
            'top_signal': None
        })
    
    # Agent D - Backtest Engine
    try:
        from agent_backtest import BacktestAgent
        agent_d = BacktestAgent(DB_CONFIG)
        
        performances.append({
            'agent_id': 'agent_d',
            'agent_name': 'Backtest Engine',
            'total_signals': 0,  # Backtest ne génère pas de signaux directs
            'avg_confidence': 0,
            'avg_ev': 0,
            'avg_kelly': 0,
            'status': 'active',
            'top_signal': None
        })
    except Exception as e:
        performances.append({
            'agent_id': 'agent_d',
            'agent_name': 'Backtest Engine',
            'total_signals': 0,
            'avg_confidence': 0,
            'avg_ev': 0,
            'avg_kelly': 0,
            'status': f'error: {str(e)[:50]}',
            'top_signal': None
        })
    
    return performances


@router.get("/health")
async def agents_health():
    """Vérifie l'état des agents et de la base de données"""
    import psycopg2
    
    agents_list = []
    db_connected = False
    total_opps = 0
    
    # Test DB connection
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM v_current_opportunities")
        total_opps = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        db_connected = True
    except Exception as e:
        print(f"DB connection error: {e}")
    
    # Test each agent
    try:
        from agent_anomaly import AnomalyDetectorAgent
        agents_list.append("Anomaly Detector")
    except:
        pass
    
    try:
        from agent_spread import SpreadOptimizerAgent
        agents_list.append("Spread Optimizer")
    except:
        pass
    
    try:
        from agent_pattern import PatternMatcherAgent
        agents_list.append("Pattern Matcher")
    except:
        pass
    
    try:
        from agent_backtest import BacktestAgent
        agents_list.append("Backtest Engine")
    except:
        pass
    
    return {
        "status": "operational" if db_connected else "degraded",
        "agents": agents_list,
        "db_connected": db_connected,
        "total_opportunities": total_opps
    }


@router.get("/summary")
async def get_agents_summary():
    """Résumé rapide de tous les agents"""
    try:
        signals = await get_all_agent_signals()
        perf = await get_agents_performance()
        health = await agents_health()
        
        return {
            "total_signals": len(signals),
            "active_agents": len(health["agents"]),
            "total_opportunities": health["total_opportunities"],
            "top_signal": signals[0] if signals else None,
            "agents_performance": perf
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
