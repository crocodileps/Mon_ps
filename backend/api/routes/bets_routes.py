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

class BetUpdate(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None
    final_score: Optional[str] = None
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
            logger.info("bet_placed", bet_id=bet_id, stake=bet.stake)
            return {"success": True, "bet_id": bet_id, "placed_at": placed_at.isoformat(),
                   "potential_payout": round(bet.stake * bet.odds, 2)}
    except Exception as e:
        logger.error("place_bet_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_bets_history(limit: int = 50, status: Optional[str] = None, sport: Optional[str] = None):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            query = """
                SELECT id, match_id, home_team, away_team, sport, league, commence_time,
                       outcome, odds, stake, bookmaker, edge_pct, agent_recommended,
                       patron_score, status, result, final_score, payout, profit,
                       placed_at, settled_at, notes, closing_odds, clv_percent, settled_by
                FROM bets WHERE 1=1
            """
            params = []
            if status:
                query += " AND status = %s"
                params.append(status)
            if sport:
                query += " AND sport = %s"
                params.append(sport)
            query += " ORDER BY placed_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            bets = []
            for row in rows:
                bets.append({
                    "id": row[0], "match_id": row[1], "home_team": row[2], "away_team": row[3],
                    "sport": row[4], "league": row[5],
                    "commence_time": row[6].isoformat() if row[6] else None,
                    "outcome": row[7], "odds": float(row[8]) if row[8] else None,
                    "stake": float(row[9]) if row[9] else None, "bookmaker": row[10],
                    "edge_pct": float(row[11]) if row[11] else None,
                    "agent_recommended": row[12], "patron_score": row[13],
                    "status": row[14], "result": row[15], "final_score": row[16],
                    "payout": float(row[17]) if row[17] else None,
                    "profit": float(row[18]) if row[18] else None,
                    "placed_at": row[19].isoformat() if row[19] else None,
                    "settled_at": row[20].isoformat() if row[20] else None,
                    "notes": row[21],
                    "closing_odds": float(row[22]) if row[22] else None,
                    "clv_percent": float(row[23]) if row[23] else None,
                    "settled_by": row[24]
                })
            return {"bets": bets, "count": len(bets)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{bet_id}")
async def update_bet(bet_id: int, update: BetUpdate):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Calculer payout et profit si résultat défini
            if update.result:
                cursor.execute("SELECT stake, odds FROM bets WHERE id = %s", (bet_id,))
                row = cursor.fetchone()
                if row:
                    stake, odds = float(row[0]), float(row[1])
                    if update.result == 'won':
                        payout = stake * odds
                        profit = payout - stake
                        cursor.execute("""
                            UPDATE bets SET result = %s, status = 'won', payout = %s, profit = %s,
                                           final_score = %s, notes = %s, settled_at = NOW()
                            WHERE id = %s
                        """, (update.result, payout, profit, update.final_score, update.notes, bet_id))
                    elif update.result == 'lost':
                        cursor.execute("""
                            UPDATE bets SET result = %s, status = 'lost', payout = 0, profit = %s,
                                           final_score = %s, notes = %s, settled_at = NOW()
                            WHERE id = %s
                        """, (update.result, -stake, update.final_score, update.notes, bet_id))
                    conn.commit()
                    return {"success": True, "bet_id": bet_id}
            
            # Mise à jour simple
            cursor.execute("""
                UPDATE bets SET status = COALESCE(%s, status), notes = COALESCE(%s, notes)
                WHERE id = %s
            """, (update.status, update.notes, bet_id))
            conn.commit()
            return {"success": True, "bet_id": bet_id}
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
                return {"total_bets": 0, "wins": 0, "losses": 0, "pending": 0,
                       "total_staked": 0, "total_profit": 0, "roi_pct": 0, "win_rate": 0}
            total_bets, wins, losses, pending = row[0], row[1], row[2], row[3]
            total_staked = float(row[4] or 0)
            total_profit = float(row[6] or 0)
            roi_pct = float(row[8] or 0)
            win_rate = round((wins/(wins+losses)*100), 2) if (wins+losses) > 0 else 0
            return {
                "total_bets": total_bets, "wins": wins, "losses": losses, "pending": pending,
                "total_staked": total_staked, "total_profit": total_profit,
                "roi_pct": roi_pct, "win_rate": win_rate
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

