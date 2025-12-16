"""
Quantum Models - Mon_PS Hedge Fund Grade

Models for quantum schema:
- TeamQuantumDNA: 99 teams with 8 DNA vectors
- QuantumFrictionMatrix: 3,403 team pair interactions
- QuantumStrategies: Team-specific strategies
- ChessClassification: 12 tactical profiles
"""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    Text, Index, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, SCHEMA_QUANTUM


class TeamQuantumDNA(Base, TimestampMixin):
    """
    Team Quantum DNA - 8 DNA vectors per team.

    Contains 99 teams with complete DNA fingerprints:
    - market_dna: Performance by market
    - context_dna: Home/Away, vs Top/Middle/Bottom
    - risk_dna: Volatility, drawdown
    - temporal_dna: Timing patterns
    - nemesis_dna: Tactical friction
    - psyche_dna: Psychological profile
    - roster_dna: Squad depth
    - physical_dna: Physical intensity
    - luck_dna: xG overperformance
    """

    __tablename__ = "team_quantum_dna"
    __table_args__ = {"schema": SCHEMA_QUANTUM}

    # Primary key
    team_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Team identification
    team_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    league: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    tier: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # top6, mid, bottom

    # Best strategy for this team
    best_strategy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # DNA Vectors (JSONB for efficient querying)
    market_dna: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    context_dna: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    risk_dna: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    temporal_dna: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    nemesis_dna: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    psyche_dna: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    roster_dna: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    physical_dna: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    luck_dna: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Aggregated metrics
    total_pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    win_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_clv: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    friction_home = relationship("QuantumFrictionMatrix", foreign_keys="QuantumFrictionMatrix.team_home_id", back_populates="team_home")
    friction_away = relationship("QuantumFrictionMatrix", foreign_keys="QuantumFrictionMatrix.team_away_id", back_populates="team_away")
    strategies = relationship("QuantumStrategy", back_populates="team")


class QuantumFrictionMatrix(Base, TimestampMixin):
    """
    Quantum Friction Matrix - DNA collision analysis.

    Contains 3,403 team pair interactions (99 × 98 / 2 + diagonal).
    """

    __tablename__ = "quantum_friction_matrix"
    __table_args__ = (
        Index("ix_friction_teams", "team_home_id", "team_away_id"),
        {"schema": SCHEMA_QUANTUM},
    )

    # Primary key
    friction_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Team references
    team_home_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{SCHEMA_QUANTUM}.team_quantum_dna.team_id"), nullable=False)
    team_away_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{SCHEMA_QUANTUM}.team_quantum_dna.team_id"), nullable=False)

    # Friction analysis
    friction_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100 scale
    chaos_potential: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Predicted scenario
    predicted_scenario: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Values: HIGH_SCORING, DEFENSIVE_BATTLE, BALANCED, CHAOTIC, etc.

    # Recommended markets (JSONB array)
    recommended_markets: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Confidence
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Match predictions
    predicted_btts_prob: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    predicted_over25_prob: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    predicted_total_goals: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    team_home = relationship("TeamQuantumDNA", foreign_keys=[team_home_id], back_populates="friction_home")
    team_away = relationship("TeamQuantumDNA", foreign_keys=[team_away_id], back_populates="friction_away")


class QuantumStrategy(Base, TimestampMixin):
    """
    Quantum Strategy - Team-specific betting strategies.
    """

    __tablename__ = "quantum_strategies"
    __table_args__ = {"schema": SCHEMA_QUANTUM}

    # Primary key
    strategy_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Team reference
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{SCHEMA_QUANTUM}.team_quantum_dna.team_id"), nullable=False)

    # Strategy details
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    market: Mapped[str] = mapped_column(String(50), nullable=False)

    # Parameters
    stake_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    min_confidence: Mapped[float] = mapped_column(Float, default=0.6)
    min_edge: Mapped[float] = mapped_column(Float, default=0.05)

    # Context filters (JSONB)
    context_filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Performance
    roi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship
    team = relationship("TeamQuantumDNA", back_populates="strategies")


class ChessClassification(Base, TimestampMixin):
    """
    Chess Engine Classification - 12 tactical profiles.

    Profiles: TOTAL_FOOTBALL, POSSESSION_STERILE, COUNTER_ATTACK,
    PARKING_BUS, PRESSING_MACHINE, etc.
    """

    __tablename__ = "chess_classifications"
    __table_args__ = {"schema": SCHEMA_QUANTUM}

    # Primary key
    classification_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Team reference
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{SCHEMA_QUANTUM}.team_quantum_dna.team_id"), nullable=False, index=True)

    # Classification
    profile_name: Mapped[str] = mapped_column(String(50), nullable=False)
    # One of 12 profiles

    # Confidence and date
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    # Features used for classification (JSONB)
    features: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Historical flag
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)


class GoalscorerProfile(Base, TimestampMixin):
    """
    Goalscorer Profiles - 876 player profiles.
    """

    __tablename__ = "goalscorer_profiles"
    __table_args__ = {"schema": SCHEMA_QUANTUM}

    # Primary key
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Player info
    player_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    team_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    league: Mapped[str] = mapped_column(String(50), nullable=False)
    position: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Stats
    goals_total: Mapped[int] = mapped_column(Integer, default=0)
    goals_home: Mapped[int] = mapped_column(Integer, default=0)
    goals_away: Mapped[int] = mapped_column(Integer, default=0)
    appearances: Mapped[int] = mapped_column(Integer, default=0)

    # Probabilities
    anytime_prob: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    first_goal_prob: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_goal_prob: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timing patterns (JSONB)
    timing_dna: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Season
    season: Mapped[str] = mapped_column(String(10), default="2024-25")
