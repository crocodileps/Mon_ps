"""Tests for PredictionFactory - ADR #007.

Validates:
1. Predictions are valid (Pydantic validation)
2. Mathematical coherence (variance, agreement)
3. Reusability (multiple calls = different instances)
"""

import pytest
import statistics
from pydantic import ValidationError
from tests.factories import (
    create_market_prediction,
    create_ensemble_realistic,
    create_ensemble_high_disagreement,
    PredictionFactory,
)
from quantum_core.models.predictions import MarketCategory, DataQuality


class TestMarketPredictionFactory:
    """Tests for MarketPrediction factory."""

    def test_create_default_prediction(self):
        """Test creating prediction with defaults."""
        pred = create_market_prediction()

        # Validate structure
        assert pred.prediction_id.startswith("test_pred_")
        assert pred.match_id == "test_match_001"
        assert pred.fair_odds == 1.85
        assert pred.confidence_score == 0.82

        # Validate probability calculated correctly
        expected_prob = 1.0 / 1.85
        assert abs(pred.probability - expected_prob) < 0.001

    def test_create_custom_prediction(self):
        """Test creating prediction with custom values."""
        pred = create_market_prediction(
            match_id="custom_match",
            fair_odds=2.50,
            confidence_score=0.90,
        )

        assert pred.match_id == "custom_match"
        assert pred.fair_odds == 2.50
        assert pred.confidence_score == 0.90

        # Probability should be recalculated
        expected_prob = 1.0 / 2.50
        assert abs(pred.probability - expected_prob) < 0.001

    def test_validation_fair_odds_must_be_above_1(self):
        """Test that fair_odds < 1.0 raises validation error."""
        with pytest.raises(ValidationError):
            create_market_prediction(fair_odds=0.95)

    def test_validation_confidence_score_bounds(self):
        """Test that confidence_score must be in [0, 1]."""
        # Too low
        with pytest.raises(ValidationError):
            create_market_prediction(confidence_score=-0.1)

        # Too high
        with pytest.raises(ValidationError):
            create_market_prediction(confidence_score=1.5)

    def test_different_instances_have_different_ids(self):
        """Test that multiple calls generate different IDs."""
        pred1 = create_market_prediction()
        pred2 = create_market_prediction()

        assert pred1.prediction_id != pred2.prediction_id


class TestEnsemblePredictionFactory:
    """Tests for EnsemblePrediction factory."""

    def test_create_realistic_ensemble(self):
        """Test creating ensemble with realistic variance."""
        ensemble = create_ensemble_realistic(
            base_odds=1.85,
            variance=0.05,
        )

        # Validate structure
        assert ensemble.prediction_id.startswith("ensemble_")
        assert len(ensemble.individual_predictions) == 4

        # All predictions should be different (not same object!)
        ids = [p.prediction_id for p in ensemble.individual_predictions]
        assert len(ids) == len(set(ids))  # All unique

    def test_ensemble_variance_is_mathematically_coherent(self):
        """Test that variance is calculated, not invented.

        CRITICAL TEST - Session #23 bug:
        - 4 identical predictions had variance=0.015 (FAUX!)
        - Now: variance calculated from real data
        """
        ensemble = create_ensemble_realistic(
            base_odds=1.85,
            variance=0.05,
        )

        # Extract fair_odds from individual predictions
        odds = [p.fair_odds for p in ensemble.individual_predictions]

        # Calculate actual variance
        actual_variance = statistics.variance(odds)

        # Declared variance should match calculated
        assert abs(ensemble.prediction_variance - actual_variance) < 0.001

    def test_ensemble_agreement_is_coherent_with_dispersion(self):
        """Test that agreement score reflects real dispersion."""
        ensemble = create_ensemble_realistic(
            base_odds=1.85,
            variance=0.05,
        )

        # Extract odds
        odds = [p.fair_odds for p in ensemble.individual_predictions]
        mean_odds = statistics.mean(odds)

        # Calculate expected agreement
        # Agreement = 1 - (max_deviation / mean)
        max_deviation = max(abs(o - mean_odds) for o in odds)
        expected_agreement = 1.0 - (max_deviation / mean_odds)

        # Declared agreement should match
        assert abs(ensemble.model_agreement_score - expected_agreement) < 0.01

    def test_ensemble_predictions_are_different(self):
        """Test that 4 predictions are DIFFERENT (not identical).

        Session #23 bug: Same object repeated 4 times.
        Now: 4 distinct objects with different values.
        """
        ensemble = create_ensemble_realistic(base_odds=1.85, variance=0.05)

        predictions = ensemble.individual_predictions

        # Different IDs
        ids = [p.prediction_id for p in predictions]
        assert len(set(ids)) == 4

        # Different fair_odds
        odds = [p.fair_odds for p in predictions]
        assert len(set(odds)) == 4  # All different

        # Different confidence_scores
        confidences = [p.confidence_score for p in predictions]
        assert len(set(confidences)) == 4  # All different

    def test_high_disagreement_ensemble(self):
        """Test creating ensemble with high disagreement."""
        ensemble = create_ensemble_high_disagreement()

        # High variance should lead to low agreement
        assert ensemble.model_agreement_score < 0.80  # < 80% agreement

    def test_ensemble_with_controlled_variance(self):
        """Test that variance parameter controls dispersion."""
        # Low variance
        ensemble_low = create_ensemble_realistic(variance=0.02)

        # High variance
        ensemble_high = create_ensemble_realistic(variance=0.20)

        # High variance ensemble should have lower agreement
        assert ensemble_high.prediction_variance > ensemble_low.prediction_variance
        assert ensemble_high.model_agreement_score < ensemble_low.model_agreement_score


class TestFactoryReusability:
    """Test factory reusability (DRY principle)."""

    def test_factory_can_be_called_multiple_times(self):
        """Test that factory is reusable."""
        preds = [create_market_prediction() for _ in range(10)]

        # All should be valid
        assert len(preds) == 10

        # All should have different IDs
        ids = [p.prediction_id for p in preds]
        assert len(set(ids)) == 10

    def test_factory_with_different_parameters(self):
        """Test factory flexibility."""
        pred1 = create_market_prediction(fair_odds=1.50, confidence_score=0.95)
        pred2 = create_market_prediction(fair_odds=3.00, confidence_score=0.65)

        assert pred1.fair_odds == 1.50
        assert pred2.fair_odds == 3.00
        assert pred1.confidence_score != pred2.confidence_score
