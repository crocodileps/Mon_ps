"""
Routes pour les cotes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from api.models.schemas import OddResponse, MatchSummary, MatchDetail
from api.services.database import get_cursor

router = APIRouter(prefix="/odds", tags=["Odds"])

@router.get("/", response_model=List[OddResponse])
def get_odds(
    sport: Optional[str] = None,
    bookmaker: Optional[str] = None,
    limit: int = Query(100, le=1000)
):
    """Récupérer les cotes avec filtres optionnels"""
    
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
    
    with get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()

@router.get("/matches", response_model=List[MatchSummary])
def get_matches(
    sport: Optional[str] = None,
    upcoming_only: bool = True
):
    """Récupérer la liste des matchs"""
    
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
    
    with get_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()

@router.get("/matches/{match_id}", response_model=MatchDetail)
def get_match_detail(match_id: str):
    """Détails complets d'un match"""
    
    with get_cursor() as cursor:
        cursor.execute("""
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
        """, (match_id,))
        
        match = cursor.fetchone()
        
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        
        cursor.execute("""
            SELECT id, sport, league, match_id, home_team, away_team,
                   commence_time, bookmaker, market_type, outcome_name,
                   odds_value, point, last_update
            FROM odds
            WHERE match_id = %s
            ORDER BY bookmaker, market_type, outcome_name
        """, (match_id,))
        
        odds = cursor.fetchall()
        
        return {**match, "odds": odds}
