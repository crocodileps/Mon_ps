#!/usr/bin/env python3
"""
🎯 ROUTES API - AGENT BTTS V2.1
================================
Endpoints pour l'analyse BTTS avec Machine Learning
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

# Ajouter le path pour l'agent (relatif au volume monté)
sys.path.insert(0, '/app/agents/btts_calculator')
sys.path.insert(0, '/home/Mon_ps/backend/agents/btts_calculator')

# Import de l'agent
AGENT_AVAILABLE = False
AgentBTTSCalculatorV2 = None

try:
    from agent_btts_v2 import AgentBTTSCalculatorV2
    AGENT_AVAILABLE = True
    print("✅ Agent BTTS V2 chargé avec succès")
except ImportError as e:
    print(f"⚠️ Agent BTTS non disponible: {e}")
    # Fallback: essayer import direct
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "agent_btts_v2", 
            "/app/agents/btts_calculator/agent_btts_v2.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            AgentBTTSCalculatorV2 = module.AgentBTTSCalculatorV2
            AGENT_AVAILABLE = True
            print("✅ Agent BTTS V2 chargé via importlib")
    except Exception as e2:
        print(f"⚠️ Fallback aussi échoué: {e2}")

logger = logging.getLogger(__name__)

# Router FastAPI
router = APIRouter(prefix="/api/btts", tags=["BTTS Calculator"])

# Instance globale de l'agent
_agent_instance = None

def get_agent():
    """Récupère ou crée l'instance de l'agent"""
    global _agent_instance
    if _agent_instance is None and AGENT_AVAILABLE and AgentBTTSCalculatorV2:
        try:
            _agent_instance = AgentBTTSCalculatorV2()
        except Exception as e:
            logger.error(f"Erreur création agent: {e}")
    return _agent_instance


# =============================================================================
# MODÈLES PYDANTIC
# =============================================================================

class MatchInput(BaseModel):
    home_team: str = Field(..., description="Équipe à domicile")
    away_team: str = Field(..., description="Équipe à l'extérieur")
    btts_yes_odds: Optional[float] = Field(None, description="Cote marché BTTS YES")
    btts_no_odds: Optional[float] = Field(None, description="Cote marché BTTS NO")

class BatchInput(BaseModel):
    matches: List[MatchInput]

class HealthResponse(BaseModel):
    status: str
    agent_available: bool
    agent_version: str
    timestamp: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """🏥 Health check de l'agent BTTS"""
    agent = get_agent()
    
    return HealthResponse(
        status="healthy" if agent else "degraded",
        agent_available=AGENT_AVAILABLE,
        agent_version=getattr(agent, 'VERSION', 'N/A') if agent else "N/A",
        timestamp=datetime.now().isoformat()
    )


@router.post("/analyze")
async def analyze_match(match: MatchInput):
    """🎯 Analyser un match pour BTTS"""
    agent = get_agent()
    if not agent:
        raise HTTPException(
            status_code=503, 
            detail=f"Agent BTTS non disponible. AGENT_AVAILABLE={AGENT_AVAILABLE}"
        )
    
    try:
        result = agent.analyze_match(
            home_team=match.home_team,
            away_team=match.away_team,
            market_odds_yes=match.btts_yes_odds,
            market_odds_no=match.btts_no_odds
        )
        return result
        
    except Exception as e:
        logger.error(f"Erreur analyse BTTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def analyze_batch(batch: BatchInput):
    """📊 Analyser plusieurs matchs en batch"""
    agent = get_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="Agent BTTS non disponible")
    
    try:
        matches = [
            {
                'home_team': m.home_team,
                'away_team': m.away_team,
                'btts_yes_odds': m.btts_yes_odds,
                'btts_no_odds': m.btts_no_odds
            }
            for m in batch.matches
        ]
        
        results = agent.batch_analyze(matches)
        return results
        
    except Exception as e:
        logger.error(f"Erreur batch BTTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-picks")
async def get_top_picks(
    min_confidence: float = Query(60.0, description="Confiance minimum"),
    limit: int = Query(10, description="Nombre max de picks")
):
    """🏆 Récupérer les meilleurs picks BTTS"""
    agent = get_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="Agent BTTS non disponible")
    
    try:
        picks = agent.get_top_picks(min_confidence=min_confidence, limit=limit)
        return {
            "count": len(picks),
            "min_confidence": min_confidence,
            "generated_at": datetime.now().isoformat(),
            "picks": picks
        }
    except Exception as e:
        logger.error(f"Erreur top picks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-stats")
async def get_model_stats():
    """📊 Statistiques du modèle"""
    agent = get_agent()
    
    if not agent:
        return {
            "status": "agent_unavailable",
            "agent_available": AGENT_AVAILABLE
        }
    
    return {
        "version": getattr(agent, 'VERSION', 'N/A'),
        "modules": list(getattr(agent, 'MODULE_WEIGHTS', {}).keys()),
        "module_weights": getattr(agent, 'MODULE_WEIGHTS', {}),
        "thresholds": getattr(agent, 'THRESHOLDS', {}),
        "dixon_coles_params": getattr(agent, 'DIXON_COLES', {})
    }
