"""
Tactical DNA Schema - Hedge Fund Grade Alpha
=============================================

Schema for tactical analysis vector.
Describes team's playing style and tactical approach.
"""

from typing import Optional
from pydantic import Field, field_validator

from .base_dna import BaseDNA
from schemas.enums import TacticalStyle, PressingIntensity, BlockHeight


class TacticalDNA(BaseDNA):
    """
    Tactical DNA vector schema.

    Attributes:
        style: Primary tactical style (GEGENPRESS, POSSESSION, etc.)
        possession_pct: Average possession percentage (0-100)
        pressing_intensity: Pressing intensity level
        block_height: Defensive block height
        passes_per_game: Average passes per game
        xg_per_shot: Expected goals per shot (finishing quality)
        ppda: Passes allowed per defensive action (pressing metric)
    """

    style: Optional[TacticalStyle] = None
    possession_pct: Optional[float] = Field(None, ge=0, le=100)
    pressing_intensity: Optional[PressingIntensity] = None
    block_height: Optional[BlockHeight] = None
    passes_per_game: Optional[float] = Field(None, ge=0)
    xg_per_shot: Optional[float] = Field(None, ge=0, le=1)
    ppda: Optional[float] = Field(None, ge=0)

    # Additional metrics
    shots_per_game: Optional[float] = Field(None, ge=0)
    shots_on_target_pct: Optional[float] = Field(None, ge=0, le=100)
    crosses_per_game: Optional[float] = Field(None, ge=0)
    corners_per_game: Optional[float] = Field(None, ge=0)

    @field_validator('possession_pct', 'shots_on_target_pct')
    @classmethod
    def validate_percentage(cls, v):
        """Ensure percentages are within valid range."""
        if v is not None and not (0 <= v <= 100):
            raise ValueError(f"Percentage must be 0-100, got {v}")
        return v
