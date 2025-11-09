"""
Routes pour les statistiques
"""
from fastapi import APIRouter
from backend.api.models.schemas import Stats, BankrollSummary
from backend.api.services.database import get_cursor

router = APIRouter(prefix="/stats", tags=["Statistics"])

@router.get("/global", response_model=Stats)
def get_global_stats():
    """Statistiques globales du système"""
    
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT 
                COUNT(*) as total_odds,
                COUNT(DISTINCT match_id) as total_matches,
                COUNT(DISTINCT bookmaker) as total_bookmakers,
                COUNT(DISTINCT sport) as total_sports,
                MAX(created_at) as last_update
            FROM odds
        """)
        
        result = cursor.fetchone()
        return {
            "total_odds": result['total_odds'],
            "total_matches": result['total_matches'],
            "total_bookmakers": result['total_bookmakers'],
            "total_sports": result['total_sports'],
            "last_update": result['last_update'],
            "api_requests_remaining": None
        }

@router.get("/bankroll", response_model=BankrollSummary)
def get_bankroll():
    """Résumé du bankroll et des performances"""
    
    with get_cursor() as cursor:
        # Vérifier si la table bets existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'bets'
            )
        """)
        
        row = cursor.fetchone()
        # CORRECTION: RealDictCursor retourne un dict, pas un tuple
        table_exists = row.get('exists') if row else False
        
        if not table_exists:
            return {
                "current_balance": 1000.0,
                "initial_balance": 1000.0,
                "total_staked": 0.0,
                "total_returned": 0.0,
                "total_profit": 0.0,
                "roi": 0.0,
                "nb_bets": 0,
                "nb_won": 0,
                "nb_lost": 0,
                "nb_pending": 0,
                "win_rate": 0.0
            }
        
        cursor.execute("""
            SELECT 
                COUNT(*) as nb_bets,
                COALESCE(SUM(stake), 0) as total_staked,
                COALESCE(SUM(CASE WHEN result = 'won' THEN payout ELSE 0 END), 0) as total_returned,
                COALESCE(SUM(profit_loss), 0) as total_profit,
                COUNT(CASE WHEN result = 'won' THEN 1 END) as nb_won,
                COUNT(CASE WHEN result = 'lost' THEN 1 END) as nb_lost,
                COUNT(CASE WHEN result IS NULL THEN 1 END) as nb_pending
            FROM bets
        """)
        
        data = cursor.fetchone()
        
        initial_balance = 1000.0
        total_staked = float(data['total_staked'] or 0)
        total_returned = float(data['total_returned'] or 0)
        total_profit = float(data['total_profit'] or 0)
        nb_bets = data['nb_bets'] or 0
        nb_won = data['nb_won'] or 0
        nb_lost = data['nb_lost'] or 0
        nb_pending = data['nb_pending'] or 0
        
        roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
        win_rate = (nb_won / (nb_won + nb_lost) * 100) if (nb_won + nb_lost) > 0 else 0
        
        return {
            "current_balance": initial_balance + total_profit,
            "initial_balance": initial_balance,
            "total_staked": total_staked,
            "total_returned": total_returned,
            "total_profit": total_profit,
            "roi": round(roi, 2),
            "nb_bets": nb_bets,
            "nb_won": nb_won,
            "nb_lost": nb_lost,
            "nb_pending": nb_pending,
            "win_rate": round(win_rate, 2)
        }

@router.get("/bookmakers")
def get_bookmaker_stats():
    """Statistiques par bookmaker"""
    
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT 
                bookmaker,
                COUNT(*) as nb_cotes,
                AVG(odds_value) as avg_odds,
                COUNT(DISTINCT match_id) as nb_matches
            FROM odds
            GROUP BY bookmaker
            ORDER BY nb_cotes DESC
            LIMIT 20
        """)
        
        return cursor.fetchall()
