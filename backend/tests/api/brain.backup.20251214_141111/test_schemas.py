"""Tests Pydantic schemas validation"""

import pytest
from datetime import date, timedelta
from backend.api.v1.brain.schemas import BrainCalculateRequest, DNAContext


class TestBrainCalculateRequest:
    """Test BrainCalculateRequest validation"""

    def test_valid_request(self):
        """Valid request passes"""
        future_date = date.today() + timedelta(days=7)
        request = BrainCalculateRequest(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=future_date
        )
        assert request.home_team == "Liverpool"
        assert request.away_team == "Chelsea"

    def test_past_date_raises_error(self):
        """Past date raises ValidationError"""
        past_date = date.today() - timedelta(days=1)
        with pytest.raises(ValueError, match="must be in the future"):
            BrainCalculateRequest(
                home_team="Liverpool",
                away_team="Chelsea",
                match_date=past_date
            )

    def test_same_teams_raises_error(self):
        """Same home/away raises ValidationError"""
        future_date = date.today() + timedelta(days=7)
        with pytest.raises(ValueError, match="must be different"):
            BrainCalculateRequest(
                home_team="Liverpool",
                away_team="Liverpool",
                match_date=future_date
            )
