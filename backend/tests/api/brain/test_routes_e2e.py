"""
E2E Tests API Routes + Concurrency
Pattern: FastAPI TestClient + Real dependencies
"""

import pytest
from concurrent.futures import as_completed
from datetime import datetime, timedelta
import time


class TestBrainRoutesE2E:
    """E2E tests endpoints Brain API"""

    def test_health_endpoint(self, test_client):
        """Test GET /api/v1/brain/health"""

        response = test_client.get("/api/v1/brain/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] in ["operational", "degraded", "error"]
        assert "version" in data
        assert "markets_count" in data

    def test_markets_endpoint(self, test_client):
        """Test GET /api/v1/brain/markets"""

        response = test_client.get("/api/v1/brain/markets")

        assert response.status_code == 200
        data = response.json()

        assert "markets" in data
        assert "total" in data
        assert data["total"] > 50  # Au moins 50 marchés

        # Vérifier structure marchés
        markets = data["markets"]
        assert all("id" in m for m in markets)
        assert all("category" in m for m in markets)

    def test_calculate_endpoint_success(self, test_client, sample_match_data):
        """Test POST /api/v1/brain/calculate success"""

        response = test_client.post(
            "/api/v1/brain/calculate",
            json=sample_match_data
        )

        assert response.status_code == 200
        data = response.json()

        # Vérifier structure response
        assert "prediction_id" in data
        assert "home_team" in data
        assert "away_team" in data
        assert "markets" in data
        assert "calculation_time" in data

        # Vérifier contenu
        assert data["home_team"] == sample_match_data["home_team"]
        assert len(data["markets"]) > 50

    def test_calculate_endpoint_validation_errors(self, test_client):
        """Test validation errors"""

        # Test 1: Teams identiques
        response = test_client.post(
            "/api/v1/brain/calculate",
            json={
                "home_team": "Liverpool",
                "away_team": "Liverpool",  # Même équipe
                "match_date": (datetime.now() + timedelta(days=1)).date().isoformat()
            }
        )

        assert response.status_code == 422  # Validation error

        # Test 2: Date passée
        response = test_client.post(
            "/api/v1/brain/calculate",
            json={
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "match_date": (datetime.now() - timedelta(days=1)).date().isoformat()
            }
        )

        assert response.status_code == 422

    def test_calculate_endpoint_missing_fields(self, test_client):
        """Test champs manquants"""

        response = test_client.post(
            "/api/v1/brain/calculate",
            json={
                "home_team": "Liverpool"
                # Manque away_team et match_date
            }
        )

        assert response.status_code == 422


class TestBrainRoutesConcurrency:
    """Tests concurrency et performance"""

    @pytest.mark.timeout(30)  # Timeout 30s
    def test_concurrent_requests(
        self,
        test_client,
        concurrent_executor,
        sample_teams_pool
    ):
        """Test 10 requêtes concurrentes"""

        def make_request(i):
            """Helper pour requête concurrente"""
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

        # Lancer 10 requêtes concurrentes
        futures = [
            concurrent_executor.submit(make_request, i)
            for i in range(10)
        ]

        results = [f.result() for f in as_completed(futures)]

        # Assertions
        assert all(status == 200 for status, _ in results), \
            "Toutes requêtes doivent réussir"

        # Performance: P95 < 5s
        times = [elapsed for _, elapsed in results]
        p95 = sorted(times)[int(0.95 * len(times))]
        assert p95 < 5.0, f"P95 trop lent: {p95}s"

    @pytest.mark.timeout(60)
    def test_sustained_load(self, test_client, sample_match_data):
        """Test charge soutenue (50 req)"""

        success_count = 0
        error_count = 0
        times = []

        for i in range(50):
            start = time.time()

            try:
                response = test_client.post(
                    "/api/v1/brain/calculate",
                    json=sample_match_data
                )

                if response.status_code == 200:
                    success_count += 1
                else:
                    error_count += 1

                elapsed = time.time() - start
                times.append(elapsed)

            except Exception as e:
                error_count += 1
                print(f"Request {i} failed: {e}")

        # Assertions
        assert success_count >= 45, f"Trop d'erreurs: {error_count}/50"

        # Performance moyenne < 2s
        avg_time = sum(times) / len(times)
        assert avg_time < 2.0, f"Temps moyen trop lent: {avg_time}s"


class TestBrainRoutesPerformance:
    """Tests performance benchmarks"""

    def test_health_endpoint_fast(self, test_client, performance_monitor):
        """Health endpoint doit être < 100ms"""

        performance_monitor.start()
        response = test_client.get("/api/v1/brain/health")
        elapsed = performance_monitor.stop()

        assert response.status_code == 200
        assert elapsed < 0.1, f"Health trop lent: {elapsed}s"

    def test_markets_endpoint_fast(self, test_client, performance_monitor):
        """Markets endpoint doit être < 500ms"""

        performance_monitor.start()
        response = test_client.get("/api/v1/brain/markets")
        elapsed = performance_monitor.stop()

        assert response.status_code == 200
        assert elapsed < 0.5, f"Markets trop lent: {elapsed}s"
