"""
E2E Tests Brain API Endpoints
"""
import pytest
from concurrent.futures import as_completed
from datetime import datetime, timedelta
import time


class TestBrainEndpointsE2E:
    """E2E tests endpoints"""

    def test_health_endpoint(self, test_client):
        """Test GET /health"""
        response = test_client.get("/api/v1/brain/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["operational", "degraded", "error"]

    def test_markets_endpoint(self, test_client):
        """Test GET /markets"""
        response = test_client.get("/api/v1/brain/markets")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 50

    def test_calculate_endpoint(self, test_client, sample_match_data):
        """Test POST /calculate"""
        response = test_client.post(
            "/api/v1/brain/calculate",
            json=sample_match_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "prediction_id" in data
        assert len(data["markets"]) > 50

    def test_validation_same_teams(self, test_client):
        """Test validation équipes identiques"""
        response = test_client.post(
            "/api/v1/brain/calculate",
            json={
                "home_team": "Liverpool",
                "away_team": "Liverpool",
                "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
            }
        )

        assert response.status_code == 422


class TestBrainConcurrency:
    """Tests concurrency"""

    @pytest.mark.timeout(30)
    def test_concurrent_requests(self, test_client, concurrent_executor, sample_teams_pool):
        """Test 10 requêtes concurrentes"""

        def make_request(i):
            home = sample_teams_pool[i % len(sample_teams_pool)]
            away = sample_teams_pool[(i + 1) % len(sample_teams_pool)]

            start = time.time()
            response = test_client.post(
                "/api/v1/brain/calculate",
                json={
                    "home_team": home,
                    "away_team": away,
                    "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
                }
            )
            elapsed = time.time() - start

            return response.status_code, elapsed

        futures = [concurrent_executor.submit(make_request, i) for i in range(10)]
        results = [f.result() for f in as_completed(futures)]

        assert all(status == 200 for status, _ in results)

        times = [elapsed for _, elapsed in results]
        p95 = sorted(times)[int(0.95 * len(times))]
        assert p95 < 5.0
