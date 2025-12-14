"""Predictions Service - Business Logic Layer.

ADR #008: Service Layer = Business logic orchestration ONLY.
- NO data access (use repository)
- NO HTTP concerns (use by API layer)
- Business rules + orchestration
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
import logging

from quantum_core.models.predictions import (
    MarketPrediction,
    EnsemblePrediction,
    ConfidenceLevel,
    MarketCategory,
    DataQuality,
)
from quantum_core.api.common.exceptions import (
    LowConfidenceError,
    UnifiedBrainError,
    MatchNotFoundError,
    InvalidDateError,
)
from quantum_core.repositories.prediction_repository import PredictionRepository

logger = logging.getLogger(__name__)


class PredictionService:
    """Service pour gérer les prédictions.

    ADR #008: Business logic ONLY (no data access).

    Architecture:
    1. Validation business rules
    2. Orchestration UnifiedBrain
    3. Gestion consensus
    4. Audit trail
    5. Data access via Repository (injected)
    """

    def __init__(
        self,
        repository: Optional[PredictionRepository] = None,
        min_confidence: float = 0.70,
        max_prediction_days: int = 60,
        default_tz: timezone = timezone.utc,
    ):
        """Initialize service.

        Args:
            repository: PredictionRepository (injected for testability)
            min_confidence: Minimum consensus threshold
            max_prediction_days: Maximum days in future
            default_tz: Default timezone (UTC)
        """
        # Repository injection (ADR #008)
        self.repository = repository

        # TODO: Initialize UnifiedBrain orchestrator
        # self.orchestrator = UnifiedBrainOrchestrator()
        # self.agent_a = AnomalyDetectorAgent()
        # self.agent_b = SpreadOptimizerAgent()
        # self.agent_c = PatternMatcherAgent()
        # self.agent_d = BacktestAgent()

        # Configuration (ADR #005)
        self.min_confidence = min_confidence
        self.max_prediction_days = max_prediction_days
        self.default_tz = default_tz

        logger.info(
            f"PredictionService initialized - "
            f"min_confidence={min_confidence}, "
            f"max_days={max_prediction_days}"
        )

    async def generate_match_prediction(
        self,
        match_id: str,
        competition: str,
        match_date: datetime,
        home_team_id: Optional[str] = None,
        away_team_id: Optional[str] = None,
    ) -> EnsemblePrediction:
        """Génère prédiction pour un match via UnifiedBrain V2.8.

        Process Hedge Fund:
        1. Validation date (pas passé, pas trop loin)
        2. Fetch match features (ADN équipes)
        3. Run 4 agents en parallèle
        4. Orchestrator consensus
        5. Validation confidence threshold
        6. Audit trail
        7. Return ensemble

        Args:
            match_id: ID unique du match
            competition: Compétition
            match_date: Date du match
            home_team_id: ID équipe domicile (optionnel)
            away_team_id: ID équipe extérieure (optionnel)

        Returns:
            EnsemblePrediction avec consensus 4 agents

        Raises:
            InvalidDateError: Si date invalide
            MatchNotFoundError: Si match inexistant
            LowConfidenceError: Si consensus < threshold
            UnifiedBrainError: Si erreur agents
        """
        logger.info(f"Generating prediction for match: {match_id}")

        # ─────────────────────────────────────────────────────────────────
        # 1. VALIDATION DATE
        # ─────────────────────────────────────────────────────────────────

        self._validate_match_date(match_date)

        # ─────────────────────────────────────────────────────────────────
        # 2. FETCH MATCH FEATURES
        # ─────────────────────────────────────────────────────────────────

        # TODO: Implement features fetching
        # features = await self.fetch_match_features(match_id)

        # ─────────────────────────────────────────────────────────────────
        # 3. RUN AGENTS (PARALLÈLE) - TODO
        # ─────────────────────────────────────────────────────────────────

        # TODO: Run 4 agents
        # import asyncio
        # predictions = await asyncio.gather(
        #     self.agent_a.predict(features),
        #     self.agent_b.predict(features),
        #     self.agent_c.predict(features),
        #     self.agent_d.predict(features),
        # )

        # ─────────────────────────────────────────────────────────────────
        # 4. ORCHESTRATOR CONSENSUS - TODO
        # ─────────────────────────────────────────────────────────────────

        # TODO: Combine predictions
        # ensemble = self.orchestrator.combine(predictions)

        # MOCK pour développement
        ensemble = self._create_mock_ensemble(match_id, competition)

        # ─────────────────────────────────────────────────────────────────
        # 5. VALIDATION CONFIDENCE
        # ─────────────────────────────────────────────────────────────────

        if ensemble.model_agreement_score < self.min_confidence:
            raise LowConfidenceError(
                f"Model agreement {ensemble.model_agreement_score:.2%} "
                f"below threshold {self.min_confidence:.2%}"
            )

        # ─────────────────────────────────────────────────────────────────
        # 6. PERSIST VIA REPOSITORY (ADR #008)
        # ─────────────────────────────────────────────────────────────────

        # Persist individual predictions
        if self.repository:
            for pred in ensemble.individual_predictions:
                await self.repository.create(pred)

        # ─────────────────────────────────────────────────────────────────
        # 7. AUDIT TRAIL - TODO
        # ─────────────────────────────────────────────────────────────────

        # TODO: Log audit record
        # await self.audit_service.log(
        #     action="PREDICTION_GENERATED",
        #     match_id=match_id,
        #     data=ensemble.model_dump()
        # )

        logger.info(
            f"Prediction generated for {match_id} - "
            f"Agreement: {ensemble.model_agreement_score:.2%}"
        )

        return ensemble

    def _validate_match_date(self, match_date: datetime) -> None:
        """Validate match date (not past, not too far future).

        ADR #005: Fix timezone naive bug.
        - Use timezone-aware datetime (not datetime.utcnow() deprecated)
        - Configurable max_prediction_days (not hardcoded 30)
        """
        # ADR #005: Timezone-aware datetime (fix DST bugs)
        now = datetime.now(self.default_tz)

        # Convert naive datetime to aware if needed
        if match_date.tzinfo is None:
            match_date = match_date.replace(tzinfo=self.default_tz)

        # Pas de match passé
        if match_date < now:
            raise InvalidDateError(f"Match date {match_date} is in the past")

        # Pas trop loin (configurable via Settings)
        max_future = now + timedelta(days=self.max_prediction_days)
        if match_date > max_future:
            raise InvalidDateError(
                f"Match date {match_date} is too far in future "
                f"(>{self.max_prediction_days} days)"
            )

    def _create_mock_ensemble(
        self, match_id: str, competition: str
    ) -> EnsemblePrediction:
        """Create mock ensemble for development.

        TODO: Remove when UnifiedBrain integrated.
        """
        # Mock market prediction (mypy-compliant avec tous les champs)
        mock_prediction = MarketPrediction(
            prediction_id=f"pred_{match_id}",
            match_id=match_id,
            market_id=f"{match_id}_1x2",
            market_name="Match Result - 1X2",
            market_category=MarketCategory.MAIN_LINE,
            probability=0.54,
            fair_odds=1.85,
            confidence_score=0.82,
            data_quality=DataQuality.GOOD,
            # Optional fields for mypy
            edge_vs_market=None,
            clv_expected=None,
            kelly_fraction=None,
            expected_value=None,
            model_agreement=None,
            computation_time_ms=None,
            expires_at=None,
            feature_versions=None,
            missing_features=None,
        )

        # Mock ensemble (mypy-compliant)
        ensemble = EnsemblePrediction(
            prediction_id=f"ensemble_{match_id}",
            match_id=match_id,
            market_name="Match Result - 1X2",
            final_prediction=mock_prediction,
            individual_predictions=[
                mock_prediction,
                mock_prediction,
                mock_prediction,
                mock_prediction,
            ],  # 4 agents
            ensemble_method="weighted_mean",
            model_weights={
                "agent_a": 0.25,
                "agent_b": 0.25,
                "agent_c": 0.25,
                "agent_d": 0.25,
            },
            prediction_variance=0.015,
            model_agreement_score=0.88,
            epistemic_uncertainty=0.08,
            aleatoric_uncertainty=0.12,
            # Optional field for mypy
            disagreement_explanation=None,
        )

        return ensemble

    async def get_prediction_by_id(
        self, prediction_id: str
    ) -> Optional[MarketPrediction]:
        """Récupère prédiction par ID.

        ADR #008: Delegate to repository.
        """
        if self.repository is None:
            # Fallback if no repository (dev mode)
            logger.warning("No repository configured - returning None")
            return None

        return await self.repository.get_by_id(prediction_id)

    async def list_predictions(
        self,
        match_id: Optional[str] = None,
        competition: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[MarketPrediction]:
        """Liste prédictions avec filtres.

        ADR #008: Delegate to repository.
        """
        if self.repository is None:
            logger.warning("No repository configured - returning []")
            return []

        filters = {}
        if match_id:
            filters["match_id"] = match_id
        # TODO: Add more filters (competition, date range)

        return await self.repository.list(filters, limit)

    async def update_prediction(
        self,
        prediction_id: str,
        fair_odds: Optional[float] = None,
        confidence_score: Optional[float] = None,
        confidence_level: Optional[ConfidenceLevel] = None,
    ) -> MarketPrediction:
        """Override manuel d'une prédiction.

        ADR #008: Delegate to repository.
        """
        if self.repository is None:
            raise NotImplementedError("No repository configured")

        data = {}
        if fair_odds is not None:
            data["fair_odds"] = fair_odds
        if confidence_score is not None:
            data["confidence_score"] = confidence_score
        # TODO: Handle confidence_level

        return await self.repository.update(prediction_id, data)

    async def get_brain_health(self) -> dict:
        """Health check UnifiedBrain.

        TODO: Implement actual health check.
        """
        return {
            "status": "healthy",
            "agents_available": ["agent_a", "agent_b", "agent_c", "agent_d"],
            "orchestrator_status": "ready",
            "last_prediction": datetime.now(self.default_tz),
        }
