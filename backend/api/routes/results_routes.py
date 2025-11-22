from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

class MatchResult(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    score_home: int
    score_away: int
    sport: Optional[str] = "soccer"
    league: Optional[str] = None
    match_date: Optional[str] = None

@router.post("/save")
async def save_match_result(result: MatchResult):
    """Endpoint pour sauvegarder un résultat de match (depuis scraper n8n)"""
    
    # Déterminer outcome
    if result.score_home > result.score_away:
        outcome = 'home'
    elif result.score_away > result.score_home:
        outcome = 'away'
    else:
        outcome = 'draw'
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO match_results 
            (match_id, home_team, away_team, sport, league, score_home, score_away, outcome, is_finished)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (match_id) 
            DO UPDATE SET
                score_home = EXCLUDED.score_home,
                score_away = EXCLUDED.score_away,
                outcome = EXCLUDED.outcome,
                is_finished = TRUE,
                last_updated = NOW()
            RETURNING id
        """, (
            result.match_id,
            result.home_team,
            result.away_team,
            result.sport,
            result.league,
            result.score_home,
            result.score_away,
            outcome
        ))
        
        result_id = cursor.fetchone()[0]
        
        # Analyser prédictions correspondantes
        cursor.execute("""
            SELECT p.*, mr.outcome as actual_outcome
            FROM agent_predictions p
            JOIN match_results mr ON p.match_id = mr.match_id
            WHERE p.match_id = %s
            AND mr.is_finished = TRUE
            AND p.was_correct IS NULL
        """, (result.match_id,))
        
        predictions = cursor.fetchall()
        analyzed = 0
        
        for pred in predictions:
            was_correct = (pred[3] == outcome)  # predicted_outcome == actual_outcome
            
            # Update prediction
            cursor.execute("""
                UPDATE agent_predictions
                SET was_correct = %s
                WHERE id = %s
            """, (was_correct, pred[0]))
            
            # Create feedback
            insights = []
            recommendations = []
            
            if was_correct:
                insights.append(f"✅ Prédiction correcte: {pred[3]}")
            else:
                insights.append(f"❌ Prédiction incorrecte: {pred[3]} → {outcome}")
                recommendations.append("🔍 Analyser facteurs d'erreur")
            
            cursor.execute("""
                INSERT INTO agent_feedback
                (prediction_id, match_id, agent_name, predicted_outcome, actual_outcome, 
                 was_correct, confidence_at_prediction, insights, recommendations)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                pred[0],  # id
                result.match_id,
                pred[2],  # agent_name
                pred[3],  # predicted_outcome
                outcome,
                was_correct,
                pred[5],  # confidence
                insights,
                recommendations
            ))
            
            analyzed += 1
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "result_id": result_id,
            "outcome": outcome,
            "predictions_analyzed": analyzed,
            "message": f"Match {result.home_team} vs {result.away_team}: {result.score_home}-{result.score_away} ({outcome})"
        }
        
    except Exception as e:
        logger.error(f"Erreur sauvegarde résultat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending")
async def get_pending_matches():
    """Liste des matchs analysés sans résultat (pour scraper)"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT DISTINCT
                aa.match_id,
                aa.home_team,
                aa.away_team,
                aa.sport,
                aa.league,
                aa.analyzed_at
            FROM agent_analyses aa
            LEFT JOIN match_results mr ON aa.match_id = mr.match_id
            WHERE mr.id IS NULL
            AND aa.analyzed_at > NOW() - INTERVAL '7 days'
            ORDER BY aa.analyzed_at DESC
            LIMIT 50
        """)
        
        matches = cursor.fetchall()
        conn.close()
        
        return {
            "pending_matches": len(matches),
            "matches": matches
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération matchs pending: {e}")
        raise HTTPException(status_code=500, detail=str(e))
