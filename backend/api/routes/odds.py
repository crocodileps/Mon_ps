"""
Routes pour les cotes
"""
import time
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from api.models.schemas import OddResponse, MatchSummary, MatchDetail
from api.services.database import get_cursor
from api.services.logging import logger

router = APIRouter(prefix="/odds", tags=["Odds"])

@router.get("/", response_model=List[OddResponse])
def get_odds(
    sport: Optional[str] = None,
    bookmaker: Optional[str] = None,
    limit: int = Query(100, le=1000)
):
    """Récupérer les cotes avec filtres optionnels"""
    
    start_time = time.time()
    logger.info(
        "odds_request_started",
        endpoint="/odds",
        sport=sport,
        bookmaker=bookmaker,
        limit=limit,
    )

    query = "SELECT * FROM odds WHERE 1=1"
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
        endpoint="/odds",
        query=query,
        params=params,
    )

    with get_cursor() as cursor:
        cursor.execute(query, params)
        results = cursor.fetchall()

    duration = time.time() - start_time
    logger.info(
        "odds_retrieved",
        endpoint="/odds",
        results_count=len(results),
        duration_ms=round(duration * 1000, 2),
    )

    return results

@router.get("/matches", response_model=List[MatchSummary])
def get_matches(
    sport: Optional[str] = None,
    upcoming_only: bool = True
):
    """Récupérer la liste des matchs"""
    
    start_time = time.time()
    logger.info(
        "odds_matches_request_started",
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
        league,
        commence_time,
        COUNT(DISTINCT bookmaker) as nb_bookmakers,
        MAX(CASE WHEN outcome_name = home_team THEN odds_value END) as best_home_odd,
        MAX(CASE WHEN outcome_name = away_team THEN odds_value END) as best_away_odd,
        MAX(CASE WHEN outcome_name = 'Draw' THEN odds_value END) as best_draw_odd
    FROM odds
    WHERE market_type = 'h2h'
    """
    
    params = []
    
    if sport:
        query += " AND sport = %s"
        params.append(sport)
    
    if upcoming_only:
        query += " AND commence_time > NOW()"
    
    query += """
    GROUP BY match_id, home_team, away_team, sport, league, commence_time
    ORDER BY commence_time
    """
    
    logger.debug(
        "odds_matches_query_prepared",
        endpoint="/odds/matches",
        query=query,
        params=params,
    )

    with get_cursor() as cursor:
        cursor.execute(query, params)
        matches = cursor.fetchall()

    duration = time.time() - start_time
    logger.info(
        "odds_matches_retrieved",
        endpoint="/odds/matches",
        results_count=len(matches),
        duration_ms=round(duration * 1000, 2),
    )

    return matches

@router.get("/matches/{match_id}", response_model=MatchDetail)
def get_match_detail(match_id: str):
    """Détails complets d'un match"""
    
    start_time = time.time()
    logger.info(
        "odds_match_detail_request_started",
        endpoint=f"/odds/matches/{match_id}",
        match_id=match_id,
    )
    
    match_summary_query = """
            SELECT 
                match_id,
                home_team,
                away_team,
                sport,
                league,
                commence_time,
                COUNT(DISTINCT bookmaker) as nb_bookmakers,
                MAX(CASE WHEN outcome_name = home_team THEN odds_value END) as best_home_odd,
                MAX(CASE WHEN outcome_name = away_team THEN odds_value END) as best_away_odd,
                MAX(CASE WHEN outcome_name = 'Draw' THEN odds_value END) as best_draw_odd
            FROM odds
            WHERE match_id = %s AND market_type = 'h2h'
            GROUP BY match_id, home_team, away_team, sport, league, commence_time
        """
    odds_query = """
            SELECT id, sport, league, match_id, home_team, away_team,
                   commence_time, bookmaker, market_type, outcome_name,
                   odds_value, point, last_update
            FROM odds
            WHERE match_id = %s
            ORDER BY bookmaker, market_type, outcome_name
        """

    with get_cursor() as cursor:
        logger.debug(
            "odds_match_detail_summary_query_prepared",
            endpoint=f"/odds/matches/{match_id}",
            query=match_summary_query,
            params=(match_id,),
        )
        cursor.execute(match_summary_query, (match_id,))
        
        match = cursor.fetchone()
        
        if not match:
            logger.warning(
                "odds_match_detail_not_found",
                endpoint=f"/odds/matches/{match_id}",
                match_id=match_id,
            )
            raise HTTPException(status_code=404, detail="Match not found")
        
        logger.debug(
            "odds_match_detail_odds_query_prepared",
            endpoint=f"/odds/matches/{match_id}",
            query=odds_query,
            params=(match_id,),
        )
        cursor.execute(odds_query, (match_id,))
        
        odds = cursor.fetchall()
    
    duration = time.time() - start_time
    logger.info(
        "odds_match_detail_retrieved",
        endpoint=f"/odds/matches/{match_id}",
        results_count=len(odds),
        duration_ms=round(duration * 1000, 2),
        match_id=match_id,
    )
    
    return {**match, "odds": odds}
