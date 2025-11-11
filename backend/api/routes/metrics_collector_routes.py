"""
Service d'exposition des métriques Prometheus pour le collector
À ajouter au backend FastAPI
"""
from fastapi import APIRouter
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import psycopg2
from typing import Dict
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Configuration DB
DB_CONFIG = {
    "host": "monps_postgres",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Métriques Prometheus
odds_collected_total = Counter(
    'monps_odds_collected_total',
    'Total number of odds collected',
    ['sport']
)

opportunities_detected_total = Counter(
    'monps_opportunities_detected_total',
    'Total number of opportunities detected',
    ['sport']
)

current_opportunities = Gauge(
    'monps_current_opportunities',
    'Number of current opportunities',
    ['sport']
)

max_spread = Gauge(
    'monps_max_spread_percent',
    'Maximum spread percentage currently available',
    ['sport']
)

bookmakers_count = Gauge(
    'monps_active_bookmakers',
    'Number of active bookmakers',
    ['sport']
)

api_requests_remaining = Gauge(
    'monps_api_requests_remaining',
    'Remaining API requests quota'
)

collection_duration = Histogram(
    'monps_collection_duration_seconds',
    'Duration of collection process'
)

last_collection_timestamp = Gauge(
    'monps_last_collection_timestamp',
    'Timestamp of last successful collection'
)


def get_db_connection():
    """Connexion à PostgreSQL"""
    return psycopg2.connect(**DB_CONFIG)


def update_metrics_from_db():
    """Mettre à jour les métriques depuis la base de données"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                sport,
                COUNT(*) as odds_count,
                COUNT(DISTINCT match_id) as matches_count,
                COUNT(DISTINCT bookmaker) as bookmakers_count
            FROM odds_history
            WHERE collected_at >= NOW() - INTERVAL '1 hour'
            GROUP BY sport
        """)
        
        for row in cursor.fetchall():
            sport, odds_count, matches_count, bookmaker_count = row
            bookmakers_count.labels(sport=sport).set(bookmaker_count)
        
        cursor.execute("""
            SELECT 
                sport,
                COUNT(*) as opp_count,
                MAX(GREATEST(home_spread_pct, away_spread_pct, COALESCE(draw_spread_pct, 0))) as max_spread_val
            FROM v_current_opportunities
            GROUP BY sport
        """)
        
        for row in cursor.fetchall():
            sport, opp_count, max_spread_val = row
            current_opportunities.labels(sport=sport).set(opp_count or 0)
            if max_spread_val:
                max_spread.labels(sport=sport).set(float(max_spread_val))
        
        cursor.execute("SELECT MAX(collected_at) FROM odds_history")
        last_collected = cursor.fetchone()[0]
        if last_collected:
            import time
            last_collection_timestamp.set(time.mktime(last_collected.timetuple()))
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Erreur mise à jour métriques: {e}")


@router.get("/metrics/collector")
async def collector_metrics():
    """Endpoint pour exposer les métriques du collector à Prometheus"""
    update_metrics_from_db()
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/metrics/collector/stats")
async def collector_stats() -> Dict:
    """Endpoint pour obtenir les stats du collector en JSON"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_odds,
                COUNT(DISTINCT match_id) as total_matches,
                COUNT(DISTINCT bookmaker) as total_bookmakers,
                COUNT(DISTINCT sport) as total_sports,
                MIN(collected_at) as first_collection,
                MAX(collected_at) as last_collection
            FROM odds_history
        """)
        
        row = cursor.fetchone()
        global_stats = {
            "total_odds": row[0],
            "total_matches": row[1],
            "total_bookmakers": row[2],
            "total_sports": row[3],
            "first_collection": row[4].isoformat() if row[4] else None,
            "last_collection": row[5].isoformat() if row[5] else None
        }
        
        cursor.execute("SELECT COUNT(*) FROM v_current_opportunities")
        current_opps = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT 
                sport, home_team, away_team,
                GREATEST(home_spread_pct, away_spread_pct, COALESCE(draw_spread_pct, 0)) as max_spread,
                bookmaker_count
            FROM v_current_opportunities
            ORDER BY max_spread DESC
            LIMIT 5
        """)
        
        top_opportunities = []
        for row in cursor.fetchall():
            top_opportunities.append({
                "sport": row[0],
                "home_team": row[1],
                "away_team": row[2],
                "max_spread_pct": float(row[3]) if row[3] else 0,
                "bookmakers": row[4]
            })
        
        cursor.execute("""
            SELECT 
                sport,
                COUNT(*) as odds_count,
                COUNT(DISTINCT match_id) as matches_count,
                COUNT(DISTINCT bookmaker) as bookmakers_count,
                MAX(collected_at) as last_update
            FROM odds_history
            WHERE collected_at >= NOW() - INTERVAL '24 hours'
            GROUP BY sport
            ORDER BY odds_count DESC
        """)
        
        sports_stats = []
        for row in cursor.fetchall():
            sports_stats.append({
                "sport": row[0],
                "odds_count": row[1],
                "matches_count": row[2],
                "bookmakers_count": row[3],
                "last_update": row[4].isoformat() if row[4] else None
            })
        
        cursor.close()
        conn.close()
        
        return {
            "global": global_stats,
            "current_opportunities": current_opps,
            "top_opportunities": top_opportunities,
            "sports": sports_stats
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération stats: {e}")
        return {"error": str(e)}
