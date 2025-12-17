"""
Market DNA Schema - Hedge Fund Grade Alpha
==========================================

Schema for market performance vector.
Describes team's betting market characteristics.
"""

from typing import Optional, Dict, Any
from pydantic import Field

from .base_dna import BaseDNA
from schemas.enums import BestStrategy


class EmpiricalProfile(BaseDNA):
    """Empirical betting profile sub-schema."""
    avg_clv: Optional[float] = None
    avg_edge: Optional[float] = None
    sample_size: Optional[int] = Field(None, ge=0)
    win_rate: Optional[float] = Field(None, ge=0, le=100)
    roi: Optional[float] = None


class MarketDNA(BaseDNA):
    """
    Market DNA vector schema.

    Attributes:
        best_strategy: Optimal betting strategy for this team
        empirical_profile: Historical performance metrics
        volatility_index: Market volatility (0-100)
        liquidity_score: Market liquidity score
        clv_history: Historical CLV performance
    """

    best_strategy: Optional[BestStrategy] = None
    empirical_profile: Optional[EmpiricalProfile] = None
    volatility_index: Optional[float] = Field(None, ge=0, le=100)
    liquidity_score: Optional[int] = Field(None, ge=0, le=10)

    # Performance by market type
    over_under_roi: Optional[float] = None
    btts_roi: Optional[float] = None
    match_result_roi: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["MarketDNA"]:
        """Create from dictionary with nested empirical_profile."""
        if data is None:
            return None
        try:
            # Handle nested empirical_profile
            if 'empirical_profile' in data and isinstance(data['empirical_profile'], dict):
                data = data.copy()
                data['empirical_profile'] = EmpiricalProfile(**data['empirical_profile'])
            return cls(**data)
        except Exception:
            return None
