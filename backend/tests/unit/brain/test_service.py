"""
Unit Tests Service Layer
Pattern: Dependency Injection (pas @patch)
"""
import pytest
from datetime import datetime, timedelta


class TestBrainServiceUnit:
    """Unit tests service avec mocks injectés"""

    def test_calculate_predictions_success(self, sample_match_data, mock_unified_brain):
        """Test calculate_predictions avec mock injecté"""
        from api.v1.brain.service import BrainService
        from api.v1.brain.schemas import BrainCalculateRequest
        from api.v1.brain.repository import BrainRepository

        # Dependency injection (pas @patch)
        mock_repo = BrainRepository()
        mock_repo.brain = mock_unified_brain

        service = BrainService(repository=mock_repo)

        request = BrainCalculateRequest(
            home_team=sample_match_data["home_team"],
            away_team=sample_match_data["away_team"],
            match_date=sample_match_data["match_date"]
        )

        # Execute
        result = service.calculate_predictions(request)

        # Assertions
        assert result.prediction_id is not None
        assert result.home_team == sample_match_data["home_team"]

    def test_get_health_status(self, mock_unified_brain):
        """Test health status avec mock"""
        from api.v1.brain.service import BrainService
        from api.v1.brain.repository import BrainRepository

        mock_repo = BrainRepository()
        mock_repo.brain = mock_unified_brain

        service = BrainService(repository=mock_repo)

        health = service.get_health()

        assert health.status == "operational"

    def test_get_markets_list(self, mock_unified_brain):
        """Test markets list avec mock"""
        from api.v1.brain.service import BrainService
        from api.v1.brain.repository import BrainRepository

        mock_repo = BrainRepository()
        mock_repo.brain = mock_unified_brain

        service = BrainService(repository=mock_repo)

        markets = service.get_markets_list()

        assert markets.total >= 0


class TestBrainServiceValidation:
    """Tests validation Pydantic"""

    def test_validate_team_names_empty(self):
        """Test validation noms équipes vides"""
        from api.v1.brain.schemas import BrainCalculateRequest

        with pytest.raises(ValueError):
            BrainCalculateRequest(
                home_team="",
                away_team="Chelsea",
                match_date=(datetime.now() + timedelta(days=1)).date().isoformat()
            )

    def test_validate_same_teams(self):
        """Test validation équipes identiques"""
        from api.v1.brain.schemas import BrainCalculateRequest

        with pytest.raises(ValueError):
            BrainCalculateRequest(
                home_team="Liverpool",
                away_team="Liverpool",
                match_date=(datetime.now() + timedelta(days=1)).date().isoformat()
            )

    def test_validate_past_date(self):
        """Test validation date passée"""
        from api.v1.brain.schemas import BrainCalculateRequest

        with pytest.raises(ValueError):
            BrainCalculateRequest(
                home_team="Liverpool",
                away_team="Chelsea",
                match_date=(datetime.now() - timedelta(days=1)).date().isoformat()
            )
