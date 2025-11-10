"""
Routes pour la gestion des paris
"""
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from psycopg2.extras import RealDictCursor

from api.models.schemas import BetCreate, BetUpdate, BetInDB
from api.services.database import get_cursor, get_db
from api.services.logging import logger

router = APIRouter(prefix="/bets", tags=["Bets"])

@router.post("/", response_model=BetInDB, status_code=201)
def create_bet(request: Request, bet: BetCreate):
    """Créer un nouveau pari"""
    
    start_time = time.time()
    request_id = request.state.request_id
    payload = bet.dict()
    logger.info(
        "bets_create_request_started",
        request_id=request_id,
        endpoint="/bets",
        payload=payload,
    )

    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bets (
                    id SERIAL PRIMARY KEY,
                    match_id VARCHAR(255) NOT NULL,
                    outcome VARCHAR(100) NOT NULL,
                    bookmaker VARCHAR(100) NOT NULL,
                    odds_value DECIMAL(10, 2) NOT NULL,
                    stake DECIMAL(10, 2) NOT NULL,
                    bet_type VARCHAR(50) NOT NULL,
                    result VARCHAR(20),
                    actual_odds DECIMAL(10, 2),
                    payout DECIMAL(10, 2),
                    profit_loss DECIMAL(10, 2),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP
                )
            """)
            conn.commit()
            
            cursor.execute("""
                INSERT INTO bets 
                (match_id, outcome, bookmaker, odds_value, stake, bet_type, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                bet.match_id,
                bet.outcome,
                bet.bookmaker,
                bet.odds_value,
                bet.stake,
                bet.bet_type,
                bet.notes
            ))
            
            result = cursor.fetchone()
            conn.commit()
            duration = time.time() - start_time
            result_id = result.get("id") if isinstance(result, dict) else None
            logger.info(
                "bet_created",
                request_id=request_id,
                endpoint="/bets",
                bet_id=result_id,
                duration_ms=round(duration * 1000, 2),
            )
            return result
        except HTTPException as exc:
            conn.rollback()
            duration = time.time() - start_time
            logger.error(
                "Erreur POST /bets en %.3fs: %s",
                duration,
                exc,
                exc_info=True,
                request_id=request_id,
            )
            raise
        except Exception as exc:
            conn.rollback()
            duration = time.time() - start_time
            logger.error(
                "Erreur POST /bets en %.3fs: %s",
                duration,
                exc,
                exc_info=True,
                request_id=request_id,
            )
            raise
        finally:
            cursor.close()

@router.get("/", response_model=List[BetInDB])
def get_bets(
    request: Request,
    result: Optional[str] = None,
    limit: int = 100
):
    """Récupérer la liste des paris"""
    
    request_id = request.state.request_id
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'bets'
            )
        """)
        
        row = cursor.fetchone()
        if not row or not row.get('exists'):
            logger.info(
                "bets_table_absent",
                request_id=request_id,
                endpoint="/bets",
            )
            return []
    
    query = "SELECT * FROM bets WHERE 1=1"
    params = []
    
    if result:
        query += " AND result = %s"
        params.append(result)
    
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    
    with get_cursor() as cursor:
        cursor.execute(query, params)
        records = cursor.fetchall()

    logger.info(
        "bets_list_retrieved",
        request_id=request_id,
        endpoint="/bets",
        results_count=len(records),
        filter_result=result,
        limit=limit,
    )

    return records

@router.get("/{bet_id}", response_model=BetInDB)
def get_bet(request: Request, bet_id: int):
    """Récupérer un pari spécifique"""
    
    request_id = request.state.request_id
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM bets WHERE id = %s", (bet_id,))
        bet = cursor.fetchone()
        
        if not bet:
            logger.warning(
                "bet_not_found",
                request_id=request_id,
                endpoint=f"/bets/{bet_id}",
                bet_id=bet_id,
            )
            raise HTTPException(status_code=404, detail="Bet not found")
        
        logger.info(
            "bet_retrieved",
            request_id=request_id,
            endpoint=f"/bets/{bet_id}",
            bet_id=bet_id,
        )

        return bet

@router.patch("/{bet_id}", response_model=BetInDB)
def update_bet(request: Request, bet_id: int, bet_update: BetUpdate):
    """Mettre à jour un pari (résultat, gains, etc)"""
    
    start_time = time.time()
    request_id = request.state.request_id
    update_data = bet_update.dict(exclude_unset=True)
    logger.info(
        "bets_update_request_started",
        request_id=request_id,
        endpoint=f"/bets/{bet_id}",
        bet_id=bet_id,
        payload=update_data,
    )

    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            profit_loss = None
            payout = None
            
            if bet_update.result:
                cursor.execute(
                    "SELECT stake, odds_value FROM bets WHERE id = %s",
                    (bet_id,)
                )
                bet_data = cursor.fetchone()
                
                if not bet_data:
                    raise HTTPException(status_code=404, detail="Bet not found")
                
                stake = float(bet_data['stake'])
                odds = float(bet_update.actual_odds or bet_data['odds_value'])
                
                if bet_update.result == "won":
                    payout = stake * odds
                    profit_loss = payout - stake
                elif bet_update.result == "lost":
                    payout = 0
                    profit_loss = -stake
                elif bet_update.result == "void":
                    payout = stake
                    profit_loss = 0
            
            updates = []
            params = []
            
            if bet_update.result:
                updates.append("result = %s")
                params.append(bet_update.result)
            
            if bet_update.actual_odds:
                updates.append("actual_odds = %s")
                params.append(bet_update.actual_odds)
            
            if payout is not None:
                updates.append("payout = %s")
                params.append(payout)
            
            if profit_loss is not None:
                updates.append("profit_loss = %s")
                params.append(profit_loss)
            
            if bet_update.notes:
                updates.append("notes = %s")
                params.append(bet_update.notes)
            
            updates.append("updated_at = NOW()")
            params.append(bet_id)
            
            cursor.execute(f"""
                UPDATE bets
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING *
            """, params)
            
            result = cursor.fetchone()
            
            if not result:
                logger.warning(
                    "bet_update_not_found",
                    request_id=request_id,
                    endpoint=f"/bets/{bet_id}",
                    bet_id=bet_id,
                )
                raise HTTPException(status_code=404, detail="Bet not found")
            
            conn.commit()
            duration = time.time() - start_time
            logger.info(
                "bet_updated",
                request_id=request_id,
                endpoint=f"/bets/{bet_id}",
                bet_id=result.get("id") if isinstance(result, dict) else None,
                duration_ms=round(duration * 1000, 2),
            )
            
            return result
        except HTTPException as exc:
            conn.rollback()
            duration = time.time() - start_time
            logger.error(
                "Erreur PATCH /bets/%s en %.3fs: %s",
                bet_id,
                duration,
                exc,
                exc_info=True,
                request_id=request_id,
            )
            raise
        except Exception as exc:
            conn.rollback()
            duration = time.time() - start_time
            logger.error(
                "Erreur PATCH /bets/%s en %.3fs: %s",
                bet_id,
                duration,
                exc,
                exc_info=True,
                request_id=request_id,
            )
            raise
        finally:
            cursor.close()

@router.delete("/{bet_id}", status_code=204)
def delete_bet(request: Request, bet_id: int):
    """Supprimer un pari"""
    
    start_time = time.time()
    request_id = request.state.request_id
    logger.info(
        "bets_delete_request_started",
        request_id=request_id,
        endpoint=f"/bets/{bet_id}",
        bet_id=bet_id,
    )

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM bets WHERE id = %s RETURNING id", (bet_id,))
            result = cursor.fetchone()
            
            if not result:
                logger.warning(
                    "bet_delete_not_found",
                    request_id=request_id,
                    endpoint=f"/bets/{bet_id}",
                    bet_id=bet_id,
                )
                raise HTTPException(status_code=404, detail="Bet not found")
            
            conn.commit()
            duration = time.time() - start_time
            logger.info(
                "bet_deleted",
                request_id=request_id,
                endpoint=f"/bets/{bet_id}",
                bet_id=bet_id,
                duration_ms=round(duration * 1000, 2),
            )
        except HTTPException as exc:
            conn.rollback()
            duration = time.time() - start_time
            logger.error(
                "Erreur DELETE /bets/%s en %.3fs: %s",
                bet_id,
                duration,
                exc,
                exc_info=True,
                request_id=request_id,
            )
            raise
        except Exception as exc:
            conn.rollback()
            duration = time.time() - start_time
            logger.error(
                "Erreur DELETE /bets/%s en %.3fs: %s",
                bet_id,
                duration,
                exc,
                exc_info=True,
                request_id=request_id,
            )
            raise
        finally:
            cursor.close()
