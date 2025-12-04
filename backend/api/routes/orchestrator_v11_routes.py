"""
ORCHESTRATOR V11 QUANT SNIPER - API ROUTES
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import sys
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, '/app/app')
sys.path.insert(0, '/app/scripts/analytics')

router = APIRouter()
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# MODÈLES PYDANTIC
# ═══════════════════════════════════════════════════════════════════════════════

class MatchAnalysisRequest(BaseModel):
    home: str = Field(..., description="Équipe à domicile")
    away: str = Field(..., description="Équipe à l'extérieur")
    market: str = Field(default="over_25", description="Marché cible")
    referee: Optional[str] = Field(None, description="Arbitre")

class BatchAnalysisRequest(BaseModel):
    matches: List[MatchAnalysisRequest] = Field(..., min_length=1, max_length=20)

class LayerResult(BaseModel):
    score: float
    reason: str
    details: Optional[Dict[str, Any]] = None

class MatchAnalysisResponse(BaseModel):
    home: str
    away: str
    target_market: str
    recommended_market: str
    score: float
    action: str
    confidence: float
    btts_prob: float
    over25_prob: float
    layers: Dict[str, LayerResult]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BatchAnalysisResponse(BaseModel):
    total_analyzed: int
    sniper_bets: int
    normal_bets: int
    skipped: int
    blocked: int
    results: List[MatchAnalysisResponse]

class LayerInfo(BaseModel):
    name: str
    max_points: float
    min_points: float
    description: str
    data_source: str

class SystemHealth(BaseModel):
    status: str
    orchestrator_version: str
    layers_active: int
    layers_total: int
    cache_loaded: bool
    database_connected: bool

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_orchestrator():
    try:
        from orchestrator_v11_quant_sniper import OrchestratorV11QuantSniper
        return OrchestratorV11QuantSniper()
    except Exception as e:
        logger.error(f"Erreur chargement Orchestrator: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur Orchestrator: {str(e)}")

def format_layer_result(layer_data: Dict) -> LayerResult:
    return LayerResult(
        score=round(layer_data.get('score', 0), 2),
        reason=layer_data.get('reason', 'N/A'),
        details={k: v for k, v in layer_data.items() if k not in ['score', 'reason']}
    )

def convert_decimals(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    return obj

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/analyze", response_model=MatchAnalysisResponse)
async def analyze_match(request: MatchAnalysisRequest):
    """🎯 Analyse complète d'un match avec Orchestrator V11"""
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.analyze_match(
            home=request.home,
            away=request.away,
            market=request.market,
            referee=request.referee,
            verbose=False
        )
        result = convert_decimals(result)
        formatted_layers = {
            name: format_layer_result(data) 
            for name, data in result.get('layers', {}).items()
        }
        return MatchAnalysisResponse(
            home=result['home'],
            away=result['away'],
            target_market=result['target_market'],
            recommended_market=result['recommended_market'],
            score=result['score'],
            action=result['action'],
            confidence=result['confidence'],
            btts_prob=result['btts_prob'],
            over25_prob=result['over25_prob'],
            layers=formatted_layers
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
async def analyze_batch(request: BatchAnalysisRequest):
    """📊 Analyse batch de plusieurs matchs"""
    try:
        orchestrator = get_orchestrator()
        results = []
        sniper = normal = skip = blocked = 0
        
        for match in request.matches:
            try:
                result = orchestrator.analyze_match(
                    home=match.home, away=match.away,
                    market=match.market, referee=match.referee,
                    verbose=False
                )
                result = convert_decimals(result)
                action = result['action']
                if action == 'SNIPER_BET': sniper += 1
                elif action == 'NORMAL_BET': normal += 1
                elif action == 'BLOCKED': blocked += 1
                else: skip += 1
                
                formatted_layers = {
                    name: format_layer_result(data) 
                    for name, data in result.get('layers', {}).items()
                }
                results.append(MatchAnalysisResponse(
                    home=result['home'], away=result['away'],
                    target_market=result['target_market'],
                    recommended_market=result['recommended_market'],
                    score=result['score'], action=result['action'],
                    confidence=result['confidence'],
                    btts_prob=result['btts_prob'],
                    over25_prob=result['over25_prob'],
                    layers=formatted_layers
                ))
            except Exception as e:
                logger.warning(f"Erreur {match.home} vs {match.away}: {e}")
                continue
        
        return BatchAnalysisResponse(
            total_analyzed=len(results),
            sniper_bets=sniper, normal_bets=normal,
            skipped=skip, blocked=blocked,
            results=results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/layers", response_model=List[LayerInfo])
async def get_layers_info():
    """📋 Info sur les 8 layers"""
    return [
        LayerInfo(name="base", max_points=10, min_points=10, description="Score de base", data_source="Constant"),
        LayerInfo(name="tactical", max_points=15, min_points=0, description="Matchup tactique", data_source="tactical_matrix (144)"),
        LayerInfo(name="team_class", max_points=10, min_points=0, description="Power index", data_source="team_class (231)"),
        LayerInfo(name="h2h", max_points=8, min_points=0, description="Historique H2H", data_source="head_to_head (772)"),
        LayerInfo(name="injuries", max_points=0, min_points=-8, description="Blessures top scorers", data_source="scorer_intelligence"),
        LayerInfo(name="xg", max_points=5, min_points=-5, description="Régression xG", data_source="team_xg_tendencies"),
        LayerInfo(name="coach", max_points=3, min_points=-1.5, description="Tendances coach", data_source="coach_intelligence (103)"),
        LayerInfo(name="referee", max_points=2, min_points=-1.5, description="Impact arbitre", data_source="referee_intelligence (21)"),
        LayerInfo(name="convergence", max_points=30, min_points=-30, description="Market DNA", data_source="market_convergence_engine"),
    ]


@router.get("/health", response_model=SystemHealth)
async def get_health():
    """🏥 Santé du système"""
    try:
        orchestrator = get_orchestrator()
        cache_loaded = bool(orchestrator.cache.get('tactical'))
        db_connected = False
        try:
            conn = orchestrator._get_conn()
            db_connected = not conn.closed
        except:
            pass
        
        return SystemHealth(
            status="healthy" if cache_loaded and db_connected else "degraded",
            orchestrator_version="11.1",
            layers_active=8,
            layers_total=8,
            cache_loaded=cache_loaded,
            database_connected=db_connected
        )
    except Exception:
        return SystemHealth(
            status="error", orchestrator_version="11.1",
            layers_active=0, layers_total=8,
            cache_loaded=False, database_connected=False
        )


@router.get("/test/{home}/{away}")
async def quick_test(
    home: str, away: str,
    market: str = Query(default="over_25"),
    referee: Optional[str] = Query(default=None)
):
    """🧪 Test rapide GET"""
    return await analyze_match(MatchAnalysisRequest(
        home=home, away=away, market=market, referee=referee
    ))
