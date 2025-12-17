"""
Gamestate DNA Schema - Hedge Fund Grade Alpha
==============================================

Schema for gamestate behavior vector.
Describes team behavior based on match situation.
"""

from typing import Optional
from pydantic import Field

from .base_dna import BaseDNA
from schemas.enums import GamestateType


class GamestateDNA(BaseDNA):
    """
    Gamestate DNA vector schema.

    Attributes:
        type: Primary gamestate behavior (COMEBACK_KING, COLLAPSE_LEADER, etc.)
        when_winning_ppg: Points per game when leading
        when_losing_ppg: Points per game when trailing
        when_drawing_ppg: Points per game when level
        comeback_rate: Rate of comebacks after being down
        collapse_rate: Rate of losing lead
        first_goal_win_rate: Win rate when scoring first
    """

    type: Optional[GamestateType] = None

    # Performance by game state
    when_winning_ppg: Optional[float] = Field(None, ge=0, le=3)
    when_losing_ppg: Optional[float] = Field(None, ge=0, le=3)
    when_drawing_ppg: Optional[float] = Field(None, ge=0, le=3)

    # Rates
    comeback_rate: Optional[float] = Field(None, ge=0, le=100)
    collapse_rate: Optional[float] = Field(None, ge=0, le=100)
    first_goal_win_rate: Optional[float] = Field(None, ge=0, le=100)

    # Goals by game state
    goals_when_winning: Optional[float] = None
    goals_when_losing: Optional[float] = None
    goals_conceded_when_winning: Optional[float] = None
    goals_conceded_when_losing: Optional[float] = None
