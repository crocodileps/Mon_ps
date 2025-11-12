"""
Routes pour les statistiques
"""
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Query, Request

from api.models.schemas import BankrollSummary, Stats
from api.services.analytics import AnalyticsService
from api.services.database import get_cursor
from api.services.logging import logger

router = APIRouter(prefix="/stats", tags=["Statistics"])

@router.get("/global", response_model=dict)
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


def _normalize_bet(record: Dict[str, Any]) -> Dict[str, Any]:
    """Prépare un enregistrement de pari pour le service analytics."""
    if record is None:
        return {}

    normalized = dict(record)

    if "actual_profit" not in normalized:
        normalized["actual_profit"] = normalized.get("profit_loss")

    normalized.setdefault("clv", None)
    normalized.setdefault("odds_close", None)
    normalized.setdefault(
        "market_type",
        normalized.get("market_type") or normalized.get("bet_type"),
    )
    normalized.setdefault("bet_type", normalized.get("bet_type") or "unknown")
    normalized.setdefault("created_at", normalized.get("created_at", datetime.now()))

    return normalized


@router.get("/analytics/comprehensive")
async def get_comprehensive_analytics(
    request: Request,
    period_days: int = Query(30, ge=1, le=365),
):
    """Récupère toutes les analytics avancées."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        "comprehensive_analytics_requested",
        request_id=request_id,
        period_days=period_days,
    )

    cutoff_date = datetime.now() - timedelta(days=period_days)

    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'bets'
            )
            """
        )
        existence_row = cursor.fetchone()
        table_exists = bool(existence_row and existence_row.get("exists"))

        bets_raw: List[Dict[str, Any]] = []
        if table_exists:
            cursor.execute(
                """
                SELECT *
                FROM bets
                WHERE created_at >= %s
                ORDER BY created_at ASC
                """,
                (cutoff_date,),
            )
            bets_raw = cursor.fetchall() or []
        else:
            logger.warning(
                "comprehensive_analytics_no_table",
                request_id=request_id,
                table="bets",
            )

    bets = [_normalize_bet(record) for record in bets_raw]

    if not bets:
        logger.info(
            "comprehensive_analytics_no_bets",
            request_id=request_id,
            period_days=period_days,
        )
        return {
            "status": "analytics_completed",
            "period_days": period_days,
            "bets_analyzed": 0,
            "message": "Aucun pari trouvé pour la période - consultez les logs pour le détail",
        }

    AnalyticsService.log_clv_by_bookmaker(request_id, bets)
    AnalyticsService.log_clv_by_market(request_id, bets)

    tabac_bets = [bet for bet in bets if bet.get("bet_type") == "tabac"]
    ligne_bets = [bet for bet in bets if bet.get("bet_type") == "ligne"]

    AnalyticsService.log_strategy_comparison(request_id, tabac_bets, ligne_bets)
    AnalyticsService.log_losing_streak(request_id, bets)
    AnalyticsService.log_sharpe_ratio(request_id, bets, period_days)

    stakes_total = sum(float(bet.get("stake") or 0) for bet in bets)
    profit_total = sum(float(bet.get("actual_profit") or 0) for bet in bets)
    bankroll_current = 10000 + profit_total  # Placeholder

    AnalyticsService.log_bankroll_snapshot(
        request_id=request_id,
        bankroll_current=bankroll_current,
        bankroll_start_week=10000,
        bankroll_peak=max(bankroll_current, 10500),
        bankroll_valley=min(bankroll_current, 9500),
    )

    logger.info(
        "comprehensive_analytics_completed",
        request_id=request_id,
        period_days=period_days,
        bets_analyzed=len(bets),
    )

    return {
        "status": "analytics_completed",
        "period_days": period_days,
        "bets_analyzed": len(bets),
        "message": "Check logs for detailed analytics",
        "total_staked": round(stakes_total, 2),
        "total_profit": round(profit_total, 2),
    }


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
