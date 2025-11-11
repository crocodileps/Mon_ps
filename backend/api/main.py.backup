"""
Application FastAPI principale
"""
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from api.config import settings
from api.routes import odds, opportunities, bets, stats
from api.services.logging import configure_logging, logger

# Configurer le logging au démarrage
configure_logging()

# Créer l'application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST pour Mon_PS - Système de paris sportifs quantitatif",
    docs_url="/docs",
    redoc_url="/redoc"
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

    # Log de la requête entrante
    logger.info(
        "request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path
    )

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

# Inclure les routes
app.include_router(odds.router)
app.include_router(opportunities.router)
app.include_router(bets.router)
app.include_router(stats.router)

@app.get("/")
def root(request: Request):
    """Route racine"""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info("root_endpoint_called", request_id=request_id)
    return {
        "message": "Bienvenue sur l'API Mon_PS",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
def health_check(request: Request):
    """Vérification de santé de l'API"""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.debug("health_check_called", request_id=request_id)
    return {"status": "ok", "service": "Mon_PS API"}

# Log au démarrage
logger.info(
    "application_started",
    app_name=settings.APP_NAME,
    version=settings.APP_VERSION,
    environment=settings.ENV
)
