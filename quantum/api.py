"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM RULE ENGINE API 2.1                                        ║
║                                                                                       ║
║  FastAPI endpoints pour le système Quantum avec Monte Carlo.                         ║
║                                                                                       ║
║  Endpoints:                                                                          ║
║  - POST /analyze         → Analyse complète d'un match                               ║
║  - POST /analyze/quick   → Analyse rapide (sans DB)                                  ║
║  - POST /analyze/batch   → Analyse multiple matchs                                   ║
║  - GET  /scenarios       → Liste des 20 scénarios                                    ║
║  - GET  /scenarios/{id}  → Détail d'un scénario                                      ║
║  - POST /monte-carlo     → Validation Monte Carlo isolée                             ║
║  - GET  /stats           → Statistiques du moteur                                    ║
║  - GET  /health          → Health check                                              ║
║                                                                                       ║
║  Port: 8002 (pour ne pas conflictuer avec le backend principal 8001)                 ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import asyncio
import logging
import time

# Imports Quantum
from quantum.services import (
    QuantumRuleEngine,
    analyze_match_quick,
    quick_validate,
    MonteCarloValidator
)
from quantum.services.rule_engine import EngineConfig, MonteCarloConfig
from quantum.models import ScenarioID, MarketType

# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION LOGGING
# ═══════════════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("QuantumAPI")

# ═══════════════════════════════════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="🎲 Quantum Rule Engine API",
    description="API pour l'analyse de matchs avec détection de scénarios et validation Monte Carlo",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS - REQUEST
# ═══════════════════════════════════════════════════════════════════════════════════════

class MatchContext(BaseModel):
    """Contexte optionnel du match"""
    rest_days_home: Optional[int] = Field(None, description="Jours de repos équipe domicile")
    rest_days_away: Optional[int] = Field(None, description="Jours de repos équipe extérieur")
    is_european_week_home: Optional[bool] = Field(False, description="Semaine européenne domicile")
    is_european_week_away: Optional[bool] = Field(False, description="Semaine européenne extérieur")
    importance: Optional[str] = Field("NORMAL", description="Importance: LOW, NORMAL, HIGH, CRITICAL")
    weather: Optional[str] = Field(None, description="Conditions météo")


class AnalyzeRequest(BaseModel):
    """Requête d'analyse de match"""
    home_team: str = Field(..., description="Nom de l'équipe domicile", example="Lyon")
    away_team: str = Field(..., description="Nom de l'équipe extérieur", example="Monaco")
    context: Optional[MatchContext] = Field(None, description="Contexte du match")
    odds: Optional[Dict[str, float]] = Field(None, description="Cotes par marché", example={"over_25": 1.85, "btts_yes": 1.90})
    monte_carlo: Optional[bool] = Field(True, description="Activer validation Monte Carlo")
    mc_simulations: Optional[int] = Field(3000, description="Nombre de simulations MC", ge=500, le=10000)


class BatchAnalyzeRequest(BaseModel):
    """Requête d'analyse batch"""
    matches: List[AnalyzeRequest] = Field(..., description="Liste des matchs à analyser")
    parallel: Optional[bool] = Field(True, description="Exécuter en parallèle")


class MonteCarloRequest(BaseModel):
    """Requête de validation Monte Carlo"""
    scenario_name: str = Field(..., description="Nom du scénario", example="TOTAL_CHAOS")
    confidence: float = Field(..., description="Confiance initiale", ge=0, le=100, example=75)
    edge: float = Field(..., description="Edge calculé", example=0.08)
    odds: Optional[float] = Field(2.0, description="Cotes", example=2.10)
    n_simulations: Optional[int] = Field(5000, description="Nombre de simulations", ge=1000, le=20000)


# ═══════════════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS - RESPONSE
# ═══════════════════════════════════════════════════════════════════════════════════════

class ScenarioResponse(BaseModel):
    """Scénario détecté"""
    id: str
    name: str
    confidence: float
    triggered_conditions: List[str]
    recommended_markets: List[str]
    historical_roi: float
    monte_carlo_validated: Optional[bool] = None
    monte_carlo_score: Optional[float] = None
    monte_carlo_robustness: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Recommandation de pari"""
    market: str
    selection: str
    odds: float
    calculated_probability: float
    implied_probability: float
    edge: float
    confidence: float
    stake_tier: str
    stake_units: float
    expected_value: float
    reasoning: str


class MonteCarloSummaryResponse(BaseModel):
    """Résumé Monte Carlo"""
    enabled: bool
    scenarios_validated: int
    scenarios_rejected: int
    scenarios_total: int
    avg_validation_score: float
    avg_success_rate: float
    robustness_distribution: Dict[str, int]
    stress_tests: Dict[str, int]
    simulation_time_ms: float


class AnalyzeResponse(BaseModel):
    """Réponse d'analyse complète"""
    success: bool
    match: str
    home_team: str
    away_team: str
    decision_source: str
    confidence_overall: float
    scenarios_count: int
    scenarios: List[ScenarioResponse]
    recommendations: List[RecommendationResponse]
    total_exposure: float
    total_expected_value: float
    avoid_markets: List[str]
    monte_carlo: Optional[MonteCarloSummaryResponse] = None
    processing_time_ms: float
    analyzed_at: str


class ScenarioDetailResponse(BaseModel):
    """Détail d'un scénario"""
    id: str
    name: str
    emoji: str
    category: str
    description: str
    conditions: List[Dict[str, Any]]
    primary_markets: List[str]
    avoid_markets: List[str]
    historical_roi: float
    historical_wr: float


class HealthResponse(BaseModel):
    """Health check"""
    status: str
    version: str
    monte_carlo_enabled: bool
    scenarios_available: int
    uptime_seconds: float


# ═══════════════════════════════════════════════════════════════════════════════════════
# GLOBAL STATE
# ═══════════════════════════════════════════════════════════════════════════════════════

# Engine singleton (réutilisé entre les requêtes)
_engine: Optional[QuantumRuleEngine] = None
_start_time = time.time()
_request_count = 0


def get_engine(monte_carlo: bool = True, n_simulations: int = 3000) -> QuantumRuleEngine:
    """Récupère ou crée le moteur"""
    global _engine
    
    # Créer un nouveau moteur si config différente
    config = EngineConfig()
    config.monte_carlo.enabled = monte_carlo
    config.monte_carlo.n_simulations = n_simulations
    config.monte_carlo.stress_test_required = False  # Désactivé pour API (performance)
    
    _engine = QuantumRuleEngine(config=config)
    return _engine


# ═══════════════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Info"])
async def root():
    """Info de l'API"""
    return {
        "name": "Quantum Rule Engine API",
        "version": "2.1.0",
        "monte_carlo": True,
        "endpoints": [
            "POST /analyze",
            "POST /analyze/quick", 
            "POST /analyze/batch",
            "GET /scenarios",
            "GET /scenarios/{scenario_id}",
            "POST /monte-carlo/validate",
            "GET /stats",
            "GET /health"
        ]
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check du système"""
    engine = get_engine()
    
    return HealthResponse(
        status="healthy",
        version="2.1.0",
        monte_carlo_enabled=engine.config.monte_carlo.enabled,
        scenarios_available=len(engine.scenario_detector.scenarios),
        uptime_seconds=time.time() - _start_time
    )


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_match(request: AnalyzeRequest):
    """
    Analyse complète d'un match avec Monte Carlo.
    
    - Détecte les scénarios applicables
    - Valide avec Monte Carlo (optionnel)
    - Génère des recommandations de paris
    """
    global _request_count
    _request_count += 1
    
    logger.info(f"[{_request_count}] Analyzing: {request.home_team} vs {request.away_team}")
    
    try:
        # Préparer le contexte
        context = None
        if request.context:
            context = request.context.model_dump()
        
        # Créer le moteur avec config
        engine = get_engine(
            monte_carlo=request.monte_carlo,
            n_simulations=request.mc_simulations
        )
        
        # Analyser
        strategy = await engine.analyze_match(
            home_team=request.home_team,
            away_team=request.away_team,
            context=context,
            odds=request.odds
        )
        
        # Construire la réponse
        scenarios = [
            ScenarioResponse(
                id=s.scenario_id.value,
                name=s.scenario_name,
                confidence=s.confidence,
                triggered_conditions=s.triggered_conditions,
                recommended_markets=[m.value for m in s.recommended_markets],
                historical_roi=s.historical_roi,
                monte_carlo_validated=s.monte_carlo_validated,
                monte_carlo_score=s.monte_carlo_score,
                monte_carlo_robustness=s.monte_carlo_robustness
            )
            for s in strategy.detected_scenarios
        ]
        
        recommendations = [
            RecommendationResponse(
                market=r.market.value,
                selection=r.selection,
                odds=r.odds,
                calculated_probability=r.calculated_probability,
                implied_probability=r.implied_probability,
                edge=r.edge,
                confidence=r.confidence,
                stake_tier=r.stake_tier.value,
                stake_units=r.stake_units,
                expected_value=r.expected_value,
                reasoning=r.reasoning
            )
            for r in strategy.recommendations
        ]
        
        mc_summary = None
        if strategy.monte_carlo_summary:
            mc = strategy.monte_carlo_summary
            mc_summary = MonteCarloSummaryResponse(
                enabled=mc.get("enabled", True),
                scenarios_validated=mc.get("scenarios_validated", 0),
                scenarios_rejected=mc.get("scenarios_rejected", 0),
                scenarios_total=mc.get("scenarios_total", 0),
                avg_validation_score=mc.get("avg_validation_score", 0),
                avg_success_rate=mc.get("avg_success_rate", 0),
                robustness_distribution=mc.get("robustness_distribution", {}),
                stress_tests=mc.get("stress_tests", {"passed": 0, "failed": 0}),
                simulation_time_ms=mc.get("simulation_time_ms", 0)
            )
        
        return AnalyzeResponse(
            success=True,
            match=f"{strategy.home_team} vs {strategy.away_team}",
            home_team=strategy.home_team,
            away_team=strategy.away_team,
            decision_source=strategy.decision_source.value,
            confidence_overall=strategy.confidence_overall,
            scenarios_count=len(strategy.detected_scenarios),
            scenarios=scenarios,
            recommendations=recommendations,
            total_exposure=strategy.total_exposure,
            total_expected_value=strategy.total_expected_value,
            avoid_markets=strategy.avoid_markets,
            monte_carlo=mc_summary,
            processing_time_ms=strategy.processing_time_ms,
            analyzed_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error analyzing match: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/quick", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_match_quick_endpoint(
    home_team: str = Query(..., description="Équipe domicile"),
    away_team: str = Query(..., description="Équipe extérieur"),
    monte_carlo: bool = Query(True, description="Activer Monte Carlo")
):
    """
    Analyse rapide sans configuration avancée.
    
    Utilise des DNA simulés (pas de connexion DB requise).
    """
    request = AnalyzeRequest(
        home_team=home_team,
        away_team=away_team,
        monte_carlo=monte_carlo,
        mc_simulations=1000  # Moins pour quick
    )
    return await analyze_match(request)


@app.post("/analyze/batch", tags=["Analysis"])
async def analyze_batch(request: BatchAnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Analyse multiple matchs en batch.
    
    Retourne immédiatement avec un ID de batch pour polling.
    """
    batch_id = f"batch_{int(time.time())}"
    
    logger.info(f"Starting batch analysis: {batch_id} with {len(request.matches)} matches")
    
    results = []
    
    for match in request.matches:
        try:
            result = await analyze_match(match)
            results.append({
                "match": f"{match.home_team} vs {match.away_team}",
                "success": True,
                "scenarios": result.scenarios_count,
                "recommendations": len(result.recommendations)
            })
        except Exception as e:
            results.append({
                "match": f"{match.home_team} vs {match.away_team}",
                "success": False,
                "error": str(e)
            })
    
    return {
        "batch_id": batch_id,
        "total": len(request.matches),
        "completed": len(results),
        "results": results
    }


@app.get("/scenarios", tags=["Scenarios"])
async def list_scenarios():
    """Liste tous les scénarios disponibles"""
    engine = get_engine()
    scenarios = engine.get_available_scenarios()
    
    return {
        "count": len(scenarios),
        "scenarios": scenarios
    }


@app.get("/scenarios/{scenario_id}", response_model=ScenarioDetailResponse, tags=["Scenarios"])
async def get_scenario(scenario_id: str):
    """Détail d'un scénario spécifique"""
    try:
        sid = ScenarioID(scenario_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    
    from quantum.models.scenarios_definitions import get_scenario
    
    scenario = get_scenario(sid)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    
    engine = get_engine()
    hist = engine.scenario_detector.historical_performance.get(sid, {})
    
    return ScenarioDetailResponse(
        id=scenario.id.value,
        name=scenario.name,
        emoji=scenario.emoji,
        category=scenario.category.value,
        description=scenario.description,
        conditions=[
            {
                "metric": c.metric,
                "operator": c.operator,
                "threshold": c.threshold,
                "description": c.description
            }
            for c in scenario.conditions
        ],
        primary_markets=[m.market.value for m in scenario.primary_markets],
        avoid_markets=[m.value for m in scenario.avoid_markets],
        historical_roi=hist.get("roi", 0),
        historical_wr=hist.get("wr", 0)
    )


@app.get("/scenarios/{scenario_id}/explain", tags=["Scenarios"])
async def explain_scenario(scenario_id: str):
    """Explication détaillée d'un scénario"""
    try:
        sid = ScenarioID(scenario_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    
    engine = get_engine()
    explanation = engine.explain_scenario(sid)
    
    return {
        "scenario_id": scenario_id,
        "explanation": explanation
    }


@app.post("/monte-carlo/validate", tags=["Monte Carlo"])
async def monte_carlo_validate(request: MonteCarloRequest):
    """
    Validation Monte Carlo isolée d'un scénario.
    
    Utile pour tester la robustesse d'une détection.
    """
    logger.info(f"MC Validation: {request.scenario_name} (conf={request.confidence}, edge={request.edge})")
    
    try:
        validation = quick_validate(
            scenario_name=request.scenario_name,
            confidence=request.confidence,
            edge=request.edge,
            odds=request.odds,
            n_simulations=request.n_simulations
        )
        
        return {
            "scenario": request.scenario_name,
            "validation": {
                "is_validated": validation.is_validated,
                "validation_score": validation.validation_score,
                "success_rate": validation.success_rate,
                "robustness": validation.robustness.value,
                "stress_test": validation.stress_test_result.value,
                "confidence_stats": {
                    "mean": validation.confidence_stats.mean,
                    "std_dev": validation.confidence_stats.std_dev,
                    "ci_95": [validation.confidence_stats.ci_95_lower, validation.confidence_stats.ci_95_upper]
                },
                "edge_stats": {
                    "mean": validation.edge_stats.mean,
                    "ci_95": [validation.edge_stats.ci_95_lower, validation.edge_stats.ci_95_upper]
                },
                "kelly": {
                    "optimal": validation.kelly_optimal,
                    "half": validation.kelly_half,
                    "quarter": validation.kelly_quarter
                },
                "warnings": validation.warnings,
                "simulation_time_ms": validation.simulation_time_ms
            }
        }
        
    except Exception as e:
        logger.error(f"MC Validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", tags=["System"])
async def get_stats():
    """Statistiques du moteur"""
    engine = get_engine()
    stats = engine.get_stats()
    
    return {
        "engine": stats,
        "api": {
            "total_requests": _request_count,
            "uptime_seconds": time.time() - _start_time
        }
    }


@app.post("/config/monte-carlo", tags=["System"])
async def configure_monte_carlo(
    enabled: bool = Query(True, description="Activer Monte Carlo"),
    n_simulations: int = Query(3000, description="Nombre de simulations", ge=500, le=10000),
    min_validation_score: float = Query(60.0, description="Score minimum", ge=0, le=100),
    stress_test: bool = Query(False, description="Exiger stress test")
):
    """Configure Monte Carlo à chaud"""
    engine = get_engine()
    
    engine.config.monte_carlo.enabled = enabled
    engine.config.monte_carlo.n_simulations = n_simulations
    engine.config.monte_carlo.min_validation_score = min_validation_score
    engine.config.monte_carlo.stress_test_required = stress_test
    
    if enabled and engine.mc_validator is None:
        engine.mc_validator = MonteCarloValidator(
            n_simulations=n_simulations,
            confidence_threshold=50.0,
            edge_threshold=0.05
        )
    
    return {
        "monte_carlo": {
            "enabled": enabled,
            "n_simulations": n_simulations,
            "min_validation_score": min_validation_score,
            "stress_test_required": stress_test
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "type": type(exc).__name__
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🎲 QUANTUM RULE ENGINE API 2.1")
    print("=" * 60)
    print("Monte Carlo: ENABLED")
    print("Port: 8002")
    print("Docs: http://localhost:8002/docs")
    print("=" * 60)
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )
