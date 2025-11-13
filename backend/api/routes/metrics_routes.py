"""
Routes pour métriques Prometheus avec refresh automatique
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from fastapi.responses import Response
import logging
from ..services.database import get_db

router = APIRouter(tags=["metrics"])
logger = logging.getLogger(__name__)

# Créer un registre personnalisé pour éviter les duplications
custom_registry = CollectorRegistry()

# Métriques Prometheus
current_opportunities = Gauge(
    'monps_current_opportunities',
    'Number of current opportunities',
    registry=custom_registry
)
max_spread_percent = Gauge(
    'monps_max_spread_percent',
    'Maximum spread percentage currently available',
    registry=custom_registry
)
active_bookmakers = Gauge(
    'monps_active_bookmakers',
    'Number of active bookmakers',
    registry=custom_registry
)

@router.get("/metrics/refresh")
def refresh_metrics(db: Session = Depends(get_db)):
    """
    Rafraîchir les métriques depuis la DB
    """
    try:
        # Compter opportunités > 5% spread
        result = db.execute("""
            SELECT
                COUNT(*) as nb_opportunities,
                COALESCE(MAX(home_spread_pct), 0) as max_spread,
                COUNT(DISTINCT bookmaker) as nb_bookmakers
            FROM v_current_opportunities
            WHERE home_spread_pct > 5
        """).fetchone()
        
        nb_opps = result[0] if result else 0
        max_spr = result[1] if result else 0
        nb_books = result[2] if result else 0
        
        current_opportunities.set(nb_opps)
        max_spread_percent.set(max_spr)
        active_bookmakers.set(nb_books)
        
        logger.info(f"Métriques mises à jour: {nb_opps} opps, {max_spr}% spread, {nb_books} books")
        
        return {
            "status": "ok",
            "opportunities": nb_opps,
            "max_spread": max_spr,
            "bookmakers": nb_books
        }
    except Exception as e:
        logger.error(f"Erreur refresh metrics: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/metrics")
def get_metrics():
    """
    Endpoint Prometheus standard
    """
    return Response(
        content=generate_latest(custom_registry),
        media_type=CONTENT_TYPE_LATEST
    )
