"""
Odds Repository - Mon_PS Hedge Fund Grade

Specialized repository for odds and CLV tracking.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import Session

from repositories.base import BaseRepository
from models.odds import Odds, TrackingCLVPicks


class OddsRepository(BaseRepository[Odds]):
    """Repository for Odds model."""

    def __init__(self, session: Session):
        super().__init__(Odds, session)

    def get_by_match(self, match_id: str) -> List[Odds]:
        """Get all odds for a match."""
        stmt = select(Odds).where(Odds.match_id == match_id)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_by_league(self, league: str, limit: int = 100) -> List[Odds]:
        """Get odds by league."""
        stmt = (
            select(Odds)
            .where(Odds.league == league)
            .order_by(desc(Odds.commence_time))
            .limit(limit)
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())


class TrackingCLVRepository(BaseRepository[TrackingCLVPicks]):
    """Repository for CLV tracking."""

    def __init__(self, session: Session):
        super().__init__(TrackingCLVPicks, session)

    def get_by_agent(self, agent: str, limit: int = 100) -> List[TrackingCLVPicks]:
        """Get picks by agent."""
        stmt = (
            select(TrackingCLVPicks)
            .where(TrackingCLVPicks.agent == agent)
            .order_by(desc(TrackingCLVPicks.match_date))
            .limit(limit)
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_recent_picks(self, days: int = 7, limit: int = 100) -> List[TrackingCLVPicks]:
        """Get recent picks."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(TrackingCLVPicks)
            .where(TrackingCLVPicks.match_date >= cutoff)
            .order_by(desc(TrackingCLVPicks.match_date))
            .limit(limit)
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())
