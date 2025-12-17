"""
Tests for Quantum V3 Models - Hedge Fund Grade Alpha
====================================================

Unit tests for ORM models and repository.
"""

import pytest
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from models.quantum_v3 import TeamQuantumDnaV3
from models.friction_matrix_v3 import QuantumFrictionMatrixV3
from models.strategies_v3 import QuantumStrategiesV3
from repositories.quantum_v3_repository import QuantumV3Repository
from backend.schemas.enums import Tier, GKStatus
from backend.schemas.dna import TacticalDNA, MarketDNA


# Use the actual database for integration tests
DATABASE_URL = "postgresql://monps_user:monps_secure_password_2024@localhost:5432/monps_db"


@pytest.fixture(scope="module")
def engine():
    """Create database engine."""
    return create_engine(DATABASE_URL)


@pytest.fixture(scope="function")
def session(engine) -> Generator[Session, None, None]:
    """Create database session."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def repo(session) -> QuantumV3Repository:
    """Create repository instance."""
    return QuantumV3Repository(session)


class TestTeamQuantumDnaV3:
    """Tests for TeamQuantumDnaV3 model."""
    
    def test_get_by_name(self, session):
        """Test getting team by name."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None
        assert team.team_name == "Liverpool"
        assert team.league == "Premier League"
    
    def test_get_by_name_case_insensitive(self, session):
        """Test case-insensitive name lookup."""
        team = TeamQuantumDnaV3.get_by_name(session, "liverpool")
        assert team is not None
        assert team.team_name == "Liverpool"
    
    def test_get_by_name_not_found(self, session):
        """Test getting non-existent team."""
        team = TeamQuantumDnaV3.get_by_name(session, "NonExistentTeam123")
        assert team is None
    
    def test_has_tag(self, session):
        """Test tag checking."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None
        # Liverpool should have some tags
        assert team.tag_count > 0
        # Test has_tag with actual tag
        if team.narrative_fingerprint_tags:
            first_tag = team.narrative_fingerprint_tags[0]
            assert team.has_tag(first_tag) is True
        assert team.has_tag("NONEXISTENT_TAG_XYZ") is False
    
    def test_computed_properties(self, session):
        """Test computed properties."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None
        
        # quality_score should be a float
        assert isinstance(team.quality_score, float)
        assert 0 <= team.quality_score <= 100
        
        # gk_status should be a string
        assert isinstance(team.gk_status, str)
        assert team.gk_status.startswith("GK_")
    
    def test_to_dict(self, session):
        """Test serialization."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None
        
        data = team.to_dict()
        assert "team_name" in data
        assert "tags" in data
        assert "quality_score" in data
        assert data["team_name"] == "Liverpool"
    
    def test_repr(self, session):
        """Test string representation."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None
        
        repr_str = repr(team)
        assert "Liverpool" in repr_str
        assert "TeamQuantumDnaV3" in repr_str


class TestQuantumV3Repository:
    """Tests for QuantumV3Repository."""
    
    def test_get_team(self, repo):
        """Test get_team method."""
        team = repo.get_team("Liverpool")
        assert team is not None
        assert team.team_name == "Liverpool"
    
    def test_get_all_teams(self, repo):
        """Test get_all_teams method."""
        teams = repo.get_all_teams()
        assert len(teams) == 96  # Expected: 96 teams
    
    def test_get_teams_by_league(self, repo):
        """Test get_teams_by_league method."""
        teams = repo.get_teams_by_league("Premier League")
        assert len(teams) == 20  # Expected: 20 PL teams
        for team in teams:
            assert team.league == "Premier League"
    
    def test_get_elite_teams(self, repo):
        """Test get_elite_teams method."""
        elite = repo.get_elite_teams()
        assert len(elite) > 0
        for team in elite:
            assert team.tier == Tier.ELITE.value
    
    def test_get_teams_count(self, repo):
        """Test get_teams_count method."""
        count = repo.get_teams_count()
        assert count == 96
    
    def test_get_leagues_summary(self, repo):
        """Test get_leagues_summary method."""
        summary = repo.get_leagues_summary()
        assert "Premier League" in summary
        assert summary["Premier League"] == 20
    
    def test_get_stats(self, repo):
        """Test get_stats method."""
        stats = repo.get_stats()
        assert "total_teams" in stats
        assert "leagues" in stats
        assert "avg_tags_per_team" in stats
        assert stats["total_teams"] == 96


class TestDNASchemas:
    """Tests for Pydantic DNA schemas."""
    
    def test_tactical_dna_creation(self):
        """Test TacticalDNA schema creation."""
        dna = TacticalDNA(
            possession_pct=65.5,
            pressing_intensity="HIGH",
            shots_per_game=15.2
        )
        assert dna.possession_pct == 65.5
        assert dna.pressing_intensity == "HIGH"
    
    def test_tactical_dna_validation(self):
        """Test TacticalDNA validation."""
        with pytest.raises(ValueError):
            TacticalDNA(possession_pct=150)  # Invalid: > 100
    
    def test_tactical_dna_to_dict(self):
        """Test TacticalDNA serialization."""
        dna = TacticalDNA(possession_pct=60.0)
        data = dna.to_dict()
        assert "possession_pct" in data
        assert data["possession_pct"] == 60.0
    
    def test_tactical_dna_from_dict(self):
        """Test TacticalDNA deserialization."""
        data = {"possession_pct": 55.0, "shots_per_game": 12.5}
        dna = TacticalDNA.from_dict(data)
        assert dna is not None
        assert dna.possession_pct == 55.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
