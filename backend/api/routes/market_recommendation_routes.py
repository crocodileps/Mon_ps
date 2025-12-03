"""
🎯 API Market Recommendation
Endpoint pour obtenir le meilleur marché pour un match
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os

router = APIRouter(prefix="/api/market-recommendation", tags=["Market Recommendation"])

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'postgres'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

class MarketRecommendation(BaseModel):
    source: str
    market: str
    market_group: str
    confidence: float
    win_rate: float
    profit: float
    sample_size: int

class MatchRecommendation(BaseModel):
    match: str
    best_market: str
    best_market_group: str
    confidence: float
    consensus: str
    advice: str
    recommendations: List[MarketRecommendation]

@router.get("/{home_team}/{away_team}", response_model=MatchRecommendation)
async def get_market_recommendation(home_team: str, away_team: str):
    """
    Retourne le meilleur marché pour un match basé sur les profils d'équipe
    
    - **home_team**: Nom de l'équipe à domicile
    - **away_team**: Nom de l'équipe à l'extérieur
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Récupérer profil équipe domicile
    cur.execute("""
        SELECT * FROM team_market_profiles 
        WHERE team_name ILIKE %s AND location = 'home'
    """, (f"%{home_team}%",))
    home_profile = cur.fetchone()
    
    # Récupérer profil équipe extérieur
    cur.execute("""
        SELECT * FROM team_market_profiles 
        WHERE team_name ILIKE %s AND location = 'away'
    """, (f"%{away_team}%",))
    away_profile = cur.fetchone()
    
    cur.close()
    conn.close()
    
    recommendations = []
    
    if home_profile:
        recommendations.append(MarketRecommendation(
            source=f"{home_profile['team_name']} (home)",
            market=home_profile['best_market'],
            market_group=home_profile['best_market_group'],
            confidence=float(home_profile['composite_score']),
            win_rate=float(home_profile['win_rate']),
            profit=float(home_profile['profit']),
            sample_size=home_profile['picks_count']
        ))
    
    if away_profile:
        recommendations.append(MarketRecommendation(
            source=f"{away_profile['team_name']} (away)",
            market=away_profile['best_market'],
            market_group=away_profile['best_market_group'],
            confidence=float(away_profile['composite_score']),
            win_rate=float(away_profile['win_rate']),
            profit=float(away_profile['profit']),
            sample_size=away_profile['picks_count']
        ))
    
    if not recommendations:
        raise HTTPException(status_code=404, detail="No profile found for these teams")
    
    # Trier par confiance
    recommendations = sorted(recommendations, key=lambda x: x.confidence, reverse=True)
    
    # Consensus
    if len(recommendations) >= 2:
        if recommendations[0].market_group == recommendations[1].market_group:
            consensus = "STRONG"
            combined_confidence = (recommendations[0].confidence + recommendations[1].confidence) / 2
            advice = f"✅ FORT: Les deux équipes convergent vers {recommendations[0].market_group}. Confiance élevée."
        else:
            consensus = "DIVERGENCE"
            combined_confidence = recommendations[0].confidence
            advice = f"⚠️ DIVERGENCE: {recommendations[0].source} suggère {recommendations[0].market}, {recommendations[1].source} suggère {recommendations[1].market}."
    else:
        consensus = "SINGLE"
        combined_confidence = recommendations[0].confidence
        advice = f"📊 SINGLE: Basé uniquement sur {recommendations[0].source}. Sample: {recommendations[0].sample_size} picks."
    
    return MatchRecommendation(
        match=f"{home_team} vs {away_team}",
        best_market=recommendations[0].market,
        best_market_group=recommendations[0].market_group,
        confidence=combined_confidence,
        consensus=consensus,
        advice=advice,
        recommendations=recommendations
    )

@router.get("/team/{team_name}")
async def get_team_profile(team_name: str):
    """Retourne le profil complet d'une équipe (home + away)"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT * FROM team_market_profiles 
        WHERE team_name ILIKE %s
        ORDER BY location
    """, (f"%{team_name}%",))
    
    profiles = cur.fetchall()
    cur.close()
    conn.close()
    
    if not profiles:
        raise HTTPException(status_code=404, detail=f"No profile found for {team_name}")
    
    return {
        "team": team_name,
        "profiles": profiles
    }

@router.get("/rules")
async def get_smart_rules():
    """Retourne toutes les règles smart générées"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT * FROM smart_market_rules ORDER BY rule_name")
    rules = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return {"rules": rules}

@router.get("/specialists/{market_group}")
async def get_specialists(market_group: str):
    """
    Retourne les équipes spécialistes d'un type de marché
    
    market_group: btts_yes, btts_no, goals_over, goals_under, home_win, away_win
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT team_name, location, best_market, win_rate, profit, picks_count
        FROM team_market_profiles 
        WHERE best_market_group = %s
          AND win_rate > 0.55
          AND profit > 0
        ORDER BY profit DESC
        LIMIT 20
    """, (market_group,))
    
    specialists = cur.fetchall()
    cur.close()
    conn.close()
    
    return {
        "market_group": market_group,
        "specialists": specialists
    }
