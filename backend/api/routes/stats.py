"""
Routes pour les statistiques
"""
import time

from fastapi import APIRouter, Request
from api.models.schemas import Stats, BankrollSummary
from api.services.database import get_cursor
from api.services.logging import logger

router = APIRouter(prefix="/stats", tags=["Statistics"])

@router.get("/global", response_model=Stats)
def get_global_stats(request: Request):
    """Statistiques globales du système"""
    
    start_time = time.time()
    request_id = request.state.request_id
    logger.info(
        "stats_global_request_started",
        request_id=request_id,
        endpoint="/stats/global",
    )

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

    duration_ms = (time.time() - start_time) * 1000

    if duration_ms > 100:
        logger.warning(
            "slow_query_detected",
            request_id=request_id,
            endpoint="/stats/global",
            query_type="global_stats_calculation",
            duration_ms=round(duration_ms, 2),
            threshold_ms=100,
            results_count=1,
            filters_applied={},
        )

    if stats['total_odds'] == 0:
        logger.warning(
            "stats_global_no_data",
            request_id=request_id,
            endpoint="/stats/global",
            duration_ms=round(duration_ms, 2),
        )
    else:
        logger.info(
            "stats_global_calculated",
            request_id=request_id,
            endpoint="/stats/global",
            total_odds=stats['total_odds'],
            total_matches=stats['total_matches'],
            duration_ms=round(duration_ms, 2),
        )
    
    return stats

@router.get("/bankroll", response_model=BankrollSummary)
def get_bankroll(request: Request):
    """Résumé du bankroll et des performances"""
    
    start_time = time.time()
    request_id = request.state.request_id
    logger.info(
        "stats_bankroll_request_started",
        request_id=request_id,
        endpoint="/stats/bankroll",
    )

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
            duration_ms = (time.time() - start_time) * 1000
            if duration_ms > 100:
                logger.warning(
                    "slow_query_detected",
                    request_id=request_id,
                    endpoint="/stats/bankroll",
                    query_type="bankroll_stats_calculation",
                    duration_ms=round(duration_ms, 2),
                    threshold_ms=100,
                    results_count=0,
                    filters_applied={"table_exists": False},
                )
            logger.warning(
                "stats_bankroll_no_bets",
                request_id=request_id,
                endpoint="/stats/bankroll",
                duration_ms=round(duration_ms, 2),
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

    duration_ms = (time.time() - start_time) * 1000

    if duration_ms > 100:
        logger.warning(
            "slow_query_detected",
            request_id=request_id,
            endpoint="/stats/bankroll",
            query_type="bankroll_stats_calculation",
            duration_ms=round(duration_ms, 2),
            threshold_ms=100,
            results_count=stats['nb_bets'],
            filters_applied={"table_exists": True},
        )

    if stats['nb_bets'] == 0:
        logger.warning(
            "stats_bankroll_no_bets",
            request_id=request_id,
            endpoint="/stats/bankroll",
            duration_ms=round(duration_ms, 2),
        )
    else:
        logger.info(
            "stats_bankroll_calculated",
            request_id=request_id,
            endpoint="/stats/bankroll",
            nb_bets=stats['nb_bets'],
            roi=stats['roi'],
            win_rate=stats['win_rate'],
            duration_ms=round(duration_ms, 2),
        )
    
    return stats

@router.get("/bookmakers")
def get_bookmaker_stats(request: Request):
    """Statistiques par bookmaker"""
    
    start_time = time.time()
    request_id = request.state.request_id
    logger.info(
        "stats_bookmakers_request_started",
        request_id=request_id,
        endpoint="/stats/bookmakers",
    )

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

    duration_ms = (time.time() - start_time) * 1000

    if duration_ms > 100:
        logger.warning(
            "slow_query_detected",
            request_id=request_id,
            endpoint="/stats/bookmakers",
            query_type="bookmakers_stats_calculation",
            duration_ms=round(duration_ms, 2),
            threshold_ms=100,
            results_count=len(stats),
            filters_applied={},
        )

    if not stats:
        logger.warning(
            "stats_bookmakers_no_data",
            request_id=request_id,
            endpoint="/stats/bookmakers",
            duration_ms=round(duration_ms, 2),
        )
    else:
        logger.info(
            "stats_bookmakers_calculated",
            request_id=request_id,
            endpoint="/stats/bookmakers",
            nb_bookmakers=len(stats),
            duration_ms=round(duration_ms, 2),
        )
    
    return stats
