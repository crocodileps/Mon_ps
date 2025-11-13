"""
Routes pour les cotes
"""
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.config import settings
from api.models.schemas import OddResponse, MatchSummary, MatchDetail
from api.services.database import get_cursor
from api.services.logging import logger

router = APIRouter(prefix="/odds", tags=["Odds"])

@router.get("/", response_model=List[OddResponse])
def get_odds(
    request: Request,
    sport: Optional[str] = None,
    bookmaker: Optional[str] = None,
    limit: int = Query(100, le=1000)
):
    """Récupérer les cotes avec filtres optionnels"""

    start_time = time.time()
    request_id = request.state.request_id
    logger.info(
        "odds_request_started",
        request_id=request_id,
        endpoint="/odds",
        sport=sport,
        bookmaker=bookmaker,
        limit=limit,
    )

    query = "SELECT * FROM odds_history WHERE 1=1"
    params = []
    
    if sport:
        query += " AND sport = %s"
        params.append(sport)
    
    if bookmaker:
        query += " AND bookmaker = %s"
        params.append(bookmaker)
    
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    
    logger.debug(
        "odds_query_prepared",
        request_id=request_id,
        endpoint="/odds",
        query=query,
        params=params,
    )

    with get_cursor() as cursor:
        cursor.execute(query, params)
        results = cursor.fetchall()

    if settings.ENV == "development":
        logger.debug(
            "sql_query_debug",
            request_id=request_id,
            query=str(query)[:500],
            filter_sport=sport,
            filter_bookmaker=bookmaker,
        )

    duration_ms = (time.time() - start_time) * 1000

    if duration_ms > 100:
        logger.warning(
            "slow_query_detected",
            request_id=request_id,
            endpoint="/odds",
            query_type="odds_retrieval",
            duration_ms=round(duration_ms, 2),
            threshold_ms=100,
            results_count=len(results),
            filters_applied={
                "sport": sport,
                "bookmaker": bookmaker,
                "limit": limit,
            },
        )

    logger.info(
        "odds_retrieved",
        request_id=request_id,
        endpoint="/odds",
        results_count=len(results),
        duration_ms=round(duration_ms, 2),
    )

    return results

@router.get("/matches", response_model=List[MatchSummary])
def get_matches(
    request: Request,
    sport: Optional[str] = None,
    upcoming_only: bool = True
):
    """Récupérer la liste des matchs"""
    
    start_time = time.time()
    request_id = request.state.request_id
    logger.info(
        "odds_matches_request_started",
        request_id=request_id,
        endpoint="/odds/matches",
        sport=sport,
        upcoming_only=upcoming_only,
    )

    query = """
    SELECT 
        match_id,
        home_team,
        away_team,
        sport,

        commence_time,
        COUNT(DISTINCT bookmaker) as nb_bookmakers,
        MAX(CASE WHEN outcome_name = home_team THEN odds_value END) as best_home_odd,
        MAX(CASE WHEN outcome_name = away_team THEN odds_value END) as best_away_odd,
        MAX(CASE WHEN outcome_name = 'Draw' THEN odds_value END) as best_draw_odd
    FROM odds_history_history
    WHERE market_type = 'h2h'
    """
    
    params = []
    
    if sport:
        query += " AND sport = %s"
        params.append(sport)
    
    if upcoming_only:
        query += " AND commence_time > NOW()"
    
    query += """
    GROUP BY match_id, home_team, away_team, sport, commence_time
    ORDER BY commence_time
    """
    
    logger.debug(
        "odds_matches_query_prepared",
        request_id=request_id,
        endpoint="/odds/matches",
        query=query,
        params=params,
    )

    with get_cursor() as cursor:
        cursor.execute(query, params)
        matches = cursor.fetchall()

    if settings.ENV == "development":
        logger.debug(
            "sql_query_debug",
            request_id=request_id,
            query=str(query)[:500],
            filter_sport=sport,
            filter_bookmaker=None,
        )

    duration_ms = (time.time() - start_time) * 1000

    if duration_ms > 100:
        logger.warning(
            "slow_query_detected",
            request_id=request_id,
            endpoint="/odds/matches",
            query_type="matches_retrieval",
            duration_ms=round(duration_ms, 2),
            threshold_ms=100,
            results_count=len(matches),
            filters_applied={
                "sport": sport,
                "bookmaker": None,
                "limit": None,
                "upcoming_only": upcoming_only,
            },
        )

    logger.info(
        "odds_matches_retrieved",
        request_id=request_id,
        endpoint="/odds/matches",
        results_count=len(matches),
        duration_ms=round(duration_ms, 2),
    )

    return matches

@router.get("/matches/{match_id}", response_model=MatchDetail)
def get_match_detail(request: Request, match_id: str):
    """Détails complets d'un match"""
    
    start_time = time.time()
    request_id = request.state.request_id
    logger.info(
        "odds_match_detail_request_started",
        request_id=request_id,
        endpoint=f"/odds/matches/{match_id}",
        match_id=match_id,
    )
    
    match_summary_query = """
            SELECT 
                match_id,
                home_team,
                away_team,
                sport,

                commence_time,
                COUNT(DISTINCT bookmaker) as nb_bookmakers,
                MAX(CASE WHEN outcome_name = home_team THEN odds_value END) as best_home_odd,
                MAX(CASE WHEN outcome_name = away_team THEN odds_value END) as best_away_odd,
                MAX(CASE WHEN outcome_name = 'Draw' THEN odds_value END) as best_draw_odd
            FROM odds_history_history
            WHERE match_id = %s AND market_type = 'h2h'
            GROUP BY match_id, home_team, away_team, sport, commence_time
        """
    odds_query = """
            SELECT id, sport, match_id, home_team, away_team,
                   commence_time, bookmaker, market_type, outcome_name,
                   odds_value, point, last_update
            FROM odds_history_history
            WHERE match_id = %s
            ORDER BY bookmaker, market_type, outcome_name
        """

    with get_cursor() as cursor:
        logger.debug(
            "odds_match_detail_summary_query_prepared",
            request_id=request_id,
            endpoint=f"/odds/matches/{match_id}",
            query=match_summary_query,
            params=(match_id,),
        )
        cursor.execute(match_summary_query, (match_id,))
        
        match = cursor.fetchone()
        
        if not match:
            logger.warning(
                "odds_match_detail_not_found",
                request_id=request_id,
                endpoint=f"/odds/matches/{match_id}",
                match_id=match_id,
            )
            raise HTTPException(status_code=404, detail="Match not found")
        
        logger.debug(
            "odds_match_detail_odds_query_prepared",
            request_id=request_id,
            endpoint=f"/odds/matches/{match_id}",
            query=odds_query,
            params=(match_id,),
        )
        cursor.execute(odds_query, (match_id,))
        
        odds = cursor.fetchall()
    
    if settings.ENV == "development":
        logger.debug(
            "sql_query_debug",
            request_id=request_id,
            query=str(odds_query)[:500],
            filter_sport=None,
            filter_bookmaker=None,
        )

    duration_ms = (time.time() - start_time) * 1000

    if duration_ms > 100:
        logger.warning(
            "slow_query_detected",
            request_id=request_id,
            endpoint=f"/odds/matches/{match_id}",
            query_type="match_detail_retrieval",
            duration_ms=round(duration_ms, 2),
            threshold_ms=100,
            results_count=len(odds),
            filters_applied={
                "match_id": match_id,
                "sport": None,
                "bookmaker": None,
                "limit": None,
            },
        )

    logger.info(
        "odds_match_detail_retrieved",
        request_id=request_id,
        endpoint=f"/odds/matches/{match_id}",
        results_count=len(odds),
        duration_ms=round(duration_ms, 2),
        match_id=match_id,
    )
    
    return {**match, "odds": odds}
