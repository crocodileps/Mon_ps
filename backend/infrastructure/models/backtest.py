"""
Backtest Models - Hedge Fund Grade Backtesting.

Modèles pour les requêtes et résultats de backtesting avec métriques
complètes de performance et analyse de risque.

Classes:
    BacktestRequest: Configuration d'un backtest
    BacktestResult: Résultats complets d'un backtest

Examples:
    >>> request = BacktestRequest(
    ...     name="UnifiedBrain V2.8 - Premier League",
    ...     strategy_name="unified_brain_v2.8",
    ...     start_date=datetime(2024, 8, 1),
    ...     end_date=datetime(2025, 5, 31),
    ...     initial_bankroll=10000.0,
    ...     markets_filter=["btts_yes", "over_25"],
    ...     min_edge_pct=5.0,
    ... )
    >>> result = BacktestResult(
    ...     request=request,
    ...     total_bets=456,
    ...     winning_bets=312,
    ...     final_bankroll=14523.50,
    ...     total_return_pct=45.23,
    ...     sharpe_ratio=1.82,
    ...     max_drawdown_pct=8.7,
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


class BacktestStatus(str, Enum):
    """Statut d'un backtest.

    Attributes:
        PENDING: En attente
        RUNNING: En cours d'exécution
        COMPLETED: Terminé avec succès
        FAILED: Échoué
        CANCELLED: Annulé
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SizingStrategy(str, Enum):
    """Stratégie de sizing pour le backtest.

    Attributes:
        KELLY: Critère de Kelly
        HALF_KELLY: Demi-Kelly
        FIXED: Montant fixe
        FIXED_PCT: Pourcentage fixe
    """

    KELLY = "kelly"
    HALF_KELLY = "half_kelly"
    FIXED = "fixed"
    FIXED_PCT = "fixed_pct"


class BacktestRequest(BaseModel):
    """Configuration d'un backtest.

    Définit tous les paramètres pour exécuter un backtest: période,
    stratégie, filtres, sizing, etc.

    Architecture Decision Records appliqués:
    - ADR #003: field_serializer pour start_date, end_date, created_at

    Attributes:
        backtest_id: ID unique du backtest
        name: Nom descriptif du backtest
        description: Description détaillée

        strategy_name: Nom de la stratégie à tester
        strategy_version: Version de la stratégie

        start_date: Date de début du backtest
        end_date: Date de fin du backtest
        competitions: Compétitions à inclure (None = toutes)
        markets_filter: Marchés à inclure (None = tous)

        initial_bankroll: Bankroll initial (€)
        sizing_strategy: Stratégie de sizing
        kelly_multiplier: Multiplicateur Kelly (si applicable)
        max_stake_pct: Mise max en % du bankroll
        min_stake: Mise minimale (€)
        max_stake: Mise maximale (€)

        min_edge_pct: Edge minimum requis (%)
        min_confidence: Confiance minimale requise [0.0, 1.0]
        max_positions: Nombre max de positions simultanées
        min_odds: Cote minimale acceptée
        max_odds: Cote maximale acceptée

        use_closing_odds: Utiliser les cotes de closing (CLV)
        include_commission: Inclure la commission
        commission_pct: Taux de commission (%)

        created_at: Timestamp de création
        created_by: Créateur du backtest

    Examples:
        >>> request = BacktestRequest(
        ...     backtest_id="bt-123",
        ...     name="UnifiedBrain V2.8 - Full Season",
        ...     strategy_name="unified_brain_v2.8",
        ...     strategy_version="2.8.0",
        ...     start_date=datetime(2024, 8, 1),
        ...     end_date=datetime(2025, 5, 31),
        ...     initial_bankroll=10000.0,
        ...     sizing_strategy=SizingStrategy.HALF_KELLY,
        ...     min_edge_pct=5.0,
        ...     min_confidence=0.65,
        ...     use_closing_odds=True,
        ... )
    """

    # Identification
    backtest_id: str = Field(..., description="ID unique du backtest")
    name: str = Field(..., min_length=3, description="Nom du backtest")
    description: Optional[str] = Field(None, description="Description détaillée")

    # Strategy
    strategy_name: str = Field(..., description="Nom de la stratégie")
    strategy_version: str = Field(..., description="Version de la stratégie")

    # Time Period
    start_date: datetime = Field(..., description="Date de début")
    end_date: datetime = Field(..., description="Date de fin")
    competitions: Optional[List[str]] = Field(
        None, description="Compétitions à inclure (None = toutes)"
    )
    markets_filter: Optional[List[str]] = Field(
        None, description="Marchés à inclure (None = tous)"
    )

    # Bankroll & Sizing
    initial_bankroll: float = Field(..., gt=0.0, description="Bankroll initial (€)")
    sizing_strategy: SizingStrategy = Field(..., description="Stratégie de sizing")
    kelly_multiplier: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Multiplicateur Kelly"
    )
    max_stake_pct: float = Field(
        default=5.0, gt=0.0, le=100.0, description="Mise max (% bankroll)"
    )
    min_stake: float = Field(default=10.0, ge=0.0, description="Mise minimale (€)")
    max_stake: float = Field(default=1000.0, gt=0.0, description="Mise maximale (€)")

    # Filters
    min_edge_pct: float = Field(
        default=0.0, ge=0.0, description="Edge minimum requis (%)"
    )
    min_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confiance minimale"
    )
    max_positions: Optional[int] = Field(
        None, ge=1, description="Positions simultanées max"
    )
    min_odds: float = Field(default=1.01, ge=1.0, description="Cote minimale")
    max_odds: Optional[float] = Field(None, gt=1.0, description="Cote maximale")

    # Execution Details
    use_closing_odds: bool = Field(
        default=False, description="Utiliser cotes de closing (CLV)"
    )
    include_commission: bool = Field(default=True, description="Inclure commission")
    commission_pct: float = Field(
        default=2.0, ge=0.0, le=10.0, description="Taux commission (%)"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp de création"
    )
    created_by: Optional[str] = Field(None, description="Créateur du backtest")

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("start_date", "end_date", "created_at", when_used="json")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime fields to ISO 8601 format.

        ADR #003: field_serializer explicite avec when_used='json'.
        - Compatible FastAPI (.model_dump_json())
        - Type-safe (mypy vérifie input/output)
        - Testable unitairement

        Args:
            dt: Datetime to serialize

        Returns:
            ISO 8601 string (e.g. '2025-12-13T22:00:00')
        """
        return dt.isoformat()

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        """Valide que end_date > start_date.

        Args:
            v: end_date
            info: Contexte de validation

        Returns:
            end_date validée

        Raises:
            ValueError: Si end_date <= start_date
        """
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class BacktestResult(BaseModel):
    """Résultats complets d'un backtest.

    Contient toutes les métriques de performance, statistiques de risque,
    et analyse détaillée du backtest.

    Architecture Decision Records appliqués:
    - ADR #002: model_validator pour calculate_performance_metrics
    - ADR #003: field_serializer pour started_at, completed_at
    - ADR #004: Pattern Hybrid pour win_rate, total_return_pct

    Attributes:
        result_id: ID unique du résultat
        request: Configuration du backtest

        status: Statut du backtest
        started_at: Timestamp de démarrage
        completed_at: Timestamp de fin
        duration_seconds: Durée d'exécution (secondes)

        # Performance Metrics
        total_bets: Nombre total de paris
        winning_bets: Nombre de paris gagnants
        losing_bets: Nombre de paris perdants
        win_rate: Taux de réussite [0.0, 1.0]

        initial_bankroll: Bankroll initial (€)
        final_bankroll: Bankroll final (€)
        total_profit: Profit total (€)
        total_return_pct: Rendement total (%)

        total_staked: Montant total misé (€)
        total_returns: Montant total des gains (€)
        roi: Return on Investment (%)

        # Risk Metrics
        sharpe_ratio: Ratio de Sharpe
        sortino_ratio: Ratio de Sortino
        calmar_ratio: Ratio de Calmar
        max_drawdown: Drawdown max (€)
        max_drawdown_pct: Drawdown max (%)
        max_drawdown_duration_days: Durée max drawdown (jours)

        volatility: Volatilité des rendements
        var_95: Value at Risk 95% (€)
        cvar_95: Conditional VaR 95% (€)

        # Betting Metrics
        avg_stake: Mise moyenne (€)
        avg_odds: Cote moyenne
        avg_edge_pct: Edge moyen (%)
        avg_profit_per_bet: Profit moyen par pari (€)

        largest_win: Plus gros gain (€)
        largest_loss: Plus grosse perte (€)
        longest_winning_streak: Plus longue série gagnante
        longest_losing_streak: Plus longue série perdante

        # Market Performance
        performance_by_market: Performance par marché
        performance_by_competition: Performance par compétition
        performance_by_month: Performance par mois

        # CLV Analysis
        avg_clv_pct: CLV moyen (%) si use_closing_odds
        clv_positive_pct: % paris avec CLV positif

        # Metadata
        total_matches_analyzed: Matchs analysés
        bets_filtered_out: Paris filtrés
        filter_reasons: Raisons de filtrage

        warnings: Avertissements
        notes: Notes additionnelles

    Examples:
        >>> result = BacktestResult(
        ...     result_id="res-123",
        ...     request=backtest_request,
        ...     status=BacktestStatus.COMPLETED,
        ...     total_bets=456,
        ...     winning_bets=312,
        ...     losing_bets=144,
        ...     win_rate=0.684,
        ...     initial_bankroll=10000.0,
        ...     final_bankroll=14523.50,
        ...     total_profit=4523.50,
        ...     total_return_pct=45.23,
        ...     sharpe_ratio=1.82,
        ...     max_drawdown_pct=8.7,
        ...     avg_edge_pct=8.3,
        ... )
    """

    # Identification
    result_id: str = Field(..., description="ID unique du résultat")
    request: BacktestRequest = Field(..., description="Configuration du backtest")

    # Execution
    status: BacktestStatus = Field(..., description="Statut du backtest")
    started_at: Optional[datetime] = Field(None, description="Timestamp démarrage")
    completed_at: Optional[datetime] = Field(None, description="Timestamp fin")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Durée (secondes)")

    # Performance Metrics
    total_bets: int = Field(..., ge=0, description="Nombre total de paris")
    winning_bets: int = Field(..., ge=0, description="Paris gagnants")
    losing_bets: int = Field(..., ge=0, description="Paris perdants")
    win_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Taux de réussite (winning_bets / total_bets). "
            "Auto-calculé si omis (default=None). "
            "Reste None si total_bets = 0 (division par zéro). "
            "Peut être overridden si nécessaire. "
            "ADR #004: Pattern Hybrid."
        ),
    )

    initial_bankroll: float = Field(..., gt=0.0, description="Bankroll initial (€)")
    final_bankroll: float = Field(..., ge=0.0, description="Bankroll final (€)")
    total_profit: float = Field(..., description="Profit total (€)")
    total_return_pct: Optional[float] = Field(
        default=None,
        description=(
            "Rendement total % (total_profit / initial_bankroll * 100). "
            "Auto-calculé si omis (default=None). "
            "Reste None si initial_bankroll = 0.0 (division par zéro). "
            "Peut être overridden si nécessaire. "
            "ADR #004: Pattern Hybrid."
        ),
    )

    total_staked: float = Field(..., ge=0.0, description="Total misé (€)")
    total_returns: float = Field(..., ge=0.0, description="Total des gains (€)")
    roi: float = Field(..., description="ROI (%)")

    # Risk Metrics
    sharpe_ratio: Optional[float] = Field(None, description="Ratio de Sharpe")
    sortino_ratio: Optional[float] = Field(None, description="Ratio de Sortino")
    calmar_ratio: Optional[float] = Field(None, description="Ratio de Calmar")
    max_drawdown: float = Field(..., description="Drawdown max (€)")
    max_drawdown_pct: float = Field(..., description="Drawdown max (%)")
    max_drawdown_duration_days: Optional[int] = Field(
        None, ge=0, description="Durée max drawdown (jours)"
    )

    volatility: float = Field(..., ge=0.0, description="Volatilité des rendements")
    var_95: Optional[float] = Field(None, description="VaR 95% (€)")
    cvar_95: Optional[float] = Field(None, description="CVaR 95% (€)")

    # Betting Metrics
    avg_stake: float = Field(..., ge=0.0, description="Mise moyenne (€)")
    avg_odds: float = Field(..., gt=1.0, description="Cote moyenne")
    avg_edge_pct: float = Field(..., description="Edge moyen (%)")
    avg_profit_per_bet: float = Field(..., description="Profit moyen/pari (€)")

    largest_win: float = Field(..., description="Plus gros gain (€)")
    largest_loss: float = Field(..., description="Plus grosse perte (€)")
    longest_winning_streak: int = Field(..., ge=0, description="Série gagnante max")
    longest_losing_streak: int = Field(..., ge=0, description="Série perdante max")

    # Detailed Performance
    performance_by_market: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Performance par marché"
    )
    performance_by_competition: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Performance par compétition"
    )
    performance_by_month: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Performance par mois"
    )

    # CLV Analysis
    avg_clv_pct: Optional[float] = Field(None, description="CLV moyen (%)")
    clv_positive_pct: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="% paris CLV positif"
    )

    # Analysis Metadata
    total_matches_analyzed: int = Field(..., ge=0, description="Matchs analysés")
    bets_filtered_out: int = Field(..., ge=0, description="Paris filtrés")
    filter_reasons: Dict[str, int] = Field(
        default_factory=dict, description="Raisons de filtrage {raison: count}"
    )

    # Additional Info
    warnings: List[str] = Field(default_factory=list, description="Avertissements")
    notes: Optional[str] = Field(None, description="Notes additionnelles")

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("started_at", "completed_at", when_used="json")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO 8601 format.

        ADR #003: field_serializer explicite avec when_used='json'.
        - Compatible FastAPI (.model_dump_json())
        - Type-safe (mypy vérifie input/output)
        - Testable unitairement

        Args:
            dt: Datetime to serialize (or None for optional fields)

        Returns:
            ISO 8601 string (e.g. '2025-12-13T22:00:00') or None
        """
        return dt.isoformat() if dt else None

    @model_validator(mode="after")
    def calculate_performance_metrics(self):
        """Calcule les métriques de performance après validation.

        ADR #002: model_validator garantit accès à tous les champs (y compris defaults).
        ADR #004: Pattern Hybrid pour auto-calcul avec possibilité override.

        Métriques calculées:
        - win_rate: winning_bets / total_bets (si total_bets > 0)
        - total_return_pct: (total_profit / initial_bankroll) * 100 (si initial_bankroll > 0)

        Utilise model_fields_set pour distinguer:
        - Champ omis (default None) → calcule
        - Champ explicitement None → respecte override
        - Champ explicitement 0.0 → respecte override

        Returns:
            Instance avec métriques calculées ou overridées
        """
        # ─────────────────────────────────────────────────────────────────────
        # AUTO-CALCUL : win_rate (ADR #004)
        # ─────────────────────────────────────────────────────────────────────

        # Ne calcule QUE si le champ n'a pas été explicitement fourni
        if "win_rate" not in self.model_fields_set and self.win_rate is None:
            # CRITIQUE: Gestion division par zéro
            if self.total_bets is not None and self.total_bets > 0:
                wins = self.winning_bets or 0
                self.win_rate = wins / self.total_bets
            # Sinon reste None (pas assez de données)

        # ─────────────────────────────────────────────────────────────────────
        # AUTO-CALCUL : total_return_pct (ADR #004)
        # ─────────────────────────────────────────────────────────────────────

        # Ne calcule QUE si le champ n'a pas été explicitement fourni
        if (
            "total_return_pct" not in self.model_fields_set
            and self.total_return_pct is None
        ):
            # CRITIQUE: Gestion division par zéro
            if (
                self.total_profit is not None
                and self.initial_bankroll is not None
                and self.initial_bankroll > 0.0  # Protection division par zéro
            ):
                self.total_return_pct = (
                    self.total_profit / self.initial_bankroll
                ) * 100

        return self
