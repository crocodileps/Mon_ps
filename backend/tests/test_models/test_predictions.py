"""
Tests pour quantum_core.models.predictions.

15 tests couvrant MarketPrediction, EnsemblePrediction et GoalscorerPrediction.
"""

import pytest
from datetime import datetime, timedelta
from quantum_core.models.predictions import (
    MarketCategory,
    ConfidenceLevel,
    DataQuality,
    MarketPrediction,
    EnsemblePrediction,
    GoalscorerPrediction,
)


class TestMarketPrediction:
    """Tests pour le modèle MarketPrediction."""

    def test_market_prediction_creation(self):
        """Test création d'une MarketPrediction basique."""
        pred = MarketPrediction(
            prediction_id="test-123",
            match_id="match-456",
            market_id="btts_yes",
            market_name="Both Teams To Score - Yes",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.68,
            fair_odds=1.47,
            confidence_score=0.82,
            data_quality=DataQuality.EXCELLENT,
        )

        assert pred.prediction_id == "test-123"
        assert pred.probability == 0.68
        assert pred.fair_odds == 1.47
        assert pred.market_category == "main_line"

    def test_implied_probability_auto_calculation(self):
        """Test calcul automatique de implied_probability."""
        pred = MarketPrediction(
            prediction_id="test-124",
            match_id="match-456",
            market_id="btts_yes",
            market_name="BTTS Yes",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.65,
            fair_odds=2.0,
            confidence_score=0.75,
            data_quality=DataQuality.GOOD,
        )

        # implied_probability = 1 / fair_odds = 1 / 2.0 = 0.5
        assert pred.implied_probability == pytest.approx(0.5, rel=1e-6)

    def test_confidence_level_very_high(self):
        """Test assignation automatique confidence_level = VERY_HIGH."""
        pred = MarketPrediction(
            prediction_id="test-125",
            match_id="match-456",
            market_id="over_25",
            market_name="Over 2.5",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.72,
            fair_odds=1.39,
            confidence_score=0.92,  # > 0.85 → VERY_HIGH
            data_quality=DataQuality.EXCELLENT,
        )

        assert pred.confidence_level == "very_high"

    def test_confidence_level_high(self):
        """Test assignation automatique confidence_level = HIGH."""
        pred = MarketPrediction(
            prediction_id="test-126",
            match_id="match-456",
            market_id="home_win",
            market_name="Home Win",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.55,
            fair_odds=1.82,
            confidence_score=0.78,  # 0.70 - 0.85 → HIGH
            data_quality=DataQuality.GOOD,
        )

        assert pred.confidence_level == "high"

    def test_confidence_level_medium(self):
        """Test assignation automatique confidence_level = MEDIUM."""
        pred = MarketPrediction(
            prediction_id="test-127",
            match_id="match-456",
            market_id="draw",
            market_name="Draw",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.28,
            fair_odds=3.57,
            confidence_score=0.62,  # 0.50 - 0.70 → MEDIUM
            data_quality=DataQuality.FAIR,
        )

        assert pred.confidence_level == "medium"

    def test_confidence_level_low(self):
        """Test assignation automatique confidence_level = LOW."""
        pred = MarketPrediction(
            prediction_id="test-128",
            match_id="match-456",
            market_id="exotic_score",
            market_name="Exact Score 3-2",
            market_category=MarketCategory.EXOTIC,
            probability=0.05,
            fair_odds=20.0,
            confidence_score=0.42,  # < 0.50 → LOW
            data_quality=DataQuality.POOR,
        )

        assert pred.confidence_level == "low"

    def test_market_prediction_with_edge(self):
        """Test MarketPrediction avec edge et kelly."""
        pred = MarketPrediction(
            prediction_id="test-129",
            match_id="match-456",
            market_id="btts_yes",
            market_name="BTTS Yes",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.68,
            fair_odds=1.47,
            confidence_score=0.82,
            data_quality=DataQuality.EXCELLENT,
            edge_vs_market=12.5,
            kelly_fraction=0.048,
            expected_value=15.69,
        )

        assert pred.edge_vs_market == 12.5
        assert pred.kelly_fraction == 0.048
        assert pred.expected_value == 15.69

    def test_market_prediction_with_metadata(self):
        """Test MarketPrediction avec métadonnées complètes."""
        now = datetime.utcnow()
        pred = MarketPrediction(
            prediction_id="test-130",
            match_id="match-456",
            market_id="over_25",
            market_name="Over 2.5",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.58,
            fair_odds=1.72,
            confidence_score=0.75,
            data_quality=DataQuality.EXCELLENT,
            model_version="unified_brain_v2.8",
            model_components=["poisson", "dixon_coles", "ensemble"],
            computation_time_ms=45,
            cache_hit=False,
            contributing_factors=["high_xg", "recent_form"],
            warning_flags=[],
            computed_at=now,
        )

        assert pred.model_version == "unified_brain_v2.8"
        assert len(pred.model_components) == 3
        assert pred.computation_time_ms == 45
        assert not pred.cache_hit
        assert "high_xg" in pred.contributing_factors

    def test_market_prediction_probability_bounds(self):
        """Test validation des bornes de probability."""
        # Probability valide
        pred = MarketPrediction(
            prediction_id="test-131",
            match_id="match-456",
            market_id="btts_yes",
            market_name="BTTS Yes",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.5,
            fair_odds=2.0,
            confidence_score=0.7,
            data_quality=DataQuality.GOOD,
        )
        assert pred.probability == 0.5

        # Probability invalide (> 1.0)
        with pytest.raises(Exception):  # Pydantic ValidationError
            MarketPrediction(
                prediction_id="test-132",
                match_id="match-456",
                market_id="btts_yes",
                market_name="BTTS Yes",
                market_category=MarketCategory.MAIN_LINE,
                probability=1.5,  # > 1.0 → invalide
                fair_odds=2.0,
                confidence_score=0.7,
                data_quality=DataQuality.GOOD,
            )

    def test_market_prediction_fair_odds_bounds(self):
        """Test validation fair_odds > 1.0."""
        # fair_odds valide
        pred = MarketPrediction(
            prediction_id="test-133",
            match_id="match-456",
            market_id="fav_win",
            market_name="Favorite Win",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.95,
            fair_odds=1.05,
            confidence_score=0.9,
            data_quality=DataQuality.EXCELLENT,
        )
        assert pred.fair_odds == 1.05

        # fair_odds invalide (<= 1.0)
        with pytest.raises(Exception):
            MarketPrediction(
                prediction_id="test-134",
                match_id="match-456",
                market_id="impossible",
                market_name="Impossible",
                market_category=MarketCategory.EXOTIC,
                probability=0.5,
                fair_odds=0.5,  # <= 1.0 → invalide
                confidence_score=0.5,
                data_quality=DataQuality.POOR,
            )


class TestEnsemblePrediction:
    """Tests pour le modèle EnsemblePrediction."""

    def test_ensemble_prediction_creation(self):
        """Test création d'une EnsemblePrediction."""
        pred1 = MarketPrediction(
            prediction_id="pred-1",
            match_id="match-456",
            market_id="btts_yes",
            market_name="BTTS Yes",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.65,
            fair_odds=1.54,
            confidence_score=0.75,
            data_quality=DataQuality.GOOD,
        )

        pred2 = MarketPrediction(
            prediction_id="pred-2",
            match_id="match-456",
            market_id="btts_yes",
            market_name="BTTS Yes",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.70,
            fair_odds=1.43,
            confidence_score=0.80,
            data_quality=DataQuality.EXCELLENT,
        )

        final_pred = MarketPrediction(
            prediction_id="final-ensemble",
            match_id="match-456",
            market_id="btts_yes",
            market_name="BTTS Yes",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.68,
            fair_odds=1.47,
            confidence_score=0.85,
            data_quality=DataQuality.EXCELLENT,
            model_agreement=0.92,
        )

        ensemble = EnsemblePrediction(
            prediction_id="ensemble-123",
            match_id="match-456",
            market_name="BTTS Yes",
            final_prediction=final_pred,
            individual_predictions=[pred1, pred2],
            ensemble_method="weighted_mean",
            model_weights={"model_a": 0.6, "model_b": 0.4},
            prediction_variance=0.012,
            model_agreement_score=0.92,
            epistemic_uncertainty=0.05,
            aleatoric_uncertainty=0.08,
        )

        assert ensemble.ensemble_method == "weighted_mean"
        assert len(ensemble.individual_predictions) == 2
        assert ensemble.model_agreement_score == 0.92
        assert ensemble.prediction_variance == 0.012

    def test_ensemble_prediction_with_disagreement(self):
        """Test EnsemblePrediction avec désaccord entre modèles."""
        pred1 = MarketPrediction(
            prediction_id="pred-1",
            match_id="match-456",
            market_id="over_25",
            market_name="Over 2.5",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.45,
            fair_odds=2.22,
            confidence_score=0.70,
            data_quality=DataQuality.GOOD,
        )

        pred2 = MarketPrediction(
            prediction_id="pred-2",
            match_id="match-456",
            market_id="over_25",
            market_name="Over 2.5",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.75,
            fair_odds=1.33,
            confidence_score=0.85,
            data_quality=DataQuality.EXCELLENT,
        )

        final_pred = MarketPrediction(
            prediction_id="final-ensemble",
            match_id="match-456",
            market_id="over_25",
            market_name="Over 2.5",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.60,
            fair_odds=1.67,
            confidence_score=0.60,
            data_quality=DataQuality.GOOD,
        )

        ensemble = EnsemblePrediction(
            prediction_id="ensemble-124",
            match_id="match-456",
            market_name="Over 2.5",
            final_prediction=final_pred,
            individual_predictions=[pred1, pred2],
            ensemble_method="mean",
            model_weights={"model_a": 0.5, "model_b": 0.5},
            prediction_variance=0.045,  # Haute variance
            model_agreement_score=0.40,  # Faible accord
            disagreement_explanation="Large spread between Poisson and Dixon-Coles models",
            epistemic_uncertainty=0.15,
            aleatoric_uncertainty=0.10,
        )

        assert ensemble.model_agreement_score == 0.40
        assert ensemble.disagreement_explanation is not None
        assert "spread" in ensemble.disagreement_explanation.lower()


class TestGoalscorerPrediction:
    """Tests pour le modèle GoalscorerPrediction."""

    def test_goalscorer_prediction_creation(self):
        """Test création d'une GoalscorerPrediction."""
        gs_pred = GoalscorerPrediction(
            player_id="haaland_9",
            player_name="Erling Haaland",
            team="Manchester City",
            position="FW",
            anytime_probability=0.68,
            first_probability=0.28,
            last_probability=0.15,
            goals_per_90=1.12,
            xg_per_90=0.98,
            minutes_expected=85,
            timing_profile="EARLY_BIRD",
            first_goal_share=0.53,
            is_starter=True,
            recent_form="HOT",
            data_quality=DataQuality.EXCELLENT,
            confidence_score=0.88,
        )

        assert gs_pred.player_name == "Erling Haaland"
        assert gs_pred.position == "FW"
        assert gs_pred.anytime_probability == 0.68
        assert gs_pred.first_probability == 0.28
        assert gs_pred.timing_profile == "EARLY_BIRD"
        assert gs_pred.is_starter is True

    def test_goalscorer_prediction_with_history(self):
        """Test GoalscorerPrediction avec historique vs adversaire."""
        gs_pred = GoalscorerPrediction(
            player_id="salah_11",
            player_name="Mohamed Salah",
            team="Liverpool",
            position="FW",
            anytime_probability=0.62,
            first_probability=0.22,
            last_probability=0.18,
            goals_per_90=0.95,
            xg_per_90=0.82,
            minutes_expected=90,
            timing_profile="CLUTCH",
            first_goal_share=0.38,
            is_starter=True,
            recent_form="WARM",
            vs_opponent_history={
                "games_played": 15,
                "goals_scored": 8,
                "avg_xg": 0.72,
                "last_5_games": [1, 0, 2, 1, 0],
            },
            data_quality=DataQuality.EXCELLENT,
            confidence_score=0.82,
        )

        assert gs_pred.vs_opponent_history is not None
        assert gs_pred.vs_opponent_history["games_played"] == 15
        assert gs_pred.vs_opponent_history["goals_scored"] == 8
        assert gs_pred.timing_profile == "CLUTCH"

    def test_goalscorer_position_validation(self):
        """Test validation du champ position (FW/MF/DF/GK)."""
        # Position valide
        gs_pred = GoalscorerPrediction(
            player_id="test_player",
            player_name="Test Player",
            team="Test FC",
            position="MF",
            anytime_probability=0.35,
            first_probability=0.12,
            last_probability=0.08,
            goals_per_90=0.45,
            xg_per_90=0.38,
            minutes_expected=90,
            timing_profile="CONSISTENT",
            first_goal_share=0.25,
            is_starter=True,
            recent_form="WARM",
            data_quality=DataQuality.GOOD,
            confidence_score=0.70,
        )
        assert gs_pred.position == "MF"

        # Position invalide
        with pytest.raises(Exception):
            GoalscorerPrediction(
                player_id="test_player",
                player_name="Test Player",
                team="Test FC",
                position="INVALID",  # Pas FW/MF/DF/GK
                anytime_probability=0.35,
                first_probability=0.12,
                last_probability=0.08,
                goals_per_90=0.45,
                xg_per_90=0.38,
                minutes_expected=90,
                timing_profile="CONSISTENT",
                first_goal_share=0.25,
                is_starter=True,
                recent_form="WARM",
                data_quality=DataQuality.GOOD,
                confidence_score=0.70,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS ADR COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════════════


class TestADR002ModelValidatorPredictions:
    """Tests validant ADR #002 pour predictions.py.

    ADR #002: model_validator pour cross-field logic.
    - Garantit accès aux defaults
    - Plus rapide que field_validator × N
    - Type-safe avec Self return
    """

    def test_model_validator_accesses_defaults(self):
        """ADR #002: model_validator accède aux defaults."""
        # Création sans spécifier implied_probability ni confidence_level
        pred = MarketPrediction(
            prediction_id="test_adr002_1",
            match_id="match_adr",
            market_id="btts_yes",
            market_name="BTTS Yes",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.68,
            fair_odds=2.0,
            confidence_score=0.82,  # > 0.70 → HIGH
            data_quality=DataQuality.EXCELLENT,
            # implied_probability omis → default 0.0 → sera calculé
            # confidence_level omis → default LOW → sera calculé
        )

        # ADR #002: model_validator a calculé les valeurs
        assert pred.implied_probability == pytest.approx(0.5, rel=1e-6)  # 1 / 2.0
        assert pred.confidence_level == "high"  # 0.82 > 0.70

    def test_model_validator_cross_field_logic(self):
        """ADR #002: model_validator permet logique inter-champs."""
        # confidence_level dépend de confidence_score
        pred = MarketPrediction(
            prediction_id="test_adr002_2",
            match_id="match_adr",
            market_id="over_25",
            market_name="Over 2.5",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.72,
            fair_odds=1.39,
            confidence_score=0.92,  # > 0.85 → VERY_HIGH
            data_quality=DataQuality.EXCELLENT,
        )

        assert pred.confidence_level == "very_high"


class TestADR003FieldSerializerPredictions:
    """Tests validant ADR #003 pour predictions.py.

    ADR #003: field_serializer explicite.
    - when_used='json' → .model_dump() garde datetime, .model_dump_json() serialise
    - Type-safe (mypy vérifie)
    - Testable unitairement
    """

    def test_datetime_serializes_to_iso8601_json(self):
        """ADR #003: .model_dump_json() serialise datetime en ISO 8601."""
        pred = MarketPrediction(
            prediction_id="test_adr003_1",
            match_id="match_adr",
            market_id="btts_yes",
            market_name="BTTS Yes",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.68,
            fair_odds=1.47,
            confidence_score=0.82,
            data_quality=DataQuality.EXCELLENT,
            computed_at=datetime(2025, 12, 13, 20, 30, 0),
        )

        json_str = pred.model_dump_json()

        # Datetime serialisé en ISO 8601
        assert '"computed_at":"2025-12-13T20:30:00"' in json_str

    def test_datetime_preserved_in_model_dump(self):
        """ADR #003: .model_dump() préserve datetime object (when_used='json')."""
        pred = MarketPrediction(
            prediction_id="test_adr003_2",
            match_id="match_adr",
            market_id="btts_yes",
            market_name="BTTS Yes",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.68,
            fair_odds=1.47,
            confidence_score=0.82,
            data_quality=DataQuality.EXCELLENT,
            computed_at=datetime(2025, 12, 13, 20, 30, 0),
        )

        data = pred.model_dump()

        # Datetime object préservé (pas string)
        assert isinstance(data["computed_at"], datetime)
        assert data["computed_at"].year == 2025


class TestADR004AutoCalculatedPredictions:
    """Tests validant ADR #004 pour predictions.py.

    ADR #004: Pattern Hybrid pour auto-calculs.
    - Default sentinelle (0.0, LOW)
    - Auto-calcul si sentinelle détectée
    - Permet override si valeur fournie
    """

    def test_implied_probability_auto_calculated(self):
        """ADR #004: implied_probability auto-calculé depuis fair_odds."""
        pred = MarketPrediction(
            prediction_id="test_adr004_1",
            match_id="match_adr",
            market_id="btts_yes",
            market_name="BTTS Yes",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.68,
            fair_odds=2.0,
            confidence_score=0.82,
            data_quality=DataQuality.EXCELLENT,
            # implied_probability omis → sera calculé
        )

        # ADR #004: implied_probability = 1 / fair_odds
        assert pred.implied_probability == pytest.approx(0.5, rel=1e-6)

    def test_implied_probability_can_be_overridden(self):
        """ADR #004: Pattern Hybrid permet override."""
        pred = MarketPrediction(
            prediction_id="test_adr004_2",
            match_id="match_adr",
            market_id="btts_yes",
            market_name="BTTS Yes",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.68,
            fair_odds=2.0,
            confidence_score=0.82,
            data_quality=DataQuality.EXCELLENT,
            implied_probability=0.48,  # Override explicite (≠ sentinelle 0.0)
        )

        # Valeur override préservée
        assert pred.implied_probability == 0.48

    def test_confidence_level_auto_calculated(self):
        """ADR #004: confidence_level auto-calculé depuis confidence_score."""
        test_cases = [
            (0.92, "very_high"),  # > 0.85
            (0.78, "high"),  # 0.70 - 0.85
            (0.62, "medium"),  # 0.50 - 0.70
            (0.42, "low"),  # < 0.50
        ]

        for score, expected_level in test_cases:
            pred = MarketPrediction(
                prediction_id=f"test_adr004_3_{score}",
                match_id="match_adr",
                market_id="btts_yes",
                market_name="BTTS Yes",
                market_category=MarketCategory.MAIN_LINE,
                probability=0.68,
                fair_odds=1.47,
                confidence_score=score,
                data_quality=DataQuality.EXCELLENT,
                # confidence_level omis → sera calculé
            )

            assert (
                pred.confidence_level == expected_level
            ), f"Score {score} should give {expected_level}"

    def test_confidence_level_can_be_overridden(self):
        """ADR #004: confidence_level peut être overridden si nécessaire."""
        pred = MarketPrediction(
            prediction_id="test_adr004_4",
            match_id="match_adr",
            market_id="exotic_score",
            market_name="Exact Score",
            market_category=MarketCategory.EXOTIC,
            probability=0.05,
            fair_odds=20.0,
            confidence_score=0.82,  # Score élevé
            data_quality=DataQuality.POOR,
            confidence_level=ConfidenceLevel.MEDIUM,  # Override à MEDIUM malgré score > 0.70
        )

        # Valeur override préservée
        assert pred.confidence_level == "medium"
