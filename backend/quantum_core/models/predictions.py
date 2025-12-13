"""
Prediction Models - Hedge Fund Grade TypeSafe Predictions.

Ce module contient les modèles Pydantic pour toutes les prédictions du système Mon_PS.
Traçabilité complète, métadonnées exhaustives, validation stricte.

Classes:
    MarketCategory: Enum des catégories de marchés
    ConfidenceLevel: Enum des niveaux de confiance
    DataQuality: Enum de la qualité des données
    MarketPrediction: Prédiction pour un marché spécifique
    EnsemblePrediction: Prédiction combinant plusieurs modèles
    GoalscorerPrediction: Prédiction pour les marchés buteurs

Examples:
    >>> pred = MarketPrediction(
    ...     prediction_id="uuid-123",
    ...     match_id="match-456",
    ...     market_id="btts_yes",
    ...     market_name="Both Teams To Score - Yes",
    ...     market_category=MarketCategory.MAIN_LINE,
    ...     probability=0.68,
    ...     fair_odds=1.47,
    ...     confidence_score=0.82,
    ... )
    >>> pred.confidence_level
    <ConfidenceLevel.HIGH: 'high'>
"""

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
    field_serializer,
)
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MarketCategory(str, Enum):
    """Catégorie de marché sportif.

    Attributes:
        MAIN_LINE: Marchés principaux (1X2, BTTS, O/U)
        ALTERNATIVE: Marchés alternatifs (Corners, Cards, etc.)
        PLAYER_PROP: Propositions joueurs (Buteur, Assists, etc.)
        EXOTIC: Marchés exotiques (Score Exact, Double Result, etc.)
    """

    MAIN_LINE = "main_line"
    ALTERNATIVE = "alternative"
    PLAYER_PROP = "player_prop"
    EXOTIC = "exotic"


class ConfidenceLevel(str, Enum):
    """Niveau de confiance dans une prédiction.

    Basé sur le confidence_score:
        VERY_HIGH: > 0.85
        HIGH: 0.70 - 0.85
        MEDIUM: 0.50 - 0.70
        LOW: < 0.50
    """

    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DataQuality(str, Enum):
    """Qualité des données sources pour la prédiction.

    Basé sur le pourcentage de features disponibles:
        EXCELLENT: 100% features disponibles
        GOOD: 80-99%
        FAIR: 60-79%
        POOR: < 60%
    """

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class MarketPrediction(BaseModel):
    """Prédiction pour un marché spécifique.

    Modèle complet avec traçabilité Hedge Fund Grade. Inclut les probabilités,
    cotes, edge, confiance, métadonnées et contexte complet.

    Attributes:
        prediction_id: UUID unique de la prédiction
        match_id: ID du match
        market_id: ID technique du marché (ex: "btts_yes")
        market_name: Nom lisible du marché (ex: "Both Teams To Score - Yes")
        market_category: Catégorie du marché

        probability: Probabilité prédite [0.0, 1.0]
        fair_odds: Cote fair calculée (> 1.0)
        implied_probability: Probabilité implicite (1 / fair_odds)

        edge_vs_market: Edge vs cote bookmaker (%)
        clv_expected: Closing Line Value attendu (%)
        kelly_fraction: Fraction Kelly recommandée [0.0, 0.25]
        expected_value: Valeur attendue (EV) de la mise

        confidence_score: Score de confiance [0.0, 1.0]
        confidence_level: Niveau de confiance (auto-calculé)
        data_quality: Qualité des données sources
        model_agreement: Accord entre modèles [0.0, 1.0]

        model_version: Version du modèle (ex: "unified_brain_v2.8")
        model_components: Liste des composants utilisés
        computation_time_ms: Temps de calcul en millisecondes
        cache_hit: Indique si résultat vient du cache

        contributing_factors: Facteurs contribuant à la prédiction
        warning_flags: Drapeaux d'avertissement

        computed_at: Timestamp de calcul
        expires_at: Timestamp d'expiration

        feature_versions: Versions des features utilisées
        missing_features: Liste des features manquantes

    Examples:
        >>> pred = MarketPrediction(
        ...     prediction_id="550e8400-e29b-41d4-a716-446655440000",
        ...     match_id="liverpool_vs_mancity_20251215",
        ...     market_id="btts_yes",
        ...     market_name="Both Teams To Score - Yes",
        ...     market_category=MarketCategory.MAIN_LINE,
        ...     probability=0.72,
        ...     fair_odds=1.389,
        ...     confidence_score=0.85,
        ...     data_quality=DataQuality.EXCELLENT,
        ... )
        >>> pred.implied_probability
        0.72
        >>> pred.confidence_level
        <ConfidenceLevel.HIGH: 'high'>
    """

    # Identification
    prediction_id: str = Field(..., description="UUID de la prédiction")
    match_id: str = Field(..., description="ID du match")
    market_id: str = Field(..., description="ID technique du marché")
    market_name: str = Field(..., description="Nom lisible du marché")
    market_category: MarketCategory = Field(..., description="Catégorie du marché")

    # Probabilités & Odds
    probability: float = Field(..., ge=0.0, le=1.0, description="Probabilité prédite")
    fair_odds: float = Field(..., gt=1.0, description="Cote fair calculée")
    implied_probability: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Probabilité implicite (auto-calculée)"
    )

    # Edge & Value
    edge_vs_market: Optional[float] = Field(
        None, description="Edge vs cote bookmaker (%)"
    )
    clv_expected: Optional[float] = Field(
        None, description="Closing Line Value attendu (%)"
    )
    kelly_fraction: Optional[float] = Field(
        None, ge=0.0, le=0.25, description="Fraction Kelly recommandée"
    )
    expected_value: Optional[float] = Field(
        None, description="Valeur attendue (EV) de la mise"
    )

    # Confiance & Qualité
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Score de confiance"
    )
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.LOW, description="Niveau de confiance (auto-calculé)"
    )
    data_quality: DataQuality = Field(..., description="Qualité des données sources")
    model_agreement: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Accord entre modèles"
    )

    # Métadonnées
    model_version: str = Field(
        default="unified_brain_v2.8", description="Version du modèle"
    )
    model_components: List[str] = Field(
        default_factory=list, description="Composants du modèle utilisés"
    )
    computation_time_ms: Optional[int] = Field(
        None, ge=0, description="Temps de calcul (ms)"
    )
    cache_hit: bool = Field(default=False, description="Résultat vient du cache")

    # Contexte
    contributing_factors: List[str] = Field(
        default_factory=list, description="Facteurs contribuant à la prédiction"
    )
    warning_flags: List[str] = Field(
        default_factory=list, description="Drapeaux d'avertissement"
    )

    # Timestamps
    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp de calcul"
    )
    expires_at: Optional[datetime] = Field(None, description="Timestamp d'expiration")

    # Features
    feature_versions: Optional[Dict[str, str]] = Field(
        None, description="Versions des features utilisées"
    )
    missing_features: Optional[List[str]] = Field(
        None, description="Features manquantes"
    )

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("computed_at", "expires_at", when_used="json")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return dt.isoformat() if dt else None

    @model_validator(mode="after")
    def calculate_derived_fields(self):
        """Calcule les champs dérivés après validation.

        Returns:
            Instance avec champs calculés
        """
        # Calcul implied_probability
        if self.implied_probability == 0.0 and self.fair_odds > 1.0:
            self.implied_probability = 1.0 / self.fair_odds

        # Calcul confidence_level
        score = self.confidence_score
        if score > 0.85:
            self.confidence_level = ConfidenceLevel.VERY_HIGH
        elif score > 0.70:
            self.confidence_level = ConfidenceLevel.HIGH
        elif score > 0.50:
            self.confidence_level = ConfidenceLevel.MEDIUM
        else:
            self.confidence_level = ConfidenceLevel.LOW

        return self


class EnsemblePrediction(BaseModel):
    """Prédiction combinant plusieurs modèles.

    Agrège les prédictions de plusieurs modèles avec méthode d'ensemble,
    tracking de la variance et de l'incertitude.

    Attributes:
        prediction_id: UUID unique de la prédiction ensemble
        match_id: ID du match
        market_name: Nom du marché

        final_prediction: Prédiction finale agrégée
        individual_predictions: Liste des prédictions individuelles

        ensemble_method: Méthode d'ensemble utilisée (mean, weighted, etc.)
        model_weights: Poids de chaque modèle {model_name: weight}

        prediction_variance: Variance entre prédictions individuelles
        model_agreement_score: Score d'accord entre modèles [0.0, 1.0]
        disagreement_explanation: Explication si désaccord significatif

        epistemic_uncertainty: Incertitude épistémique (manque de connaissance)
        aleatoric_uncertainty: Incertitude aléatoire (inhérente)

        computed_at: Timestamp de calcul

    Examples:
        >>> ensemble = EnsemblePrediction(
        ...     prediction_id="ensemble-123",
        ...     match_id="match-456",
        ...     market_name="Over 2.5 Goals",
        ...     final_prediction=final_pred,
        ...     individual_predictions=[pred1, pred2, pred3],
        ...     ensemble_method="weighted_mean",
        ...     model_weights={"model_a": 0.4, "model_b": 0.35, "model_c": 0.25},
        ...     prediction_variance=0.012,
        ...     model_agreement_score=0.92,
        ...     epistemic_uncertainty=0.05,
        ...     aleatoric_uncertainty=0.08,
        ... )
    """

    prediction_id: str = Field(..., description="UUID de la prédiction ensemble")
    match_id: str = Field(..., description="ID du match")
    market_name: str = Field(..., description="Nom du marché")

    final_prediction: MarketPrediction = Field(
        ..., description="Prédiction finale agrégée"
    )
    individual_predictions: List[MarketPrediction] = Field(
        ..., min_length=1, description="Prédictions individuelles"
    )

    ensemble_method: str = Field(
        ..., description="Méthode d'ensemble (mean, weighted, stacking, etc.)"
    )
    model_weights: Dict[str, float] = Field(..., description="Poids de chaque modèle")

    prediction_variance: float = Field(
        ..., ge=0.0, description="Variance entre prédictions"
    )
    model_agreement_score: float = Field(
        ..., ge=0.0, le=1.0, description="Score d'accord entre modèles"
    )
    disagreement_explanation: Optional[str] = Field(
        None, description="Explication si désaccord significatif"
    )

    epistemic_uncertainty: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Incertitude épistémique (manque de connaissance)",
    )
    aleatoric_uncertainty: float = Field(
        ..., ge=0.0, le=1.0, description="Incertitude aléatoire (inhérente)"
    )

    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp de calcul"
    )

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("computed_at", when_used="json")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        return dt.isoformat()


class GoalscorerPrediction(BaseModel):
    """Prédiction pour les marchés buteur (Anytime/First/Last).

    Modèle spécialisé pour les prédictions de buteur incluant le profil timing,
    la forme récente et l'historique vs adversaire.

    Attributes:
        player_id: ID unique du joueur
        player_name: Nom du joueur
        team: Équipe du joueur
        position: Position (FW, MF, DF, GK)

        anytime_probability: Probabilité de marquer à n'importe quel moment
        first_probability: Probabilité de marquer en premier
        last_probability: Probabilité de marquer en dernier

        goals_per_90: Moyenne de buts par 90 minutes
        xg_per_90: xG moyen par 90 minutes
        minutes_expected: Minutes attendues dans ce match

        timing_profile: Profil timing (EARLY_BIRD, CLUTCH, DIESEL, CONSISTENT)
        first_goal_share: % de ses buts qui sont des premiers buts d'équipe

        is_starter: Indique si le joueur est titulaire
        recent_form: Forme récente (HOT, WARM, COLD, FROZEN)
        vs_opponent_history: Historique vs cet adversaire

        data_quality: Qualité des données
        confidence_score: Score de confiance
        computed_at: Timestamp de calcul

    Examples:
        >>> gs_pred = GoalscorerPrediction(
        ...     player_id="haaland_9",
        ...     player_name="Erling Haaland",
        ...     team="Manchester City",
        ...     position="FW",
        ...     anytime_probability=0.68,
        ...     first_probability=0.28,
        ...     last_probability=0.15,
        ...     goals_per_90=1.12,
        ...     xg_per_90=0.98,
        ...     minutes_expected=85,
        ...     timing_profile="EARLY_BIRD",
        ...     first_goal_share=0.53,
        ...     is_starter=True,
        ...     recent_form="HOT",
        ...     data_quality=DataQuality.EXCELLENT,
        ...     confidence_score=0.88,
        ... )
    """

    player_id: str = Field(..., description="ID unique du joueur")
    player_name: str = Field(..., description="Nom du joueur")
    team: str = Field(..., description="Équipe du joueur")
    position: str = Field(
        ..., pattern="^(FW|MF|DF|GK)$", description="Position (FW/MF/DF/GK)"
    )

    anytime_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Probabilité Anytime Goalscorer"
    )
    first_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Probabilité First Goalscorer"
    )
    last_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Probabilité Last Goalscorer"
    )

    goals_per_90: float = Field(..., ge=0.0, description="Buts par 90 minutes")
    xg_per_90: float = Field(..., ge=0.0, description="xG par 90 minutes")
    minutes_expected: int = Field(..., ge=0, le=120, description="Minutes attendues")

    timing_profile: str = Field(
        ...,
        pattern="^(EARLY_BIRD|CLUTCH|DIESEL|CONSISTENT)$",
        description="Profil timing",
    )
    first_goal_share: float = Field(
        ..., ge=0.0, le=1.0, description="% de ses buts en tant que 1er but équipe"
    )

    is_starter: bool = Field(..., description="Est titulaire")
    recent_form: str = Field(
        ..., pattern="^(HOT|WARM|COLD|FROZEN)$", description="Forme récente"
    )
    vs_opponent_history: Optional[Dict[str, Any]] = Field(
        None, description="Historique vs adversaire"
    )

    data_quality: DataQuality = Field(..., description="Qualité des données")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Score de confiance"
    )
    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp de calcul"
    )

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("computed_at", when_used="json")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        return dt.isoformat()
