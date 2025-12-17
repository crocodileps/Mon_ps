"""
QuantumV3Repository - Hedge Fund Grade Alpha
=============================================

Repository pattern for Quantum V3 data access.
Abstracts database queries and provides clean API.

Usage:
    from repositories import QuantumV3Repository
    from core.database import get_db
    
    with get_db() as session:
        repo = QuantumV3Repository(session)
        liverpool = repo.get_team("Liverpool")
        elite_teams = repo.get_elite_teams()
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.quantum_v3 import TeamQuantumDnaV3
from models.friction_matrix_v3 import QuantumFrictionMatrixV3
from models.strategies_v3 import QuantumStrategiesV3
from schemas.enums import Tier, League


class QuantumV3Repository:
    """
    Repository for Quantum V3 database operations.
    
    Provides a clean abstraction over SQLAlchemy queries.
    All database access should go through this repository.
    """
    
    def __init__(self, session: Session):
        """Initialize with database session."""
        self.session = session
    
    # ══════════════════════════════════════════════════════════════════════
    # TEAM QUERIES
    # ══════════════════════════════════════════════════════════════════════
    
    def get_team(self, name: str) -> Optional[TeamQuantumDnaV3]:
        """Get team by name (case-insensitive)."""
        return TeamQuantumDnaV3.get_by_name(self.session, name)
    
    def get_team_by_id(self, team_id: int) -> Optional[TeamQuantumDnaV3]:
        """Get team by ID."""
        return self.session.query(TeamQuantumDnaV3).filter(
            TeamQuantumDnaV3.team_id == team_id
        ).first()
    
    def get_all_teams(self) -> List[TeamQuantumDnaV3]:
        """Get all teams."""
        return TeamQuantumDnaV3.get_all(self.session)
    
    def get_teams_by_league(self, league: str) -> List[TeamQuantumDnaV3]:
        """Get all teams in a specific league."""
        return TeamQuantumDnaV3.get_by_league(self.session, league)
    
    def get_elite_teams(self, league: Optional[str] = None) -> List[TeamQuantumDnaV3]:
        """Get all ELITE tier teams."""
        return TeamQuantumDnaV3.get_elite_teams(self.session, league)
    
    def get_teams_by_tags(
        self, 
        tags: List[str], 
        match_all: bool = True
    ) -> List[TeamQuantumDnaV3]:
        """Get teams by tags."""
        return TeamQuantumDnaV3.get_by_tags(self.session, tags, match_all)
    
    def get_teams_with_gk_status(self, status: str) -> List[TeamQuantumDnaV3]:
        """Get teams with specific GK status (GK_ELITE, GK_LEAKY, etc.)."""
        return self.get_teams_by_tags([status])
    
    def get_teams_count(self) -> int:
        """Get total number of teams."""
        return TeamQuantumDnaV3.count(self.session)
    
    def get_leagues_summary(self) -> Dict[str, int]:
        """Get count of teams per league."""
        results = self.session.query(
            TeamQuantumDnaV3.league,
            func.count(TeamQuantumDnaV3.team_id)
        ).group_by(TeamQuantumDnaV3.league).all()
        
        return {league: count for league, count in results if league}
    
    def get_tier_distribution(self) -> Dict[str, int]:
        """Get count of teams per tier."""
        results = self.session.query(
            TeamQuantumDnaV3.tier,
            func.count(TeamQuantumDnaV3.team_id)
        ).group_by(TeamQuantumDnaV3.tier).all()
        
        return {tier: count for tier, count in results if tier}
    
    # ══════════════════════════════════════════════════════════════════════
    # FRICTION QUERIES
    # ══════════════════════════════════════════════════════════════════════
    
    def get_friction(
        self, 
        team_a: str, 
        team_b: str
    ) -> Optional[QuantumFrictionMatrixV3]:
        """Get friction between two teams."""
        return QuantumFrictionMatrixV3.get_friction(self.session, team_a, team_b)
    
    def get_high_friction_matchups(
        self, 
        threshold: float = 70.0
    ) -> List[QuantumFrictionMatrixV3]:
        """Get matchups with friction above threshold."""
        return self.session.query(QuantumFrictionMatrixV3).filter(
            QuantumFrictionMatrixV3.friction_score >= threshold
        ).order_by(QuantumFrictionMatrixV3.friction_score.desc()).all()
    
    # ══════════════════════════════════════════════════════════════════════
    # STRATEGY QUERIES
    # ══════════════════════════════════════════════════════════════════════
    
    def get_best_strategy(self, team_name: str) -> Optional[QuantumStrategiesV3]:
        """Get best strategy for a team."""
        return QuantumStrategiesV3.get_best_for_team(self.session, team_name)
    
    def get_all_strategies(self, team_name: str) -> List[QuantumStrategiesV3]:
        """Get all strategies for a team."""
        return QuantumStrategiesV3.get_all_for_team(self.session, team_name)
    
    # ══════════════════════════════════════════════════════════════════════
    # AGGREGATE QUERIES
    # ══════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics."""
        total_teams = self.get_teams_count()
        leagues = self.get_leagues_summary()
        tiers = self.get_tier_distribution()
        
        # Average tags per team
        avg_tags = self.session.query(
            func.avg(func.array_length(TeamQuantumDnaV3.narrative_fingerprint_tags, 1))
        ).scalar() or 0
        
        return {
            "total_teams": total_teams,
            "leagues": leagues,
            "tiers": tiers,
            "avg_tags_per_team": round(avg_tags, 2),
        }
