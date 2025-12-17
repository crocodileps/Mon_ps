"""
FrictionMatrixV3 ORM Model - Hedge Fund Grade Alpha
====================================================

Model for quantum.quantum_friction_matrix_v3 table.
Represents friction (interaction) between two teams.
"""

from typing import Optional, List, Any
from sqlalchemy import Integer, String, Float, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, Session

from models.base import Base, TimestampMixin


class QuantumFrictionMatrixV3(Base, TimestampMixin):
    """
    Friction matrix between two teams.

    Friction represents how two teams' DNA profiles interact
    when they play against each other.
    """

    __tablename__ = "quantum_friction_matrix_v3"
    __table_args__ = {"schema": "quantum"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_a_name: Mapped[str] = mapped_column(String(100), index=True)
    team_b_name: Mapped[str] = mapped_column(String(100), index=True)

    # Friction metrics
    friction_score: Mapped[Optional[float]] = mapped_column(Float)
    chaos_potential: Mapped[Optional[float]] = mapped_column(Float)
    goals_expected: Mapped[Optional[float]] = mapped_column(Float)
    btts_probability: Mapped[Optional[float]] = mapped_column(Float)

    # Style clash
    style_clash: Mapped[Optional[float]] = mapped_column(Float)
    tempo_clash: Mapped[Optional[float]] = mapped_column(Float)

    # JSONB details
    friction_details: Mapped[Optional[dict]] = mapped_column(JSONB)

    @classmethod
    def get_friction(
        cls,
        session: Session,
        team_a: str,
        team_b: str
    ) -> Optional["QuantumFrictionMatrixV3"]:
        """Get friction between two teams (order-independent)."""
        return session.query(cls).filter(
            ((cls.team_a_name == team_a) & (cls.team_b_name == team_b)) |
            ((cls.team_a_name == team_b) & (cls.team_b_name == team_a))
        ).first()

    def __repr__(self) -> str:
        score_str = f"{self.friction_score:.2f}" if self.friction_score else "N/A"
        return f"<Friction {self.team_a_name} vs {self.team_b_name}: {score_str}>"
