"""
Quantum Repository - Mon_PS Hedge Fund Grade

Specialized repository for Quantum DNA system.
"""

from typing import List, Optional
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import Session

from repositories.base import BaseRepository
from models.quantum import (
    TeamQuantumDNA,
    QuantumFrictionMatrix,
    QuantumStrategy,
    GoalscorerProfile,
)


class TeamDNARepository(BaseRepository[TeamQuantumDNA]):
    """Repository for Team Quantum DNA."""

    def __init__(self, session: Session):
        super().__init__(TeamQuantumDNA, session)

    def get_by_name(self, team_name: str) -> Optional[TeamQuantumDNA]:
        """Get team by name."""
        stmt = select(TeamQuantumDNA).where(
            TeamQuantumDNA.team_name.ilike(f"%{team_name}%")
        )
        result = self.session.execute(stmt)
        return result.scalars().first()

    def get_by_league(self, league: str) -> List[TeamQuantumDNA]:
        """Get all teams in a league."""
        stmt = select(TeamQuantumDNA).where(
            TeamQuantumDNA.league == league
        ).order_by(TeamQuantumDNA.team_name)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_top_performers(self, limit: int = 10) -> List[TeamQuantumDNA]:
        """Get teams with best total PnL."""
        stmt = (
            select(TeamQuantumDNA)
            .where(TeamQuantumDNA.total_pnl.isnot(None))
            .order_by(desc(TeamQuantumDNA.total_pnl))
            .limit(limit)
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())


class FrictionMatrixRepository(BaseRepository[QuantumFrictionMatrix]):
    """Repository for Quantum Friction Matrix."""

    def __init__(self, session: Session):
        super().__init__(QuantumFrictionMatrix, session)

    def get_friction(self, home_id: int, away_id: int) -> Optional[QuantumFrictionMatrix]:
        """Get friction between two teams."""
        stmt = select(QuantumFrictionMatrix).where(
            and_(
                QuantumFrictionMatrix.team_home_id == home_id,
                QuantumFrictionMatrix.team_away_id == away_id
            )
        )
        result = self.session.execute(stmt)
        return result.scalars().first()


class StrategyRepository(BaseRepository[QuantumStrategy]):
    """Repository for Quantum Strategies."""

    def __init__(self, session: Session):
        super().__init__(QuantumStrategy, session)

    def get_team_strategies(self, team_id: int) -> List[QuantumStrategy]:
        """Get all strategies for a team."""
        stmt = (
            select(QuantumStrategy)
            .where(QuantumStrategy.team_id == team_id)
            .order_by(desc(QuantumStrategy.roi))
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())


class GoalscorerRepository(BaseRepository[GoalscorerProfile]):
    """Repository for Goalscorer Profiles."""

    def __init__(self, session: Session):
        super().__init__(GoalscorerProfile, session)

    def get_by_team(self, team_name: str) -> List[GoalscorerProfile]:
        """Get all goalscorers for a team."""
        stmt = (
            select(GoalscorerProfile)
            .where(GoalscorerProfile.team_name.ilike(f"%{team_name}%"))
            .order_by(desc(GoalscorerProfile.goals_total))
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_top_scorers(self, league: str = None, limit: int = 20) -> List[GoalscorerProfile]:
        """Get top goalscorers."""
        stmt = select(GoalscorerProfile)
        if league:
            stmt = stmt.where(GoalscorerProfile.league == league)
        stmt = stmt.order_by(desc(GoalscorerProfile.goals_total)).limit(limit)
        result = self.session.execute(stmt)
        return list(result.scalars().all())
