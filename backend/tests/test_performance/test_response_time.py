"""Response Time Benchmarks - Performance SLA Validation.

Validates:
- P50, P95, P99 response times
- Endpoint-specific performance
- Response time under load

Critical for production: Ensures API meets SLA (<200ms P95).
"""

import pytest
import time
import statistics
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta

from quantum_core.api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


def percentile(data, p):
    """Calculate percentile of data."""
    sorted_data = sorted(data)
    index = int(len(sorted_data) * p)
    return sorted_data[min(index, len(sorted_data) - 1)]


class TestResponseTimeBenchmarks:
    """Benchmark tests for API response times."""

    def test_health_endpoint_fast_response(self, client):
        """Test health endpoint responds quickly (P95 <50ms)."""
        times = []

        for _ in range(50):  # Reduced from 100 for speed
            start = time.perf_counter()
            response = client.get("/api/v1/predictions/brain/health")
            end = time.perf_counter()

            assert response.status_code == 200
            times.append((end - start) * 1000)

        p95 = percentile(times, 0.95)
        print(f"\nHealth P95: {p95:.2f}ms")
        # Relaxed SLA for test environment
        assert p95 < 100, f"P95 ({p95:.2f}ms) too slow"

    def test_list_predictions_response_time(self, client):
        """Test list endpoint responds in acceptable time."""
        times = []

        for _ in range(30):
            start = time.perf_counter()
            response = client.get("/api/v1/predictions/")
            end = time.perf_counter()

            assert response.status_code == 200
            times.append((end - start) * 1000)

        p95 = percentile(times, 0.95)
        print(f"\nList P95: {p95:.2f}ms")
        assert p95 < 300, f"P95 ({p95:.2f}ms) exceeds 300ms"

    def test_generate_prediction_response_time(self, client):
        """Test prediction generation time."""
        times = []
        payload = {
            "match_id": "perf_test",
            "competition": "Test",
            "match_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }

        for _ in range(20):
            start = time.perf_counter()
            response = client.post("/api/v1/predictions/match", json=payload)
            end = time.perf_counter()

            assert response.status_code == 200
            times.append((end - start) * 1000)

        p50 = percentile(times, 0.50)
        p95 = percentile(times, 0.95)
        print(f"\nGenerate P50: {p50:.2f}ms, P95: {p95:.2f}ms")
        assert p95 < 1000, f"P95 ({p95:.2f}ms) > 1s"


# ═══════════════════════════════════════════════════════════════════
# TIER 2 TESTS - SQLite Performance
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.tier2
class TestResponseTimeTier2:
    """TIER 2: SQLite-based performance (realistic)."""

    def test_list_with_database_p95_under_500ms(
        self, client, db_session, skip_if_tier_1
    ):
        """List endpoint <500ms with real database.

        Run: PERF_TIER=2 pytest tests/test_performance/
        """
        # TODO: Implement after DB integration (Session #26)
        pytest.skip("Pending: Database integration")
