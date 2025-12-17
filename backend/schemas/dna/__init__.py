"""
Mon_PS DNA Schemas Package - Hedge Fund Grade Alpha
====================================================

Pydantic schemas for all 31 DNA vectors.
Each schema validates and types the JSONB content.

Usage:
    from backend.schemas.dna import TacticalDNA, MarketDNA

    tactical = TacticalDNA(possession_pct=65.5, pressing_intensity="HIGH")
    print(tactical.possession_pct)  # IDE autocomplete works!
"""

from .base_dna import BaseDNA
from .tactical_dna import TacticalDNA
from .market_dna import MarketDNA, EmpiricalProfile
from .gamestate_dna import GamestateDNA
from .momentum_dna import MomentumDNA
from .goalkeeper_dna import GoalkeeperDNA
from .common_dna import (
    TimingDNA,
    PsycheDNA,
    NemesisDNA,
    RosterDNA,
    LuckDNA,
    ContextDNA,
    HomeAwayDNA,
    FormDNA,
)

__all__ = [
    "BaseDNA",
    "TacticalDNA",
    "MarketDNA",
    "EmpiricalProfile",
    "GamestateDNA",
    "MomentumDNA",
    "GoalkeeperDNA",
    "TimingDNA",
    "PsycheDNA",
    "NemesisDNA",
    "RosterDNA",
    "LuckDNA",
    "ContextDNA",
    "HomeAwayDNA",
    "FormDNA",
]
