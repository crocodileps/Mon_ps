"""
Tests Hedge Fund Grade - TeamQuantumDnaV3
==========================================

Suite de tests SIGNIFICATIFS qui vérifient vraiment la qualité des données
et la fonctionnalité du model.

Philosophie: Un test qui passe ne doit JAMAIS masquer un bug.
"""

import pytest
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from models.quantum_v3 import TeamQuantumDnaV3
from schemas.enums import Tier, League
from schemas.dna import TacticalDNA, MarketDNA

DATABASE_URL = "postgresql://monps_user:monps_secure_password_2024@localhost:5432/monps_db"


@pytest.fixture(scope="module")
def engine():
    return create_engine(DATABASE_URL)


@pytest.fixture(scope="function")
def session(engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestDataIntegrity:
    """Tests d'intégrité des données - CRITIQUES."""

    def test_total_teams_count(self, session):
        """Vérifie que nous avons exactement 96 équipes (Top 5 Leagues)."""
        count = TeamQuantumDnaV3.count(session)
        assert count == 96, f"Expected 96 teams, got {count}"

    def test_five_leagues_exist(self, session):
        """Vérifie que les 5 leagues sont présentes."""
        leagues = TeamQuantumDnaV3.count_by_league(session)
        expected_leagues = {"Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"}
        actual_leagues = set(leagues.keys())

        missing = expected_leagues - actual_leagues
        extra = actual_leagues - expected_leagues

        assert not missing, f"Missing leagues: {missing}"
        assert not extra, f"Unexpected leagues: {extra}"
        assert len(leagues) == 5, f"Expected 5 leagues, got {len(leagues)}"

    def test_league_team_counts(self, session):
        """Vérifie le nombre d'équipes par league."""
        leagues = TeamQuantumDnaV3.count_by_league(session)

        expected = {
            "Premier League": 20,
            "La Liga": 20,
            "Bundesliga": 18,
            "Serie A": 20,
            "Ligue 1": 18,
        }

        for league, expected_count in expected.items():
            actual = leagues.get(league, 0)
            assert actual == expected_count, \
                f"{league}: expected {expected_count}, got {actual}"

    def test_known_teams_in_correct_league(self, session):
        """Vérifie que les équipes connues sont dans la bonne league."""
        test_cases = [
            ("Liverpool", "Premier League"),
            ("Barcelona", "La Liga"),
            ("Bayern Munich", "Bundesliga"),
            ("Juventus", "Serie A"),
            ("Paris Saint Germain", "Ligue 1"),
            ("Real Madrid", "La Liga"),
            ("Manchester City", "Premier League"),
            ("Inter", "Serie A"),
            ("Borussia Dortmund", "Bundesliga"),
            ("Marseille", "Ligue 1"),
        ]

        for team_name, expected_league in test_cases:
            team = TeamQuantumDnaV3.get_by_name(session, team_name)
            assert team is not None, f"Team {team_name} not found"
            assert team.league == expected_league, \
                f"{team_name}: expected {expected_league}, got {team.league}"

    def test_all_teams_have_league(self, session):
        """Vérifie qu'aucune équipe n'a une league NULL."""
        teams = TeamQuantumDnaV3.get_all(session)
        teams_without_league = [t.team_name for t in teams if not t.league]
        assert len(teams_without_league) == 0, \
            f"Teams without league: {teams_without_league}"


class TestModelFunctionality:
    """Tests de fonctionnalité du model."""

    def test_get_by_name_case_insensitive(self, session):
        """Test recherche case-insensitive."""
        team1 = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        team2 = TeamQuantumDnaV3.get_by_name(session, "liverpool")
        team3 = TeamQuantumDnaV3.get_by_name(session, "LIVERPOOL")

        assert team1 is not None
        assert team2 is not None
        assert team3 is not None
        assert team1.team_id == team2.team_id == team3.team_id

    def test_get_by_name_not_found(self, session):
        """Test équipe non existante."""
        team = TeamQuantumDnaV3.get_by_name(session, "NonExistentTeam12345")
        assert team is None

    def test_get_by_league(self, session):
        """Test filtre par league."""
        pl_teams = TeamQuantumDnaV3.get_by_league(session, "Premier League")

        assert len(pl_teams) == 20
        for team in pl_teams:
            assert team.league == "Premier League"

    def test_get_by_tags(self, session):
        """Test recherche par tags."""
        # Get teams with any GK tag
        gk_teams = TeamQuantumDnaV3.get_by_tags(
            session,
            ["GK_ELITE", "GK_SOLID", "GK_LEAKY"],
            match_all=False
        )
        assert len(gk_teams) > 0

    def test_get_elite_teams(self, session):
        """Test filtre ELITE."""
        elite = TeamQuantumDnaV3.get_elite_teams(session)
        for team in elite:
            assert team.tier == Tier.ELITE.value


class TestComputedProperties:
    """Tests des propriétés calculées."""

    def test_quality_score_range(self, session):
        """Quality score doit être entre 0 et 100."""
        teams = TeamQuantumDnaV3.get_all(session)
        for team in teams:
            assert 0 <= team.quality_score <= 100, \
                f"{team.team_name}: quality_score={team.quality_score} out of range"

    def test_tag_count(self, session):
        """Tag count doit correspondre au nombre réel de tags."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None

        actual_count = len(team.narrative_fingerprint_tags or [])
        assert team.tag_count == actual_count

    def test_gk_status_format(self, session):
        """GK status doit commencer par GK_."""
        teams = TeamQuantumDnaV3.get_all(session)
        for team in teams:
            assert team.gk_status.startswith("GK_"), \
                f"{team.team_name}: gk_status={team.gk_status}"

    def test_is_elite_consistency(self, session):
        """is_elite doit être cohérent avec tier et win_rate."""
        teams = TeamQuantumDnaV3.get_all(session)
        for team in teams:
            if team.is_elite:
                assert team.tier == Tier.ELITE.value, \
                    f"{team.team_name}: is_elite=True but tier={team.tier}"
                assert team.win_rate is not None and team.win_rate > 55, \
                    f"{team.team_name}: is_elite=True but win_rate={team.win_rate}"

    def test_league_enum_valid(self, session):
        """league_enum doit retourner un League enum ou None."""
        teams = TeamQuantumDnaV3.get_all(session)
        for team in teams:
            league_enum = team.league_enum
            if league_enum:
                assert isinstance(league_enum, League), \
                    f"{team.team_name}: league_enum is not a League enum"


class TestOptionDPlusFeatures:
    """Tests des features Option D+ (typed DNA)."""

    def test_tactical_dna_typed_returns_object(self, session):
        """tactical_dna_typed doit retourner un TacticalDNA ou None."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None

        # Si tactical_dna existe, typed doit retourner un objet
        if team.tactical_dna:
            typed = team.tactical_dna_typed
            # Peut être None si parsing échoue, mais ne doit pas lever d'exception
            if typed:
                assert isinstance(typed, TacticalDNA)

    def test_market_dna_typed_returns_object(self, session):
        """market_dna_typed doit retourner un MarketDNA ou None."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None

        if team.market_dna:
            typed = team.market_dna_typed
            if typed:
                assert isinstance(typed, MarketDNA)

    def test_typed_dna_lazy_parsing(self, session):
        """Lazy parsing: accès répété ne doit pas re-parser."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None

        # Premier accès
        typed1 = team.tactical_dna_typed
        # Deuxième accès (doit retourner le même objet)
        typed2 = team.tactical_dna_typed

        if typed1 is not None:
            assert typed1 is typed2, "Lazy parsing broken: different objects returned"


class TestTagHelpers:
    """Tests des helpers de tags."""

    def test_has_tag_true(self, session):
        """has_tag retourne True si tag présent."""
        teams = TeamQuantumDnaV3.get_all(session)
        for team in teams:
            if team.narrative_fingerprint_tags:
                first_tag = team.narrative_fingerprint_tags[0]
                assert team.has_tag(first_tag) is True
                break

    def test_has_tag_false(self, session):
        """has_tag retourne False si tag absent."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None
        assert team.has_tag("NONEXISTENT_TAG_XYZ") is False

    def test_get_tags_by_prefix(self, session):
        """get_tags_by_prefix filtre correctement."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None

        gk_tags = team.get_tags_by_prefix("GK_")
        for tag in gk_tags:
            assert tag.startswith("GK_")


class TestSerialization:
    """Tests de sérialisation."""

    def test_to_dict_keys(self, session):
        """to_dict doit contenir les clés attendues."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None

        data = team.to_dict()
        expected_keys = {
            "team_id", "team_name", "league", "tier",
            "win_rate", "roi", "tags", "quality_score",
            "gk_status", "is_elite"
        }

        missing = expected_keys - set(data.keys())
        assert not missing, f"Missing keys in to_dict: {missing}"

    def test_to_summary_minimal(self, session):
        """to_summary doit être minimal."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None

        summary = team.to_summary()
        assert len(summary) <= 10, "to_summary should be minimal"

    def test_repr_format(self, session):
        """__repr__ doit être informatif."""
        team = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
        assert team is not None

        repr_str = repr(team)
        assert "Liverpool" in repr_str
        assert "TeamQuantumDnaV3" in repr_str
        assert team.league in repr_str  # League should be in repr


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
