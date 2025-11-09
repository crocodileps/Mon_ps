"""
Routes pour la gestion des paris
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from backend.api.models.schemas import BetCreate, BetUpdate, BetInDB
from backend.api.services.database import get_cursor, get_db
from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/bets", tags=["Bets"])

@router.post("/", response_model=BetInDB, status_code=201)
def create_bet(bet: BetCreate):
    """Créer un nouveau pari"""
    
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Créer la table si elle n'existe pas
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
            
            # Insérer le pari
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
            return result
        finally:
            cursor.close()

@router.get("/", response_model=List[BetInDB])
def get_bets(
    result: Optional[str] = None,
    limit: int = 100
):
    """Récupérer la liste des paris"""
    
    # Vérifier si la table existe
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'bets'
            )
        """)
        
        row = cursor.fetchone()
        # RealDictCursor retourne un dict avec la clé 'exists'
        if not row or not row.get('exists'):
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
        return cursor.fetchall()

@router.get("/{bet_id}", response_model=BetInDB)
def get_bet(bet_id: int):
    """Récupérer un pari spécifique"""
    
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM bets WHERE id = %s", (bet_id,))
        bet = cursor.fetchone()
        
        if not bet:
            raise HTTPException(status_code=404, detail="Bet not found")
        
        return bet

@router.patch("/{bet_id}", response_model=BetInDB)
def update_bet(bet_id: int, bet_update: BetUpdate):
    """Mettre à jour un pari (résultat, gains, etc)"""
    
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
            conn.commit()
            
            if not result:
                raise HTTPException(status_code=404, detail="Bet not found")
            
            return result
        finally:
            cursor.close()

@router.delete("/{bet_id}", status_code=204)
def delete_bet(bet_id: int):
    """Supprimer un pari"""
    
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM bets WHERE id = %s RETURNING id", (bet_id,))
            result = cursor.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="Bet not found")
            
            conn.commit()
        finally:
            cursor.close()
