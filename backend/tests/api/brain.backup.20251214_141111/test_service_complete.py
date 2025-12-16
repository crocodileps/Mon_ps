"""
Tests Service Layer - Business Logic + Edge Cases
Pattern: Unit tests avec mocks + quelques integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import uuid


class TestBrainServiceUnit:
    """Unit tests service layer avec mocks"""

    @patch('api.v1.brain.service.BrainRepository')
    def test_calculate_predictions_success(self, MockRepo, sample_match_data):
        """Test calculate_predictions success path"""
        from api.v1.brain.service import BrainService
        from api.v1.brain.schemas import BrainCalculateRequest

        # Setup mock
        mock_repo = MockRepo.return_value
        mock_repo.calculate_predictions.return_value = {
            "markets": {"btts_yes_prob": {"prediction": {"probability": 0.6}}},
            "calculation_time": 0.15,
            "brain_version": "2.8.0",
            "created_at": datetime.now()
        }

        # Create request
        request = BrainCalculateRequest(
            home_team=sample_match_data["home_team"],
            away_team=sample_match_data["away_team"],
            match_date=sample_match_data["match_date"]
        )

        # Execute
        service = BrainService()
        result = service.calculate_predictions(request)

        # Assertions
        assert result.prediction_id is not None
        assert result.home_team == sample_match_data["home_team"]
        assert result.markets is not None
        assert result.calculation_time == 0.15

    @patch('api.v1.brain.service.BrainRepository')
    def test_calculate_predictions_error_handling(self, MockRepo):
        """Test error handling dans service"""
        from api.v1.brain.service import BrainService
        from api.v1.brain.schemas import BrainCalculateRequest

        # Setup mock qui throw
        mock_repo = MockRepo.return_value
        mock_repo.calculate_predictions.side_effect = RuntimeError("Brain crashed")

        # Create request
        request = BrainCalculateRequest(
            home_team="Test",
            away_team="Test2",
            match_date=(datetime.now() + timedelta(days=1)).date().isoformat()
        )

        # Execute & Assert
        service = BrainService()
        with pytest.raises(Exception):  # Could be RuntimeError or other
            service.calculate_predictions(request)

    @patch('api.v1.brain.service.BrainRepository')
    def test_get_health_status(self, MockRepo):
        """Test health status"""
        from api.v1.brain.service import BrainService

        mock_repo = MockRepo.return_value
        mock_repo.get_health_status.return_value = {
            "status": "operational",
            "version": "2.8.0",
            "markets_count": 93,
            "goalscorer_profiles": 876,
            "uptime_percent": 99.9
        }

        service = BrainService()
        health = service.get_health()

        assert health.status == "operational"
        assert health.version == "2.8.0"

    @patch('api.v1.brain.service.BrainRepository')
    def test_get_supported_markets(self, MockRepo):
        """Test get supported markets"""
        from api.v1.brain.service import BrainService

        mock_repo = MockRepo.return_value
        mock_repo.get_supported_markets.return_value = [
            {"id": "btts", "name": "BTTS", "category": "goals"},
            {"id": "over_under_25", "name": "O/U 2.5", "category": "goals"},
        ]

        service = BrainService()
        markets = service.get_markets_list()

        assert markets.total > 0
        assert len(markets.markets) > 0


class TestBrainServiceValidation:
    """Tests validation business rules"""

    @patch('api.v1.brain.service.BrainRepository')
    def test_validate_team_names(self, MockRepo):
        """Test validation noms équipes"""
        from api.v1.brain.service import BrainService
        from api.v1.brain.schemas import BrainCalculateRequest

        # Test avec noms invalides devrait être catchés par Pydantic
        with pytest.raises(ValueError):
            req = BrainCalculateRequest(
                home_team="",  # Vide
                away_team="Chelsea",
                match_date=(datetime.now() + timedelta(days=1)).date().isoformat()
            )

    @patch('api.v1.brain.service.BrainRepository')
    def test_validate_match_date_future(self, MockRepo):
        """Test validation date future"""
        from api.v1.brain.schemas import BrainCalculateRequest

        # Date passée devrait fail Pydantic validation
        with pytest.raises(ValueError):
            req = BrainCalculateRequest(
                home_team="Liverpool",
                away_team="Chelsea",
                match_date=(datetime.now() - timedelta(days=1)).date().isoformat()
            )
