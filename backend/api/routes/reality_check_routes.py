"""
🧠 REALITY CHECK API ROUTES V1.0
================================

Endpoints pour analyser les matchs avec le module Reality Check.
Fournit des warnings qualitatifs et des ajustements de confiance.

Endpoints:
- GET  /api/reality/health              - Status du service
- GET  /api/reality/analyze/{home}/{away} - Analyse complète d'un match
- POST /api/reality/batch               - Analyse multiple matchs
- GET  /api/reality/team/{team_name}    - Profil Reality d'une équipe
- GET  /api/reality/tactical/{style_a}/{style_b} - Matchup tactique
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import sys

# Path pour imports
sys.path.insert(0, '/app')

# Import Reality Check
try:
    from agents.reality_check import RealityChecker
    from agents.reality_check.data_service import RealityDataService
    _checker = RealityChecker()
    _data_service = RealityDataService()
    REALITY_CHECK_AVAILABLE = True
except ImportError as e:
    _checker = None
    _data_service = None
    REALITY_CHECK_AVAILABLE = False
    print(f"⚠️ Reality Check not available: {e}")

router = APIRouter(prefix="/api/reality", tags=["Reality Check"])


# ═══════════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class BatchMatchRequest(BaseModel):
    matches: List[Dict[str, str]]  # [{"home": "Team A", "away": "Team B"}, ...]


class RealityAnalysisResponse(BaseModel):
    home_team: str
    away_team: str
    reality_score: int
    convergence: str
    home_tier: str
    away_tier: str
    tier_gap: int
    warnings: List[str]
    adjustments: Dict[str, float]
    scores: Dict[str, int]
    recommendation: str


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health():
    """Status du service Reality Check"""
    return {
        "status": "healthy" if REALITY_CHECK_AVAILABLE else "unavailable",
        "service": "Reality Check V1.0",
        "enabled": REALITY_CHECK_AVAILABLE
    }


@router.get("/analyze/{home_team}/{away_team}")
async def analyze_match(
    home_team: str, 
    away_team: str,
    referee: Optional[str] = Query(None, description="Nom de l'arbitre (optionnel)")
):
    """
    🧠 Analyse Reality Check complète d'un match.
    
    Retourne:
    - Reality Score (0-100)
    - Convergence level (full/partial/divergence/strong_divergence)
    - Tiers des équipes
    - Warnings détectés
    - Ajustements recommandés
    """
    if not REALITY_CHECK_AVAILABLE:
        raise HTTPException(503, "Reality Check service not available")
    
    try:
        result = _checker.analyze_match(home_team, away_team, referee=referee)
        
        return {
            "home_team": result.home_team,
            "away_team": result.away_team,
            "reality_score": result.reality_score,
            "convergence": result.convergence,
            "home_tier": result.home_tier,
            "away_tier": result.away_tier,
            "tier_gap": result.tier_gap,
            "warnings": result.warnings,
            "warnings_count": len(result.warnings),
            "adjustments": result.adjustments,
            "scores": {
                "class": result.class_score,
                "tactical": result.tactical_score,
                "momentum": result.momentum_score,
                "context": result.context_score
            },
            "recommendation": result.recommendation
        }
    except Exception as e:
        raise HTTPException(500, f"Analysis error: {str(e)}")


@router.post("/batch")
async def analyze_batch(request: BatchMatchRequest):
    """
    🧠 Analyse Reality Check pour plusieurs matchs.
    
    Body: {"matches": [{"home": "Team A", "away": "Team B"}, ...]}
    """
    if not REALITY_CHECK_AVAILABLE:
        raise HTTPException(503, "Reality Check service not available")
    
    results = []
    for match in request.matches:
        home = match.get("home", "")
        away = match.get("away", "")
        
        if not home or not away:
            results.append({"error": "Missing home or away team"})
            continue
        
        try:
            result = _checker.analyze_match(home, away)
            results.append({
                "home_team": home,
                "away_team": away,
                "reality_score": result.reality_score,
                "convergence": result.convergence,
                "tier_gap": result.tier_gap,
                "warnings_count": len(result.warnings),
                "top_warning": result.warnings[0] if result.warnings else None
            })
        except Exception as e:
            results.append({
                "home_team": home,
                "away_team": away,
                "error": str(e)
            })
    
    return {
        "total": len(results),
        "results": results
    }


@router.get("/team/{team_name}")
async def get_team_profile(team_name: str):
    """
    📊 Profil Reality d'une équipe.
    
    Retourne: Tier, Power Index, Style, Big Game Factor, etc.
    """
    if not REALITY_CHECK_AVAILABLE:
        raise HTTPException(503, "Reality Check service not available")
    
    try:
        team_class = _data_service.get_team_class(team_name)
        team_momentum = _data_service.get_team_momentum(team_name)
        
        if not team_class:
            raise HTTPException(404, f"Team not found: {team_name}")
        
        return {
            "team_name": team_class.get("team_name", team_name),
            "tier": team_class.get("tier", "C"),
            "league": team_class.get("league"),
            "power_index": team_class.get("calculated_power_index"),
            "historical_strength": team_class.get("historical_strength"),
            "playing_style": team_class.get("playing_style"),
            "big_game_factor": team_class.get("big_game_factor"),
            "home_fortress_factor": team_class.get("home_fortress_factor"),
            "away_weakness_factor": team_class.get("away_weakness_factor"),
            "coach": team_class.get("coach"),
            "star_players": team_class.get("star_players"),
            "momentum": {
                "status": team_momentum.get("momentum_status") if team_momentum else "unknown",
                "score": team_momentum.get("momentum_score") if team_momentum else 50,
                "last_5": team_momentum.get("last_5_results") if team_momentum else None
            } if team_momentum else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


@router.get("/tactical/{style_a}/{style_b}")
async def get_tactical_matchup(style_a: str, style_b: str):
    """
    🧩 Analyse d'un matchup tactique.
    
    Styles disponibles: possession, pressing, counter, low_block_counter, 
    defensive, attacking, balanced, direct, etc.
    """
    if not REALITY_CHECK_AVAILABLE:
        raise HTTPException(503, "Reality Check service not available")
    
    try:
        matchup = _data_service.get_tactical_matchup(style_a, style_b)
        
        if not matchup:
            # Essayer l'inverse
            matchup = _data_service.get_tactical_matchup(style_b, style_a)
            if matchup:
                # Inverser les résultats
                matchup["style_a"], matchup["style_b"] = style_b, style_a
                matchup["win_rate_a"], matchup["win_rate_b"] = matchup["win_rate_b"], matchup["win_rate_a"]
        
        if not matchup:
            return {
                "style_a": style_a,
                "style_b": style_b,
                "found": False,
                "message": f"No tactical data for {style_a} vs {style_b}"
            }
        
        return {
            "style_a": matchup.get("style_a"),
            "style_b": matchup.get("style_b"),
            "found": True,
            "win_rate_a": matchup.get("win_rate_a"),
            "draw_rate": matchup.get("draw_rate"),
            "win_rate_b": matchup.get("win_rate_b"),
            "upset_probability": matchup.get("upset_probability"),
            "btts_probability": matchup.get("btts_probability"),
            "over_25_probability": matchup.get("over_25_probability"),
            "notes": matchup.get("notes")
        }
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


@router.get("/referee/{referee_name}")
async def get_referee_profile(referee_name: str):
    """
    👨‍⚖️ Profil d'un arbitre.
    """
    if not REALITY_CHECK_AVAILABLE:
        raise HTTPException(503, "Reality Check service not available")
    
    try:
        ref = _data_service.get_referee_profile(referee_name)
        
        if not ref:
            raise HTTPException(404, f"Referee not found: {referee_name}")
        
        return {
            "referee_name": ref.get("referee_name"),
            "league": ref.get("league"),
            "strictness_level": ref.get("strictness_level"),
            "avg_yellow_cards": ref.get("avg_yellow_cards_per_game"),
            "penalty_frequency": ref.get("penalty_frequency"),
            "under_over_tendency": ref.get("under_over_tendency"),
            "avg_goals_per_game": ref.get("avg_goals_per_game"),
            "home_bias_factor": ref.get("home_bias_factor"),
            "matches_officiated": ref.get("matches_officiated")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


@router.get("/styles")
async def get_available_styles():
    """
    📋 Liste des styles tactiques disponibles.
    """
    return {
        "styles": [
            "possession",
            "pressing", 
            "counter",
            "low_block_counter",
            "defensive",
            "attacking",
            "balanced",
            "direct",
            "physical",
            "technical"
        ],
        "description": "Use these styles in /tactical/{style_a}/{style_b}"
    }


@router.get("/tiers")
async def get_tier_info():
    """
    📊 Information sur les Tiers.
    """
    return {
        "tiers": {
            "S": {"strength": 95, "description": "Elite mondiale (Man City, Real Madrid, Bayern, PSG)"},
            "A": {"strength": 82, "description": "Top européen (Liverpool, Arsenal, Barcelona, Inter...)"},
            "B": {"strength": 68, "description": "Bon niveau (Tottenham, Roma, Monaco...)"},
            "C": {"strength": 55, "description": "Milieu de tableau (Brighton, Sevilla, Freiburg...)"},
            "D": {"strength": 40, "description": "Bas de tableau (Southampton, Lecce, Bochum...)"}
        },
        "correction_factors": {
            "S": 0.80,
            "A": 0.85,
            "B": 0.90,
            "C": 0.95,
            "D": 1.00
        }
    }
