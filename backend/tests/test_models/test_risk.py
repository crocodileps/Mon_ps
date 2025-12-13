"""
Tests pour quantum_core.models.risk.

5 tests couvrant PositionSize, VaRCalculation et PortfolioRisk.
"""

import pytest
from datetime import datetime, timedelta
from quantum_core.models.risk import (
    SizingMethod,
    RiskLevel,
    VaRMethod,
    PositionSize,
    VaRCalculation,
    PortfolioRisk,
)


class TestPositionSize:
    """Tests pour le modèle PositionSize."""

    def test_position_size_creation(self):
        """Test création d'une PositionSize."""
        position = PositionSize(
            market_id="btts_yes",
            market_name="Both Teams To Score - Yes",
            recommended_stake=125.50,
            recommended_stake_pct=1.25,
            max_stake=250.0,
            min_stake=10.0,
            kelly_fraction=0.048,
            kelly_multiplier=0.5,
            sizing_method=SizingMethod.HALF_KELLY,
            edge_pct=12.5,
            expected_value=15.69,
            probability=0.68,
            fair_odds=1.47,
            market_odds=1.72,
            max_risk_pct=2.5,
            risk_level=RiskLevel.MEDIUM,
            bankroll=10000.0,
            portfolio_exposure=1250.0,
            portfolio_exposure_pct=12.5,
        )

        assert position.market_id == "btts_yes"
        assert position.recommended_stake == 125.50
        assert position.kelly_fraction == 0.048
        assert position.sizing_method == "half_kelly"
        assert position.risk_level == "medium"

    def test_position_size_risk_level_auto_low(self):
        """Test assignation automatique risk_level = LOW."""
        position = PositionSize(
            market_id="test",
            market_name="Test Market",
            recommended_stake=50.0,
            recommended_stake_pct=0.5,  # < 1.0 → LOW
            max_stake=100.0,
            min_stake=10.0,
            kelly_fraction=0.02,
            sizing_method=SizingMethod.KELLY,
            edge_pct=5.0,
            expected_value=2.5,
            probability=0.55,
            fair_odds=1.82,
            market_odds=1.90,
            max_risk_pct=2.5,
            risk_level=RiskLevel.LOW,  # Sera auto-calculé
            bankroll=10000.0,
            portfolio_exposure=500.0,
            portfolio_exposure_pct=5.0,
        )

        assert position.risk_level == "low"

    def test_position_size_risk_level_auto_high(self):
        """Test assignation automatique risk_level = HIGH."""
        position = PositionSize(
            market_id="test",
            market_name="Test Market",
            recommended_stake=350.0,
            recommended_stake_pct=3.5,  # 2.5-5.0 → HIGH
            max_stake=500.0,
            min_stake=10.0,
            kelly_fraction=0.08,
            sizing_method=SizingMethod.KELLY,
            edge_pct=15.0,
            expected_value=52.5,
            probability=0.72,
            fair_odds=1.39,
            market_odds=1.60,
            max_risk_pct=5.0,
            risk_level=RiskLevel.HIGH,
            bankroll=10000.0,
            portfolio_exposure=2000.0,
            portfolio_exposure_pct=20.0,
        )

        assert position.risk_level == "high"


class TestVaRCalculation:
    """Tests pour le modèle VaRCalculation."""

    def test_var_calculation_creation(self):
        """Test création d'une VaRCalculation."""
        var = VaRCalculation(
            confidence_level=0.95,
            time_horizon_days=1,
            var_amount=250.0,
            var_pct=2.5,
            cvar_amount=380.0,
            cvar_pct=3.8,
            method=VaRMethod.HISTORICAL,
            observations_used=500,
            worst_loss_observed=-450.0,
            worst_loss_pct=-4.5,
            best_gain_observed=520.0,
            best_gain_pct=5.2,
            mean_return=0.035,
            std_dev=0.12,
            sharpe_ratio=0.29,
        )

        assert var.confidence_level == 0.95
        assert var.var_amount == 250.0
        assert var.cvar_amount == 380.0
        assert var.method == "historical"
        assert var.observations_used == 500

    def test_var_calculation_monte_carlo(self):
        """Test VaRCalculation avec méthode Monte Carlo."""
        var = VaRCalculation(
            confidence_level=0.99,
            time_horizon_days=7,
            var_amount=450.0,
            var_pct=4.5,
            cvar_amount=680.0,
            cvar_pct=6.8,
            method=VaRMethod.MONTE_CARLO,
            observations_used=10000,
            simulation_runs=100000,
            worst_loss_observed=-920.0,
            worst_loss_pct=-9.2,
            best_gain_observed=1150.0,
            best_gain_pct=11.5,
            mean_return=0.042,
            std_dev=0.18,
            sharpe_ratio=0.23,
            sortino_ratio=0.35,
        )

        assert var.method == "monte_carlo"
        assert var.simulation_runs == 100000
        assert var.sortino_ratio == 0.35


class TestPortfolioRisk:
    """Tests pour le modèle PortfolioRisk."""

    def test_portfolio_risk_creation(self):
        """Test création d'un PortfolioRisk."""
        var_1day = VaRCalculation(
            confidence_level=0.95,
            var_amount=250.0,
            var_pct=2.5,
            cvar_amount=380.0,
            cvar_pct=3.8,
            method=VaRMethod.HISTORICAL,
            observations_used=500,
            worst_loss_observed=-450.0,
            worst_loss_pct=-4.5,
            best_gain_observed=520.0,
            best_gain_pct=5.2,
            mean_return=0.035,
            std_dev=0.12,
        )

        portfolio = PortfolioRisk(
            portfolio_id="main_portfolio",
            bankroll=10000.0,
            currency="EUR",
            total_exposure=1250.0,
            total_exposure_pct=12.5,
            active_positions_count=8,
            markets_exposed=["btts_yes", "over_25", "home_win"],
            largest_position_amount=250.0,
            largest_position_pct=2.5,
            concentration_ratio=0.48,
            var_1day_95=var_1day,
            correlation_exposure=450.0,
            correlation_risk_score=0.35,
            max_exposure_limit=2500.0,
            max_exposure_limit_pct=25.0,
            available_capital=8750.0,
            capital_utilization_pct=12.5,
            risk_score=4.2,
            risk_level=RiskLevel.MEDIUM,
        )

        assert portfolio.portfolio_id == "main_portfolio"
        assert portfolio.bankroll == 10000.0
        assert portfolio.total_exposure == 1250.0
        assert portfolio.active_positions_count == 8
        assert portfolio.risk_score == 4.2
        assert portfolio.risk_level == "medium"
        assert len(portfolio.markets_exposed) == 3


class TestRiskLevelValidation:
    """Tests des risk levels et validators."""

    def test_position_size_very_high_risk(self):
        """Test RiskLevel.VERY_HIGH si stake >= 5% bankroll."""
        position = PositionSize(
            market_id="match_very_risky",
            market_name="Very High Risk Market",
            recommended_stake=550.0,  # 5.5% de 10000
            recommended_stake_pct=5.5,  # >= 5.0 → VERY_HIGH
            max_stake=1000.0,
            min_stake=10.0,
            kelly_fraction=0.055,
            sizing_method=SizingMethod.KELLY,
            edge_pct=8.2,
            expected_value=45.1,
            probability=0.67,
            fair_odds=1.49,
            market_odds=1.65,
            max_risk_pct=10.0,
            risk_level=RiskLevel.LOW,  # Sera overridden par validator
            bankroll=10000.0,
            portfolio_exposure=2500.0,
            portfolio_exposure_pct=25.0,
        )

        # Le validator doit assigner VERY_HIGH
        assert position.risk_level == "very_high"

    def test_position_size_medium_risk(self):
        """Test RiskLevel.MEDIUM si 1% <= stake < 2.5%."""
        position = PositionSize(
            match_id="match_medium_risk",
            market_id="over_2_5",
            market_name="Over 2.5 Goals",
            recommended_stake=200.0,  # 2% de 10000
            recommended_stake_pct=2.0,  # 1.0-2.5 → MEDIUM
            max_stake=400.0,
            min_stake=10.0,
            kelly_fraction=0.02,
            sizing_method=SizingMethod.KELLY,
            edge_pct=4.5,
            expected_value=9.0,
            probability=0.58,
            fair_odds=1.72,
            market_odds=1.80,
            max_risk_pct=5.0,
            risk_level=RiskLevel.LOW,
            bankroll=10000.0,
            portfolio_exposure=1000.0,
            portfolio_exposure_pct=10.0,
        )

        assert position.risk_level == "medium"

    def test_position_size_edge_case_exactly_5_pct(self):
        """Test RiskLevel.VERY_HIGH si stake = exactement 5.0%."""
        position = PositionSize(
            market_id="edge_case",
            market_name="Edge Case Market",
            recommended_stake=500.0,  # Exactement 5% de 10000
            recommended_stake_pct=5.0,  # = 5.0 → VERY_HIGH (car >= 5.0)
            max_stake=1000.0,
            min_stake=10.0,
            kelly_fraction=0.05,
            sizing_method=SizingMethod.KELLY,
            edge_pct=7.0,
            expected_value=35.0,
            probability=0.65,
            fair_odds=1.54,
            market_odds=1.65,
            max_risk_pct=10.0,
            risk_level=RiskLevel.LOW,
            bankroll=10000.0,
            portfolio_exposure=2000.0,
            portfolio_exposure_pct=20.0,
        )

        # Validator: >= 5.0 → VERY_HIGH
        assert position.risk_level == "very_high"


# ═══════════════════════════════════════════════════════════════════════════════
# ADR COMPLIANCE TESTS - HEDGE FUND GRADE
# ═══════════════════════════════════════════════════════════════════════════════


class TestADR002ModelValidatorRisk:
    """Tests validant ADR #002 pour risk.py.

    ADR #002: model_validator pour logique cross-field.
    - Accès garanti à tous les champs (y compris defaults)
    - Type safety complète
    - Pattern explicite pour dépendances inter-champs
    """

    def test_model_validator_risk_level_auto_calculated(self):
        """ADR #002: model_validator calculate risk_level from recommended_stake_pct."""
        position = PositionSize(
            market_id="test_auto",
            market_name="Test Auto Risk Level",
            recommended_stake=150.0,
            recommended_stake_pct=1.5,  # 1.0-2.5 → MEDIUM
            max_stake=300.0,
            min_stake=10.0,
            kelly_fraction=0.015,
            sizing_method=SizingMethod.KELLY,
            edge_pct=8.0,
            expected_value=12.0,
            probability=0.60,
            fair_odds=1.67,
            market_odds=1.75,
            max_risk_pct=5.0,
            # risk_level omis → auto-calculé
            bankroll=10000.0,
            portfolio_exposure=800.0,
            portfolio_exposure_pct=8.0,
        )

        # model_validator doit calculer MEDIUM
        assert position.risk_level == "medium"

    def test_model_validator_accesses_all_fields(self):
        """ADR #002: model_validator a accès à tous les champs (cross-field logic)."""
        # Teste que model_validator peut accéder à recommended_stake_pct
        # pour calculer risk_level correctement
        position = PositionSize(
            market_id="test_access",
            market_name="Test Field Access",
            recommended_stake=450.0,
            recommended_stake_pct=4.5,  # 2.5-5.0 → HIGH
            max_stake=500.0,
            min_stake=10.0,
            kelly_fraction=0.045,
            sizing_method=SizingMethod.HALF_KELLY,
            edge_pct=10.0,
            expected_value=45.0,
            probability=0.65,
            fair_odds=1.54,
            market_odds=1.68,
            max_risk_pct=10.0,
            bankroll=10000.0,
            portfolio_exposure=1500.0,
            portfolio_exposure_pct=15.0,
        )

        # Vérifie accès cross-field fonctionnel
        assert position.risk_level == "high"
        assert position.recommended_stake_pct == 4.5


class TestADR003FieldSerializerRisk:
    """Tests validant ADR #003 pour risk.py.

    ADR #003: field_serializer explicite avec when_used='json'.
    - Compatible FastAPI (.model_dump_json())
    - Type-safe (mypy vérifie)
    - Testable unitairement
    """

    def test_position_datetime_serializes_json(self):
        """ADR #003: PositionSize.computed_at serialized to ISO 8601 in JSON."""
        position = PositionSize(
            market_id="test",
            market_name="Test Market",
            recommended_stake=100.0,
            recommended_stake_pct=1.0,
            max_stake=200.0,
            min_stake=10.0,
            kelly_fraction=0.01,
            sizing_method=SizingMethod.KELLY,
            edge_pct=5.0,
            expected_value=5.0,
            probability=0.55,
            fair_odds=1.82,
            market_odds=1.90,
            max_risk_pct=2.5,
            bankroll=10000.0,
            portfolio_exposure=500.0,
            portfolio_exposure_pct=5.0,
            computed_at=datetime(2025, 12, 13, 22, 0, 0),
        )

        json_str = position.model_dump_json()
        assert '"computed_at":"2025-12-13T22:00:00"' in json_str

    def test_var_datetime_serializes_json(self):
        """ADR #003: VaRCalculation datetime fields serialized to ISO 8601."""
        var = VaRCalculation(
            confidence_level=0.95,
            var_amount=250.0,
            var_pct=2.5,
            cvar_amount=380.0,
            cvar_pct=3.8,
            method=VaRMethod.HISTORICAL,
            observations_used=500,
            worst_loss_observed=-450.0,
            worst_loss_pct=-4.5,
            best_gain_observed=520.0,
            best_gain_pct=5.2,
            mean_return=0.035,
            std_dev=0.12,
            computed_at=datetime(2025, 12, 13, 22, 0, 0),
            based_on_data_from=datetime(2025, 11, 1, 0, 0, 0),
            based_on_data_to=datetime(2025, 12, 13, 0, 0, 0),
        )

        json_str = var.model_dump_json()
        assert '"computed_at":"2025-12-13T22:00:00"' in json_str
        assert '"based_on_data_from":"2025-11-01T00:00:00"' in json_str
        assert '"based_on_data_to":"2025-12-13T00:00:00"' in json_str

    def test_portfolio_datetime_serializes_json(self):
        """ADR #003: PortfolioRisk.computed_at serialized to ISO 8601."""
        var_1day = VaRCalculation(
            confidence_level=0.95,
            var_amount=250.0,
            var_pct=2.5,
            cvar_amount=380.0,
            cvar_pct=3.8,
            method=VaRMethod.HISTORICAL,
            observations_used=500,
            worst_loss_observed=-450.0,
            worst_loss_pct=-4.5,
            best_gain_observed=520.0,
            best_gain_pct=5.2,
            mean_return=0.035,
            std_dev=0.12,
        )

        portfolio = PortfolioRisk(
            portfolio_id="test_portfolio",
            bankroll=10000.0,
            total_exposure=1000.0,
            total_exposure_pct=10.0,
            active_positions_count=5,
            largest_position_amount=200.0,
            largest_position_pct=2.0,
            concentration_ratio=0.40,
            var_1day_95=var_1day,
            correlation_exposure=300.0,
            correlation_risk_score=0.30,
            max_exposure_limit=2500.0,
            max_exposure_limit_pct=25.0,
            available_capital=9000.0,
            capital_utilization_pct=10.0,
            risk_score=3.5,
            risk_level=RiskLevel.MEDIUM,
            computed_at=datetime(2025, 12, 13, 22, 0, 0),
        )

        json_str = portfolio.model_dump_json()
        assert '"computed_at":"2025-12-13T22:00:00"' in json_str

    def test_datetime_preserved_model_dump(self):
        """ADR #003: .model_dump() preserves datetime objects (not serialized)."""
        position = PositionSize(
            market_id="test",
            market_name="Test Market",
            recommended_stake=100.0,
            recommended_stake_pct=1.0,
            max_stake=200.0,
            min_stake=10.0,
            kelly_fraction=0.01,
            sizing_method=SizingMethod.KELLY,
            edge_pct=5.0,
            expected_value=5.0,
            probability=0.55,
            fair_odds=1.82,
            market_odds=1.90,
            max_risk_pct=2.5,
            bankroll=10000.0,
            portfolio_exposure=500.0,
            portfolio_exposure_pct=5.0,
            computed_at=datetime(2025, 12, 13, 22, 0, 0),
        )

        data = position.model_dump()
        assert isinstance(data["computed_at"], datetime)
        assert data["computed_at"] == datetime(2025, 12, 13, 22, 0, 0)


class TestADR004AutoCalculatedRisk:
    """Tests validant ADR #004 pour risk.py.

    ADR #004: Pattern Hybrid pour auto-calculs.
    - Default sentinelle (RiskLevel.LOW)
    - Auto-calcul si sentinelle détectée
    - Permet override si valeur fournie
    """

    def test_risk_level_auto_calculated_from_stake_pct(self):
        """ADR #004: risk_level auto-calculated when sentinelle (LOW) detected."""
        # recommended_stake_pct = 3.0% → HIGH (2.5-5.0%)
        position = PositionSize(
            market_id="test_auto",
            market_name="Test Auto Calculate",
            recommended_stake=300.0,
            recommended_stake_pct=3.0,  # → HIGH
            max_stake=500.0,
            min_stake=10.0,
            kelly_fraction=0.03,
            sizing_method=SizingMethod.KELLY,
            edge_pct=9.0,
            expected_value=27.0,
            probability=0.62,
            fair_odds=1.61,
            market_odds=1.72,
            max_risk_pct=5.0,
            # risk_level omis → sentinelle LOW → auto-calcul
            bankroll=10000.0,
            portfolio_exposure=1200.0,
            portfolio_exposure_pct=12.0,
        )

        # Auto-calculé à HIGH
        assert position.risk_level == "high"

    def test_risk_level_can_be_overridden(self):
        """ADR #004: risk_level can be overridden if explicitly provided."""
        # Même si recommended_stake_pct = 3.0% (HIGH),
        # si on override à MEDIUM, ça doit être respecté
        position = PositionSize(
            market_id="test_override",
            market_name="Test Override",
            recommended_stake=300.0,
            recommended_stake_pct=3.0,  # → HIGH normalement
            max_stake=500.0,
            min_stake=10.0,
            kelly_fraction=0.03,
            sizing_method=SizingMethod.KELLY,
            edge_pct=9.0,
            expected_value=27.0,
            probability=0.62,
            fair_odds=1.61,
            market_odds=1.72,
            max_risk_pct=5.0,
            risk_level=RiskLevel.MEDIUM,  # Override explicite
            bankroll=10000.0,
            portfolio_exposure=1200.0,
            portfolio_exposure_pct=12.0,
        )

        # Override doit être respecté
        assert position.risk_level == "medium"


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASES TESTS - HEDGE FUND GRADE
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCasesPositionSize:
    """Tests edge cases critiques pour PositionSize.

    Standard Hedge Fund Grade:
    - Valeurs zéro (0.0, 0)
    - Valeurs extrêmes (limites)
    - Valeurs négatives (edge négatif)
    - Override avec sentinelle
    """

    def test_kelly_fraction_zero(self):
        """Edge case CRITIQUE: kelly_fraction = 0.0 (bunker strategy).

        Scénario réel: Pas d'edge détecté, kelly = 0.0
        Vérifie que 0.0 n'est PAS traité comme falsy.
        """
        position = PositionSize(
            market_id="test_kelly_zero",
            market_name="No Edge Market",
            recommended_stake=0.0,  # Pas de mise si kelly = 0
            recommended_stake_pct=0.0,
            max_stake=100.0,
            min_stake=10.0,
            kelly_fraction=0.0,  # ← Edge case: kelly = 0.0
            sizing_method=SizingMethod.KELLY,
            edge_pct=0.0,  # Pas d'edge
            expected_value=0.0,
            probability=0.50,  # 50/50
            fair_odds=2.0,
            market_odds=2.0,  # Fair = market → 0 edge
            max_risk_pct=2.5,
            bankroll=10000.0,
            portfolio_exposure=500.0,
            portfolio_exposure_pct=5.0,
        )

        # CRITIQUE: Doit être LOW (0.0% < 1.0%)
        assert position.kelly_fraction == 0.0
        assert position.risk_level == "low"

    def test_edge_pct_negative(self):
        """Edge case: edge_pct négatif (bad market).

        Scénario réel: Cotes défavorables, edge négatif
        """
        position = PositionSize(
            market_id="test_negative_edge",
            market_name="Bad Odds Market",
            recommended_stake=0.0,  # Pas de mise sur edge négatif
            recommended_stake_pct=0.0,
            max_stake=100.0,
            min_stake=10.0,
            kelly_fraction=0.0,
            sizing_method=SizingMethod.FIXED,
            edge_pct=-5.0,  # ← Edge négatif
            expected_value=-50.0,  # EV négatif
            probability=0.45,
            fair_odds=2.22,
            market_odds=2.00,  # Cotes trop basses
            max_risk_pct=2.5,
            bankroll=10000.0,
            portfolio_exposure=500.0,
            portfolio_exposure_pct=5.0,
        )

        assert position.edge_pct == -5.0
        assert position.expected_value == -50.0
        assert position.risk_level == "low"  # 0.0% < 1.0%

    def test_extreme_kelly_fraction(self):
        """Edge case: kelly_fraction = 1.0 (max possible).

        Scénario réel: Edge massif, kelly suggère 100% bankroll
        """
        position = PositionSize(
            market_id="test_extreme_kelly",
            market_name="Extreme Edge Market",
            recommended_stake=10000.0,  # Full kelly
            recommended_stake_pct=100.0,  # 100% → VERY_HIGH
            max_stake=10000.0,
            min_stake=10.0,
            kelly_fraction=1.0,  # ← Max kelly
            sizing_method=SizingMethod.KELLY,
            edge_pct=200.0,  # Edge énorme
            expected_value=20000.0,
            probability=0.95,
            fair_odds=1.05,
            market_odds=3.0,  # Cotes incroyables
            max_risk_pct=100.0,
            bankroll=10000.0,
            portfolio_exposure=5000.0,
            portfolio_exposure_pct=50.0,
        )

        assert position.kelly_fraction == 1.0
        assert position.risk_level == "very_high"  # 100% >= 5.0%

    def test_override_risk_level_with_sentinelle(self):
        """Pattern Hybrid: Override risk_level avec valeur différente sentinelle."""
        # recommended_stake_pct = 0.5% → LOW normalement
        # Mais on override à HIGH explicitement
        position = PositionSize(
            market_id="test_override_high",
            market_name="Override Risk High",
            recommended_stake=50.0,
            recommended_stake_pct=0.5,  # < 1.0% → LOW normalement
            max_stake=100.0,
            min_stake=10.0,
            kelly_fraction=0.005,
            sizing_method=SizingMethod.HALF_KELLY,
            edge_pct=3.0,
            expected_value=1.5,
            probability=0.52,
            fair_odds=1.92,
            market_odds=2.0,
            max_risk_pct=2.5,
            risk_level=RiskLevel.HIGH,  # ← Override à HIGH (pas LOW)
            bankroll=10000.0,
            portfolio_exposure=300.0,
            portfolio_exposure_pct=3.0,
        )

        # Override doit être respecté (HIGH, pas LOW)
        assert position.risk_level == "high"


class TestEdgeCasesVaRCalculation:
    """Tests edge cases critiques pour VaRCalculation.

    Standard Hedge Fund Grade:
    - Valeurs zéro (std_dev=0.0)
    - Valeurs None (sharpe_ratio=None, sortino_ratio=None)
    - Valeurs extrêmes (VaR énorme)
    - Valeurs négatives (mean_return<0)
    """

    def test_std_dev_zero(self):
        """Edge case CRITIQUE: std_dev = 0.0 (no volatility).

        Scénario réel: Stratégie à rendement constant
        Vérifie que 0.0 n'est PAS traité comme falsy.
        """
        var = VaRCalculation(
            confidence_level=0.95,
            var_amount=0.0,  # Pas de risque si std_dev = 0
            var_pct=0.0,
            cvar_amount=0.0,
            cvar_pct=0.0,
            method=VaRMethod.PARAMETRIC,
            observations_used=100,
            worst_loss_observed=0.0,
            worst_loss_pct=0.0,
            best_gain_observed=50.0,
            best_gain_pct=0.5,
            mean_return=0.01,
            std_dev=0.0,  # ← Edge case: 0 volatility
        )

        # CRITIQUE: std_dev = 0.0 est valide
        assert var.std_dev == 0.0
        assert var.var_amount == 0.0

    def test_sharpe_ratio_none(self):
        """Edge case: sharpe_ratio = None (missing data)."""
        var = VaRCalculation(
            confidence_level=0.95,
            var_amount=250.0,
            var_pct=2.5,
            cvar_amount=380.0,
            cvar_pct=3.8,
            method=VaRMethod.HISTORICAL,
            observations_used=50,  # Peu de données
            worst_loss_observed=-450.0,
            worst_loss_pct=-4.5,
            best_gain_observed=520.0,
            best_gain_pct=5.2,
            mean_return=0.035,
            std_dev=0.12,
            sharpe_ratio=None,  # ← Pas assez de données
            sortino_ratio=None,  # ← Pas assez de données
        )

        assert var.sharpe_ratio is None
        assert var.sortino_ratio is None

    def test_extreme_var_amount(self):
        """Edge case: VaR très élevé (stratégie très risquée)."""
        var = VaRCalculation(
            confidence_level=0.99,  # Confiance 99%
            var_amount=5000.0,  # ← VaR énorme
            var_pct=50.0,  # 50% du bankroll!
            cvar_amount=7500.0,
            cvar_pct=75.0,
            method=VaRMethod.MONTE_CARLO,
            observations_used=10000,
            simulation_runs=100000,
            worst_loss_observed=-9000.0,  # Perte catastrophique possible
            worst_loss_pct=-90.0,
            best_gain_observed=3000.0,
            best_gain_pct=30.0,
            mean_return=0.05,
            std_dev=0.50,  # Volatilité énorme
            sharpe_ratio=0.10,  # Mauvais ratio
        )

        assert var.var_amount == 5000.0
        assert var.var_pct == 50.0
        assert var.std_dev == 0.50

    def test_negative_mean_return(self):
        """Edge case: mean_return négatif (losing strategy)."""
        var = VaRCalculation(
            confidence_level=0.95,
            var_amount=400.0,
            var_pct=4.0,
            cvar_amount=600.0,
            cvar_pct=6.0,
            method=VaRMethod.HISTORICAL,
            observations_used=200,
            worst_loss_observed=-800.0,
            worst_loss_pct=-8.0,
            best_gain_observed=300.0,
            best_gain_pct=3.0,
            mean_return=-0.02,  # ← Rendement moyen négatif
            std_dev=0.15,
            sharpe_ratio=-0.13,  # Sharpe négatif
        )

        assert var.mean_return == -0.02
        assert var.sharpe_ratio == -0.13


class TestEdgeCasesPortfolioRisk:
    """Tests edge cases critiques pour PortfolioRisk.

    Standard Hedge Fund Grade:
    - Valeurs zéro (total_exposure=0.0, active_positions_count=0)
    - Valeurs None (var_7day_95=None)
    - Valeurs extrêmes (concentration_ratio=1.0)
    - Scores de corrélation (0.0, 1.0)
    """

    def test_zero_exposure(self):
        """Edge case CRITIQUE: total_exposure = 0.0 (no positions).

        Scénario réel: Portfolio vide après clôture de toutes les positions
        Vérifie que 0.0 n'est PAS traité comme falsy.
        """
        var_1day = VaRCalculation(
            confidence_level=0.95,
            var_amount=0.0,  # Pas de risque si pas d'exposition
            var_pct=0.0,
            cvar_amount=0.0,
            cvar_pct=0.0,
            method=VaRMethod.HISTORICAL,
            observations_used=100,
            worst_loss_observed=0.0,
            worst_loss_pct=0.0,
            best_gain_observed=0.0,
            best_gain_pct=0.0,
            mean_return=0.0,
            std_dev=0.0,
        )

        portfolio = PortfolioRisk(
            portfolio_id="empty_portfolio",
            bankroll=10000.0,
            total_exposure=0.0,  # ← Edge case: 0 exposure
            total_exposure_pct=0.0,
            active_positions_count=0,
            largest_position_amount=0.0,
            largest_position_pct=0.0,
            concentration_ratio=0.0,
            var_1day_95=var_1day,
            correlation_exposure=0.0,
            correlation_risk_score=0.0,
            max_exposure_limit=2500.0,
            max_exposure_limit_pct=25.0,
            available_capital=10000.0,
            capital_utilization_pct=0.0,
            risk_score=0.0,
            risk_level=RiskLevel.LOW,
        )

        # CRITIQUE: 0.0 est valide (portfolio vide)
        assert portfolio.total_exposure == 0.0
        assert portfolio.active_positions_count == 0

    def test_extreme_concentration_ratio(self):
        """Edge case: concentration_ratio = 1.0 (une seule position).

        Scénario réel: Portfolio avec une seule grosse position
        """
        var_1day = VaRCalculation(
            confidence_level=0.95,
            var_amount=500.0,
            var_pct=5.0,
            cvar_amount=750.0,
            cvar_pct=7.5,
            method=VaRMethod.HISTORICAL,
            observations_used=100,
            worst_loss_observed=-1000.0,
            worst_loss_pct=-10.0,
            best_gain_observed=800.0,
            best_gain_pct=8.0,
            mean_return=0.02,
            std_dev=0.20,
        )

        portfolio = PortfolioRisk(
            portfolio_id="concentrated_portfolio",
            bankroll=10000.0,
            total_exposure=2000.0,
            total_exposure_pct=20.0,
            active_positions_count=1,  # Une seule position
            largest_position_amount=2000.0,
            largest_position_pct=20.0,
            concentration_ratio=1.0,  # ← Edge case: 100% concentré
            var_1day_95=var_1day,
            correlation_exposure=0.0,  # Une position → pas de corrélation
            correlation_risk_score=0.0,
            max_exposure_limit=2500.0,
            max_exposure_limit_pct=25.0,
            available_capital=8000.0,
            capital_utilization_pct=20.0,
            risk_score=7.5,
            risk_level=RiskLevel.HIGH,
        )

        assert portfolio.concentration_ratio == 1.0
        assert portfolio.active_positions_count == 1

    def test_var_7day_95_none(self):
        """Edge case: var_7day_95 = None (optional field)."""
        var_1day = VaRCalculation(
            confidence_level=0.95,
            var_amount=250.0,
            var_pct=2.5,
            cvar_amount=380.0,
            cvar_pct=3.8,
            method=VaRMethod.HISTORICAL,
            observations_used=100,
            worst_loss_observed=-450.0,
            worst_loss_pct=-4.5,
            best_gain_observed=520.0,
            best_gain_pct=5.2,
            mean_return=0.035,
            std_dev=0.12,
        )

        portfolio = PortfolioRisk(
            portfolio_id="test_portfolio",
            bankroll=10000.0,
            total_exposure=1000.0,
            total_exposure_pct=10.0,
            active_positions_count=5,
            largest_position_amount=200.0,
            largest_position_pct=2.0,
            concentration_ratio=0.40,
            var_1day_95=var_1day,
            var_7day_95=None,  # ← Edge case: Optional None
            correlation_exposure=300.0,
            correlation_risk_score=0.30,
            max_exposure_limit=2500.0,
            max_exposure_limit_pct=25.0,
            available_capital=9000.0,
            capital_utilization_pct=10.0,
            risk_score=3.5,
            risk_level=RiskLevel.MEDIUM,
        )

        assert portfolio.var_7day_95 is None

    def test_correlation_risk_extremes(self):
        """Edge case: correlation_risk_score aux limites (0.0, 1.0)."""
        var_1day = VaRCalculation(
            confidence_level=0.95,
            var_amount=300.0,
            var_pct=3.0,
            cvar_amount=450.0,
            cvar_pct=4.5,
            method=VaRMethod.HISTORICAL,
            observations_used=200,
            worst_loss_observed=-500.0,
            worst_loss_pct=-5.0,
            best_gain_observed=600.0,
            best_gain_pct=6.0,
            mean_return=0.04,
            std_dev=0.15,
        )

        # Test avec correlation_risk_score = 1.0 (fully correlated)
        portfolio_high_corr = PortfolioRisk(
            portfolio_id="high_correlation",
            bankroll=10000.0,
            total_exposure=1500.0,
            total_exposure_pct=15.0,
            active_positions_count=10,
            largest_position_amount=200.0,
            largest_position_pct=2.0,
            concentration_ratio=0.45,
            var_1day_95=var_1day,
            correlation_exposure=1500.0,  # Tout corrélé
            correlation_risk_score=1.0,  # ← Edge case: 100% corrélé
            max_exposure_limit=2500.0,
            max_exposure_limit_pct=25.0,
            available_capital=8500.0,
            capital_utilization_pct=15.0,
            risk_score=8.5,
            risk_level=RiskLevel.VERY_HIGH,
        )

        assert portfolio_high_corr.correlation_risk_score == 1.0

        # Test avec correlation_risk_score = 0.0 (uncorrelated)
        portfolio_no_corr = PortfolioRisk(
            portfolio_id="no_correlation",
            bankroll=10000.0,
            total_exposure=1000.0,
            total_exposure_pct=10.0,
            active_positions_count=8,
            largest_position_amount=150.0,
            largest_position_pct=1.5,
            concentration_ratio=0.35,
            var_1day_95=var_1day,
            correlation_exposure=0.0,  # Aucune corrélation
            correlation_risk_score=0.0,  # ← Edge case: 0% corrélé
            max_exposure_limit=2500.0,
            max_exposure_limit_pct=25.0,
            available_capital=9000.0,
            capital_utilization_pct=10.0,
            risk_score=2.5,
            risk_level=RiskLevel.LOW,
        )

        assert portfolio_no_corr.correlation_risk_score == 0.0
