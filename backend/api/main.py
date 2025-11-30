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
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        "request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2)
    )
    return response

# Routes de base
app.include_router(bets.router, prefix="/bets", tags=["bets"])
app.include_router(odds.router, prefix="/odds", tags=["odds"])
app.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
app.include_router(metrics.router, tags=["metrics"])
app.include_router(settings_route.router, prefix="/settings", tags=["settings"])
app.include_router(metrics_routes.router)
app.include_router(agents_routes.router)
app.include_router(manual_bets_routes.router)
app.include_router(metrics_collector_routes.router, tags=["Metrics Collector"])
app.include_router(bets_routes.router)
app.include_router(agents_stats_routes.router)
app.include_router(agents_comparison_routes.router)
app.include_router(settlement_routes.router)

# Telegram Routes
from api.routes.telegram_routes import router as telegram_router
from api.routes.agent_telegram_test import router as agent_telegram_router
from api.routes.telegram_stats_routes import router as telegram_stats_router
from api.routes.briefing_routes import router as briefing_router
app.include_router(telegram_router)
app.include_router(agent_telegram_router)
app.include_router(telegram_stats_router)
app.include_router(briefing_router)

# Stats & Results Routes
from api.routes import stats_routes
from api.routes import results_routes
app.include_router(stats_routes.router, prefix="/stats", tags=["stats"])
app.include_router(results_routes.router, prefix="/results", tags=["results"])

# Strategies & Ferrari Routes
from api.routes import strategies_routes
from api.routes import ferrari_routes
from api.routes import ferrari_variations_routes
from api.routes import variations_routes
from api.routes import ferrari_monitoring_routes
from api.routes import ferrari_matches_routes
app.include_router(strategies_routes.router, prefix="/strategies", tags=["strategies"])
app.include_router(ferrari_routes.router, prefix="/api/ferrari", tags=["Ferrari 2.0"])
app.include_router(ferrari_variations_routes.router, prefix="/api/ferrari", tags=["Ferrari Variations Real"])
app.include_router(ferrari_monitoring_routes.router, prefix="/api/ferrari", tags=["Ferrari Monitoring"])
app.include_router(ferrari_matches_routes.router, prefix="/api/ferrari", tags=["Ferrari Matches"])
app.include_router(variations_routes.router, prefix="/strategies", tags=["Variations"])

# Patron Diamond V3 Routes
from api.routes.patron_diamond_routes import router as patron_diamond_router
app.include_router(patron_diamond_router)

# Tracking CLV Routes
from api.routes.tracking_clv_routes import router as tracking_clv_router
app.include_router(tracking_clv_router)

# ALGO V4 - Data-Driven Betting
from api.routes import algo_v4_routes
app.include_router(algo_v4_routes.router)

# Dynamic Intelligence V5.1
from api.routes import dynamic_intelligence_routes
app.include_router(dynamic_intelligence_routes.router)

# BTTS Calculator V2.1 Routes
from api.routes import btts_routes

# Pro Command Center 3.0
from api.routes import pro_command_center
app.include_router(btts_routes.router)
app.include_router(pro_command_center.router)

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
