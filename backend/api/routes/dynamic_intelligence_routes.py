"""
🧠 DYNAMIC INTELLIGENCE API ROUTES - V5.1
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from api.services.dynamic_intelligence_service import dynamic_intel

router = APIRouter(prefix="/api/smart", tags=["Smart Intelligence V5"])


class AnalyzeRequest(BaseModel):
    home_team: str
    away_team: str
    market_type: str = "dc_1x"


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "Dynamic Intelligence V5.1 SMART"}


@router.get("/profile/{team_name}")
async def get_team_profile(team_name: str):
    """Profil SMART d'une équipe"""
    profile = dynamic_intel.get_smart_profile(team_name)
    if not profile:
        raise HTTPException(404, f"Équipe non trouvée: {team_name}")
    return profile.__dict__


@router.post("/analyze")
async def analyze_match(request: AnalyzeRequest):
    """Analyse SMART complète d'un match"""
    return dynamic_intel.full_smart_analysis(
        request.home_team,
        request.away_team,
        request.market_type
    )


@router.get("/analyze/{home_team}/{away_team}")
async def analyze_match_get(
    home_team: str, 
    away_team: str,
    market: str = Query("dc_1x", description="Type de marché")
):
    """Analyse SMART d'un match (GET)"""
    return dynamic_intel.full_smart_analysis(home_team, away_team, market)


@router.get("/upcoming")
async def analyze_upcoming(market: Optional[str] = None):
    """Analyse tous les matchs à venir"""
    results = dynamic_intel.analyze_upcoming_matches(market)
    
    # Stats
    valid = [r for r in results if "VALID" in r.get('verdict', '')]
    caution = [r for r in results if "CAUTION" in r.get('verdict', '')]
    danger = [r for r in results if "DANGER" in r.get('verdict', '') and "REJECT" not in r.get('verdict', '')]
    reject = [r for r in results if "REJECT" in r.get('verdict', '')]
    
    return {
        "total": len(results),
        "summary": {
            "valid": len(valid),
            "caution": len(caution),
            "danger": len(danger),
            "reject": len(reject)
        },
        "matches": results
    }


@router.get("/test/everton-newcastle")
async def test_everton():
    """Test: Simulation Everton vs Newcastle (doit être REJECT)"""
    return dynamic_intel.simulate_everton_newcastle()
