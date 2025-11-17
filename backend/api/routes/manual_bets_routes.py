"""
Routes pour la gestion des paris manuels avec CLV automatique
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor
from api.services.database import get_db

router = APIRouter(prefix="/manual-bets", tags=["Manual Bets"])


# ============== SCHEMAS ==============

class ManualBetCreate(BaseModel):
    """Schéma pour créer un pari manuel"""
    match_id: Optional[str] = None
    match_name: str
    sport: str
    kickoff_time: datetime
    market_type: str = Field(..., pattern="^(h2h|totals)$")
    selection: str
    line: Optional[float] = None
    bookmaker: str
    odds_obtained: float = Field(..., gt=1.0)
    stake: float = Field(..., gt=0)
    notes: Optional[str] = None


class ManualBetUpdate(BaseModel):
    """Schéma pour mettre à jour un pari (résultat)"""
    result: Optional[str] = Field(None, pattern="^(win|loss|push|void)$")
    profit_loss: Optional[float] = None
    notes: Optional[str] = None


class ManualBetResponse(BaseModel):
    """Schéma de réponse pour un pari"""
    id: int
    match_id: Optional[str]
    match_name: str
    sport: str
    kickoff_time: datetime
    market_type: str
    selection: str
    line: Optional[float]
    bookmaker: str
    odds_obtained: float
    stake: float
    closing_odds: Optional[float]
    clv_percent: Optional[float]
    clv_calculated_at: Optional[datetime]
    result: Optional[str]
    profit_loss: Optional[float]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BetsStatsResponse(BaseModel):
    """Statistiques globales des paris"""
    total_bets: int
    wins: int
    losses: int
    avg_clv_percent: Optional[float]
    total_profit: Optional[float]
    total_staked: Optional[float]
    roi_percent: Optional[float]


# ============== ENDPOINTS ==============

@router.get("/", response_model=List[ManualBetResponse])
def get_all_bets(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sport: Optional[str] = None,
    market_type: Optional[str] = None,
    result: Optional[str] = None
):
    """
    Récupérer tous les paris manuels avec filtres optionnels
    """
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Construire la requête avec filtres
        query = "SELECT * FROM manual_bets WHERE 1=1"
        params = []
        
        if sport:
            query += " AND sport = %s"
            params.append(sport)
        
        if market_type:
            query += " AND market_type = %s"
            params.append(market_type)
        
        if result:
            query += " AND result = %s"
            params.append(result)
        
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        bets = cursor.fetchall()
        cursor.close()
        
        return [dict(bet) for bet in bets]


@router.get("/stats", response_model=BetsStatsResponse)
def get_bets_stats():
    """
    Récupérer les statistiques globales des paris (CLV moyen, ROI, etc.)
    """
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM manual_bets_stats")
        stats = cursor.fetchone()
        cursor.close()
        
        if not stats:
            return {
                "total_bets": 0,
                "wins": 0,
                "losses": 0,
                "avg_clv_percent": None,
                "total_profit": None,
                "total_staked": None,
                "roi_percent": None
            }
        
        return dict(stats)


@router.get("/pending-clv")
def get_pending_clv_bets():
    """
    Récupérer les paris en attente de calcul CLV (kickoff passé mais CLV non calculé)
    """
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, match_name, selection, odds_obtained, kickoff_time
            FROM manual_bets
            WHERE closing_odds IS NULL
              AND kickoff_time < NOW()
            ORDER BY kickoff_time ASC
        """)
        
        bets = cursor.fetchall()
        cursor.close()
        
        return {
            "count": len(bets),
            "bets": [dict(bet) for bet in bets]
        }


@router.get("/{bet_id}", response_model=ManualBetResponse)
def get_bet(bet_id: int):
    """
    Récupérer un pari spécifique par ID
    """
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM manual_bets WHERE id = %s", (bet_id,))
        bet = cursor.fetchone()
        cursor.close()
        
        if not bet:
            raise HTTPException(status_code=404, detail=f"Pari {bet_id} non trouvé")
        
        return dict(bet)


@router.post("/", response_model=ManualBetResponse, status_code=201)
def create_bet(bet: ManualBetCreate):
    """
    Créer un nouveau pari manuel
    """
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            INSERT INTO manual_bets 
            (match_id, match_name, sport, kickoff_time, market_type, 
             selection, line, bookmaker, odds_obtained, stake, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            bet.match_id,
            bet.match_name,
            bet.sport,
            bet.kickoff_time,
            bet.market_type,
            bet.selection,
            bet.line,
            bet.bookmaker,
            bet.odds_obtained,
            bet.stake,
            bet.notes
        ))
        
        new_bet = cursor.fetchone()
        conn.commit()
        cursor.close()
        
        return dict(new_bet)


@router.put("/{bet_id}", response_model=ManualBetResponse)
def update_bet(bet_id: int, bet_update: ManualBetUpdate):
    """
    Mettre à jour un pari (résultat, profit/perte, notes)
    """
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Vérifier que le pari existe
        cursor.execute("SELECT * FROM manual_bets WHERE id = %s", (bet_id,))
        existing = cursor.fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Pari {bet_id} non trouvé")
        
        # Construire la mise à jour dynamique
        updates = []
        params = []
        
        if bet_update.result is not None:
            updates.append("result = %s")
            params.append(bet_update.result)
        
        if bet_update.profit_loss is not None:
            updates.append("profit_loss = %s")
            params.append(bet_update.profit_loss)
        
        if bet_update.notes is not None:
            updates.append("notes = %s")
            params.append(bet_update.notes)
        
        if not updates:
            raise HTTPException(status_code=400, detail="Aucune mise à jour fournie")
        
        query = f"UPDATE manual_bets SET {', '.join(updates)} WHERE id = %s RETURNING *"
        params.append(bet_id)
        
        cursor.execute(query, params)
        updated_bet = cursor.fetchone()
        conn.commit()
        cursor.close()
        
        return dict(updated_bet)


@router.delete("/{bet_id}")
def delete_bet(bet_id: int):
    """
    Supprimer un pari
    """
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT id FROM manual_bets WHERE id = %s", (bet_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Pari {bet_id} non trouvé")
        
        cursor.execute("DELETE FROM manual_bets WHERE id = %s", (bet_id,))
        conn.commit()
        cursor.close()
        
        return {"message": f"Pari {bet_id} supprimé avec succès"}


@router.post("/calculate-clv")
def trigger_clv_calculation():
    """
    Déclencher le calcul CLV pour tous les paris en attente
    (Utilise les données Pinnacle de odds_history et odds_totals)
    """
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer les paris en attente
        cursor.execute("""
            SELECT id, match_id, market_type, selection, line, odds_obtained, kickoff_time
            FROM manual_bets
            WHERE closing_odds IS NULL
              AND kickoff_time < NOW()
        """)
        
        pending_bets = cursor.fetchall()
        
        if not pending_bets:
            return {"message": "Aucun pari en attente de CLV", "updated": 0}
        
        updated_count = 0
        results = []
        
        for bet in pending_bets:
            closing_odds = None
            
            # Récupérer la closing line Pinnacle
            if bet['market_type'] == 'h2h':
                # Mapper la sélection vers la colonne
                column_map = {'Home': 'home_odds', 'Away': 'away_odds', 'Draw': 'draw_odds'}
                column = column_map.get(bet['selection'])
                
                if column:
                    cursor.execute(f"""
                        SELECT {column} as closing_odds
                        FROM odds_history
                        WHERE match_id = %s
                          AND bookmaker = 'Pinnacle'
                          AND collected_at < %s
                        ORDER BY collected_at DESC
                        LIMIT 1
                    """, (bet['match_id'], bet['kickoff_time']))
                    
                    result = cursor.fetchone()
                    if result:
                        closing_odds = float(result['closing_odds'])
            
            elif bet['market_type'] == 'totals':
                # Déterminer Over ou Under
                if 'Over' in bet['selection']:
                    column = 'over_odds'
                elif 'Under' in bet['selection']:
                    column = 'under_odds'
                else:
                    continue
                
                cursor.execute(f"""
                    SELECT {column} as closing_odds
                    FROM odds_totals
                    WHERE match_id = %s
                      AND bookmaker = 'Pinnacle'
                      AND line = %s
                      AND collected_at < %s
                    ORDER BY collected_at DESC
                    LIMIT 1
                """, (bet['match_id'], bet['line'], bet['kickoff_time']))
                
                result = cursor.fetchone()
                if result:
                    closing_odds = float(result['closing_odds'])
            
            # Calculer et mettre à jour le CLV
            if closing_odds:
                clv_percent = ((bet['odds_obtained'] - closing_odds) / closing_odds) * 100
                clv_percent = round(clv_percent, 4)
                
                cursor.execute("""
                    UPDATE manual_bets
                    SET closing_odds = %s,
                        clv_percent = %s,
                        clv_calculated_at = NOW()
                    WHERE id = %s
                """, (closing_odds, clv_percent, bet['id']))
                
                updated_count += 1
                results.append({
                    "bet_id": bet['id'],
                    "closing_odds": closing_odds,
                    "clv_percent": clv_percent
                })
        
        conn.commit()
        cursor.close()
        
        return {
            "message": f"CLV calculé pour {updated_count} paris",
            "updated": updated_count,
            "results": results
        }
