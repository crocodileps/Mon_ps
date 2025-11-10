"""
Application FastAPI principale
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.config import settings
from api.routes import odds, opportunities, bets, stats

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

# Inclure les routes
app.include_router(odds.router)
app.include_router(opportunities.router)
app.include_router(bets.router)
app.include_router(stats.router)

@app.get("/")
def root():
    """Route racine"""
    return {
        "message": "Bienvenue sur l'API Mon_PS",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
def health_check():
    """Vérification de santé de l'API"""
    return {"status": "ok", "service": "Mon_PS API"}
