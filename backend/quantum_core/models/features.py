"""
Feature Models - Hedge Fund Grade Feature Engineering.

Modèles pour la gestion des features avec métadonnées complètes,
tracking de qualité et versioning.

Classes:
    FeatureMetadata: Métadonnées pour une feature spécifique
    TeamFeatures: Features d'une équipe pour un match
    MatchFeatures: Features complètes d'un match (home + away)

Examples:
    >>> meta = FeatureMetadata(
    ...     feature_name="xg_per_90",
    ...     feature_type="continuous",
    ...     source="understat",
    ...     version="2.1.0",
    ...     computed_at=datetime.utcnow(),
    ... )
    >>> team_feat = TeamFeatures(
    ...     team_name="Liverpool",
    ...     xg_per_90=2.14,
    ...     xga_per_90=0.87,
    ...     ppda=8.3,
    ...     feature_metadata=[meta],
    ...     completeness_score=0.95,
    ... )
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


class FeatureType(str, Enum):
    """Type de feature pour le ML.

    Attributes:
        CONTINUOUS: Feature continue (ex: xG, possession)
        CATEGORICAL: Feature catégorielle (ex: form, timing_profile)
        BINARY: Feature binaire (ex: is_starter, is_home)
        ORDINAL: Feature ordinale (ex: rank, position)
    """

    CONTINUOUS = "continuous"
    CATEGORICAL = "categorical"
    BINARY = "binary"
    ORDINAL = "ordinal"


class FeatureSource(str, Enum):
    """Source de données pour une feature.

    Attributes:
        UNDERSTAT: Données Understat (xG, shots)
        FBREF: Données FBRef (stats avancées)
        SOFASCORE: Données SofaScore (ratings, momentum)
        CALCULATED: Feature calculée (dérivée)
        COMPOSITE: Feature composite (plusieurs sources)
    """

    UNDERSTAT = "understat"
    FBREF = "fbref"
    SOFASCORE = "sofascore"
    CALCULATED = "calculated"
    COMPOSITE = "composite"


class FeatureMetadata(BaseModel):
    """Métadonnées pour une feature spécifique.

    Tracking complet de l'origine, version, qualité et fraîcheur des features.
    Essentiel pour la traçabilité Hedge Fund Grade.

    Attributes:
        feature_name: Nom technique de la feature
        feature_type: Type de la feature (continuous, categorical, etc.)
        source: Source de données originale
        version: Version du calcul/extraction de la feature

        computed_at: Timestamp de calcul de la feature
        data_timestamp: Timestamp des données sources
        staleness_seconds: Âge des données en secondes

        is_imputed: Indique si la feature a été imputée
        imputation_method: Méthode d'imputation utilisée
        original_value: Valeur originale avant imputation

        quality_score: Score de qualité [0.0, 1.0]
        confidence: Confiance dans la valeur

        transformations_applied: Transformations appliquées
        normalization_params: Paramètres de normalisation

    Examples:
        >>> meta = FeatureMetadata(
        ...     feature_name="xg_per_90",
        ...     feature_type=FeatureType.CONTINUOUS,
        ...     source=FeatureSource.UNDERSTAT,
        ...     version="2.1.0",
        ...     computed_at=datetime.utcnow(),
        ...     data_timestamp=datetime(2025, 12, 13),
        ...     staleness_seconds=3600,
        ...     quality_score=0.98,
        ...     confidence=0.95,
        ... )
    """

    feature_name: str = Field(..., description="Nom technique de la feature")
    feature_type: FeatureType = Field(..., description="Type de feature")
    source: FeatureSource = Field(..., description="Source de données")
    version: str = Field(..., description="Version du calcul")

    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp de calcul"
    )
    data_timestamp: Optional[datetime] = Field(
        None, description="Timestamp des données sources"
    )
    staleness_seconds: Optional[int] = Field(
        None, ge=0, description="Âge des données (secondes)"
    )

    is_imputed: bool = Field(default=False, description="Feature imputée")
    imputation_method: Optional[str] = Field(
        None, description="Méthode d'imputation (mean, median, forward_fill, etc.)"
    )
    original_value: Optional[Any] = Field(
        None, description="Valeur originale avant imputation"
    )

    quality_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Score de qualité"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confiance dans la valeur"
    )

    transformations_applied: List[str] = Field(
        default_factory=list, description="Transformations appliquées (log, sqrt, etc.)"
    )
    normalization_params: Optional[Dict[str, float]] = Field(
        None, description="Paramètres de normalisation (mean, std, min, max)"
    )

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("computed_at", "data_timestamp", when_used="json")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return dt.isoformat() if dt else None


class TeamFeatures(BaseModel):
    """Features d'une équipe pour un match.

    Contient toutes les features d'une équipe avec métadonnées et score de complétude.

    Attributes:
        team_name: Nom de l'équipe
        team_id: ID technique de l'équipe
        is_home: Indique si l'équipe joue à domicile

        # Attacking Features
        xg_per_90: Expected Goals par 90 minutes
        goals_per_90: Buts réels par 90 minutes
        shots_per_90: Tirs par 90 minutes
        shots_on_target_pct: % tirs cadrés

        # Defensive Features
        xga_per_90: xG Against par 90 minutes
        goals_against_per_90: Buts encaissés par 90 minutes
        ppda: Passes Allowed per Defensive Action
        tackles_per_90: Tacles par 90 minutes

        # Possession & Control
        possession_pct: % possession moyenne
        pass_completion_pct: % passes réussies
        progressive_passes_per_90: Passes progressives par 90

        # Physical & Discipline
        fouls_per_90: Fautes par 90 minutes
        cards_per_90: Cartons par 90 minutes
        corners_per_90: Corners par 90 minutes

        # Form & Momentum
        recent_form: Forme récente (5 derniers matchs)
        points_per_game: Points moyens par match
        win_rate: Taux de victoire

        # Advanced Metrics
        elo_rating: Cote Elo
        fifa_ranking: Classement FIFA
        squad_value_millions: Valeur effectif (millions €)

        # Metadata
        feature_metadata: Liste des métadonnées de toutes les features
        completeness_score: Score de complétude [0.0, 1.0]
        missing_features: Liste des features manquantes
        data_quality: Qualité globale des données

        computed_at: Timestamp de calcul

    Examples:
        >>> team = TeamFeatures(
        ...     team_name="Liverpool",
        ...     team_id="liverpool_fc",
        ...     is_home=True,
        ...     xg_per_90=2.14,
        ...     xga_per_90=0.87,
        ...     possession_pct=63.2,
        ...     ppda=8.3,
        ...     recent_form="WWDWW",
        ...     elo_rating=1987,
        ...     completeness_score=0.95,
        ...     data_quality="excellent",
        ... )
    """

    # Identification
    team_name: str = Field(..., description="Nom de l'équipe")
    team_id: str = Field(..., description="ID technique")
    is_home: bool = Field(..., description="Joue à domicile")

    # Attacking Features
    xg_per_90: Optional[float] = Field(None, ge=0.0, description="xG par 90min")
    goals_per_90: Optional[float] = Field(None, ge=0.0, description="Buts par 90min")
    shots_per_90: Optional[float] = Field(None, ge=0.0, description="Tirs par 90min")
    shots_on_target_pct: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="% tirs cadrés"
    )

    # Defensive Features
    xga_per_90: Optional[float] = Field(None, ge=0.0, description="xGA par 90min")
    goals_against_per_90: Optional[float] = Field(
        None, ge=0.0, description="Buts encaissés par 90min"
    )
    ppda: Optional[float] = Field(None, ge=0.0, description="PPDA")
    tackles_per_90: Optional[float] = Field(
        None, ge=0.0, description="Tacles par 90min"
    )

    # Possession & Control
    possession_pct: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="% possession"
    )
    pass_completion_pct: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="% passes réussies"
    )
    progressive_passes_per_90: Optional[float] = Field(
        None, ge=0.0, description="Passes progressives par 90min"
    )

    # Physical & Discipline
    fouls_per_90: Optional[float] = Field(None, ge=0.0, description="Fautes par 90min")
    cards_per_90: Optional[float] = Field(None, ge=0.0, description="Cartons par 90min")
    corners_per_90: Optional[float] = Field(
        None, ge=0.0, description="Corners par 90min"
    )

    # Form & Momentum
    recent_form: Optional[str] = Field(
        None, pattern="^[WDLWDL]{0,10}$", description="Forme récente (W/D/L)"
    )
    points_per_game: Optional[float] = Field(
        None, ge=0.0, le=3.0, description="Points moyens par match"
    )
    win_rate: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Taux de victoire"
    )

    # Advanced Metrics
    elo_rating: Optional[int] = Field(None, ge=0, le=3000, description="Cote Elo")
    fifa_ranking: Optional[int] = Field(None, ge=1, description="Classement FIFA")
    squad_value_millions: Optional[float] = Field(
        None, ge=0.0, description="Valeur effectif (millions €)"
    )

    # Metadata
    feature_metadata: List[FeatureMetadata] = Field(
        default_factory=list, description="Métadonnées des features"
    )
    completeness_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Score de complétude"
    )
    missing_features: List[str] = Field(
        default_factory=list, description="Features manquantes"
    )
    data_quality: str = Field(
        default="excellent",
        pattern="^(excellent|good|fair|poor)$",
        description="Qualité globale",
    )

    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp de calcul"
    )

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("computed_at", when_used="json")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        return dt.isoformat()


class MatchFeatures(BaseModel):
    """Features complètes d'un match (home + away).

    Agrège les features des deux équipes plus les features de match.

    Attributes:
        match_id: ID unique du match
        competition: Compétition (ex: "Premier League")
        season: Saison (ex: "2025-26")
        match_date: Date du match

        home_team: Features équipe domicile
        away_team: Features équipe extérieur

        # Match Context Features
        h2h_home_wins: Victoires domicile en H2H
        h2h_draws: Nuls en H2H
        h2h_away_wins: Victoires extérieur en H2H
        days_since_last_match_home: Jours repos équipe domicile
        days_since_last_match_away: Jours repos équipe extérieur

        referee: Arbitre du match
        referee_cards_per_90: Cartons moyens de l'arbitre
        referee_penalties_per_90: Pénaltys moyens de l'arbitre

        temperature: Température (°C)
        weather_condition: Conditions météo

        # Derived Features
        xg_differential: xG_home - xG_away
        elo_differential: Elo_home - Elo_away
        value_differential: Valeur_home - Valeur_away

        # Quality Metrics
        overall_completeness: Complétude globale [0.0, 1.0]
        overall_quality: Qualité globale
        feature_count: Nombre total de features
        missing_feature_count: Nombre de features manquantes

        computed_at: Timestamp de calcul
        expires_at: Timestamp d'expiration

    Examples:
        >>> match = MatchFeatures(
        ...     match_id="liverpool_vs_mancity_20251215",
        ...     competition="Premier League",
        ...     season="2025-26",
        ...     match_date=datetime(2025, 12, 15, 15, 0),
        ...     home_team=liverpool_features,
        ...     away_team=mancity_features,
        ...     h2h_home_wins=12,
        ...     h2h_draws=8,
        ...     h2h_away_wins=15,
        ...     xg_differential=0.27,
        ...     elo_differential=-23,
        ...     overall_completeness=0.92,
        ...     overall_quality="excellent",
        ... )
    """

    # Identification
    match_id: str = Field(..., description="ID unique du match")
    competition: str = Field(..., description="Compétition")
    season: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Saison (YYYY-YY)")
    match_date: datetime = Field(..., description="Date du match")

    # Team Features
    home_team: TeamFeatures = Field(..., description="Features équipe domicile")
    away_team: TeamFeatures = Field(..., description="Features équipe extérieur")

    # Head-to-Head
    h2h_home_wins: Optional[int] = Field(
        None, ge=0, description="Victoires domicile H2H"
    )
    h2h_draws: Optional[int] = Field(None, ge=0, description="Nuls H2H")
    h2h_away_wins: Optional[int] = Field(
        None, ge=0, description="Victoires extérieur H2H"
    )

    # Rest & Fatigue
    days_since_last_match_home: Optional[int] = Field(
        None, ge=0, le=30, description="Jours repos domicile"
    )
    days_since_last_match_away: Optional[int] = Field(
        None, ge=0, le=30, description="Jours repos extérieur"
    )

    # Referee
    referee: Optional[str] = Field(None, description="Nom arbitre")
    referee_cards_per_90: Optional[float] = Field(
        None, ge=0.0, description="Cartons moyens arbitre"
    )
    referee_penalties_per_90: Optional[float] = Field(
        None, ge=0.0, description="Pénaltys moyens arbitre"
    )

    # Weather
    temperature: Optional[float] = Field(None, description="Température (°C)")
    weather_condition: Optional[str] = Field(
        None,
        pattern="^(clear|cloudy|rainy|snowy|windy)$",
        description="Conditions météo",
    )

    # Derived Features (auto-calculated)
    xg_differential: Optional[float] = Field(
        None, description="xG_home - xG_away (auto-calculé)"
    )
    elo_differential: Optional[int] = Field(
        None, description="Elo_home - Elo_away (auto-calculé)"
    )
    value_differential: Optional[float] = Field(
        None, description="Valeur_home - Valeur_away (auto-calculé)"
    )

    # Quality Metrics
    overall_completeness: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Complétude globale"
    )
    overall_quality: str = Field(
        default="excellent",
        pattern="^(excellent|good|fair|poor)$",
        description="Qualité globale",
    )
    feature_count: int = Field(default=0, ge=0, description="Nombre total features")
    missing_feature_count: int = Field(
        default=0, ge=0, description="Features manquantes"
    )

    # Timestamps
    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp de calcul"
    )
    expires_at: Optional[datetime] = Field(None, description="Timestamp d'expiration")

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("computed_at", "expires_at", when_used="json")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return dt.isoformat() if dt else None

    @model_validator(mode="after")
    def calculate_differentials(self):
        """Calcule automatiquement les differentials après validation.

        Returns:
            Instance avec differentials calculés
        """
        # xg_differential
        if self.xg_differential is None:
            home_xg = self.home_team.xg_per_90
            away_xg = self.away_team.xg_per_90
            if home_xg is not None and away_xg is not None:
                self.xg_differential = home_xg - away_xg

        # elo_differential
        if self.elo_differential is None:
            home_elo = self.home_team.elo_rating
            away_elo = self.away_team.elo_rating
            if home_elo is not None and away_elo is not None:
                self.elo_differential = home_elo - away_elo

        # value_differential
        if self.value_differential is None:
            home_val = self.home_team.squad_value_millions
            away_val = self.away_team.squad_value_millions
            if home_val is not None and away_val is not None:
                self.value_differential = home_val - away_val

        return self
