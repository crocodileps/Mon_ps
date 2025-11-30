"""
🧠 ALGO V4 API ROUTES
══════════════════════════════════════════════════════════════════════════════

Endpoints pour l'algorithme V4 data-driven.

VERSION: 4.0.0
DATE: 29/11/2025
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from pydantic import BaseModel

from api.services.algo_v4_service import algo_v4, AlgoV4Service

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/algo-v4", tags=["Algo V4"])


# ═══════════════════════════════════════════════════════════════════════════════
# MODÈLES
# ═══════════════════════════════════════════════════════════════════════════════

class AnalyzePickRequest(BaseModel):
    home_team: str
    away_team: str
    market_type: str
    odds: float
    original_score: Optional[int] = 50


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "ALGO V4 - Data-Driven Betting",
        "version": "4.0.0"
    }


@router.get("/recommendations")
async def get_recommendations():
    """
    🏆 Obtenir les paris recommandés avec ALGO V4
    
    Retourne les picks analysés et classés par recommandation:
    - STRONG_BET: Paris fortement recommandés
    - VALUE_BET: Bonne valeur
    - CAUTION: À surveiller
    - AVOID: À éviter
    """
    try:
        recommendations = algo_v4.get_recommended_bets()
        return recommendations
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/today")
async def get_today_analysis():
    """
    📊 Analyse de tous les picks du jour avec ALGO V4
    """
    try:
        analyses = algo_v4.analyze_today_picks()
        return {
            "total": len(analyses),
            "picks": analyses
        }
    except Exception as e:
        logger.error(f"Error analyzing today: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_single_pick(request: AnalyzePickRequest):
    """
    🔍 Analyser un pick spécifique avec toutes les règles ALGO V4
    """
    try:
        analysis = algo_v4.analyze_pick(
            home_team=request.home_team,
            away_team=request.away_team,
            market_type=request.market_type,
            odds=request.odds,
            original_score=request.original_score
        )
        
        return {
            "match": analysis.match_name,
            "market": analysis.market_type,
            "original_market": analysis.original_market,
            "odds": analysis.odds,
            "score": analysis.score,
            "recommendation": analysis.recommendation,
            "confidence": analysis.confidence,
            "reasons": analysis.reasons,
            "warnings": analysis.warnings,
            "team_stats": analysis.team_stats,
            "scorers": analysis.scorers,
            "historical_validation": analysis.historical_validation
        }
    except Exception as e:
        logger.error(f"Error analyzing pick: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate-market/{market_type}")
async def validate_market(market_type: str):
    """
    📈 Valider un type de marché basé sur l'historique
    """
    try:
        validation = algo_v4.validate_market(market_type)
        return {
            "market_type": validation.market_type,
            "is_profitable": validation.is_profitable,
            "profit_units": validation.profit_units,
            "win_rate": validation.win_rate,
            "recommendation": validation.recommendation,
            "reason": validation.reason
        }
    except Exception as e:
        logger.error(f"Error validating market: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team-stats/{team_name}")
async def get_team_stats(team_name: str):
    """
    ⚽ Obtenir les stats d'une équipe
    """
    try:
        stats = algo_v4.get_team_stats(team_name)
        if stats:
            return stats.__dict__
        else:
            raise HTTPException(status_code=404, detail=f"Team not found: {team_name}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scorers/{team_name}")
async def get_team_scorers(team_name: str):
    """
    🔥 Obtenir les buteurs d'une équipe
    """
    try:
        scorers = algo_v4.get_team_scorers(team_name)
        return {
            "team": team_name,
            "scorers": [s.__dict__ for s in scorers]
        }
    except Exception as e:
        logger.error(f"Error getting scorers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profitable-markets")
async def get_profitable_markets():
    """
    💰 Obtenir la liste des marchés rentables vs à éviter
    """
    from api.services.algo_v4_service import PROFITABLE_MARKETS, MARKETS_TO_AVOID
    
    return {
        "profitable": PROFITABLE_MARKETS,
        "avoid": MARKETS_TO_AVOID,
        "note": "Basé sur l'historique de 979 paris résolus"
    }


@router.get("/match-analysis/{home_team}/{away_team}")
async def analyze_match(home_team: str, away_team: str):
    """
    🏟️ Analyse complète d'un match avec toutes les données
    """
    try:
        # Stats équipes
        home_stats = algo_v4.get_team_stats(home_team)
        away_stats = algo_v4.get_team_stats(away_team)
        
        # Buteurs
        home_scorers = algo_v4.get_team_scorers(home_team)
        away_scorers = algo_v4.get_team_scorers(away_team)
        
        # Calculer probabilités
        btts_prob = 0
        over25_prob = 0
        
        if home_stats and away_stats:
            btts_prob = (home_stats.home_btts_rate + away_stats.away_btts_rate) / 2
            over25_prob = (home_stats.home_over25_rate + away_stats.away_over25_rate) / 2
        
        # Recommandations par marché
        markets_analysis = {}
        for market in ["dc_1x", "dc_12", "btts_yes", "btts_no", "over_25", "home"]:
            validation = algo_v4.validate_market(market)
            markets_analysis[market] = {
                "recommendation": validation.recommendation,
                "profit_history": validation.profit_units,
                "win_rate": validation.win_rate
            }
        
        return {
            "match": f"{home_team} vs {away_team}",
            "home_team": {
                "name": home_team,
                "stats": home_stats.__dict__ if home_stats else None,
                "scorers": [s.__dict__ for s in home_scorers]
            },
            "away_team": {
                "name": away_team,
                "stats": away_stats.__dict__ if away_stats else None,
                "scorers": [s.__dict__ for s in away_scorers]
            },
            "probabilities": {
                "btts": round(btts_prob, 1),
                "over_25": round(over25_prob, 1)
            },
            "markets_analysis": markets_analysis,
            "best_bets": [
                m for m, v in markets_analysis.items() 
                if v["recommendation"] in ["STRONG_BET", "VALUE_BET"]
            ]
        }
    except Exception as e:
        logger.error(f"Error analyzing match: {e}")
        raise HTTPException(status_code=500, detail=str(e))
