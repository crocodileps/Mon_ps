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
