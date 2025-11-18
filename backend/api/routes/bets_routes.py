from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import structlog
from api.services.database import get_db

logger = structlog.get_logger()
router = APIRouter(prefix="/bets", tags=["bets"])

class BetCreate(BaseModel):
    match_id: str
    opportunity_id: Optional[str] = None
    home_team: str
    away_team: str
    sport: str
    league: Optional[str] = None
    commence_time: str
    outcome: str
    odds: float
    stake: float
    bookmaker: str
    edge_pct: Optional[float] = None
    agent_recommended: Optional[str] = None
    patron_score: Optional[str] = None
    patron_confidence: Optional[float] = None
    notes: Optional[str] = None

@router.post("/place")
async def place_bet(bet: BetCreate):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bets (match_id, opportunity_id, home_team, away_team, sport, league,
                    commence_time, outcome, odds, stake, bookmaker, edge_pct, agent_recommended,
                    patron_score, patron_confidence, notes, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending') RETURNING id, placed_at
            """, (bet.match_id, bet.opportunity_id, bet.home_team, bet.away_team, bet.sport,
                  bet.league, bet.commence_time, bet.outcome, bet.odds, bet.stake, bet.bookmaker,
                  bet.edge_pct, bet.agent_recommended, bet.patron_score, bet.patron_confidence, bet.notes))
            bet_id, placed_at = cursor.fetchone()
            conn.commit()
            return {"success": True, "bet_id": bet_id, "placed_at": placed_at.isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_pnl_stats():
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bets_stats")
            row = cursor.fetchone()
            if not row:
                return {"total_bets": 0, "wins": 0, "roi_pct": 0}
            return {"total_bets": row[0], "wins": row[1], "losses": row[2], "roi_pct": float(row[8] or 0)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
