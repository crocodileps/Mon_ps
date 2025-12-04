
"""

API FastAPI principale pour Mon_PS

"""

import time

import uuid



from fastapi import FastAPI, Request

from fastapi.middleware.cors import CORSMiddleware

from api.config import settings

from api.services.logging import logger

from api.routes import bets, odds, opportunities, stats, metrics

from api.routes import agents_routes

from api.routes import metrics_collector_routes

from api.routes import settings as settings_route

from api.routes import metrics_routes

from api.routes import manual_bets_routes

from api.routes import bets_routes

from api.routes import agents_stats_routes

from api.routes import agents_comparison_routes

from api.routes import settlement_routes
from api.routes import pro_score_v3_routes
from api.routes import coach_routes



app = FastAPI(

    title=settings.APP_NAME,

    version=settings.APP_VERSION,

    debug=settings.DEBUG

)



# CORS

app.add_middleware(

    CORSMiddleware,

    allow_origins=settings.CORS_ORIGINS,

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)



# Middleware pour ajouter un ID de corrélation à chaque requête

@app.middleware("http")

async def add_correlation_id(request: Request, call_next):

    """Ajoute un identifiant unique à chaque requête entrante"""

    request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    

    return response



# Middleware de logging des requêtes

@app.middleware("http")

async def log_requests(request: Request, call_next):

    """Log toutes les requêtes avec durée d'exécution"""

    start_time = time.time()

    

    request_id = getattr(request.state, "request_id", "unknown")

    

    # Traiter la requête

    response = await call_next(request)

    

    # Calculer le temps d'exécution

    duration_ms = (time.time() - start_time) * 1000

    

    # Log de la réponse

    logger.info(

        "request_completed",

        request_id=request_id,

        method=request.method,

        path=request.url.path,

        status_code=response.status_code,

        duration_ms=round(duration_ms, 2)

    )

    

    return response



# Routes

app.include_router(bets.router, prefix="/bets", tags=["bets"])

app.include_router(odds.router, prefix="/odds", tags=["odds"])

app.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])

app.include_router(stats.router, prefix="/stats", tags=["stats"])

app.include_router(metrics.router, tags=["metrics"])

app.include_router(settings_route.router, prefix="/settings", tags=["settings"])

app.include_router(metrics_routes.router)

app.include_router(agents_routes.router)

app.include_router(manual_bets_routes.router)

app.include_router(

    metrics_collector_routes.router,

    tags=["Metrics Collector"]

)

app.include_router(bets_routes.router)

app.include_router(agents_stats_routes.router)

app.include_router(agents_comparison_routes.router)

app.include_router(settlement_routes.router)



@app.on_event("startup")

async def startup():

    logger.info(

        "application_started",

        app_name=settings.APP_NAME,

        version=settings.APP_VERSION,

        environment=settings.ENV

    )



@app.get("/")

def root():

    return {

        "app": settings.APP_NAME,

        "version": settings.APP_VERSION,

        "status": "running"
    }
   
@app.get("/health")

def health():

    return {"status": "healthy"}



# Telegram Bot Routes
from api.routes.telegram_routes import router as telegram_router
app.include_router(telegram_router)

# Coach Intelligence Routes
app.include_router(coach_routes.router)
from api.routes.fullgain import router as fullgain_router
from api.routes.dynamic_intelligence_routes import router as smart_v5_router
from api.routes.reality_check_routes import router as reality_check_router
app.include_router(fullgain_router)
app.include_router(smart_v5_router)
app.include_router(reality_check_router)

# Agent Telegram Test Routes
from api.routes.agent_telegram_test import router as agent_telegram_router
app.include_router(agent_telegram_router)




# Telegram Stats Routes (HTML)
from api.routes.telegram_stats_routes import router as telegram_stats_router
app.include_router(telegram_stats_router)

# Briefing Routes
from api.routes.briefing_routes import router as briefing_router
app.include_router(briefing_router)

# Stats routes (Learning System)
from api.routes import stats_routes
app.include_router(stats_routes.router, prefix="/stats", tags=["stats"])

# Results routes (Scraper n8n)
from api.routes import results_routes
app.include_router(results_routes.router, prefix="/results", tags=["results"])

# Strategies routes (Meta-learning)
from api.routes import strategies_routes
from api.routes import ferrari_routes
from api.routes import ferrari_variations_routes
from api.routes import variations_routes
app.include_router(strategies_routes.router, prefix="/strategies", tags=["strategies"])

# Results routes (Récupération résultats matchs)
from api.routes import results_routes
from api.routes import ferrari_monitoring_routes
from api.routes import ferrari_matches_routes
app.include_router(results_routes.router, prefix="/results", tags=["results"])
app.include_router(ferrari_routes.router, prefix="/api/ferrari", tags=["Ferrari 2.0"])
app.include_router(ferrari_variations_routes.router, prefix="/api/ferrari", tags=["Ferrari Variations Real"])
app.include_router(ferrari_monitoring_routes.router, prefix="/api/ferrari", tags=["Ferrari Monitoring"])
app.include_router(ferrari_matches_routes.router, prefix="/api/ferrari", tags=["Ferrari Matches"])
app.include_router(variations_routes.router, prefix="/strategies", tags=["Variations"])

# Patron Diamond V3 Routes (Multi-Marchés)
from api.routes.patron_diamond_routes import router as patron_diamond_router
app.include_router(patron_diamond_router)

# Tracking CLV Routes (Dashboard Stats)
from api.routes.tracking_clv_routes import router as tracking_clv_router
app.include_router(tracking_clv_router)

# Combinés Intelligents Routes
from api.routes import combos_routes
app.include_router(combos_routes.router)

# Ferrari Intelligence Routes (FERRARI 2.0 ULTIMATE)
from api.routes.ferrari_intelligence_routes import router as ferrari_intelligence_router
app.include_router(ferrari_intelligence_router)
app.include_router(pro_score_v3_routes.router)

# ============================================================================
# PRO COMMAND CENTER & PERFORMANCE V2
# ============================================================================
from api.routes import pro_command_center
from api.routes import pro_performance_v2

app.include_router(pro_command_center.router)
app.include_router(pro_performance_v2.router)

# ============================================================================
# MARKET RECOMMENDATION ROUTES (ML Smart Quant 2.0)
# ============================================================================
from api.routes.market_recommendation_routes import router as market_recommendation_router
app.include_router(market_recommendation_router)

# ML Prediction Routes (Smart Quant 2.0)
from api.routes.ml_prediction_routes import router as ml_prediction_router
app.include_router(ml_prediction_router)

# ============================================================================
# ORCHESTRATOR V11 QUANT SNIPER (NEW!)
# ============================================================================
from api.routes.orchestrator_v11_routes import router as orchestrator_v11_router
app.include_router(orchestrator_v11_router, prefix="/api/v11", tags=["Orchestrator V11 Quant Sniper"])
