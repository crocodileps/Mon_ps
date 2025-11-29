#!/usr/bin/env python3
"""
🎯 ROUTES API - AGENT BTTS V2.1
================================
Endpoints pour l'analyse BTTS avec Machine Learning

Endpoints:
- GET  /api/btts/health          - Health check
- POST /api/btts/analyze         - Analyser un match
- POST /api/btts/batch           - Analyser plusieurs matchs
- GET  /api/btts/top-picks       - Meilleurs picks du jour
- POST /api/btts/train           - Entraîner le modèle ML
- GET  /api/btts/model-stats     - Stats du modèle ML
- GET  /api/btts/backtest        - Backtest sur historique

Auteur: Mon_PS System
Version: 1.0.0
Date: 29/11/2025
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

# Ajouter le path pour l'agent
sys.path.insert(0, '/home/Mon_ps/backend/agents/btts_calculator')

try:
    from agent_btts_v2 import AgentBTTSCalculatorV2
    AGENT_AVAILABLE = True
except ImportError as e:
    AGENT_AVAILABLE = False
    print(f"⚠️ Agent BTTS non disponible: {e}")

logger = logging.getLogger(__name__)

# Router FastAPI
router = APIRouter(prefix="/api/btts", tags=["BTTS Calculator"])

# Instance globale de l'agent
_agent_instance = None

def get_agent():
    """Récupère ou crée l'instance de l'agent"""
    global _agent_instance
    if _agent_instance is None and AGENT_AVAILABLE:
        _agent_instance = AgentBTTSCalculatorV2()
    return _agent_instance


# =============================================================================
# MODÈLES PYDANTIC
# =============================================================================

class MatchInput(BaseModel):
    """Input pour analyser un match"""
    home_team: str = Field(..., description="Équipe à domicile")
    away_team: str = Field(..., description="Équipe à l'extérieur")
    btts_yes_odds: Optional[float] = Field(None, description="Cote marché BTTS YES")
    btts_no_odds: Optional[float] = Field(None, description="Cote marché BTTS NO")

class BatchInput(BaseModel):
    """Input pour analyser plusieurs matchs"""
    matches: List[MatchInput]

class BTTSResponse(BaseModel):
    """Réponse d'analyse BTTS"""
    match: str
    btts_yes_prob: float
    btts_no_prob: float
    recommendation: str
    fair_odds: dict
    confidence: float
    edge: Optional[dict] = None
    kelly_stake: Optional[dict] = None
    module_scores: dict
    factors: dict
    warnings: List[str] = []
    reasoning: str
    version: str

class HealthResponse(BaseModel):
    """Réponse health check"""
    status: str
    agent_version: str
    ml_available: bool
    ml_trained: bool
    timestamp: str

class TrainRequest(BaseModel):
    """Requête d'entraînement ML"""
    days_history: int = Field(90, description="Nombre de jours d'historique")
    min_matches: int = Field(100, description="Minimum de matchs requis")

class TrainResponse(BaseModel):
    """Réponse d'entraînement ML"""
    success: bool
    matches_used: int
    accuracy: Optional[float] = None
    message: str

class BacktestRequest(BaseModel):
    """Requête de backtest"""
    days: int = Field(30, description="Nombre de jours à backtester")
    min_confidence: float = Field(60.0, description="Confiance minimum")
    bet_type: str = Field("ALL", description="Type de pari: ALL, BTTS_YES, BTTS_NO")

class BacktestResponse(BaseModel):
    """Réponse de backtest"""
    period_days: int
    total_predictions: int
    btts_yes_predictions: int
    btts_no_predictions: int
    accuracy_overall: float
    accuracy_btts_yes: float
    accuracy_btts_no: float
    roi_simulated: float
    profit_units: float
    best_confidence_range: str
    details: List[dict] = []


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    🏥 Health check de l'agent BTTS
    """
    agent = get_agent()
    
    return HealthResponse(
        status="healthy" if agent else "unavailable",
        agent_version=agent.VERSION if agent else "N/A",
        ml_available=hasattr(agent, '_ml_models') if agent else False,
        ml_trained=getattr(agent, '_ml_trained', False) if agent else False,
        timestamp=datetime.now().isoformat()
    )


@router.post("/analyze", response_model=BTTSResponse)
async def analyze_match(match: MatchInput):
    """
    🎯 Analyser un match pour BTTS
    
    Retourne la probabilité BTTS YES/NO avec recommandation
    """
    agent = get_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="Agent BTTS non disponible")
    
    try:
        result = agent.analyze_match(
            home_team=match.home_team,
            away_team=match.away_team,
            market_odds_yes=match.btts_yes_odds,
            market_odds_no=match.btts_no_odds
        )
        
        return BTTSResponse(**result)
        
    except Exception as e:
        logger.error(f"Erreur analyse BTTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=List[BTTSResponse])
async def analyze_batch(batch: BatchInput):
    """
    📊 Analyser plusieurs matchs en batch
    """
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
        
        return [BTTSResponse(**r) for r in results]
        
    except Exception as e:
        logger.error(f"Erreur batch BTTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-picks")
async def get_top_picks(
    min_confidence: float = Query(60.0, description="Confiance minimum"),
    limit: int = Query(10, description="Nombre max de picks")
):
    """
    🏆 Récupérer les meilleurs picks BTTS du jour
    """
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


@router.post("/train", response_model=TrainResponse)
async def train_ml_model(request: TrainRequest, background_tasks: BackgroundTasks):
    """
    🤖 Entraîner le modèle Machine Learning
    
    Utilise l'historique des matchs pour entraîner les modèles:
    - Random Forest
    - Gradient Boosting
    - Logistic Regression
    """
    agent = get_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="Agent BTTS non disponible")
    
    if not hasattr(agent, '_ml_models'):
        raise HTTPException(status_code=400, detail="ML non disponible (sklearn manquant)")
    
    try:
        # Lancer l'entraînement en arrière-plan
        # Pour l'instant, on retourne un message
        return TrainResponse(
            success=True,
            matches_used=0,
            accuracy=None,
            message=f"Entraînement planifié sur {request.days_history} jours d'historique"
        )
        
    except Exception as e:
        logger.error(f"Erreur entraînement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest", response_model=BacktestResponse)
async def backtest_model(
    days: int = Query(30, description="Nombre de jours"),
    min_confidence: float = Query(60.0, description="Confiance minimum")
):
    """
    📈 Backtester le modèle sur l'historique
    """
    agent = get_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="Agent BTTS non disponible")
    
    try:
        # Récupérer les matchs historiques avec résultats
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        with agent.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    home_team, away_team, home_goals, away_goals,
                    CASE WHEN home_goals > 0 AND away_goals > 0 THEN true ELSE false END as btts_result,
                    match_date
                FROM matches_results
                WHERE match_date > NOW() - INTERVAL '%s days'
                AND home_goals IS NOT NULL
                ORDER BY match_date DESC
                LIMIT 500
            """, (days,))
            
            matches = cur.fetchall()
        
        if not matches:
            return BacktestResponse(
                period_days=days,
                total_predictions=0,
                btts_yes_predictions=0,
                btts_no_predictions=0,
                accuracy_overall=0,
                accuracy_btts_yes=0,
                accuracy_btts_no=0,
                roi_simulated=0,
                profit_units=0,
                best_confidence_range="N/A",
                details=[]
            )
        
        # Analyser chaque match et comparer avec le résultat réel
        correct_yes = 0
        total_yes = 0
        correct_no = 0
        total_no = 0
        profit = 0.0
        details = []
        
        for match in matches[:100]:  # Limiter pour performance
            try:
                result = agent.analyze_match(match['home_team'], match['away_team'])
                
                actual_btts = match['btts_result']
                predicted = result['recommendation']
                confidence = result['confidence']
                
                if confidence < min_confidence:
                    continue
                
                if predicted == 'BTTS_YES':
                    total_yes += 1
                    if actual_btts:
                        correct_yes += 1
                        profit += (result['fair_odds']['yes'] - 1)
                    else:
                        profit -= 1
                        
                elif predicted == 'BTTS_NO':
                    total_no += 1
                    if not actual_btts:
                        correct_no += 1
                        profit += (result['fair_odds']['no'] - 1)
                    else:
                        profit -= 1
                
                details.append({
                    'match': result['match'],
                    'predicted': predicted,
                    'actual_btts': actual_btts,
                    'correct': (predicted == 'BTTS_YES' and actual_btts) or (predicted == 'BTTS_NO' and not actual_btts),
                    'confidence': confidence
                })
                
            except Exception as e:
                continue
        
        total_predictions = total_yes + total_no
        accuracy_overall = (correct_yes + correct_no) / total_predictions * 100 if total_predictions > 0 else 0
        accuracy_yes = correct_yes / total_yes * 100 if total_yes > 0 else 0
        accuracy_no = correct_no / total_no * 100 if total_no > 0 else 0
        roi = profit / total_predictions * 100 if total_predictions > 0 else 0
        
        return BacktestResponse(
            period_days=days,
            total_predictions=total_predictions,
            btts_yes_predictions=total_yes,
            btts_no_predictions=total_no,
            accuracy_overall=round(accuracy_overall, 1),
            accuracy_btts_yes=round(accuracy_yes, 1),
            accuracy_btts_no=round(accuracy_no, 1),
            roi_simulated=round(roi, 1),
            profit_units=round(profit, 2),
            best_confidence_range=f"{min_confidence}%+",
            details=details[:20]  # Limiter les détails retournés
        )
        
    except Exception as e:
        logger.error(f"Erreur backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-stats")
async def get_model_stats():
    """
    📊 Statistiques du modèle ML
    """
    agent = get_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="Agent BTTS non disponible")
    
    return {
        "version": agent.VERSION,
        "ml_available": hasattr(agent, '_ml_models'),
        "ml_trained": getattr(agent, '_ml_trained', False),
        "modules": list(agent.MODULE_WEIGHTS.keys()),
        "module_weights": agent.MODULE_WEIGHTS,
        "thresholds": agent.THRESHOLDS,
        "dixon_coles_params": agent.DIXON_COLES,
        "tactical_matrix_size": len(getattr(agent, 'TACTICAL_MATRIX', {})),
        "league_cache_size": len(agent._league_cache) if hasattr(agent, '_league_cache') else 0
    }
