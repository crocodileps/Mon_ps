"""
🏎️ FERRARI Intelligence API Routes
===================================
Endpoints pour accéder à l'intelligence tactique FERRARI

Endpoints:
- GET /ferrari/health - Santé du service
- GET /ferrari/team/{team_name} - Profil d'une équipe
- GET /ferrari/match/{home}/{away} - Analyse enrichie d'un match
- GET /ferrari/alerts/{team_name}/{market} - Alertes pour un marché
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

# Import du service Ferrari
import sys
sys.path.insert(0, '/app')
from api.services.ferrari_intelligence_service import get_ferrari_intelligence

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ferrari", tags=["Ferrari Intelligence"])


@router.get("/health")
async def health_check():
    """Vérifie la santé du service Ferrari Intelligence"""
    try:
        ferrari = get_ferrari_intelligence()
        # Test rapide
        profile = ferrari.get_team_profile("Barcelona")
        return {
            "status": "healthy",
            "service": "Ferrari Intelligence",
            "version": "1.0.0",
            "test_team": "Barcelona",
            "test_found": profile is not None,
            "test_tags": len(profile.tags) if profile else 0
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/team/{team_name}")
async def get_team_profile(team_name: str):
    """
    Récupère le profil complet d'une équipe
    
    Args:
        team_name: Nom de l'équipe
        
    Returns:
        Profil avec style, tags, alertes, stats
    """
    try:
        ferrari = get_ferrari_intelligence()
        profile = ferrari.get_team_profile(team_name)
        
        if not profile:
            raise HTTPException(status_code=404, detail=f"Équipe '{team_name}' non trouvée")
        
        return {
            "team": profile.name,
            "style": {
                "type": profile.style,
                "score": profile.style_score
            },
            "profiles": {
                "home": profile.home_profile,
                "away": profile.away_profile
            },
            "strength": {
                "home": profile.home_strength,
                "away": profile.away_strength
            },
            "stats": {
                "home_win_rate": profile.home_win_rate,
                "home_draw_rate": profile.home_draw_rate,
                "away_win_rate": profile.away_win_rate,
                "btts_rate": profile.btts_rate,
                "over25_rate": profile.over25_rate,
                "clean_sheet_rate": profile.clean_sheet_rate
            },
            "tags": profile.tags,
            "market_alerts": profile.market_alerts,
            "reliability": {
                "matches_analyzed": profile.matches_analyzed,
                "is_reliable": profile.is_reliable,
                "confidence": profile.confidence
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get_team_profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/match/{home_team}/{away_team}")
async def analyze_match(home_team: str, away_team: str):
    """
    Analyse enrichie d'un match avec intelligence FERRARI
    
    Args:
        home_team: Équipe à domicile
        away_team: Équipe à l'extérieur
        
    Returns:
        Analyse complète avec profils, matchup, pièges, recommandations
    """
    try:
        ferrari = get_ferrari_intelligence()
        enrichment = ferrari.enrich_match_analysis(home_team, away_team)
        
        return {
            "match": f"{home_team} vs {away_team}",
            "home_profile": enrichment['home_profile'],
            "away_profile": enrichment['away_profile'],
            "style_matchup": enrichment['style_matchup'],
            "traps": enrichment['traps'],
            "recommendations": enrichment['recommendations'],
            "confidence_adjustment": enrichment['confidence_adjustment'],
            "ferrari_analyzed": enrichment['ferrari_analyzed']
        }
        
    except Exception as e:
        logger.error(f"Erreur analyze_match: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{team_name}/{market}")
async def get_market_alerts(team_name: str, market: str):
    """
    Récupère les alertes pour une équipe sur un marché spécifique
    
    Args:
        team_name: Nom de l'équipe
        market: Type de marché (btts_yes, over_25, dc_12, home, away, draw...)
        
    Returns:
        Alerte avec niveau, raison, alternative
    """
    try:
        ferrari = get_ferrari_intelligence()
        alert = ferrari.get_market_alerts(team_name, market)
        
        if not alert:
            return {
                "team": team_name,
                "market": market,
                "has_alert": False,
                "message": "Aucune alerte pour ce marché"
            }
        
        return {
            "team": team_name,
            "market": alert.market,
            "has_alert": True,
            "level": alert.level.value,
            "reason": alert.reason,
            "alternative": alert.alternative,
            "value": alert.value,
            "threshold": alert.threshold
        }
        
    except Exception as e:
        logger.error(f"Erreur get_market_alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traps/{home_team}/{away_team}/{market}")
async def check_match_traps(home_team: str, away_team: str, market: str):
    """
    Vérifie les pièges pour un match sur un marché donné
    
    Args:
        home_team: Équipe à domicile
        away_team: Équipe à l'extérieur
        market: Type de marché
        
    Returns:
        Détails des pièges et recommandation
    """
    try:
        ferrari = get_ferrari_intelligence()
        trap_info = ferrari.check_match_traps(home_team, away_team, market)
        
        return {
            "match": f"{home_team} vs {away_team}",
            "market": market,
            "has_trap": trap_info['has_trap'],
            "alerts": trap_info['alerts'],
            "recommendation": trap_info['recommendation'],
            "confidence_penalty": trap_info['confidence_penalty']
        }
        
    except Exception as e:
        logger.error(f"Erreur check_match_traps: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-teams")
async def get_top_teams(limit: int = 20, min_matches: int = 10):
    """
    Récupère les équipes avec le plus de données et tags
    
    Args:
        limit: Nombre d'équipes à retourner
        min_matches: Minimum de matchs analysés
        
    Returns:
        Liste des top équipes avec leurs profils
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import os
        
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'monps_postgres'),
            port=5432,
            database=os.getenv('DB_NAME', 'monps_db'),
            user=os.getenv('DB_USER', 'monps_user'),
            password=os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT team_name, current_style, current_style_score,
                   home_win_rate, away_win_rate,
                   tags, market_alerts,
                   matches_analyzed, is_reliable
            FROM team_intelligence
            WHERE matches_analyzed >= %s
            ORDER BY matches_analyzed DESC, jsonb_array_length(tags) DESC
            LIMIT %s
        """, (min_matches, limit))
        
        teams = []
        for row in cur.fetchall():
            teams.append({
                "team": row['team_name'],
                "style": row['current_style'],
                "style_score": row['current_style_score'],
                "home_win_rate": float(row['home_win_rate']) if row['home_win_rate'] else None,
                "away_win_rate": float(row['away_win_rate']) if row['away_win_rate'] else None,
                "tags": row['tags'] or [],
                "alerts_count": len(row['market_alerts'] or {}),
                "matches": row['matches_analyzed'],
                "reliable": row['is_reliable']
            })
        
        cur.close()
        conn.close()
        
        return {
            "total": len(teams),
            "min_matches": min_matches,
            "teams": teams
        }
        
    except Exception as e:
        logger.error(f"Erreur get_top_teams: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════
# INTÉGRATION PATRON + FERRARI
# ════════════════════════════════════════════════════════════════════════

@router.get("/analyze-enriched/{home_team}/{away_team}")
async def analyze_match_enriched(home_team: str, away_team: str, 
                                  match_id: str = "auto"):
    """
    Analyse complète enrichie PATRON Diamond + FERRARI Intelligence
    
    Combine:
    - Analyse PATRON (Poisson, xG, probabilités)
    - Intelligence FERRARI (profils, pièges, alertes)
    - Scores ajustés et recommandations contextuelles
    """
    try:
        from api.services.patron_ferrari_integration import get_patron_ferrari
        
        pf = get_patron_ferrari()
        result = pf.analyze_match_enriched(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur analyze_match_enriched: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-check/{home_team}/{away_team}/{market}")
async def quick_market_check(home_team: str, away_team: str, market: str):
    """
    Check rapide d'un marché avant de parier
    
    Retourne:
    - safe_to_bet: bool
    - trap_detected: bool
    - recommendation: str
    - context des équipes
    """
    try:
        from api.services.patron_ferrari_integration import get_patron_ferrari
        
        pf = get_patron_ferrari()
        result = pf.get_market_recommendation(home_team, away_team, market)
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur quick_market_check: {e}")
        raise HTTPException(status_code=500, detail=str(e))
