#!/usr/bin/env python3
"""
API Router - Match Analysis V2

Endpoints pour l'analyse de matchs utilisant le paradigme ADN + Friction.

Endpoints:
    GET  /api/v1/match-analysis/{home}/{away}   - Analyse un match
    POST /api/v1/match-analysis/batch           - Analyse plusieurs matchs

Auteur: Mon_PS Quant Team
Date: 12 Décembre 2025
"""

import sys
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quantum.analyzers.match_analyzer_v2 import MatchAnalyzerV2


# ═══════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════

class MatchRequest(BaseModel):
    """Request model for a single match."""
    home: str
    away: str


class BatchRequest(BaseModel):
    """Request model for batch analysis."""
    matches: List[MatchRequest]
    format: str = "json"


class ProfileInfo(BaseModel):
    """Profile information for a team."""
    team: str
    profile: str
    family: str
    confidence: float
    secondary: Optional[str] = None


class FrictionInfo(BaseModel):
    """Friction analysis result."""
    clash_type: str
    tempo: str
    description: str


class ModifiersInfo(BaseModel):
    """Market modifiers."""
    goals: float
    cards: float
    corners: float


class TimingInfo(BaseModel):
    """Timing information."""
    first_half_bias: float
    late_goal_prob: float


class ConfidenceInfo(BaseModel):
    """Confidence information."""
    overall: float
    tier: str
    factors: dict


# ═══════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════

router = APIRouter(
    prefix="/api/v1/match-analysis",
    tags=["Match Analysis"],
    responses={404: {"description": "Team not found"}}
)

# Initialize analyzer (singleton)
_analyzer = None


def get_analyzer() -> MatchAnalyzerV2:
    """Get or create the analyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = MatchAnalyzerV2()
    return _analyzer


# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@router.get("/{home}/{away}")
async def analyze_match(
    home: str,
    away: str,
    format: str = Query("json", pattern="^(json|full)$", description="Output format")
):
    """
    Analyse un match entre deux équipes.

    **Paramètres:**
    - `home`: Nom de l'équipe à domicile
    - `away`: Nom de l'équipe à l'extérieur
    - `format`: "json" (données brutes) ou "full" (avec narrative et markdown)

    **Retourne:**
    - Profils tactiques des deux équipes
    - Type de friction et tempo attendu
    - Modificateurs de marchés (goals, cards, corners)
    - Recommandations de paris (primary, secondary, avoid)
    - Score de confiance

    **Exemple:**
    ```
    GET /api/v1/match-analysis/Liverpool/Manchester%20City?format=full
    ```
    """
    analyzer = get_analyzer()

    try:
        result = analyzer.analyze(home, away, format=format)
        return result
    except KeyError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Team not found: {str(e).strip(chr(39))}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis error: {str(e)}"
        )


@router.post("/batch")
async def analyze_batch(request: BatchRequest):
    """
    Analyse plusieurs matchs en batch.

    **Body:**
    ```json
    {
        "matches": [
            {"home": "Liverpool", "away": "Manchester City"},
            {"home": "Arsenal", "away": "Chelsea"}
        ],
        "format": "json"
    }
    ```

    **Retourne:**
    - count: Nombre de matchs analysés
    - analyses: Liste des analyses
    - errors: Liste des erreurs (le cas échéant)
    """
    analyzer = get_analyzer()

    results = []
    errors = []

    for match in request.matches:
        try:
            result = analyzer.analyze(match.home, match.away, format=request.format)
            results.append(result)
        except KeyError as e:
            errors.append({
                "match": f"{match.home} vs {match.away}",
                "error": f"Team not found: {str(e).strip(chr(39))}"
            })
        except Exception as e:
            errors.append({
                "match": f"{match.home} vs {match.away}",
                "error": str(e)
            })

    return {
        "count": len(results),
        "analyses": results,
        "errors": errors if errors else None
    }


@router.get("/teams")
async def list_teams():
    """
    Liste toutes les équipes disponibles.

    **Retourne:**
    - teams: Liste des noms d'équipes
    - count: Nombre total d'équipes
    """
    analyzer = get_analyzer()

    teams = sorted(analyzer.teams.keys())
    return {
        "count": len(teams),
        "teams": teams
    }


@router.get("/profiles/distribution")
async def get_profile_distribution():
    """
    Retourne la distribution des profils tactiques.

    **Retourne:**
    - distribution: Dict profil -> count
    - families: Dict famille -> count
    """
    analyzer = get_analyzer()

    profiles = {}
    families = {}

    for team_name, team_data in analyzer.teams.items():
        tp = team_data.get('tactical', {}).get('tactical_profile', {})
        profile = tp.get('profile', 'UNKNOWN')
        family = tp.get('family', 'UNKNOWN')

        profiles[profile] = profiles.get(profile, 0) + 1
        families[family] = families.get(family, 0) + 1

    return {
        "profiles": dict(sorted(profiles.items(), key=lambda x: -x[1])),
        "families": dict(sorted(families.items(), key=lambda x: -x[1]))
    }


# ═══════════════════════════════════════════════════════════════════
# TEST STANDALONE
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    async def test():
        print("Testing Match Analysis Router...")

        # Test analyze_match
        result = await analyze_match("Liverpool", "Manchester City", format="json")
        print(f"Liverpool vs Man City: {result['friction']['clash_type']}")

        # Test batch
        batch = BatchRequest(
            matches=[
                MatchRequest(home="Arsenal", away="Chelsea"),
                MatchRequest(home="Barcelona", away="Real Madrid")
            ],
            format="json"
        )
        batch_result = await analyze_batch(batch)
        print(f"Batch: {batch_result['count']} analyses")

        # Test teams list
        teams = await list_teams()
        print(f"Teams: {teams['count']} available")

        # Test distribution
        dist = await get_profile_distribution()
        print(f"Distribution: {dist['profiles']}")

        print("All tests passed!")

    asyncio.run(test())
