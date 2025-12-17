"""
Goalkeeper DNA Schema - Hedge Fund Grade Alpha
==============================================

Schema for goalkeeper performance vector.
"""

from typing import Optional
from pydantic import Field

from .base_dna import BaseDNA
from schemas.enums import GKStatus


class GoalkeeperDNA(BaseDNA):
    """
    Goalkeeper DNA vector schema.

    Attributes:
        status: GK classification (GK_ELITE, GK_SOLID, GK_LEAKY)
        name: Primary goalkeeper name
        save_rate: Save percentage (0-100)
        clean_sheet_rate: Clean sheet percentage (0-100)
        xg_prevented: Expected goals prevented per game
        goals_conceded_per_game: Average goals conceded
    """

    status: Optional[GKStatus] = None
    name: Optional[str] = None

    # Performance metrics
    save_rate: Optional[float] = Field(None, ge=0, le=100)
    clean_sheet_rate: Optional[float] = Field(None, ge=0, le=100)
    xg_prevented: Optional[float] = None
    goals_conceded_per_game: Optional[float] = Field(None, ge=0)

    # Shot stopping
    shots_faced_per_game: Optional[float] = Field(None, ge=0)
    saves_per_game: Optional[float] = Field(None, ge=0)

    # Distribution
    pass_completion: Optional[float] = Field(None, ge=0, le=100)
    long_ball_accuracy: Optional[float] = Field(None, ge=0, le=100)
