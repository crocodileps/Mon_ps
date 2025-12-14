"""Concurrent Load Tests - Scalability Validation.

Validates:
- Concurrent request handling
- Thread safety
- Resource contention

Critical for production: Ensures API handles multiple users.
"""

import pytest
import asyncio
import httpx
from datetime import datetime, timezone, timedelta


@pytest.fixture
def base_url():
    """Base URL for async HTTP client."""
    return "http://testserver"


class TestConcurrentLoad:
    """Tests for concurrent request handling."""

    @pytest.mark.anyio
    async def test_concurrent_health_checks(self, base_url):
        """Test 10 concurrent health check requests."""
        from quantum_core.api.main import app

        async def health_check(client):
            response = await client.get(f"{base_url}/api/v1/predictions/brain/health")
            return response.status_code

        async with httpx.AsyncClient(app=app, base_url=base_url) as client:
            tasks = [health_check(client) for _ in range(10)]
            results = await asyncio.gather(*tasks)

        successes = sum(1 for status in results if status == 200)
        print(f"\n✅ 10 concurrent: {successes}/10 succeeded")
        assert successes == 10

    @pytest.mark.anyio
    async def test_concurrent_list_requests(self, base_url):
        """Test 30 concurrent list requests."""
        from quantum_core.api.main import app

        async def list_predictions(client):
            response = await client.get(f"{base_url}/api/v1/predictions/")
            return response.status_code

        async with httpx.AsyncClient(app=app, base_url=base_url) as client:
            tasks = [list_predictions(client) for _ in range(30)]
            results = await asyncio.gather(*tasks)

        successes = sum(1 for status in results if status == 200)
        print(f"\n✅ 30 concurrent: {successes}/30 succeeded")
        assert successes >= 28  # Allow 2 failures

    @pytest.mark.anyio
    async def test_concurrent_mixed_requests(self, base_url):
        """Test 50 concurrent mixed requests."""
        from quantum_core.api.main import app

        async def mixed_request(client, i):
            if i % 2 == 0:
                response = await client.get(
                    f"{base_url}/api/v1/predictions/brain/health"
                )
            else:
                response = await client.get(f"{base_url}/api/v1/predictions/")
            return response.status_code

        async with httpx.AsyncClient(
            app=app, base_url=base_url, timeout=30.0
        ) as client:
            tasks = [mixed_request(client, i) for i in range(50)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        successes = sum(1 for r in results if not isinstance(r, Exception) and r == 200)

        print(f"\n✅ 50 concurrent: {successes}/50 succeeded")
        assert successes >= 45  # >90% success
