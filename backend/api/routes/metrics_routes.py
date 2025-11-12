"""
Routes pour métriques Prometheus avec refresh automatique
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import logging

from ..database import get_db

router = APIRouter(tags=["metrics"])  # ⭐ PAS de prefix ici
logger = logging.getLogger(__name__)

# Métriques Prometheus
current_opportunities = Gauge(
    'monps_current_opportunities',
    'Number of current opportunities'
)

max_spread_percent = Gauge(
    'monps_max_spread_percent',
    'Maximum spread percentage currently available'
)

active_bookmakers = Gauge(
    'monps_active_bookmakers',
    'Number of active bookmakers'
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
        
        # Mettre à jour les métriques
        current_opportunities.set(nb_opps)
        max_spread_percent.set(float(max_spr))
        active_bookmakers.set(nb_books)
        
        logger.info(f"Metrics refreshed: {nb_opps} opps, {max_spr}% max spread")
        
        return {
            "updated": True,
            "opportunities": nb_opps,
            "max_spread": float(max_spr),
            "bookmakers": nb_books
        }
        
    except Exception as e:
        logger.error(f"Error refreshing metrics: {e}")
        return {"updated": False, "error": str(e)}
