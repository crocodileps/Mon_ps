"""Integration tests for SmartCache in BrainRepository."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta


class TestBrainRepositoryCacheIntegration:
    """Test SmartCache integration in BrainRepository.calculate_predictions()."""

    @pytest.fixture
    def mock_brain(self):
        """Mock UnifiedBrain with realistic prediction."""
        brain = MagicMock()

        # Create mock prediction object with attributes
        mock_prediction = MagicMock()
        mock_prediction.home_win_prob = 0.45
        mock_prediction.draw_prob = 0.30
        mock_prediction.away_win_prob = 0.25
        mock_prediction.over_25 = 0.65
        mock_prediction.btts = 0.55

        brain.analyze_match.return_value = mock_prediction
        return brain

    @pytest.fixture
    def repository(self, mock_brain):
        """BrainRepository with mocked brain."""
        from api.v1.brain.repository import BrainRepository

        repo = BrainRepository(brain_client=mock_brain)
        return repo

    def test_cache_miss_computes_and_caches(
        self, repository, mock_brain, monkeypatch
    ):
        """Test cache MISS → compute + cache + return.

        Flow:
        1. Cache miss (empty cache)
        2. Compute prediction (call brain)
        3. Store in cache
        4. Return result
        """
        # Arrange: Mock cache (miss)
        mock_cache = MagicMock()
        mock_cache.get.return_value = (None, False)  # Cache miss
        monkeypatch.setattr("api.v1.brain.repository.smart_cache", mock_cache)

        # Act
        result = repository.calculate_predictions(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=datetime.now(timezone.utc) + timedelta(days=7)
        )

        # Assert
        assert "markets" in result
        assert result["brain_version"] == "2.8.0"
        assert isinstance(result["created_at"], str)  # ISO format

        # Verify brain called
        mock_brain.analyze_match.assert_called_once_with(
            home="Liverpool",
            away="Chelsea"
        )

        # Verify cache operations
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()

        # Verify cache.set() arguments
        cache_set_call = mock_cache.set.call_args
        assert cache_set_call[1]["ttl"] == 3600  # PRE_MATCH (7 days ahead)

    def test_cache_hit_fresh_no_compute(
        self, repository, mock_brain, monkeypatch
    ):
        """Test cache HIT fresh → NO compute.

        Flow:
        1. Cache hit (fresh value)
        2. Return cached immediately
        3. NO brain computation
        4. NO cache write
        """
        # Arrange: Mock cache (hit fresh)
        cached_data = {
            "markets": {"over_25": {"prediction": {"probability": 0.65}}},
            "calculation_time": 0.15,
            "brain_version": "2.8.0",
            "created_at": "2025-12-14T10:00:00Z"
        }
        mock_cache = MagicMock()
        mock_cache.get.return_value = (cached_data, False)  # Fresh
        monkeypatch.setattr("api.v1.brain.repository.smart_cache", mock_cache)

        # Act
        result = repository.calculate_predictions(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=datetime.now(timezone.utc) + timedelta(days=7)
        )

        # Assert
        assert result == cached_data

        # Verify NO brain computation
        mock_brain.analyze_match.assert_not_called()

        # Verify NO cache write (already cached)
        mock_cache.set.assert_not_called()

    def test_cache_hit_stale_returns_immediately(
        self, repository, mock_brain, monkeypatch
    ):
        """Test cache HIT stale (X-Fetch) → return stale immediately.

        Flow:
        1. Cache hit (stale value, X-Fetch triggered)
        2. Return stale value immediately (zero latency)
        3. NO brain computation (background refresh)
        4. NO cache write (X-Fetch handles)
        """
        # Arrange: Mock cache (hit stale)
        stale_data = {
            "markets": {"over_25": {"prediction": {"probability": 0.65}}},
            "calculation_time": 0.15,
            "brain_version": "2.8.0",
            "created_at": "2025-12-14T09:00:00Z"  # 1h ago
        }
        mock_cache = MagicMock()
        mock_cache.get.return_value = (stale_data, True)  # Stale
        monkeypatch.setattr("api.v1.brain.repository.smart_cache", mock_cache)

        # Act
        result = repository.calculate_predictions(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=datetime.now(timezone.utc) + timedelta(days=7)
        )

        # Assert
        assert result == stale_data  # Stale returned immediately

        # Verify NO brain computation (X-Fetch probabilistic refresh)
        mock_brain.analyze_match.assert_not_called()

        # Verify NO cache write (X-Fetch handles background)
        mock_cache.set.assert_not_called()

    def test_team_name_normalization(
        self, repository, monkeypatch
    ):
        """Test team name normalization for cache key consistency.

        Ensures:
        - Spaces replaced with underscores
        - Accents removed
        - Lowercase conversion
        - Consistent cache keys
        """
        # Arrange
        mock_cache = MagicMock()
        mock_cache.get.return_value = (None, False)
        monkeypatch.setattr("api.v1.brain.repository.smart_cache", mock_cache)

        # Act: Call with spaces and accents
        repository.calculate_predictions(
            home_team="Manchester United",
            away_team="Saint-Étienne",
            match_date=datetime.now(timezone.utc) + timedelta(days=7)
        )

        # Assert: Verify cache key normalized
        cache_get_call = mock_cache.get.call_args[0][0]

        # Should contain normalized team names
        assert "manchester_united" in cache_get_call
        assert "saint_etienne" in cache_get_call  # Accent removed

        # Should NOT contain original formatting
        assert "Manchester" not in cache_get_call
        assert "Étienne" not in cache_get_call

    def test_ttl_dynamic_pre_match(
        self, repository, mock_brain, monkeypatch
    ):
        """Test TTL = 3600s for PRE_MATCH (>24h ahead)."""
        # Arrange
        mock_cache = MagicMock()
        mock_cache.get.return_value = (None, False)
        monkeypatch.setattr("api.v1.brain.repository.smart_cache", mock_cache)

        # Act: Match in 7 days (PRE_MATCH)
        repository.calculate_predictions(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=datetime.now(timezone.utc) + timedelta(days=7)
        )

        # Assert: TTL = 3600 (1 hour)
        cache_set_call = mock_cache.set.call_args
        assert cache_set_call[1]["ttl"] == 3600

    def test_ttl_dynamic_soon(
        self, repository, mock_brain, monkeypatch
    ):
        """Test TTL = 900s for SOON (<24h ahead)."""
        # Arrange
        mock_cache = MagicMock()
        mock_cache.get.return_value = (None, False)
        monkeypatch.setattr("api.v1.brain.repository.smart_cache", mock_cache)

        # Act: Match in 12 hours (SOON)
        repository.calculate_predictions(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=datetime.now(timezone.utc) + timedelta(hours=12)
        )

        # Assert: TTL = 900 (15 minutes)
        cache_set_call = mock_cache.set.call_args
        assert cache_set_call[1]["ttl"] == 900

    def test_ttl_dynamic_live(
        self, repository, mock_brain, monkeypatch
    ):
        """Test TTL = 60s for LIVE (<2h ahead)."""
        # Arrange
        mock_cache = MagicMock()
        mock_cache.get.return_value = (None, False)
        monkeypatch.setattr("api.v1.brain.repository.smart_cache", mock_cache)

        # Act: Match in 1 hour (LIVE/VERY SOON)
        repository.calculate_predictions(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=datetime.now(timezone.utc) + timedelta(hours=1)
        )

        # Assert: TTL = 60 (1 minute)
        cache_set_call = mock_cache.set.call_args
        assert cache_set_call[1]["ttl"] == 60

    def test_ttl_dynamic_post_match(
        self, repository, mock_brain, monkeypatch
    ):
        """Test TTL = 86400s for POST_MATCH (finished)."""
        # Arrange
        mock_cache = MagicMock()
        mock_cache.get.return_value = (None, False)
        monkeypatch.setattr("api.v1.brain.repository.smart_cache", mock_cache)

        # Act: Match finished (1 day ago)
        repository.calculate_predictions(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=datetime.now(timezone.utc) - timedelta(days=1)
        )

        # Assert: TTL = 86400 (24 hours)
        cache_set_call = mock_cache.set.call_args
        assert cache_set_call[1]["ttl"] == 86400

    def test_created_at_json_serializable(
        self, repository, monkeypatch
    ):
        """Test created_at is ISO string (JSON serializable).

        Critical: SmartCache uses json.dumps(), so datetime must be string.
        """
        # Arrange
        mock_cache = MagicMock()
        mock_cache.get.return_value = (None, False)
        monkeypatch.setattr("api.v1.brain.repository.smart_cache", mock_cache)

        # Act
        result = repository.calculate_predictions(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=datetime.now(timezone.utc) + timedelta(days=7)
        )

        # Assert: created_at is string (ISO format)
        assert isinstance(result["created_at"], str)

        # Verify parseable
        datetime.fromisoformat(result["created_at"])  # Should not raise

    def test_redis_unavailable_graceful_degradation(
        self, repository, mock_brain, monkeypatch
    ):
        """Test Redis unavailable → graceful fallback to compute.

        SmartCache handles Redis errors gracefully:
        - cache.get() returns (None, False) on error
        - cache.set() fails silently
        - Repository continues to work (compute only)
        """
        # Arrange: Mock cache with Redis error
        mock_cache = MagicMock()
        mock_cache.get.return_value = (None, False)  # Redis error → miss
        mock_cache.set.side_effect = Exception("Redis connection refused")
        monkeypatch.setattr("api.v1.brain.repository.smart_cache", mock_cache)

        # Act: Should NOT crash
        result = repository.calculate_predictions(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=datetime.now(timezone.utc) + timedelta(days=7)
        )

        # Assert: Computation succeeded
        assert "markets" in result
        assert result["brain_version"] == "2.8.0"

        # Brain was called (no cache)
        mock_brain.analyze_match.assert_called_once()
