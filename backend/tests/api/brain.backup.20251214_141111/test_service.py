"""Tests Brain service layer"""

import pytest
from unittest.mock import Mock, patch
from datetime import date, timedelta, datetime
from backend.api.v1.brain.service import BrainService
from backend.api.v1.brain.schemas import BrainCalculateRequest


class TestBrainService:
    """Test BrainService business logic"""

    @patch('backend.api.v1.brain.service.BrainRepository')
    def test_calculate_predictions_success(self, mock_repo):
        """Calculate predictions returns valid response"""
        # Mock repository
        mock_instance = Mock()
        mock_instance.calculate_predictions.return_value = {
            "markets": {"over_under_25": {"over": {"probability": 0.67, "confidence": 0.85}}},
            "calculation_time": 3.2,
            "brain_version": "2.8.0",
            "created_at": datetime.now()
        }
        mock_repo.return_value = mock_instance

        # Test
        service = BrainService()
        future_date = date.today() + timedelta(days=7)
        request = BrainCalculateRequest(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=future_date
        )

        response = service.calculate_predictions(request)

        assert response.home_team == "Liverpool"
        assert response.brain_version == "2.8.0"
        assert response.calculation_time == 3.2
