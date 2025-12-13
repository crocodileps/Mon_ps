#!/usr/bin/env python3
"""
API Router - Team DNA Profiles V1.0

Endpoints pour accéder aux profils ADN détaillés des équipes.
Basé sur le DNANarrativeGenerator avec 15 axes continus.

Endpoints:
    GET  /api/v1/team-dna/{team}              - Profil ADN complet d'une équipe
    GET  /api/v1/team-dna/{team}/axes         - Uniquement les 15 axes
    GET  /api/v1/team-dna/{team}/markets      - Marchés exploitables
    GET  /api/v1/team-dna/compare/{team_a}/{team_b} - Comparaison de deux ADN
    GET  /api/v1/team-dna/search              - Recherche par caractéristiques

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

from quantum.profilers.dna_narrative_generator import DNANarrativeGenerator


# ═══════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════

class AxeInfo(BaseModel):
    """Single axis information."""
    name: str
    value: int
    level: str


class MarketsInfo(BaseModel):
    """Markets information."""
    markets_for: List[str]
    markets_against: List[str]


class TeamDNAProfile(BaseModel):
    """Full DNA profile for a team."""
    team: str
    identity: str
    summary: str
    axes: dict
    forces: List[dict]
    faiblesses: List[dict]
    markets_for: List[str]
    markets_against: List[str]


class ComparisonResult(BaseModel):
    """Comparison between two teams."""
    team_a: str
    team_b: str
    axes_comparison: dict
    advantages_a: List[str]
    advantages_b: List[str]
    friction_zones: List[str]


class SearchRequest(BaseModel):
    """Search request model."""
    min_values: Optional[dict] = None
    max_values: Optional[dict] = None
    forces_required: Optional[List[str]] = None


# ═══════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════

router = APIRouter(
    prefix="/api/v1/team-dna",
    tags=["Team DNA"],
    responses={404: {"description": "Team not found"}}
)

# Initialize generator (singleton)
_generator = None


def get_generator() -> DNANarrativeGenerator:
    """Get or create the generator singleton."""
    global _generator
    if _generator is None:
        _generator = DNANarrativeGenerator()
    return _generator


# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@router.get("/{team}")
async def get_team_dna(team: str):
    """
    Retourne le profil ADN complet d'une équipe.

    **Paramètres:**
    - `team`: Nom de l'équipe

    **Retourne:**
    - identity: Phrase unique décrivant l'équipe
    - summary: Résumé forces/faiblesses
    - axes: Les 15 axes (0-100)
    - forces: Axes > 65 (points forts)
    - faiblesses: Axes < 35 (points faibles)
    - markets_for: Marchés exploitables POUR l'équipe
    - markets_against: Marchés exploitables CONTRE l'équipe

    **Exemple:**
    ```
    GET /api/v1/team-dna/Liverpool
    ```
    """
    generator = get_generator()

    try:
        profile = generator.generate_profile(team)
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Team not found: {team}"
            )
        return profile
    except KeyError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Team not found: {str(e).strip(chr(39))}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating profile: {str(e)}"
        )


@router.get("/{team}/axes")
async def get_team_axes(team: str):
    """
    Retourne uniquement les 15 axes d'une équipe.

    **Axes disponibles:**
    - pressing_intensity (0-100)
    - possession_control (0-100)
    - verticality (0-100)
    - wide_play (0-100)
    - set_piece_threat (0-100)
    - clinical_finishing (0-100)
    - block_depth (0-100)
    - defensive_compactness (0-100)
    - aerial_resistance (0-100)
    - transition_defense (0-100)
    - goalkeeper_reliability (0-100)
    - diesel_factor (0-100)
    - first_half_intensity (0-100)
    - clutch_factor (0-100)
    - home_dominance (0-100)

    **Exemple:**
    ```
    GET /api/v1/team-dna/Liverpool/axes
    ```
    """
    generator = get_generator()

    try:
        profile = generator.generate_profile(team)
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Team not found: {team}"
            )
        return {
            "team": team,
            "axes": profile.get("axes", {})
        }
    except KeyError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Team not found: {str(e).strip(chr(39))}"
        )


@router.get("/{team}/markets")
async def get_team_markets(team: str):
    """
    Retourne les marchés exploitables pour/contre une équipe.

    **Retourne:**
    - markets_for: Marchés à jouer POUR cette équipe
    - markets_against: Marchés à jouer CONTRE cette équipe

    **Exemple:**
    ```
    GET /api/v1/team-dna/Liverpool/markets
    ```
    """
    generator = get_generator()

    try:
        profile = generator.generate_profile(team)
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Team not found: {team}"
            )
        return {
            "team": team,
            "markets_for": profile.get("markets_for", []),
            "markets_against": profile.get("markets_against", [])
        }
    except KeyError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Team not found: {str(e).strip(chr(39))}"
        )


@router.get("/compare/{team_a}/{team_b}")
async def compare_teams(team_a: str, team_b: str):
    """
    Compare les profils ADN de deux équipes.

    **Paramètres:**
    - `team_a`: Première équipe
    - `team_b`: Deuxième équipe

    **Retourne:**
    - axes_comparison: Différence sur chaque axe
    - advantages_a: Axes où team_a domine (>10 points)
    - advantages_b: Axes où team_b domine (>10 points)
    - friction_zones: Axes où les deux sont forts (conflit potentiel)

    **Exemple:**
    ```
    GET /api/v1/team-dna/compare/Liverpool/Manchester%20City
    ```
    """
    generator = get_generator()

    try:
        profile_a = generator.generate_profile(team_a)
        profile_b = generator.generate_profile(team_b)

        if not profile_a:
            raise HTTPException(status_code=404, detail=f"Team not found: {team_a}")
        if not profile_b:
            raise HTTPException(status_code=404, detail=f"Team not found: {team_b}")

        axes_a = profile_a.get("axes", {})
        axes_b = profile_b.get("axes", {})

        comparison = {}
        advantages_a = []
        advantages_b = []
        friction_zones = []

        for axe in axes_a.keys():
            # Handle dict format {score: X, percentile: Y} or int format
            raw_a = axes_a.get(axe, {"score": 50})
            raw_b = axes_b.get(axe, {"score": 50})
            val_a = int(raw_a.get("score", 50)) if isinstance(raw_a, dict) else raw_a
            val_b = int(raw_b.get("score", 50)) if isinstance(raw_b, dict) else raw_b
            diff = val_a - val_b

            comparison[axe] = {
                "team_a": val_a,
                "team_b": val_b,
                "difference": diff
            }

            # Avantages significatifs (>10 points)
            if diff > 10:
                advantages_a.append(f"{axe}: +{diff}")
            elif diff < -10:
                advantages_b.append(f"{axe}: +{abs(diff)}")

            # Friction zones (deux équipes fortes sur le même axe)
            if val_a >= 60 and val_b >= 60:
                friction_zones.append(f"{axe}: {val_a} vs {val_b}")

        return {
            "team_a": team_a,
            "team_b": team_b,
            "identity_a": profile_a.get("identity", ""),
            "identity_b": profile_b.get("identity", ""),
            "axes_comparison": comparison,
            "advantages_a": advantages_a,
            "advantages_b": advantages_b,
            "friction_zones": friction_zones
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Comparison error: {str(e)}"
        )


@router.get("/search")
async def search_teams(
    min_pressing: Optional[int] = Query(None, ge=0, le=100),
    min_possession: Optional[int] = Query(None, ge=0, le=100),
    min_verticality: Optional[int] = Query(None, ge=0, le=100),
    min_defensive: Optional[int] = Query(None, ge=0, le=100),
    max_pressing: Optional[int] = Query(None, ge=0, le=100),
    max_possession: Optional[int] = Query(None, ge=0, le=100),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Recherche des équipes par caractéristiques ADN.

    **Paramètres:**
    - `min_pressing`: Pressing intensity minimum
    - `min_possession`: Possession control minimum
    - `min_verticality`: Verticality minimum
    - `min_defensive`: Defensive compactness minimum
    - `max_pressing`: Pressing intensity maximum
    - `max_possession`: Possession control maximum
    - `limit`: Nombre max de résultats (default: 20)

    **Exemple:**
    ```
    GET /api/v1/team-dna/search?min_possession=70&limit=10
    ```
    """
    generator = get_generator()

    try:
        results = []

        for team_key in generator.teams.keys():
            profile = generator.generate_profile(team_key)
            if not profile:
                continue

            axes_raw = profile.get("axes", {})

            # Extract values from dict format {score: X, percentile: Y}
            def get_val(key, default=0):
                raw = axes_raw.get(key, {"score": default})
                return int(raw.get("score", default)) if isinstance(raw, dict) else raw

            pressing = get_val("pressing_intensity", 0)
            possession = get_val("possession_control", 0)
            verticality_val = get_val("verticality", 0)
            defensive = get_val("defensive_compactness", 0)

            # Apply filters
            if min_pressing and pressing < min_pressing:
                continue
            if min_possession and possession < min_possession:
                continue
            if min_verticality and verticality_val < min_verticality:
                continue
            if min_defensive and defensive < min_defensive:
                continue
            if max_pressing and pressing > max_pressing:
                continue
            if max_possession and possession > max_possession:
                continue

            results.append({
                "team": profile.get("team", team_key),
                "identity": profile.get("identity", ""),
                "axes_summary": {
                    "pressing_intensity": pressing,
                    "possession_control": possession,
                    "verticality": verticality_val,
                    "defensive_compactness": defensive
                }
            })

            if len(results) >= limit:
                break

        return {
            "count": len(results),
            "filters_applied": {
                "min_pressing": min_pressing,
                "min_possession": min_possession,
                "min_verticality": min_verticality,
                "min_defensive": min_defensive,
                "max_pressing": max_pressing,
                "max_possession": max_possession
            },
            "results": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search error: {str(e)}"
        )


@router.get("/teams")
async def list_all_teams():
    """
    Liste toutes les équipes disponibles avec leur identité.

    **Retourne:**
    - count: Nombre total d'équipes
    - teams: Liste des équipes avec identité

    **Exemple:**
    ```
    GET /api/v1/team-dna/teams
    ```
    """
    generator = get_generator()

    teams_list = []
    for team_key in sorted(generator.teams.keys()):
        profile = generator.generate_profile(team_key)
        if profile:
            teams_list.append({
                "team": profile.get("team", team_key),
                "identity": profile.get("identity", "")
            })

    return {
        "count": len(teams_list),
        "teams": teams_list
    }


# ═══════════════════════════════════════════════════════════════════
# TEST STANDALONE
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    async def test():
        print("Testing Team DNA Router...")

        # Test get_team_dna
        result = await get_team_dna("Liverpool")
        print(f"Liverpool identity: {result['identity']}")
        print(f"Liverpool forces: {len(result['forces'])}")

        # Test axes
        axes = await get_team_axes("Manchester City")
        print(f"Man City axes count: {len(axes['axes'])}")

        # Test markets
        markets = await get_team_markets("Atletico Madrid")
        print(f"Atletico markets_for: {markets['markets_for']}")

        # Test comparison
        comparison = await compare_teams("Liverpool", "Manchester City")
        print(f"Friction zones: {comparison['friction_zones']}")

        # Test search (pass None for Query params, use actual values)
        search = await search_teams(
            min_pressing=None,
            min_possession=60,
            min_verticality=None,
            min_defensive=None,
            max_pressing=None,
            max_possession=None,
            limit=5
        )
        print(f"Teams with possession > 60: {search['count']}")

        # Test list teams
        teams = await list_all_teams()
        print(f"Total teams: {teams['count']}")

        print("All tests passed!")

    asyncio.run(test())
