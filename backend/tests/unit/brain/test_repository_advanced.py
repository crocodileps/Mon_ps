"""
Unit Tests - Repository Advanced (DI + Error Paths)
Objectif: repository.py 74% → 95%+
"""
import pytest
import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime, timedelta


class TestBrainRepositoryDependencyInjection:
    """Tests dependency injection"""

    def test_repository_with_injected_brain(self):
        """Test DI avec brain client injecté"""
        from api.v1.brain.repository import BrainRepository

        # Mock UnifiedBrain
        mock_brain = MagicMock()
        mock_brain.analyze_match.return_value = MagicMock(
            to_dict=lambda: {"test": "data"}
        )

        # Injection
        repo = BrainRepository(brain_client=mock_brain)

        assert repo.brain == mock_brain
        assert repo.env == "INJECTED"

    def test_repository_without_injection_uses_production(self):
        """Test sans DI utilise production path"""
        from api.v1.brain.repository import BrainRepository

        # Sans injection, devrait initialiser vrai brain
        # (skip si quantum_core pas accessible)
        try:
            repo = BrainRepository()
            assert repo.brain is not None
            assert repo.env in ["DOCKER", "LOCAL"]
        except RuntimeError as e:
            # Acceptable si quantum_core pas accessible
            assert "quantum_core not found" in str(e)


class TestBrainRepositoryInitializationErrors:
    """Tests erreurs initialisation"""

    def test_repository_quantum_core_not_found(self):
        """Test erreur quand quantum_core absent"""
        from api.v1.brain.repository import BrainRepository

        # Mock Path.exists() pour simuler absence
        with patch('api.v1.brain.repository.Path') as MockPath:
            mock_docker = MagicMock()
            mock_docker.exists.return_value = False
            mock_local = MagicMock()
            mock_local.exists.return_value = False

            MockPath.side_effect = [mock_docker, mock_local]

            with pytest.raises(RuntimeError) as exc:
                BrainRepository()

            assert "quantum_core not found" in str(exc.value)

    def test_repository_import_error(self):
        """Test ImportError UnifiedBrain"""
        from api.v1.brain.repository import BrainRepository

        # Mock quantum_core exists mais import fail
        with patch('api.v1.brain.repository.Path') as MockPath:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            MockPath.return_value = mock_path

            # Mock import pour lever ImportError
            with patch.dict(sys.modules, {'brain.unified_brain': None}):
                with pytest.raises(RuntimeError) as exc:
                    BrainRepository()

                assert "Failed to import UnifiedBrain" in str(exc.value)

    def test_repository_initialization_exception(self):
        """Test exception during UnifiedBrain init"""
        from api.v1.brain.repository import BrainRepository

        with patch('api.v1.brain.repository.Path') as MockPath:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            MockPath.return_value = mock_path

            # Mock UnifiedBrain qui lance exception
            mock_brain_class = MagicMock(
                side_effect=Exception("Memory allocation failed")
            )

            with patch.dict(sys.modules, {'brain.unified_brain': MagicMock(UnifiedBrain=mock_brain_class)}):
                with pytest.raises(RuntimeError) as exc:
                    BrainRepository()

                assert "Failed to initialize UnifiedBrain" in str(exc.value)


class TestBrainRepositoryCircuitBreaker:
    """Tests circuit breaker pattern"""

    def test_calculate_predictions_brain_not_initialized(self):
        """Test calculation avec brain None"""
        from api.v1.brain.repository import BrainRepository

        # Create repo avec brain = None (simuler corruption)
        repo = BrainRepository(brain_client=MagicMock())
        repo.brain = None

        with pytest.raises(RuntimeError) as exc:
            repo.calculate_predictions(
                home_team="Liverpool",
                away_team="Chelsea",
                match_date=datetime.now() + timedelta(days=1)
            )

        assert "Brain engine not initialized" in str(exc.value)

    def test_calculate_predictions_attribute_error(self):
        """Test AttributeError (méthode manquante)"""
        from api.v1.brain.repository import BrainRepository

        # Mock brain sans méthode analyze_match
        mock_brain = MagicMock()
        del mock_brain.analyze_match  # Remove method

        repo = BrainRepository(brain_client=mock_brain)

        with pytest.raises(RuntimeError) as exc:
            repo.calculate_predictions(
                home_team="Liverpool",
                away_team="Chelsea",
                match_date=datetime.now() + timedelta(days=1)
            )

        assert "Brain engine corruption" in str(exc.value)

    def test_calculate_predictions_quantum_core_failure(self):
        """Test exception interne Quantum Core"""
        from api.v1.brain.repository import BrainRepository

        # Mock brain qui lance exception
        mock_brain = MagicMock()
        mock_brain.analyze_match.side_effect = Exception("C++ segfault")

        repo = BrainRepository(brain_client=mock_brain)

        with pytest.raises(RuntimeError) as exc:
            repo.calculate_predictions(
                home_team="Liverpool",
                away_team="Chelsea",
                match_date=datetime.now() + timedelta(days=1)
            )

        assert "Quantum Core calculation failure" in str(exc.value)
        assert "C++ segfault" in str(exc.value)

    def test_get_supported_markets_brain_not_initialized(self):
        """Test markets avec brain None"""
        from api.v1.brain.repository import BrainRepository

        repo = BrainRepository(brain_client=MagicMock())
        repo.brain = None

        with pytest.raises(RuntimeError) as exc:
            repo.get_supported_markets()

        assert "Brain not initialized" in str(exc.value)

    def test_get_supported_markets_exception(self):
        """Test markets exception (fallback graceful)"""
        from api.v1.brain.repository import BrainRepository

        mock_brain = MagicMock()
        mock_brain.analyze_match.side_effect = Exception("Network timeout")

        repo = BrainRepository(brain_client=mock_brain)

        # Should return fallback hardcoded list (not raise)
        markets = repo.get_supported_markets()

        assert isinstance(markets, list)
        assert len(markets) == 3  # Fallback has 3 markets
        assert markets[0]["id"] == "over_under_25"

    def test_get_health_status_brain_not_initialized(self):
        """Test health avec brain None"""
        from api.v1.brain.repository import BrainRepository

        repo = BrainRepository(brain_client=MagicMock())
        repo.brain = None

        health = repo.get_health_status()

        assert health["status"] == "error"
        assert "Brain not initialized" in health["error"]

    def test_get_health_status_exception(self):
        """Test health exception graceful"""
        from api.v1.brain.repository import BrainRepository

        mock_brain = MagicMock()
        mock_brain.health_check.side_effect = Exception("Health check failed")

        repo = BrainRepository(brain_client=mock_brain)

        health = repo.get_health_status()

        assert health["status"] == "error"
        assert "Health check failed" in health["error"]

    def test_calculate_goalscorers_brain_not_initialized(self):
        """Test goalscorers avec brain None"""
        from api.v1.brain.repository import BrainRepository

        repo = BrainRepository(brain_client=MagicMock())
        repo.brain = None

        with pytest.raises(RuntimeError) as exc:
            repo.calculate_goalscorers(
                home_team="Liverpool",
                away_team="Chelsea",
                match_date=datetime.now() + timedelta(days=1)
            )

        assert "Brain not initialized" in str(exc.value)

    def test_calculate_goalscorers_exception(self):
        """Test goalscorers placeholder"""
        from api.v1.brain.repository import BrainRepository

        mock_brain = MagicMock()
        # Goalscorers returns placeholder (not yet implemented in V2.8.0)

        repo = BrainRepository(brain_client=mock_brain)

        # Should return placeholder structure
        result = repo.calculate_goalscorers(
            home_team="Liverpool",
            away_team="Chelsea",
            match_date=datetime.now() + timedelta(days=1)
        )

        assert "home_goalscorers" in result
        assert "away_goalscorers" in result
        assert result["home_goalscorers"] == []
        assert result["away_goalscorers"] == []
