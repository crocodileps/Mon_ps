"""Performance test tiers - Progressive validation.

TIER 1: Mocks (fast, CI every commit)
TIER 2: SQLite (medium, nightly)
TIER 3: PostgreSQL (slow, pre-release)
"""

import pytest
import os


@pytest.fixture(scope="session")
def performance_tier():
    """Get current performance tier from environment."""
    return int(os.getenv("PERF_TIER", "1"))


@pytest.fixture
def skip_if_tier_1(performance_tier):
    """Skip test if TIER 1 (mock only)."""
    if performance_tier < 2:
        pytest.skip("Requires PERF_TIER >= 2 (database)")
