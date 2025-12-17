"""
Momentum DNA Schema - Hedge Fund Grade Alpha
============================================

Schema for momentum vector.
Describes team's current form and momentum.
"""

from typing import Optional, List
from pydantic import Field

from .base_dna import BaseDNA
from schemas.enums import MomentumLevel


class MomentumDNA(BaseDNA):
    """
    Momentum DNA vector schema.

    Attributes:
        level: Current momentum level (BLAZING, HOT, etc.)
        last_5_results: Last 5 match results (W/D/L)
        last_5_points: Points from last 5 matches
        form_trend: Trend direction (UP, DOWN, STABLE)
        goals_last_5: Goals scored in last 5
        conceded_last_5: Goals conceded in last 5
    """

    level: Optional[MomentumLevel] = None
    last_5_results: Optional[List[str]] = None  # ['W', 'W', 'D', 'L', 'W']
    last_5_points: Optional[int] = Field(None, ge=0, le=15)
    form_trend: Optional[str] = None  # 'UP', 'DOWN', 'STABLE'

    # Goals metrics
    goals_last_5: Optional[int] = Field(None, ge=0)
    conceded_last_5: Optional[int] = Field(None, ge=0)
    clean_sheets_last_5: Optional[int] = Field(None, ge=0, le=5)

    # xG metrics
    xg_last_5: Optional[float] = None
    xga_last_5: Optional[float] = None
