"""
API FastAPI principale pour Mon_PS
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.config import settings
from api.services.logging import logger
from api.routes import bets, odds, opportunities, stats, metrics

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

# Routes
app.include_router(bets.router, prefix="/bets", tags=["bets"])
app.include_router(odds.router, prefix="/odds", tags=["odds"])
app.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
app.include_router(metrics.router, tags=["metrics"])

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
