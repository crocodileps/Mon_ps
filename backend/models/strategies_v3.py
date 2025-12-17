"""
QuantumStrategiesV3 ORM Model - Hedge Fund Grade Alpha
======================================================

Model for quantum.quantum_strategies_v3 table.
Represents betting strategies and their performance per team.
"""

from typing import Optional, List
from sqlalchemy import Integer, String, Float, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, Session

from models.base import Base, TimestampMixin


class QuantumStrategiesV3(Base, TimestampMixin):
    """
    Betting strategies performance per team.
    """

    __tablename__ = "quantum_strategies_v3"
    __table_args__ = {"schema": "quantum"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_name: Mapped[str] = mapped_column(String(100), index=True)
    strategy_name: Mapped[str] = mapped_column(String(50), index=True)

    # Performance metrics
    total_bets: Mapped[Optional[int]] = mapped_column(Integer)
    wins: Mapped[Optional[int]] = mapped_column(Integer)
    losses: Mapped[Optional[int]] = mapped_column(Integer)
    win_rate: Mapped[Optional[float]] = mapped_column(Float)
    roi: Mapped[Optional[float]] = mapped_column(Float)
    pnl: Mapped[Optional[float]] = mapped_column(Float)
    avg_odds: Mapped[Optional[float]] = mapped_column(Float)

    # Flags
    is_best_strategy: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)

    @classmethod
    def get_best_for_team(
        cls,
        session: Session,
        team_name: str
    ) -> Optional["QuantumStrategiesV3"]:
        """Get best strategy for a team."""
        return session.query(cls).filter(
            cls.team_name == team_name,
            cls.is_best_strategy == True
        ).first()

    @classmethod
    def get_all_for_team(
        cls,
        session: Session,
        team_name: str
    ) -> List["QuantumStrategiesV3"]:
        """Get all strategies for a team."""
        return session.query(cls).filter(
            cls.team_name == team_name
        ).order_by(cls.roi.desc()).all()

    def __repr__(self) -> str:
        best = "★" if self.is_best_strategy else ""
        roi_str = f"{self.roi:.1f}%" if self.roi else "N/A"
        return f"<Strategy {self.team_name}:{self.strategy_name} ROI:{roi_str}{best}>"
