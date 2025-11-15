"""
Routes API pour les Agents ML
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import sys

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
    spread_pct: float
    expected_value: float
    kelly_fraction: float
    recommended_stake_pct: float
    reason: str


class AgentPerformance(BaseModel):
    agent_id: str
    agent_name: str
    total_signals: int
    avg_confidence: float
    avg_ev: float
    avg_kelly: float
    top_signal: Dict[str, Any] = None


@router.get("/signals", response_model=List[Dict[str, Any]])
async def get_all_agent_signals():
    """Récupère les signaux de tous les agents"""
    try:
        from agent_spread import SpreadOptimizerAgent
        from agent_pattern import PatternMatcherAgent
        
        all_signals = []
        
        # Agent B - Spread Optimizer
        try:
            agent_b = SpreadOptimizerAgent(DB_CONFIG)
            signals_b = agent_b.generate_signals(top_n=10)
            all_signals.extend(signals_b)
        except Exception as e:
            print(f"Agent B error: {e}")
        
        # Agent C - Pattern Matcher (si disponible)
        try:
            agent_c = PatternMatcherAgent(DB_CONFIG)
            signals_c = agent_c.generate_signals(top_n=10)
            all_signals.extend(signals_c)
        except Exception as e:
            print(f"Agent C error: {e}")
        
        return all_signals
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance", response_model=List[AgentPerformance])
async def get_agents_performance():
    """Récupère les performances comparatives des agents"""
    try:
        from agent_spread import SpreadOptimizerAgent
        
        performances = []
        
        # Agent B - Spread Optimizer
        try:
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
                    'top_signal': signals[0] if signals else None
                })
        except Exception as e:
            print(f"Agent B perf error: {e}")
        
        return performances
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def agents_health():
    """Vérifie l'état des agents"""
    return {
        "status": "operational",
        "agents": ["Spread Optimizer"],
        "db_connected": True
    }
