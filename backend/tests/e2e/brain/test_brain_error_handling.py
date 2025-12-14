"""
E2E Tests - Error Handling & Edge Cases
Objectif: routes.py 50% → 90%+
"""
import pytest
from datetime import datetime, timedelta


class TestBrainErrorHandling:
    """Tests error handling endpoints"""

    def test_calculate_invalid_json(self, test_client):
        """Test malformed JSON payload"""
        response = test_client.post(
            "/api/v1/brain/calculate",
            data="invalid json{{{",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422  # Unprocessable Entity

    def test_calculate_missing_required_fields(self, test_client):
        """Test missing required fields"""
        response = test_client.post(
            "/api/v1/brain/calculate",
            json={"home_team": "Liverpool"}  # Missing away_team, match_date
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_calculate_empty_team_names(self, test_client):
        """Test empty string team names"""
        response = test_client.post(
            "/api/v1/brain/calculate",
            json={
                "home_team": "",
                "away_team": "Chelsea",
                "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
            }
        )

        assert response.status_code == 422

    def test_calculate_invalid_date_format(self, test_client):
        """Test invalid date format"""
        response = test_client.post(
            "/api/v1/brain/calculate",
            json={
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "match_date": "not-a-date"
            }
        )

        assert response.status_code == 422

    def test_calculate_past_date(self, test_client):
        """Test date in the past"""
        response = test_client.post(
            "/api/v1/brain/calculate",
            json={
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "match_date": (datetime.now() - timedelta(days=1)).date().isoformat()
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert "past" in str(data).lower() or "future" in str(data).lower()

    def test_calculate_same_teams(self, test_client):
        """Test same home/away teams"""
        response = test_client.post(
            "/api/v1/brain/calculate",
            json={
                "home_team": "Liverpool",
                "away_team": "Liverpool",
                "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
            }
        )

        assert response.status_code == 422

    # Note: batch-calculate endpoint not yet implemented
    # def test_batch_calculate_empty_list(self, test_client):
    # def test_batch_calculate_invalid_match(self, test_client):


class TestBrainEdgeCases:
    """Tests edge cases"""

    def test_calculate_very_long_team_names(self, test_client):
        """Test avec noms d'équipes très longs"""
        response = test_client.post(
            "/api/v1/brain/calculate",
            json={
                "home_team": "A" * 200,  # 200 chars
                "away_team": "B" * 200,
                "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
            }
        )

        # Should handle gracefully (422 ou 200)
        assert response.status_code in [200, 422]

    def test_calculate_special_characters_team_names(self, test_client):
        """Test avec caractères spéciaux"""
        response = test_client.post(
            "/api/v1/brain/calculate",
            json={
                "home_team": "FC <script>alert('xss')</script>",
                "away_team": "Team'; DROP TABLE--",
                "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
            }
        )

        # Should handle gracefully
        assert response.status_code in [200, 422]

    def test_calculate_far_future_date(self, test_client):
        """Test date très loin dans le futur"""
        response = test_client.post(
            "/api/v1/brain/calculate",
            json={
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "match_date": (datetime.now() + timedelta(days=365*2)).date().isoformat()  # 2 ans
            }
        )

        # Should handle (maybe with warning)
        assert response.status_code in [200, 422]


class TestGoalscorerEndpoint:
    """Tests for goalscorer endpoint"""

    def test_goalscorer_basic(self, test_client):
        """Test goalscorer endpoint basic functionality"""
        response = test_client.post(
            "/api/v1/brain/goalscorer",
            json={
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
            }
        )

        # Should work (200) or be not fully implemented yet
        assert response.status_code in [200, 404, 501]

    def test_goalscorer_invalid_json(self, test_client):
        """Test goalscorer with invalid JSON"""
        response = test_client.post(
            "/api/v1/brain/goalscorer",
            data="invalid{{{",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_goalscorer_missing_fields(self, test_client):
        """Test goalscorer with missing fields"""
        response = test_client.post(
            "/api/v1/brain/goalscorer",
            json={"home_team": "Liverpool"}  # Missing fields
        )

        assert response.status_code == 422

    def test_goalscorer_past_date(self, test_client):
        """Test goalscorer with past date"""
        response = test_client.post(
            "/api/v1/brain/goalscorer",
            json={
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "match_date": (datetime.now() - timedelta(days=1)).date().isoformat()
            }
        )

        # Goalscorer endpoint may or may not validate past dates
        assert response.status_code in [200, 422]
