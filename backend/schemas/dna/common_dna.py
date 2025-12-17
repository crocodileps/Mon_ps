"""
Common DNA Schemas - Hedge Fund Grade Alpha
============================================

Schemas for simpler DNA vectors that share common patterns.
"""

from typing import Optional, List, Dict, Any
from pydantic import Field

from .base_dna import BaseDNA


class TimingDNA(BaseDNA):
    """Timing of goals DNA vector."""
    diesel_factor: Optional[float] = None  # Late goal tendency
    fast_starter: Optional[float] = None   # Early goal tendency
    goals_0_15: Optional[float] = None
    goals_15_30: Optional[float] = None
    goals_30_45: Optional[float] = None
    goals_45_60: Optional[float] = None
    goals_60_75: Optional[float] = None
    goals_75_90: Optional[float] = None


class PsycheDNA(BaseDNA):
    """Psychological profile DNA vector."""
    killer_instinct: Optional[str] = None  # HIGH, MEDIUM, LOW
    mentality: Optional[str] = None        # PREDATOR, CONSERVATIVE, BALANCED
    big_game_performance: Optional[float] = None
    pressure_handling: Optional[float] = None


class NemesisDNA(BaseDNA):
    """Tactical vulnerabilities DNA vector."""
    weak_against_style: Optional[List[str]] = None
    strong_against_style: Optional[List[str]] = None
    verticality_weakness: Optional[float] = None
    set_piece_vulnerability: Optional[float] = None


class RosterDNA(BaseDNA):
    """Squad composition DNA vector."""
    squad_depth: Optional[int] = Field(None, ge=0)
    avg_age: Optional[float] = Field(None, ge=15, le=45)
    injury_prone: Optional[bool] = None
    mvp_name: Optional[str] = None
    mvp_dependency: Optional[float] = Field(None, ge=0, le=100)


class LuckDNA(BaseDNA):
    """Luck/variance DNA vector."""
    luck_profile: Optional[str] = None  # LUCKY, UNLUCKY, NEUTRAL
    xpoints_delta: Optional[float] = None
    xg_overperformance: Optional[float] = None
    penalty_luck: Optional[float] = None


class ContextDNA(BaseDNA):
    """Historical context DNA vector."""
    xg_for_2024: Optional[float] = None
    xg_against_2024: Optional[float] = None
    xg_diff_2024: Optional[float] = None
    position_2024: Optional[int] = Field(None, ge=1, le=20)
    points_2024: Optional[int] = Field(None, ge=0)


class HomeAwayDNA(BaseDNA):
    """Home/Away performance DNA vector."""
    home_win_rate: Optional[float] = Field(None, ge=0, le=100)
    away_win_rate: Optional[float] = Field(None, ge=0, le=100)
    home_goals_avg: Optional[float] = None
    away_goals_avg: Optional[float] = None
    home_advantage_factor: Optional[float] = None


class FormDNA(BaseDNA):
    """Current form DNA vector."""
    current_ppg: Optional[float] = Field(None, ge=0, le=3)
    current_position: Optional[int] = Field(None, ge=1)
    points_from_last_6: Optional[int] = Field(None, ge=0, le=18)
    trend: Optional[str] = None  # IMPROVING, DECLINING, STABLE
