"""
Risk Models - Hedge Fund Grade Risk Management.

Modèles pour la gestion du risque portfolio incluant sizing, VaR,
et métriques de risque avancées.

Classes:
    PortfolioRisk: Analyse de risque du portfolio complet
    PositionSize: Calcul de taille de position Kelly/Fixed
    VaRCalculation: Calcul de Value at Risk (VaR)

Examples:
    >>> var = VaRCalculation(
    ...     confidence_level=0.95,
    ...     var_amount=250.0,
    ...     cvar_amount=380.0,
    ...     method="historical",
    ... )
    >>> position = PositionSize(
    ...     market_id="btts_yes",
    ...     recommended_stake=125.50,
    ...     kelly_fraction=0.048,
    ...     sizing_method="kelly",
    ...     max_risk_pct=2.5,
    ... )
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SizingMethod(str, Enum):
    """Méthode de calcul de taille de position.

    Attributes:
        KELLY: Critère de Kelly (optimal long terme)
        HALF_KELLY: Demi-Kelly (plus conservateur)
        QUARTER_KELLY: Quart de Kelly (très conservateur)
        FIXED: Montant fixe par pari
        FIXED_PCT: Pourcentage fixe du bankroll
    """

    KELLY = "kelly"
    HALF_KELLY = "half_kelly"
    QUARTER_KELLY = "quarter_kelly"
    FIXED = "fixed"
    FIXED_PCT = "fixed_pct"


class RiskLevel(str, Enum):
    """Niveau de risque d'une position ou du portfolio.

    Attributes:
        LOW: Risque faible (< 1% bankroll)
        MEDIUM: Risque moyen (1-2.5%)
        HIGH: Risque élevé (2.5-5%)
        VERY_HIGH: Risque très élevé (> 5%)
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class VaRMethod(str, Enum):
    """Méthode de calcul du VaR.

    Attributes:
        HISTORICAL: VaR historique (distribution empirique)
        PARAMETRIC: VaR paramétrique (assume normalité)
        MONTE_CARLO: VaR Monte Carlo (simulations)
    """

    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"


class PositionSize(BaseModel):
    """Calcul de taille de position pour un marché.

    Détermine la taille optimale d'une position basée sur edge,
    volatilité et contraintes de risque.

    Attributes:
        market_id: ID du marché
        market_name: Nom du marché

        recommended_stake: Mise recommandée (€)
        recommended_stake_pct: Mise recommandée (% bankroll)
        max_stake: Mise maximale autorisée (€)
        min_stake: Mise minimale autorisée (€)

        kelly_fraction: Fraction Kelly calculée [0.0, 1.0]
        kelly_multiplier: Multiplicateur appliqué (0.5 = half-kelly)
        sizing_method: Méthode de sizing utilisée

        edge_pct: Edge estimé (%)
        expected_value: EV de la mise
        probability: Probabilité estimée
        fair_odds: Cote fair
        market_odds: Cote bookmaker

        max_risk_pct: Risque max autorisé (% bankroll)
        risk_level: Niveau de risque de cette position

        bankroll: Bankroll actuel (€)
        portfolio_exposure: Exposition totale actuelle (€)
        portfolio_exposure_pct: Exposition totale (%)

        constraints_applied: Contraintes appliquées
        warnings: Avertissements

        computed_at: Timestamp de calcul

    Examples:
        >>> position = PositionSize(
        ...     market_id="btts_yes",
        ...     market_name="Both Teams To Score - Yes",
        ...     recommended_stake=125.50,
        ...     recommended_stake_pct=1.25,
        ...     max_stake=250.0,
        ...     min_stake=10.0,
        ...     kelly_fraction=0.048,
        ...     kelly_multiplier=0.5,
        ...     sizing_method=SizingMethod.HALF_KELLY,
        ...     edge_pct=12.5,
        ...     expected_value=15.69,
        ...     probability=0.68,
        ...     fair_odds=1.47,
        ...     market_odds=1.72,
        ...     max_risk_pct=2.5,
        ...     risk_level=RiskLevel.MEDIUM,
        ...     bankroll=10000.0,
        ...     portfolio_exposure=1250.0,
        ...     portfolio_exposure_pct=12.5,
        ... )
    """

    # Identification
    market_id: str = Field(..., description="ID du marché")
    market_name: str = Field(..., description="Nom du marché")

    # Stakes
    recommended_stake: float = Field(..., ge=0.0, description="Mise recommandée (€)")
    recommended_stake_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Mise recommandée (% bankroll)"
    )
    max_stake: float = Field(..., ge=0.0, description="Mise maximale (€)")
    min_stake: float = Field(..., ge=0.0, description="Mise minimale (€)")

    # Kelly & Sizing
    kelly_fraction: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction Kelly calculée"
    )
    kelly_multiplier: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Multiplicateur Kelly"
    )
    sizing_method: SizingMethod = Field(..., description="Méthode de sizing")

    # Edge & Value
    edge_pct: float = Field(..., description="Edge estimé (%)")
    expected_value: float = Field(..., description="EV de la mise (€)")
    probability: float = Field(..., ge=0.0, le=1.0, description="Probabilité estimée")
    fair_odds: float = Field(..., gt=1.0, description="Cote fair")
    market_odds: float = Field(..., gt=1.0, description="Cote bookmaker")

    # Risk
    max_risk_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Risque max (% bankroll)"
    )
    risk_level: RiskLevel = Field(..., description="Niveau de risque")

    # Portfolio Context
    bankroll: float = Field(..., gt=0.0, description="Bankroll actuel (€)")
    portfolio_exposure: float = Field(
        ..., ge=0.0, description="Exposition totale actuelle (€)"
    )
    portfolio_exposure_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Exposition totale (%)"
    )

    # Constraints & Warnings
    constraints_applied: List[str] = Field(
        default_factory=list,
        description="Contraintes appliquées (max_risk, max_exposure, etc.)",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Avertissements (high_exposure, low_edge, etc.)",
    )

    # Timestamp
    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp de calcul"
    )

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("computed_at", when_used="json")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        return dt.isoformat()

    @field_validator("risk_level", mode="before")
    @classmethod
    def assign_risk_level(cls, v: Any, info) -> RiskLevel:
        """Assigne automatiquement le niveau de risque.

        Args:
            v: Valeur fournie
            info: Contexte de validation

        Returns:
            Niveau de risque calculé
        """
        if "recommended_stake_pct" in info.data:
            pct = info.data["recommended_stake_pct"]
            if pct < 1.0:
                return RiskLevel.LOW
            elif pct < 2.5:
                return RiskLevel.MEDIUM
            elif pct < 5.0:
                return RiskLevel.HIGH
            else:
                return RiskLevel.VERY_HIGH
        return v if isinstance(v, RiskLevel) else RiskLevel.LOW


class VaRCalculation(BaseModel):
    """Calcul de Value at Risk (VaR) et Conditional VaR.

    Mesure le risque maximum sur un horizon temporel avec un niveau
    de confiance donné.

    Attributes:
        confidence_level: Niveau de confiance (ex: 0.95 = 95%)
        time_horizon_days: Horizon temporel (jours)

        var_amount: VaR en € (perte max probable)
        var_pct: VaR en % du bankroll
        cvar_amount: CVaR (Expected Shortfall) en €
        cvar_pct: CVaR en % du bankroll

        method: Méthode de calcul (historical, parametric, monte_carlo)
        observations_used: Nombre d'observations utilisées
        simulation_runs: Nombre de simulations (si Monte Carlo)

        worst_loss_observed: Pire perte observée (€)
        worst_loss_pct: Pire perte observée (%)
        best_gain_observed: Meilleur gain observé (€)
        best_gain_pct: Meilleur gain observé (%)

        mean_return: Rendement moyen
        std_dev: Écart-type des rendements
        sharpe_ratio: Ratio de Sharpe
        sortino_ratio: Ratio de Sortino

        computed_at: Timestamp de calcul
        based_on_data_from: Date début des données
        based_on_data_to: Date fin des données

    Examples:
        >>> var = VaRCalculation(
        ...     confidence_level=0.95,
        ...     time_horizon_days=1,
        ...     var_amount=250.0,
        ...     var_pct=2.5,
        ...     cvar_amount=380.0,
        ...     cvar_pct=3.8,
        ...     method=VaRMethod.HISTORICAL,
        ...     observations_used=500,
        ...     worst_loss_observed=-450.0,
        ...     worst_loss_pct=-4.5,
        ...     mean_return=0.035,
        ...     std_dev=0.12,
        ...     sharpe_ratio=0.29,
        ... )
    """

    # Configuration
    confidence_level: float = Field(
        ..., ge=0.0, le=1.0, description="Niveau de confiance (ex: 0.95)"
    )
    time_horizon_days: int = Field(
        default=1, ge=1, le=365, description="Horizon temporel (jours)"
    )

    # VaR & CVaR
    var_amount: float = Field(..., description="VaR en € (perte max probable)")
    var_pct: float = Field(..., description="VaR en % du bankroll")
    cvar_amount: float = Field(..., description="CVaR (Expected Shortfall) en €")
    cvar_pct: float = Field(..., description="CVaR en % du bankroll")

    # Calculation Details
    method: VaRMethod = Field(..., description="Méthode de calcul")
    observations_used: int = Field(..., ge=1, description="Observations utilisées")
    simulation_runs: Optional[int] = Field(
        None, ge=1000, description="Simulations (si Monte Carlo)"
    )

    # Extremes
    worst_loss_observed: float = Field(..., description="Pire perte observée (€)")
    worst_loss_pct: float = Field(..., description="Pire perte observée (%)")
    best_gain_observed: float = Field(..., description="Meilleur gain observé (€)")
    best_gain_pct: float = Field(..., description="Meilleur gain observé (%)")

    # Performance Metrics
    mean_return: float = Field(..., description="Rendement moyen")
    std_dev: float = Field(..., ge=0.0, description="Écart-type des rendements")
    sharpe_ratio: Optional[float] = Field(None, description="Ratio de Sharpe")
    sortino_ratio: Optional[float] = Field(None, description="Ratio de Sortino")

    # Timestamps
    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp de calcul"
    )
    based_on_data_from: Optional[datetime] = Field(
        None, description="Date début données"
    )
    based_on_data_to: Optional[datetime] = Field(None, description="Date fin données")

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer(
        "computed_at", "based_on_data_from", "based_on_data_to", when_used="json"
    )
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return dt.isoformat() if dt else None


class PortfolioRisk(BaseModel):
    """Analyse de risque du portfolio complet.

    Agrège toutes les métriques de risque du portfolio incluant
    exposition, concentration, corrélations et VaR.

    Attributes:
        portfolio_id: ID du portfolio
        bankroll: Bankroll total (€)
        currency: Devise (EUR, USD, etc.)

        total_exposure: Exposition totale (€)
        total_exposure_pct: Exposition totale (% bankroll)
        active_positions_count: Nombre de positions actives
        markets_exposed: Liste des marchés exposés

        largest_position_amount: Taille plus grosse position (€)
        largest_position_pct: Taille plus grosse position (%)
        concentration_ratio: Ratio de concentration (top 3 / total)

        var_1day_95: VaR 1 jour 95%
        var_7day_95: VaR 7 jours 95%
        cvar_1day_95: CVaR 1 jour 95%

        correlation_exposure: Exposition à des marchés corrélés (€)
        correlation_risk_score: Score de risque corrélation [0.0, 1.0]

        risk_adjusted_return: Rendement ajusté du risque (Sharpe)
        kelly_leverage: Levier Kelly global du portfolio

        max_exposure_limit: Limite d'exposition max (€)
        max_exposure_limit_pct: Limite d'exposition max (%)
        available_capital: Capital disponible (€)
        capital_utilization_pct: Utilisation du capital (%)

        risk_warnings: Avertissements de risque
        risk_score: Score de risque global [0.0, 10.0]
        risk_level: Niveau de risque global

        computed_at: Timestamp de calcul

    Examples:
        >>> portfolio = PortfolioRisk(
        ...     portfolio_id="main_portfolio",
        ...     bankroll=10000.0,
        ...     currency="EUR",
        ...     total_exposure=1250.0,
        ...     total_exposure_pct=12.5,
        ...     active_positions_count=8,
        ...     largest_position_amount=250.0,
        ...     largest_position_pct=2.5,
        ...     concentration_ratio=0.48,
        ...     var_1day_95=VaRCalculation(...),
        ...     correlation_risk_score=0.35,
        ...     risk_score=4.2,
        ...     risk_level=RiskLevel.MEDIUM,
        ... )
    """

    # Identification
    portfolio_id: str = Field(..., description="ID du portfolio")
    bankroll: float = Field(..., gt=0.0, description="Bankroll total (€)")
    currency: str = Field(
        default="EUR", pattern="^(EUR|USD|GBP)$", description="Devise"
    )

    # Exposure
    total_exposure: float = Field(..., ge=0.0, description="Exposition totale (€)")
    total_exposure_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Exposition totale (%)"
    )
    active_positions_count: int = Field(..., ge=0, description="Positions actives")
    markets_exposed: List[str] = Field(
        default_factory=list, description="Marchés exposés"
    )

    # Concentration
    largest_position_amount: float = Field(
        ..., ge=0.0, description="Plus grosse position (€)"
    )
    largest_position_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Plus grosse position (%)"
    )
    concentration_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Ratio concentration (top 3 / total)"
    )

    # VaR
    var_1day_95: VaRCalculation = Field(..., description="VaR 1 jour 95%")
    var_7day_95: Optional[VaRCalculation] = Field(None, description="VaR 7 jours 95%")
    cvar_1day_95: Optional[float] = Field(None, description="CVaR 1 jour 95% (€)")

    # Correlation
    correlation_exposure: float = Field(
        ..., ge=0.0, description="Exposition marchés corrélés (€)"
    )
    correlation_risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Score risque corrélation"
    )

    # Performance
    risk_adjusted_return: Optional[float] = Field(
        None, description="Rendement ajusté risque (Sharpe)"
    )
    kelly_leverage: Optional[float] = Field(
        None, ge=0.0, description="Levier Kelly global"
    )

    # Limits & Available Capital
    max_exposure_limit: float = Field(..., gt=0.0, description="Limite exposition (€)")
    max_exposure_limit_pct: float = Field(
        ..., gt=0.0, le=100.0, description="Limite exposition (%)"
    )
    available_capital: float = Field(..., ge=0.0, description="Capital disponible (€)")
    capital_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Utilisation capital (%)"
    )

    # Risk Assessment
    risk_warnings: List[str] = Field(
        default_factory=list, description="Avertissements de risque"
    )
    risk_score: float = Field(
        ..., ge=0.0, le=10.0, description="Score risque global [0-10]"
    )
    risk_level: RiskLevel = Field(..., description="Niveau de risque global")

    # Timestamp
    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp de calcul"
    )

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("computed_at", when_used="json")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        return dt.isoformat()
