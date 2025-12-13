"""
Tests pour quantum_core.models.backtest.

4 tests couvrant BacktestRequest et BacktestResult.
"""

import pytest
from datetime import datetime, timedelta
from quantum_core.models.backtest import (
    BacktestStatus,
    SizingStrategy,
    BacktestRequest,
    BacktestResult,
)


class TestBacktestRequest:
    """Tests pour le modèle BacktestRequest."""

    def test_backtest_request_creation(self):
        """Test création d'une BacktestRequest complète."""
        request = BacktestRequest(
            backtest_id="bt-123",
            name="UnifiedBrain V2.8 - Full Season",
            description="Backtest complet saison 2024-25",
            strategy_name="unified_brain_v2.8",
            strategy_version="2.8.0",
            start_date=datetime(2024, 8, 1),
            end_date=datetime(2025, 5, 31),
            competitions=["Premier League", "La Liga"],
            markets_filter=["btts_yes", "over_25", "home_win"],
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.HALF_KELLY,
            kelly_multiplier=0.5,
            max_stake_pct=5.0,
            min_stake=10.0,
            max_stake=500.0,
            min_edge_pct=5.0,
            min_confidence=0.65,
            max_positions=10,
            min_odds=1.50,
            max_odds=5.0,
            use_closing_odds=True,
            include_commission=True,
            commission_pct=2.0,
        )

        assert request.backtest_id == "bt-123"
        assert request.name == "UnifiedBrain V2.8 - Full Season"
        assert request.strategy_name == "unified_brain_v2.8"
        assert request.sizing_strategy == "half_kelly"
        assert request.kelly_multiplier == 0.5
        assert request.min_edge_pct == 5.0
        assert request.use_closing_odds is True
        assert len(request.competitions) == 2
        assert len(request.markets_filter) == 3

    def test_backtest_request_end_date_validation(self):
        """Test validation que end_date > start_date."""
        # Dates valides
        request = BacktestRequest(
            backtest_id="bt-124",
            name="Test Backtest",
            strategy_name="test_strategy",
            strategy_version="1.0.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.FIXED,
        )
        assert request.end_date > request.start_date

        # end_date <= start_date → invalide
        with pytest.raises(Exception):
            BacktestRequest(
                backtest_id="bt-125",
                name="Invalid Backtest",
                strategy_name="test_strategy",
                strategy_version="1.0.0",
                start_date=datetime(2024, 12, 31),
                end_date=datetime(2024, 1, 1),  # Avant start_date
                initial_bankroll=10000.0,
                sizing_strategy=SizingStrategy.FIXED,
            )


class TestBacktestResult:
    """Tests pour le modèle BacktestResult."""

    def test_backtest_result_creation(self):
        """Test création d'un BacktestResult complet."""
        request = BacktestRequest(
            backtest_id="bt-123",
            name="Test Backtest",
            strategy_name="unified_brain_v2.8",
            strategy_version="2.8.0",
            start_date=datetime(2024, 8, 1),
            end_date=datetime(2025, 5, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.HALF_KELLY,
        )

        result = BacktestResult(
            result_id="res-123",
            request=request,
            status=BacktestStatus.COMPLETED,
            started_at=datetime(2025, 12, 13, 10, 0),
            completed_at=datetime(2025, 12, 13, 10, 15),
            duration_seconds=900,
            total_bets=456,
            winning_bets=312,
            losing_bets=144,
            win_rate=0.684,
            initial_bankroll=10000.0,
            final_bankroll=14523.50,
            total_profit=4523.50,
            total_return_pct=45.23,
            total_staked=22800.0,
            total_returns=27323.50,
            roi=19.84,
            sharpe_ratio=1.82,
            sortino_ratio=2.45,
            calmar_ratio=5.20,
            max_drawdown=-870.0,
            max_drawdown_pct=-8.7,
            max_drawdown_duration_days=12,
            volatility=0.15,
            var_95=-320.0,
            cvar_95=-485.0,
            avg_stake=50.0,
            avg_odds=1.92,
            avg_edge_pct=8.3,
            avg_profit_per_bet=9.92,
            largest_win=245.0,
            largest_loss=-125.0,
            longest_winning_streak=18,
            longest_losing_streak=6,
            total_matches_analyzed=1250,
            bets_filtered_out=794,
        )

        assert result.status == "completed"
        assert result.total_bets == 456
        assert result.winning_bets == 312
        assert result.win_rate == 0.684
        assert result.total_return_pct == 45.23
        assert result.sharpe_ratio == 1.82
        assert result.max_drawdown_pct == -8.7

    def test_backtest_result_win_rate_auto_calculation(self):
        """Test calcul automatique du win_rate."""
        request = BacktestRequest(
            backtest_id="bt-124",
            name="Test",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.FIXED,
        )

        result = BacktestResult(
            result_id="res-124",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=100,
            winning_bets=68,
            losing_bets=32,
            win_rate=0.0,  # Sera auto-calculé
            initial_bankroll=10000.0,
            final_bankroll=11500.0,
            total_profit=1500.0,
            total_return_pct=0.0,  # Sera auto-calculé
            total_staked=5000.0,
            total_returns=6500.0,
            roi=30.0,
            max_drawdown=-200.0,
            max_drawdown_pct=-2.0,
            volatility=0.08,
            avg_stake=50.0,
            avg_odds=2.0,
            avg_edge_pct=5.0,
            avg_profit_per_bet=15.0,
            largest_win=150.0,
            largest_loss=-50.0,
            longest_winning_streak=12,
            longest_losing_streak=4,
            total_matches_analyzed=500,
            bets_filtered_out=400,
        )

        # win_rate = 68 / 100 = 0.68
        assert result.win_rate == pytest.approx(0.68, rel=1e-6)
        # total_return_pct = (1500 / 10000) * 100 = 15.0
        assert result.total_return_pct == pytest.approx(15.0, rel=1e-6)
