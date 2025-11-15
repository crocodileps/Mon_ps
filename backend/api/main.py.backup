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
from api.routes import metrics_collector_routes
from api.routes import settings as settings_route
from api.routes import metrics_routes

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
app.include_router(
    metrics_collector_routes.router,
    tags=["Metrics Collector"]
)

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
