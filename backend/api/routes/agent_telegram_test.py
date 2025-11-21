"""
Route de test : Orchestrator + Telegram
"""
from fastapi import APIRouter
import asyncio
import os

router = APIRouter(prefix="/agent-telegram", tags=["Agent Telegram"])


@router.post("/test-orchestrator-alerts")
async def test_orchestrator_telegram():
    """
    Test : L'Orchestrator analyse tous les agents et envoie les meilleures opportunités sur Telegram
    """
    import sys
    sys.path.append('/app/agents')
    
    from agents.orchestrator import MultiAgentOrchestrator
    
    db_config = {
        'host': os.getenv('DB_HOST', 'postgres'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'monps_db'),
        'user': os.getenv('DB_USER', 'monps_user'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    # Créer l'orchestrator
    orchestrator = MultiAgentOrchestrator(db_config, bankroll=5000)
    
    # Pipeline complet
    orchestrator.run_all_agents(top_n=10)
    orchestrator.run_backtest()
    
    # Envoyer sur Telegram
    result = await orchestrator.send_best_opportunities_telegram()
    
    return result


@router.post("/test-agent-b-alerts")
async def test_agent_b_telegram():
    """
    DEPRECATED : Utilise test-orchestrator-alerts à la place
    """
    return {
        "status": "deprecated",
        "message": "Utilise /agent-telegram/test-orchestrator-alerts à la place",
        "redirect": "/agent-telegram/test-orchestrator-alerts"
    }
