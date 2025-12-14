"""Test Data Factories - ADR #007.

Provides factories for creating test data with mathematical coherence.
"""

from tests.factories.prediction_factory import (
    PredictionFactory,
    create_market_prediction,
    create_ensemble_realistic,
    create_ensemble_high_disagreement,
)

__all__ = [
    "PredictionFactory",
    "create_market_prediction",
    "create_ensemble_realistic",
    "create_ensemble_high_disagreement",
]
