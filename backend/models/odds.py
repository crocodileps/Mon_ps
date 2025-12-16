"""
Odds Models - Mon_PS Hedge Fund Grade

Models for odds data in public schema:
- Odds: Main odds table (150K+ records)
- OddsHistory: Historical odds snapshots
- OddsTotals: Over/Under markets
- OddsBTTS: Both Teams To Score
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    Text, Index, ForeignKey, JSON, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Odds(Base, TimestampMixin):
    """
    Main odds table - stores current odds from all bookmakers.

    Contains 150K+ records across 30+ bookmakers.
    """

    __tablename__ = "odds"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Match identification
    match_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    home_team: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    away_team: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    league: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    commence_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Bookmaker info
    bookmaker: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    bookmaker_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Market type
    market: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Odds values
    home_odds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    draw_odds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    away_odds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # For totals
    line: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    over_odds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    under_odds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Metadata
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Indexes for common queries
    __table_args__ = (
        Index("ix_odds_match_bookmaker", "match_id", "bookmaker", "market"),
        Index("ix_odds_league_date", "league", "commence_time"),
        Index("ix_odds_collected", "collected_at"),
    )


class TrackingCLVPicks(Base, TimestampMixin):
    """
    CLV (Closing Line Value) tracking for picks.

    Contains 3,361+ tracked picks with CLV analysis.
    """

    __tablename__ = "tracking_clv_picks"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Pick identification
    pick_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Match info
    match_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    home_team: Mapped[str] = mapped_column(String(100), nullable=False)
    away_team: Mapped[str] = mapped_column(String(100), nullable=False)
    league: Mapped[str] = mapped_column(String(100), nullable=False)
    match_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Pick details
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    selection: Mapped[str] = mapped_column(String(100), nullable=False)
    bookmaker: Mapped[str] = mapped_column(String(100), nullable=False)

    # Odds tracking
    odds_at_pick: Mapped[float] = mapped_column(Float, nullable=False)
    odds_at_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # CLV calculation
    clv_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hours_before_match: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Result
    is_won: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    stake: Mapped[float] = mapped_column(Float, default=1.0)
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Agent/Strategy info
    agent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    strategy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_clv_league_date", "league", "match_date"),
        Index("ix_clv_agent", "agent", "match_date"),
        Index("ix_clv_market", "market", "match_date"),
    )
