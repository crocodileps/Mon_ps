"""Resource Usage Tests - Memory Leak Detection.

Validates:
- Memory stability over time
- No resource leaks
- Response size reasonable

Critical for production: Ensures long-running stability.
"""

import pytest
import gc
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta

from quantum_core.api.main import app


class TestMemoryStability:
    """Tests for memory leaks and resource cleanup."""

    def test_no_memory_leak_after_many_requests(self):
        """Test that memory doesn't grow unbounded."""
        client = TestClient(app)

        gc.collect()
        initial_objects = len(gc.get_objects())

        # 500 requests (reduced from 1000 for speed)
        for i in range(500):
            response = client.get("/api/v1/predictions/brain/health")
            assert response.status_code == 200

            if i % 50 == 0:
                gc.collect()

        gc.collect()
        final_objects = len(gc.get_objects())

        growth = final_objects - initial_objects
        growth_pct = (growth / initial_objects) * 100

        print(f"\nMemory: {initial_objects} → {final_objects} ({growth_pct:.1f}%)")
        # Allow <15% growth
        assert growth_pct < 15, f"Memory leak: {growth_pct:.1f}% growth"

    def test_response_size_reasonable(self):
        """Test that responses aren't excessively large."""
        client = TestClient(app)

        # Health endpoint (should be tiny)
        response = client.get("/api/v1/predictions/brain/health")
        health_size = len(response.content)
        print(f"\nHealth size: {health_size} bytes")
        assert health_size < 2048, "Health response too large"

        # Prediction endpoint
        payload = {
            "match_id": "size_test",
            "competition": "Test",
            "match_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }
        response = client.post("/api/v1/predictions/match", json=payload)
        pred_size = len(response.content)
        print(f"Prediction size: {pred_size} bytes")
        assert pred_size < 100 * 1024, "Prediction response too large"
