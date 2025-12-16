"""
Unit of Work Pattern - Mon_PS Hedge Fund Grade

Manages transactions across multiple repositories.
Ensures atomic operations.
"""

from typing import Optional
from sqlalchemy.orm import Session

from repositories.odds_repository import OddsRepository, TrackingCLVRepository
from repositories.quantum_repository import (
    TeamDNARepository,
    FrictionMatrixRepository,
    StrategyRepository,
    GoalscorerRepository,
)


class UnitOfWork:
    """
    Unit of Work pattern for transaction management.

    Usage:
        with UnitOfWork(session) as uow:
            team = uow.teams.get_by_name("Arsenal")
            team.total_pnl = 100.0
            uow.commit()

    Provides:
    - Single transaction across all repositories
    - Automatic rollback on exception
    - Explicit commit required
    """

    def __init__(self, session: Session):
        self.session = session
        self._odds: Optional[OddsRepository] = None
        self._tracking: Optional[TrackingCLVRepository] = None
        self._teams: Optional[TeamDNARepository] = None
        self._friction: Optional[FrictionMatrixRepository] = None
        self._strategies: Optional[StrategyRepository] = None
        self._goalscorers: Optional[GoalscorerRepository] = None

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()
        self.session.close()

    # Lazy-loaded repositories
    @property
    def odds(self) -> OddsRepository:
        if self._odds is None:
            self._odds = OddsRepository(self.session)
        return self._odds

    @property
    def tracking(self) -> TrackingCLVRepository:
        if self._tracking is None:
            self._tracking = TrackingCLVRepository(self.session)
        return self._tracking

    @property
    def teams(self) -> TeamDNARepository:
        if self._teams is None:
            self._teams = TeamDNARepository(self.session)
        return self._teams

    @property
    def friction(self) -> FrictionMatrixRepository:
        if self._friction is None:
            self._friction = FrictionMatrixRepository(self.session)
        return self._friction

    @property
    def strategies(self) -> StrategyRepository:
        if self._strategies is None:
            self._strategies = StrategyRepository(self.session)
        return self._strategies

    @property
    def goalscorers(self) -> GoalscorerRepository:
        if self._goalscorers is None:
            self._goalscorers = GoalscorerRepository(self.session)
        return self._goalscorers

    def commit(self) -> None:
        """Commit the current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.session.rollback()

    def flush(self) -> None:
        """Flush pending changes without committing."""
        self.session.flush()
