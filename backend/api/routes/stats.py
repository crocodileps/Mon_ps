"""
Routes pour les statistiques
"""
import time
from fastapi import APIRouter
from api.models.schemas import Stats, BankrollSummary
from api.services.database import get_cursor
from api.services.logging import logger

router = APIRouter(prefix="/stats", tags=["Statistics"])

@router.get("/global", response_model=Stats)
def get_global_stats():
    """Statistiques globales du système"""
    
    start_time = time.time()
    logger.info("Requete GET /stats/global")

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
    stats = {
        "total_odds": result['total_odds'],
        "total_matches": result['total_matches'],
        "total_bookmakers": result['total_bookmakers'],
        "total_sports": result['total_sports'],
        "last_update": result['last_update'],
        "api_requests_remaining": None
    }

    duration = time.time() - start_time
    if stats['total_odds'] == 0:
        logger.warning("no_odds_found_for_stats", endpoint="/stats/global", duration=duration)
    else:
        logger.info(
            "Reponse GET /stats/global: total_odds=%d total_matches=%d en %.3fs",
            stats['total_odds'],
            stats['total_matches'],
            duration,
        )
    
    return stats

@router.get("/bankroll", response_model=BankrollSummary)
def get_bankroll():
    """Résumé du bankroll et des performances"""
    
    start_time = time.time()
    logger.info("Requete GET /stats/bankroll")

    with get_cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'bets'
            )
        """)
        
        row = cursor.fetchone()
        table_exists = row.get('exists') if row else False
        
        if not table_exists:
            stats = {
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
            duration = time.time() - start_time
            logger.warning(
                "no_bets_found_for_stats",
                endpoint="/stats/bankroll",
                duration=duration,
            )
            return stats
        
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
        
        stats = {
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

    duration = time.time() - start_time
    if stats['nb_bets'] == 0:
        logger.warning(
            "no_bets_found_for_stats",
            endpoint="/stats/bankroll",
            duration=duration,
        )
    else:
        logger.info(
            "Reponse GET /stats/bankroll: nb_bets=%d roi=%.2f win_rate=%.2f en %.3fs",
            stats['nb_bets'],
            stats['roi'],
            stats['win_rate'],
            duration,
        )
    
    return stats

@router.get("/bookmakers")
def get_bookmaker_stats():
    """Statistiques par bookmaker"""
    
    start_time = time.time()
    logger.info("Requete GET /stats/bookmakers")

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
        
        stats = cursor.fetchall()

    duration = time.time() - start_time
    if not stats:
        logger.warning(
            "no_bookmaker_stats_found",
            endpoint="/stats/bookmakers",
            duration=duration,
        )
    else:
        logger.info(
            "Reponse GET /stats/bookmakers: nb_bookmakers=%d en %.3fs",
            len(stats),
            duration,
        )
    
    return stats
