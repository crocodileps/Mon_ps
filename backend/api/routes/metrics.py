"""
Route pour exposer les métriques Prometheus
"""
from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import create_engine, text
import os

router = APIRouter()

# Métriques métier
total_bets_gauge = Gauge('monps_total_bets', 'Total number of bets')
bankroll_gauge = Gauge('monps_bankroll', 'Current bankroll in EUR')
roi_gauge = Gauge('monps_roi', 'Return on Investment')
win_rate_gauge = Gauge('monps_win_rate', 'Win rate percentage')

# Métriques HTTP (on les crée mais elles seront remplies plus tard via middleware)
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

INITIAL_BANKROLL = 1000.0

def get_engine():
    """Créer le moteur SQLAlchemy"""
    db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    return create_engine(db_url)

def calculate_metrics():
    """Calculate all metrics from database"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Total
            result = conn.execute(text("SELECT COUNT(*) FROM bets")).scalar()
            total = result or 0
            total_bets_gauge.set(total)
            
            if total == 0:
                bankroll_gauge.set(INITIAL_BANKROLL)
                roi_gauge.set(0)
                win_rate_gauge.set(0)
                return
            
            # Profit
            profit = conn.execute(text("SELECT COALESCE(SUM(profit), 0) FROM bets")).scalar()
            total_profit = float(profit or 0)
            
            # Stake
            stake = conn.execute(text("SELECT COALESCE(SUM(stake), 1) FROM bets")).scalar()
            total_stake = float(stake or 1)
            
            # Bankroll
            bankroll_gauge.set(INITIAL_BANKROLL + total_profit)
            
            # ROI
            roi = (total_profit / total_stake * 100) if total_stake > 0 else 0
            roi_gauge.set(roi)
            
            # Win rate
            won = conn.execute(text("SELECT COUNT(*) FROM bets WHERE result = 'won'")).scalar()
            won_total = won or 0
            win_rate_gauge.set((won_total / total * 100) if total > 0 else 0)
        
    except Exception as e:
        print(f"Error calculating metrics: {e}")
        import traceback
        traceback.print_exc()

@router.get("/metrics")
def get_metrics():
    """Expose Prometheus metrics"""
    calculate_metrics()
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
