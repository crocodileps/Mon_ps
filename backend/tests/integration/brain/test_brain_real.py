"""
Integration Tests avec VRAI UnifiedBrain
"""
import pytest
from datetime import datetime, timedelta


class TestBrainRepositoryIntegration:
    """Tests avec vrai UnifiedBrain V2.8.0"""

    def test_calculate_predictions_real(self, brain_repository_real, sample_match_data):
        """Test calculate avec vrai brain"""

        result = brain_repository_real.calculate_predictions(
            home_team=sample_match_data["home_team"],
            away_team=sample_match_data["away_team"],
            match_date=datetime.fromisoformat(sample_match_data["match_date"])
        )

        assert "markets" in result
        assert len(result["markets"]) > 50
        assert result["brain_version"] == "2.8.0"
        assert result["calculation_time"] < 5.0

    def test_health_check_real(self, brain_repository_real):
        """Test health avec vrai brain"""

        health = brain_repository_real.get_health_status()

        assert health["status"] == "operational"
        assert health["markets_count"] >= 90

    def test_get_supported_markets_real(self, brain_repository_real):
        """Test markets list avec vrai brain"""

        markets = brain_repository_real.get_supported_markets()

        assert len(markets) > 50
        assert all("id" in m for m in markets)

    @pytest.mark.parametrize("home,away", [
        ("Liverpool", "Chelsea"),
        ("Manchester City", "Arsenal"),
        ("Real Madrid", "Barcelona"),
    ])
    def test_different_matchups(self, brain_repository_real, home, away):
        """Test différents matchups"""

        result = brain_repository_real.calculate_predictions(
            home_team=home,
            away_team=away,
            match_date=datetime.now() + timedelta(days=2)
        )

        assert len(result["markets"]) > 50
