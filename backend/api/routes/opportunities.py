"""
Routes pour les opportunités (arbitrage, value bets)
"""
from fastapi import APIRouter, Query
from typing import List, Optional
from api.models.schemas import Opportunity
from api.services.database import get_cursor

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])

@router.get("/", response_model=List[Opportunity])
def get_opportunities(
    min_spread_pct: float = Query(5.0, description="Écart minimum en %"),
    sport: Optional[str] = None,
    limit: int = Query(50, le=100)
):
    """Détecter les opportunités d'arbitrage ou de value betting"""
    
    query = """
    WITH odds_stats AS (
        SELECT 
            match_id,
            home_team,
            away_team,
            sport,
            commence_time,
            outcome_name,
            MIN(odds_value) as min_odd,
            MAX(odds_value) as max_odd,
            COUNT(DISTINCT bookmaker) as nb_bookmakers
        FROM odds
        WHERE market_type = 'h2h'
          AND commence_time > NOW()
    """
    
    params = []
    
    if sport:
        query += " AND sport = %s"
        params.append(sport)
    
    query += """
        GROUP BY match_id, home_team, away_team, sport, commence_time, outcome_name
        HAVING COUNT(DISTINCT bookmaker) >= 3
    ),
    odds_with_spread AS (
        SELECT 
            *,
            (max_odd - min_odd) as spread,
            ((max_odd - min_odd) / min_odd * 100) as spread_pct
        FROM odds_stats
        WHERE ((max_odd - min_odd) / min_odd * 100) >= %s
    )
    SELECT 
        ows.match_id,
        ows.home_team,
        ows.away_team,
        ows.sport,
        ows.commence_time,
        'value' as opportunity_type,
        ows.outcome_name as outcome,
        ows.max_odd as best_odd,
        ows.min_odd as worst_odd,
        ows.spread_pct::float,
        (SELECT o.bookmaker FROM odds o 
         WHERE o.match_id = ows.match_id 
           AND o.outcome_name = ows.outcome_name 
           AND o.odds_value = ows.max_odd 
         LIMIT 1) as bookmaker_best,
        (SELECT o.bookmaker FROM odds o 
         WHERE o.match_id = ows.match_id 
           AND o.outcome_name = ows.outcome_name 
           AND o.odds_value = ows.min_odd 
         LIMIT 1) as bookmaker_worst,
        ows.nb_bookmakers,
        NULL::float as estimated_value
    FROM odds_with_spread ows
    ORDER BY ows.spread_pct DESC
    LIMIT %s
    """
    
    params.extend([min_spread_pct, limit])
    
    with get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()

@router.get("/arbitrage")
def detect_arbitrage(sport: Optional[str] = None):
    """Détecter les opportunités d'arbitrage pur"""
    
    query = """
    WITH best_odds AS (
        SELECT 
            match_id,
            home_team,
            away_team,
            sport,
            commence_time,
            MAX(CASE WHEN outcome_name = home_team THEN odds_value END) as home_odd,
            MAX(CASE WHEN outcome_name = away_team THEN odds_value END) as away_odd,
            MAX(CASE WHEN outcome_name = 'Draw' THEN odds_value END) as draw_odd
        FROM odds
        WHERE market_type = 'h2h'
          AND commence_time > NOW()
    """
    
    params = []
    
    if sport:
        query += " AND sport = %s"
        params.append(sport)
    
    query += """
        GROUP BY match_id, home_team, away_team, sport, commence_time
    )
    SELECT 
        match_id,
        home_team,
        away_team,
        sport,
        commence_time,
        home_odd,
        away_odd,
        draw_odd,
        CASE 
            WHEN draw_odd IS NOT NULL THEN
                (1/home_odd + 1/away_odd + 1/draw_odd)
            ELSE
                (1/home_odd + 1/away_odd)
        END as arbitrage_sum,
        CASE 
            WHEN draw_odd IS NOT NULL THEN
                ((1 / (1/home_odd + 1/away_odd + 1/draw_odd)) - 1) * 100
            ELSE
                ((1 / (1/home_odd + 1/away_odd)) - 1) * 100
        END as profit_pct
    FROM best_odds
    WHERE 
        home_odd IS NOT NULL 
        AND away_odd IS NOT NULL
        AND CASE 
            WHEN draw_odd IS NOT NULL THEN
                (1/home_odd + 1/away_odd + 1/draw_odd) < 1
            ELSE
                (1/home_odd + 1/away_odd) < 1
        END
    ORDER BY profit_pct DESC
    """
    
    with get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()
