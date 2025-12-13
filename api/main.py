#!/usr/bin/env python3
"""
MON_PS API - FastAPI Application

Quantitative Sports Trading Platform - Hedge Fund Grade
Chess Engine Paradigm - ADN + Friction Analysis

Auteur: Mon_PS Quant Team
Date: 12 Décembre 2025
"""

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import routers
from api.routers.match_analysis import router as match_analysis_router
from api.routers.team_dna import router as team_dna_router


# ═══════════════════════════════════════════════════════════════════
# APPLICATION
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Mon_PS Quant API",
    description="""
## Quantitative Sports Trading Platform

### Paradigme Chess Engine
- Chaque équipe a un ADN unique (12 profils tactiques)
- La collision de 2 ADN produit une FRICTION
- La friction détermine les marchés exploitables

### Endpoints disponibles
- `/api/v1/match-analysis/{home}/{away}` - Analyse de match
- `/api/v1/match-analysis/batch` - Analyse batch
- `/api/v1/match-analysis/teams` - Liste des équipes
- `/api/v1/match-analysis/profiles/distribution` - Distribution des profils
- `/api/v1/team-dna/{team}` - Profil ADN complet (15 axes)
- `/api/v1/team-dna/{team}/axes` - Les 15 axes uniquement
- `/api/v1/team-dna/{team}/markets` - Marchés exploitables
- `/api/v1/team-dna/compare/{team_a}/{team_b}` - Comparaison ADN

### Profils Tactiques
- OFFENSIVE: POSSESSION, GEGENPRESS, WIDE_ATTACK, DIRECT_ATTACK
- DEFENSIVE: LOW_BLOCK, MID_BLOCK, PARK_THE_BUS
- HYBRID: TRANSITION, ADAPTIVE, BALANCED
- CONTEXTUAL: HOME_DOMINANT, SCORE_DEPENDENT
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════
# ROUTERS
# ═══════════════════════════════════════════════════════════════════

app.include_router(match_analysis_router)
app.include_router(team_dna_router)


# ═══════════════════════════════════════════════════════════════════
# ROOT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "Mon_PS Quant API",
        "version": "2.0.0",
        "paradigm": "Chess Engine - ADN + Friction",
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "match_analysis": "/api/v1/match-analysis/{home}/{away}",
            "batch_analysis": "/api/v1/match-analysis/batch",
            "teams": "/api/v1/match-analysis/teams",
            "team_dna": "/api/v1/team-dna/{team}",
            "team_dna_compare": "/api/v1/team-dna/compare/{team_a}/{team_b}"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mon_ps_api"}


# ═══════════════════════════════════════════════════════════════════
# RUN (for development)
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
