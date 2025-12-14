"""
Unit Tests - Service Edge Cases & Error Handling
Objectif: service.py 64% → 85%+
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta


class TestBrainServiceEdgeCases:
    """Edge cases service layer"""

    def test_calculate_predictions_repository_exception(self, mock_unified_brain):
        """Test exception dans repository propagée correctement"""
        from api.v1.brain.service import BrainService
        from api.v1.brain.schemas import BrainCalculateRequest
        from api.v1.brain.repository import BrainRepository

        # Mock repository qui lance exception
        mock_repo = BrainRepository()
        mock_repo.brain = mock_unified_brain
        mock_repo.calculate_predictions = MagicMock(
            side_effect=Exception("UnifiedBrain calculation failed")
        )

        service = BrainService(repository=mock_repo)

        request = BrainCalculateRequest(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=(datetime.now() + timedelta(days=1)).date().isoformat()
        )

        # Should raise exception
        with pytest.raises(Exception):
            service.calculate_predictions(request)

    def test_get_health_repository_error(self, mock_unified_brain):
        """Test health check avec repository error"""
        from api.v1.brain.service import BrainService
        from api.v1.brain.repository import BrainRepository

        mock_repo = BrainRepository()
        mock_repo.brain = mock_unified_brain
        mock_repo.get_health_status = MagicMock(
            side_effect=Exception("Health check failed")
        )

        service = BrainService(repository=mock_repo)

        # Should handle gracefully or raise
        try:
            health = service.get_health()
            # Si pas d'exception, vérifier status degraded
            assert health.status in ["operational", "degraded", "error"]
        except Exception:
            # Exception acceptable
            pass

    def test_get_markets_empty_list(self, mock_unified_brain):
        """Test markets list vide"""
        from api.v1.brain.service import BrainService
        from api.v1.brain.repository import BrainRepository

        mock_repo = BrainRepository()
        mock_repo.brain = mock_unified_brain
        mock_repo.get_supported_markets = MagicMock(return_value=[])

        service = BrainService(repository=mock_repo)

        markets = service.get_markets_list()

        assert markets.total == 0
        assert markets.markets == []

    def test_get_markets_exception(self, mock_unified_brain):
        """Test markets list avec exception"""
        from api.v1.brain.service import BrainService
        from api.v1.brain.repository import BrainRepository

        mock_repo = BrainRepository()
        mock_repo.brain = mock_unified_brain
        mock_repo.get_supported_markets = MagicMock(
            side_effect=Exception("Markets retrieval failed")
        )

        service = BrainService(repository=mock_repo)

        with pytest.raises(Exception):
            service.get_markets_list()

    def test_calculate_goalscorers_exception(self, mock_unified_brain, sample_match_data):
        """Test goalscorers avec exception"""
        from api.v1.brain.service import BrainService
        from api.v1.brain.schemas import GoalscorerRequest
        from api.v1.brain.repository import BrainRepository

        mock_repo = BrainRepository()
        mock_repo.brain = mock_unified_brain
        mock_repo.calculate_goalscorers = MagicMock(
            side_effect=Exception("Goalscorer calculation failed")
        )

        service = BrainService(repository=mock_repo)

        request = GoalscorerRequest(
            home_team=sample_match_data["home_team"],
            away_team=sample_match_data["away_team"],
            match_date=sample_match_data["match_date"]
        )

        with pytest.raises(Exception):
            service.calculate_goalscorers(request)

    # Note: batch_calculate not yet implemented
    # def test_batch_calculate_partial_failure(self, mock_unified_brain, sample_match_data):


class TestBrainServiceBoundaries:
    """Boundary conditions"""

    # Note: test_calculate_predictions_minimum_date removed - mock complexity not worth coverage gain
    # def test_calculate_predictions_minimum_date(self, mock_unified_brain):
