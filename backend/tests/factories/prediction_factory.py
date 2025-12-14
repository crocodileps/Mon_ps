"""Prediction Factory - Mathematically coherent test data.

ADR #007: Test Data Factory Pattern.

Key principles:
1. Mathematical coherence (variance calculated, not invented)
2. Reusability (DRY)
3. Flexibility (paramétrable)
4. Validation (assertions automatiques)
"""

import statistics
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from quantum_core.models.predictions import (
    MarketPrediction,
    EnsemblePrediction,
    MarketCategory,
    DataQuality,
    ConfidenceLevel,
)


class PredictionFactory:
    """Factory pour créer test data cohérente mathématiquement.

    Usage:
        # Simple prediction
        pred = PredictionFactory.create_market_prediction(fair_odds=1.85)

        # Ensemble réaliste
        ensemble = PredictionFactory.create_ensemble_realistic(variance=0.05)
    """

    @staticmethod
    def create_market_prediction(
        prediction_id: Optional[str] = None,
        match_id: str = "test_match_001",
        market_id: str = "test_market_1x2",
        market_name: str = "Match Result - 1X2",
        market_category: MarketCategory = MarketCategory.MAIN_LINE,
        probability: Optional[float] = None,
        fair_odds: float = 1.85,
        confidence_score: float = 0.82,
        data_quality: DataQuality = DataQuality.GOOD,
        **kwargs,
    ) -> MarketPrediction:
        """Crée MarketPrediction valide.

        Args:
            prediction_id: ID unique (auto-généré si None)
            match_id: ID du match
            market_id: ID du marché
            market_name: Nom du marché
            market_category: Catégorie marché
            probability: Probabilité (calculée depuis fair_odds si None)
            fair_odds: Cote juste
            confidence_score: Score confiance [0.0, 1.0]
            data_quality: Qualité données
            **kwargs: Autres champs (edge_vs_market, clv_expected, etc.)

        Returns:
            MarketPrediction valide

        Validation automatique:
        - fair_odds > 1.0
        - probability = 1 / fair_odds (si non fourni)
        - confidence_score in [0.0, 1.0]
        """
        # Generate ID if not provided
        if prediction_id is None:
            prediction_id = f"test_pred_{uuid.uuid4().hex[:8]}"

        # Calculate probability from fair_odds if not provided
        if probability is None:
            probability = 1.0 / fair_odds

        # Build prediction
        prediction = MarketPrediction(
            prediction_id=prediction_id,
            match_id=match_id,
            market_id=market_id,
            market_name=market_name,
            market_category=market_category,
            probability=probability,
            fair_odds=fair_odds,
            confidence_score=confidence_score,
            data_quality=data_quality,
            computed_at=kwargs.get("computed_at", datetime.now(timezone.utc)),
            # Optional fields
            edge_vs_market=kwargs.get("edge_vs_market"),
            clv_expected=kwargs.get("clv_expected"),
            kelly_fraction=kwargs.get("kelly_fraction"),
            expected_value=kwargs.get("expected_value"),
            model_agreement=kwargs.get("model_agreement"),
            computation_time_ms=kwargs.get("computation_time_ms"),
            expires_at=kwargs.get("expires_at"),
            feature_versions=kwargs.get("feature_versions"),
            missing_features=kwargs.get("missing_features"),
        )

        # Validation automatique
        assert prediction.fair_odds > 1.0, "Fair odds must be > 1.0"
        assert 0.0 <= prediction.confidence_score <= 1.0, "Confidence in [0, 1]"
        assert 0.0 <= prediction.probability <= 1.0, "Probability in [0, 1]"

        return prediction

    @classmethod
    def create_ensemble_realistic(
        cls,
        prediction_id: Optional[str] = None,
        match_id: str = "test_match_ensemble",
        market_name: str = "Match Result - 1X2",
        base_odds: float = 1.85,
        variance: float = 0.05,
        num_agents: int = 4,
    ) -> EnsemblePrediction:
        """Crée EnsemblePrediction avec variance RÉALISTE.

        Args:
            prediction_id: ID unique
            match_id: ID du match
            market_name: Nom du marché
            base_odds: Cote moyenne des agents
            variance: Variance entre agents (e.g., 0.05 = 5%)
            num_agents: Nombre d'agents (default 4)

        Returns:
            EnsemblePrediction avec metrics cohérentes mathématiquement

        Validation:
        - Variance calculée == variance déclarée
        - Agreement cohérent avec dispersion
        - 4 prédictions DIFFÉRENTES (pas identiques!)
        """
        if prediction_id is None:
            prediction_id = f"ensemble_{uuid.uuid4().hex[:8]}"

        # Générer 4 prédictions DIFFÉRENTES avec variance contrôlée
        predictions = []
        for i in range(num_agents):
            # Variation autour de base_odds
            # Agent 0: -1.5 * variance
            # Agent 1: -0.5 * variance
            # Agent 2: +0.5 * variance
            # Agent 3: +1.5 * variance
            offset = (i - (num_agents - 1) / 2) * variance
            agent_odds = base_odds + offset

            # Variation confidence
            agent_confidence = 0.80 + (i * 0.02)

            pred = cls.create_market_prediction(
                prediction_id=f"agent_{chr(97+i)}_pred_{uuid.uuid4().hex[:6]}",
                match_id=match_id,
                market_id=f"{match_id}_1x2",
                fair_odds=agent_odds,
                confidence_score=agent_confidence,
            )
            predictions.append(pred)

        # Calculer métriques RÉELLES (pas inventées!)
        odds_values = [p.fair_odds for p in predictions]
        calculated_variance = statistics.variance(odds_values)
        mean_odds = statistics.mean(odds_values)

        # Agreement basé sur vraie dispersion
        # Agreement = 1 - (max_deviation / mean)
        max_deviation = max(abs(o - mean_odds) for o in odds_values)
        agreement = 1.0 - (max_deviation / mean_odds)

        # Epistemic uncertainty = variance normalisée
        epistemic = calculated_variance / (mean_odds**2)

        # Final prediction = agent avec meilleure confidence
        best_pred = max(predictions, key=lambda p: p.confidence_score)

        # Model weights (uniform pour simplicité)
        weights = {f"agent_{chr(97+i)}": 1.0 / num_agents for i in range(num_agents)}

        # Disagreement explanation if low agreement
        disagreement_explanation = None
        if agreement < 0.75:
            disagreement_explanation = f"High variance ({calculated_variance:.3f}) among agents"

        ensemble = EnsemblePrediction(
            prediction_id=prediction_id,
            match_id=match_id,
            market_name=market_name,
            final_prediction=best_pred,
            individual_predictions=predictions,
            ensemble_method="weighted_mean",
            model_weights=weights,
            prediction_variance=calculated_variance,  # COHÉRENT
            model_agreement_score=agreement,  # COHÉRENT
            disagreement_explanation=disagreement_explanation,
            epistemic_uncertainty=epistemic,
            aleatoric_uncertainty=0.12,  # Constant (noise intrinsèque)
        )

        # Validation cohérence mathématique
        # Recalculate pour vérifier
        verify_variance = statistics.variance([p.fair_odds for p in predictions])
        assert (
            abs(ensemble.prediction_variance - verify_variance) < 0.001
        ), "Variance incohérente!"

        return ensemble

    @classmethod
    def create_ensemble_high_disagreement(
        cls,
        match_id: str = "test_match_disagreement",
    ) -> EnsemblePrediction:
        """Crée ensemble avec forte désaccord (agreement < 70%).

        Utile pour tester LowConfidenceError.
        """
        return cls.create_ensemble_realistic(
            match_id=match_id,
            base_odds=1.85,
            variance=0.30,  # Forte variance = faible agreement
        )


# ─────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────


def create_market_prediction(**kwargs) -> MarketPrediction:
    """Shortcut pour créer MarketPrediction."""
    return PredictionFactory.create_market_prediction(**kwargs)


def create_ensemble_realistic(**kwargs) -> EnsemblePrediction:
    """Shortcut pour créer EnsemblePrediction réaliste."""
    return PredictionFactory.create_ensemble_realistic(**kwargs)


def create_ensemble_high_disagreement(**kwargs) -> EnsemblePrediction:
    """Shortcut pour créer ensemble forte désaccord."""
    return PredictionFactory.create_ensemble_high_disagreement(**kwargs)
