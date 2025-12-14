"""
Integration Tests - Error Paths & Edge Cases
Objectif: repository.py 73% → 85%+
"""
import pytest
from datetime import datetime, timedelta


class TestBrainRepositoryErrorPaths:
    """Tests error paths avec vrai UnifiedBrain"""

    def test_calculate_predictions_invalid_team_graceful(self, brain_repository_real):
        """Test avec équipe invalide (graceful degradation)"""

        # Équipe fictive/invalide
        try:
            result = brain_repository_real.calculate_predictions(
                home_team="ÉQUIPE_QUI_NEXISTE_PAS_12345",
                away_team="AUTRE_ÉQUIPE_FICTIVE_67890",
                match_date=datetime.now() + timedelta(days=2)
            )

            # Si pas d'exception, vérifier résultat valide
            assert "markets" in result
            # markets can be dict or list depending on implementation
            assert isinstance(result["markets"], (list, dict))
            assert result["calculation_time"] < 5.0
        except Exception as e:
            # Exception acceptable si équipe inconnue
            assert "unknown" in str(e).lower() or "not found" in str(e).lower()

    def test_calculate_predictions_performance_boundary(self, brain_repository_real, performance_monitor):
        """Test performance avec date extrême"""

        performance_monitor.start()

        # Date très loin (1 an)
        result = brain_repository_real.calculate_predictions(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=datetime.now() + timedelta(days=365)
        )

        elapsed = performance_monitor.stop()

        assert result is not None
        # Performance doit rester raisonnable même avec date extrême
        assert elapsed < 10.0  # Max 10s

    def test_health_check_consistency(self, brain_repository_real):
        """Test health check multiple fois (consistency)"""

        health1 = brain_repository_real.get_health_status()
        health2 = brain_repository_real.get_health_status()

        # Health status doit être consistent
        assert health1["status"] == health2["status"]
        assert health1["markets_count"] == health2["markets_count"]


class TestBrainRepositoryBoundaries:
    """Boundary conditions integration"""

    @pytest.mark.parametrize("days_ahead", [1, 7, 30, 90])
    def test_calculate_predictions_various_dates(self, brain_repository_real, days_ahead):
        """Test différentes dates futures"""

        result = brain_repository_real.calculate_predictions(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=datetime.now() + timedelta(days=days_ahead)
        )

        assert len(result["markets"]) > 50
        assert result["calculation_time"] < 5.0
