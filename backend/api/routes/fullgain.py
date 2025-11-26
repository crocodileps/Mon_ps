"""
FULL GAIN 2.0 - Endpoints API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import os
import sys

# Ajouter le chemin des services
sys.path.insert(0, '/home/Mon_ps/backend/api/services/fullgain')

from prediction_engine_v2 import PredictionEngineV2 as PredictionEngine
import psycopg2
from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/fullgain", tags=["Full Gain 2.0"])

def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=5432,
        database='monps_db',
        user='monps_user',
        password=os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
    )

@router.get("/teams")
async def get_teams(
    min_matches: int = Query(5, description="Minimum de matchs joués"),
    order_by: str = Query("btts_pct", description="Colonne de tri"),
    limit: int = Query(50, description="Nombre max de résultats")
):
    """Liste des équipes avec stats"""
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    allowed_columns = ['btts_pct', 'over_25_pct', 'matches_played', 'last5_form_points', 'avg_goals_scored']
    if order_by not in allowed_columns:
        order_by = 'btts_pct'
    
    cur.execute(f"""
        SELECT 
            team_name, league, matches_played,
            wins, draws, losses,
            btts_pct, over_25_pct, clean_sheet_pct,
            form, current_streak,
            last5_btts_pct, last5_over25_pct, last5_form_points,
            data_quality_score
        FROM team_statistics_live
        WHERE matches_played >= %s
        ORDER BY {order_by} DESC NULLS LAST
        LIMIT %s
    """, (min_matches, limit))
    
    teams = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    return {"count": len(teams), "teams": teams}

@router.get("/teams/{team_name}")
async def get_team_stats(team_name: str):
    """Stats détaillées d'une équipe"""
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT * FROM team_statistics_live WHERE team_name ILIKE %s", (f"%{team_name}%",))
    row = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Équipe non trouvée")
    
    return dict(row)

@router.get("/h2h/{team_a}/{team_b}")
async def get_h2h(team_a: str, team_b: str):
    """Head-to-Head entre deux équipes"""
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    t1, t2 = sorted([team_a, team_b])
    
    cur.execute("""
        SELECT * FROM team_head_to_head 
        WHERE team_a ILIKE %s AND team_b ILIKE %s
    """, (f"%{t1}%", f"%{t2}%"))
    
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if not row:
        return {"message": "Pas de H2H trouvé", "team_a": team_a, "team_b": team_b}
    
    return dict(row)

@router.get("/predict/{home_team}/{away_team}")
async def predict_match(home_team: str, away_team: str):
    """Prédiction BTTS et Over 2.5 pour un match"""
    engine = PredictionEngine()
    
    # Trouver les noms exacts
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT team_name FROM team_statistics_live WHERE team_name ILIKE %s", (f"%{home_team}%",))
    home_row = cur.fetchone()
    
    cur.execute("SELECT team_name FROM team_statistics_live WHERE team_name ILIKE %s", (f"%{away_team}%",))
    away_row = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if not home_row or not away_row:
        raise HTTPException(status_code=404, detail="Équipe non trouvée")
    
    prediction = engine.predict_match(home_row['team_name'], away_row['team_name'])
    return prediction

@router.get("/predictions/btts")
async def get_btts_predictions(
    min_score: float = Query(60, description="Score BTTS minimum"),
    limit: int = Query(20, description="Nombre max")
):
    """Top prédictions BTTS"""
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Récupérer les matchs à venir
    cur.execute("""
        SELECT DISTINCT home_team, away_team, commence_time
        FROM odds_history
        WHERE commence_time > NOW()
        ORDER BY commence_time
        LIMIT 100
    """)
    
    matches = cur.fetchall()
    cur.close()
    conn.close()
    
    engine = PredictionEngine()
    predictions = []
    
    for match in matches:
        try:
            pred = engine.predict_match(match['home_team'], match['away_team'])
            btts_score = pred['btts'].get('score', 0)
            if btts_score and btts_score >= min_score:
                predictions.append({
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'commence_time': match['commence_time'].isoformat() if match['commence_time'] else None,
                    'btts_score': btts_score,
                    'btts_recommendation': pred['btts'].get('recommendation'),
                    'confidence': pred['btts'].get('confidence')
                })
        except:
            pass
    
    predictions.sort(key=lambda x: x['btts_score'], reverse=True)
    
    return {"count": len(predictions[:limit]), "predictions": predictions[:limit]}

@router.get("/stats/summary")
async def get_stats_summary():
    """Résumé des statistiques"""
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            (SELECT COUNT(*) FROM match_results) as total_matches,
            (SELECT COUNT(*) FROM match_results WHERE is_finished) as finished_matches,
            (SELECT COUNT(*) FROM team_statistics_live) as total_teams,
            (SELECT COUNT(*) FROM team_head_to_head) as total_h2h,
            (SELECT MAX(last_match_date) FROM team_statistics_live) as last_update
    """)
    
    stats = dict(cur.fetchone())
    cur.close()
    conn.close()
    
    return stats
