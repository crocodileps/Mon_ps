"""
Integration Tests Repository avec VRAI UnifiedBrain
Pattern: Real dependencies, pas de mocks
"""

import pytest
from datetime import datetime, timedelta


class TestBrainRepositoryIntegration:
    """Tests integration avec vrai UnifiedBrain V2.8.0"""

    def test_calculate_predictions_real_brain(
        self,
        brain_repository_real,
        sample_match_data,
        performance_monitor
    ):
        """Test calculate_predictions avec vrai UnifiedBrain"""

        performance_monitor.start()

        result = brain_repository_real.calculate_predictions(
            home_team=sample_match_data["home_team"],
            away_team=sample_match_data["away_team"],
            match_date=datetime.fromisoformat(sample_match_data["match_date"])
        )

        elapsed = performance_monitor.stop()

        # Assertions structure
        assert "markets" in result
        assert "calculation_time" in result
        assert "brain_version" in result
        assert "created_at" in result

        # Assertions contenu
        assert len(result["markets"]) > 50  # Au moins 50 marchés
        assert result["brain_version"] == "2.8.0"

        # Assertions performance (P95 < 5s)
        assert elapsed < 5.0, f"Trop lent: {elapsed}s"

        # Assertions probabilités valides
        for market_id, market_data in result["markets"].items():
            pred = market_data["prediction"]
            assert 0.0 <= pred["probability"] <= 1.0, \
                f"Probabilité invalide pour {market_id}: {pred['probability']}"

    def test_multiple_teams_consistency(
        self,
        brain_repository_real,
        sample_teams_pool
    ):
        """Test consistance prédictions sur plusieurs équipes"""

        results = []
        match_date = datetime.now() + timedelta(days=1)

        # Tester 5 matchs différents
        for i in range(5):
            home = sample_teams_pool[i]
            away = sample_teams_pool[i + 1]

            result = brain_repository_real.calculate_predictions(
                home_team=home,
                away_team=away,
                match_date=match_date
            )

            results.append(result)

        # Assertions: Tous doivent avoir structure identique
        first_markets = set(results[0]["markets"].keys())
        for r in results[1:]:
            assert set(r["markets"].keys()) == first_markets, \
                "Markets keys doivent être identiques"

    def test_get_supported_markets_real(self, brain_repository_real):
        """Test get_supported_markets retourne vraie liste"""

        markets = brain_repository_real.get_supported_markets()

        assert len(markets) > 50  # Au moins 50 marchés
        assert all("id" in m for m in markets)
        assert all("name" in m for m in markets)
        assert all("category" in m for m in markets)

        # Vérifier catégories connues
        categories = set(m["category"] for m in markets)
        expected_categories = {"goals", "result", "cards", "corners"}
        assert expected_categories.issubset(categories)

    def test_health_check_real(self, brain_repository_real):
        """Test health check avec vrai brain"""

        health = brain_repository_real.get_health_status()

        assert health["status"] == "operational"
        assert health["version"] == "2.8.0"
        assert health["markets_count"] >= 90  # Au moins 90 marchés
        assert "quantum_core_path" in health
        assert "environment" in health

    @pytest.mark.parametrize("home,away", [
        ("Liverpool", "Chelsea"),
        ("Manchester City", "Arsenal"),
        ("Real Madrid", "Barcelona"),
    ])
    def test_different_matchups(
        self,
        brain_repository_real,
        home,
        away
    ):
        """Test différents matchups avec parametrize"""

        result = brain_repository_real.calculate_predictions(
            home_team=home,
            away_team=away,
            match_date=datetime.now() + timedelta(days=2)
        )

        assert len(result["markets"]) > 50
        assert result["calculation_time"] < 5.0


class TestBrainRepositoryEdgeCases:
    """Tests edge cases et error handling"""

    def test_unknown_team(self, brain_repository_real):
        """Test avec équipe inconnue"""

        # UnifiedBrain pourrait throw ou retourner résultat
        # On capture les 2 comportements
        try:
            result = brain_repository_real.calculate_predictions(
                home_team="UnknownTeamXYZ",
                away_team="Liverpool",
                match_date=datetime.now() + timedelta(days=1)
            )
            # Si pas d'erreur, vérifier format response
            assert "markets" in result
        except RuntimeError as e:
            # Si erreur, vérifier message explicite
            assert "Brain error" in str(e)

    def test_same_team_home_away(self, brain_repository_real):
        """Test même équipe home et away (invalide)"""

        # Devrait gérer gracefully ou throw
        try:
            result = brain_repository_real.calculate_predictions(
                home_team="Liverpool",
                away_team="Liverpool",  # Même équipe !
                match_date=datetime.now() + timedelta(days=1)
            )
            # Si accepté, on log warning
            print("⚠️ Warning: Same team home/away accepté")
        except (RuntimeError, ValueError):
            # Comportement attendu
            pass

    def test_past_date(self, brain_repository_real):
        """Test avec date passée"""

        past_date = datetime.now() - timedelta(days=30)

        # UnifiedBrain pourrait accepter ou refuser
        try:
            result = brain_repository_real.calculate_predictions(
                home_team="Liverpool",
                away_team="Chelsea",
                match_date=past_date
            )
            assert "markets" in result
        except RuntimeError:
            pass  # Acceptable
