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
        """Test calcul automatique du win_rate et total_return_pct.

        Pattern Hybrid ADR #004: Les champs OMIS sont auto-calculés.
        (Avant: utilisait 0.0 comme sentinelle, maintenant: omis → None → calculé)
        """
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
            # win_rate OMIS → auto-calculé via model_validator
            initial_bankroll=10000.0,
            final_bankroll=11500.0,
            total_profit=1500.0,
            # total_return_pct OMIS → auto-calculé via model_validator
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

        # win_rate = 68 / 100 = 0.68 (auto-calculé)
        assert result.win_rate == pytest.approx(0.68, rel=1e-6)
        # total_return_pct = (1500 / 10000) * 100 = 15.0 (auto-calculé)
        assert result.total_return_pct == pytest.approx(15.0, rel=1e-6)


# ═══════════════════════════════════════════════════════════════════════════════
# ADR COMPLIANCE TESTS - HEDGE FUND GRADE
# ═══════════════════════════════════════════════════════════════════════════════


class TestADR002ModelValidatorBacktest:
    """Tests validant ADR #002 pour backtest.py.

    ADR #002: model_validator pour logique cross-field.
    - Accès garanti à tous les champs (y compris defaults)
    - Type safety complète
    - Pattern explicite pour dépendances inter-champs
    """

    def test_model_validator_calculates_metrics(self):
        """ADR #002: model_validator calcule win_rate et total_return_pct."""
        request = BacktestRequest(
            backtest_id="bt-auto",
            name="Auto Metrics",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.KELLY,
        )

        result = BacktestResult(
            result_id="res-auto",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=100,
            winning_bets=62,
            losing_bets=38,
            # win_rate omis → auto-calculé
            initial_bankroll=10000.0,
            final_bankroll=11500.0,
            total_profit=1500.0,
            # total_return_pct omis → auto-calculé
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

        # model_validator doit calculer les métriques
        assert result.win_rate == pytest.approx(0.62, rel=1e-6)
        assert result.total_return_pct == pytest.approx(15.0, rel=1e-6)

    def test_model_validator_cross_field_logic(self):
        """ADR #002: model_validator accède à plusieurs champs."""
        request = BacktestRequest(
            backtest_id="bt-cross",
            name="Cross Field",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=5000.0,
            sizing_strategy=SizingStrategy.FIXED,
        )

        result = BacktestResult(
            result_id="res-cross",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=50,
            winning_bets=35,
            losing_bets=15,
            initial_bankroll=5000.0,
            final_bankroll=5750.0,
            total_profit=750.0,
            total_staked=2500.0,
            total_returns=3250.0,
            roi=30.0,
            max_drawdown=-150.0,
            max_drawdown_pct=-3.0,
            volatility=0.10,
            avg_stake=50.0,
            avg_odds=2.1,
            avg_edge_pct=6.0,
            avg_profit_per_bet=15.0,
            largest_win=120.0,
            largest_loss=-50.0,
            longest_winning_streak=8,
            longest_losing_streak=3,
            total_matches_analyzed=200,
            bets_filtered_out=150,
        )

        # Vérifie accès cross-field fonctionnel
        assert result.win_rate == pytest.approx(0.70, rel=1e-6)  # 35/50
        assert result.total_return_pct == pytest.approx(15.0, rel=1e-6)  # 750/5000*100


class TestADR003FieldSerializerBacktest:
    """Tests validant ADR #003 pour backtest.py.

    ADR #003: field_serializer explicite avec when_used='json'.
    - Compatible FastAPI (.model_dump_json())
    - Type-safe (mypy vérifie)
    - Testable unitairement
    """

    def test_request_datetime_serializes_json(self):
        """ADR #003: BacktestRequest datetime fields serialized to ISO 8601."""
        request = BacktestRequest(
            backtest_id="bt-json",
            name="JSON Test",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1, 0, 0, 0),
            end_date=datetime(2024, 12, 31, 23, 59, 59),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.KELLY,
            created_at=datetime(2025, 12, 13, 22, 0, 0),
        )

        json_str = request.model_dump_json()
        assert '"start_date":"2024-01-01T00:00:00"' in json_str
        assert '"end_date":"2024-12-31T23:59:59"' in json_str
        assert '"created_at":"2025-12-13T22:00:00"' in json_str

    def test_result_datetime_serializes_json(self):
        """ADR #003: BacktestResult datetime fields serialized to ISO 8601."""
        request = BacktestRequest(
            backtest_id="bt-result-json",
            name="Result JSON",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.KELLY,
        )

        result = BacktestResult(
            result_id="res-json",
            request=request,
            status=BacktestStatus.COMPLETED,
            started_at=datetime(2025, 12, 13, 10, 0, 0),
            completed_at=datetime(2025, 12, 13, 10, 15, 0),
            total_bets=100,
            winning_bets=60,
            losing_bets=40,
            initial_bankroll=10000.0,
            final_bankroll=11000.0,
            total_profit=1000.0,
            total_staked=5000.0,
            total_returns=6000.0,
            roi=20.0,
            max_drawdown=-100.0,
            max_drawdown_pct=-1.0,
            volatility=0.05,
            avg_stake=50.0,
            avg_odds=2.0,
            avg_edge_pct=5.0,
            avg_profit_per_bet=10.0,
            largest_win=100.0,
            largest_loss=-50.0,
            longest_winning_streak=10,
            longest_losing_streak=5,
            total_matches_analyzed=500,
            bets_filtered_out=400,
        )

        json_str = result.model_dump_json()
        assert '"started_at":"2025-12-13T10:00:00"' in json_str
        assert '"completed_at":"2025-12-13T10:15:00"' in json_str

    def test_datetime_preserved_model_dump(self):
        """ADR #003: .model_dump() preserves datetime objects."""
        request = BacktestRequest(
            backtest_id="bt-preserve",
            name="Preserve Test",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1, 0, 0, 0),
            end_date=datetime(2024, 12, 31, 0, 0, 0),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.KELLY,
            created_at=datetime(2025, 12, 13, 22, 0, 0),
        )

        data = request.model_dump()
        assert isinstance(data["start_date"], datetime)
        assert isinstance(data["end_date"], datetime)
        assert isinstance(data["created_at"], datetime)
        assert data["start_date"] == datetime(2024, 1, 1, 0, 0, 0)


class TestADR004AutoCalculatedBacktest:
    """Tests validant ADR #004 pour backtest.py.

    ADR #004: Pattern Hybrid pour auto-calculs.
    - Default sentinelle (None)
    - Auto-calcul si sentinelle détectée
    - Permet override si valeur fournie
    """

    def test_win_rate_auto_calculated(self):
        """ADR #004: win_rate auto-calculated when sentinelle (None) detected."""
        request = BacktestRequest(
            backtest_id="bt-auto-wr",
            name="Auto Win Rate",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.KELLY,
        )

        result = BacktestResult(
            result_id="res-auto-wr",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=80,
            winning_bets=56,  # 56/80 = 0.7
            losing_bets=24,
            # win_rate omis (None) → auto-calculé
            initial_bankroll=10000.0,
            final_bankroll=11200.0,
            total_profit=1200.0,
            total_staked=4000.0,
            total_returns=5200.0,
            roi=30.0,
            max_drawdown=-120.0,
            max_drawdown_pct=-1.2,
            volatility=0.06,
            avg_stake=50.0,
            avg_odds=2.0,
            avg_edge_pct=5.5,
            avg_profit_per_bet=15.0,
            largest_win=120.0,
            largest_loss=-50.0,
            longest_winning_streak=12,
            longest_losing_streak=4,
            total_matches_analyzed=400,
            bets_filtered_out=320,
        )

        # Auto-calculé à 0.7
        assert result.win_rate == pytest.approx(0.7, rel=1e-6)

    def test_win_rate_can_be_overridden(self):
        """ADR #004: win_rate can be overridden if explicitly provided."""
        request = BacktestRequest(
            backtest_id="bt-override-wr",
            name="Override Win Rate",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.KELLY,
        )

        result = BacktestResult(
            result_id="res-override-wr",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=100,
            winning_bets=60,  # 60/100 = 0.6 normalement
            losing_bets=40,
            win_rate=0.65,  # Override à 0.65 (ajusté manuellement)
            initial_bankroll=10000.0,
            final_bankroll=11000.0,
            total_profit=1000.0,
            total_staked=5000.0,
            total_returns=6000.0,
            roi=20.0,
            max_drawdown=-100.0,
            max_drawdown_pct=-1.0,
            volatility=0.05,
            avg_stake=50.0,
            avg_odds=2.0,
            avg_edge_pct=5.0,
            avg_profit_per_bet=10.0,
            largest_win=100.0,
            largest_loss=-50.0,
            longest_winning_streak=10,
            longest_losing_streak=5,
            total_matches_analyzed=500,
            bets_filtered_out=400,
        )

        # Override doit être respecté
        assert result.win_rate == pytest.approx(0.65, rel=1e-6)


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASES TESTS - HEDGE FUND GRADE
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCasesBacktest:
    """Tests edge cases critiques pour backtest.py.

    Standard Hedge Fund Grade - BACKTEST SPÉCIFIQUE:
    - Division par zéro (total_bets=0, initial_bankroll=0.0)
    - Valeurs None (données manquantes)
    - Valeurs zéro VALIDES (win_rate=0.0, total_return_pct=0.0)
    - Valeurs extrêmes (1000 bets, 1000% return)
    - Valeurs négatives (losing strategy)
    - Override avec sentinelle None
    """

    def test_zero_bets_division_by_zero(self):
        """Edge case CRITIQUE: total_bets = 0 (division par zéro).

        Scénario réel: Backtest sans paris exécutés (tous filtrés)
        win_rate doit rester None (pas crash)
        """
        request = BacktestRequest(
            backtest_id="bt-zero-bets",
            name="Zero Bets",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.KELLY,
        )

        result = BacktestResult(
            result_id="res-zero-bets",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=0,  # ← Division par zéro
            winning_bets=0,
            losing_bets=0,
            # win_rate omis → reste None (division par zéro protégée)
            initial_bankroll=10000.0,
            final_bankroll=10000.0,
            total_profit=0.0,
            # total_return_pct omis → reste None (total_profit=0)
            total_staked=0.0,
            total_returns=0.0,
            roi=0.0,
            max_drawdown=0.0,
            max_drawdown_pct=0.0,
            volatility=0.0,
            avg_stake=0.0,
            avg_odds=1.01,  # Minimum valid odd (constraint gt=1.0)
            avg_edge_pct=0.0,
            avg_profit_per_bet=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            longest_winning_streak=0,
            longest_losing_streak=0,
            total_matches_analyzed=1000,
            bets_filtered_out=1000,
        )

        # CRITIQUE: win_rate doit être None (pas crash, pas 0.0)
        assert result.win_rate is None
        # total_return_pct aussi None (0.0 / 10000.0 * 100 = 0.0, mais calculé)
        assert result.total_return_pct == pytest.approx(0.0, rel=1e-6)

    def test_all_losing_bets_win_rate_zero(self):
        """Edge case CRITIQUE: win_rate = 0.0 (100% pertes - VALIDE).

        Scénario réel: Stratégie catastrophique (0 victoires)
        0.0 est une valeur VALIDE (pas sentinelle)
        """
        request = BacktestRequest(
            backtest_id="bt-all-losses",
            name="All Losses",
            strategy_name="bad_strategy",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.FIXED,
        )

        result = BacktestResult(
            result_id="res-all-losses",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=100,
            winning_bets=0,  # 0 victoires
            losing_bets=100,
            # win_rate omis → calculé à 0.0
            initial_bankroll=10000.0,
            final_bankroll=7500.0,
            total_profit=-2500.0,
            total_staked=5000.0,
            total_returns=2500.0,
            roi=-50.0,
            max_drawdown=-2500.0,
            max_drawdown_pct=-25.0,
            volatility=0.20,
            avg_stake=50.0,
            avg_odds=2.0,
            avg_edge_pct=-5.0,
            avg_profit_per_bet=-25.0,
            largest_win=0.0,
            largest_loss=-50.0,
            longest_winning_streak=0,
            longest_losing_streak=100,
            total_matches_analyzed=500,
            bets_filtered_out=400,
        )

        # CRITIQUE: 0.0 valide (pas None, pas erreur)
        assert result.win_rate == pytest.approx(0.0, rel=1e-6)

    def test_all_winning_bets_win_rate_one(self):
        """Edge case: win_rate = 1.0 (100% victoires)."""
        request = BacktestRequest(
            backtest_id="bt-all-wins",
            name="All Wins",
            strategy_name="perfect_strategy",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.KELLY,
        )

        result = BacktestResult(
            result_id="res-all-wins",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=50,
            winning_bets=50,  # 100% wins
            losing_bets=0,
            initial_bankroll=10000.0,
            final_bankroll=15000.0,
            total_profit=5000.0,
            total_staked=2500.0,
            total_returns=7500.0,
            roi=200.0,
            max_drawdown=0.0,
            max_drawdown_pct=0.0,
            volatility=0.10,
            avg_stake=50.0,
            avg_odds=3.0,
            avg_edge_pct=15.0,
            avg_profit_per_bet=100.0,
            largest_win=200.0,
            largest_loss=0.0,
            longest_winning_streak=50,
            longest_losing_streak=0,
            total_matches_analyzed=200,
            bets_filtered_out=150,
        )

        assert result.win_rate == pytest.approx(1.0, rel=1e-6)

    def test_negative_return_losing_strategy(self):
        """Edge case: total_return_pct négatif (losing strategy)."""
        request = BacktestRequest(
            backtest_id="bt-negative",
            name="Negative Return",
            strategy_name="losing_strategy",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.FIXED,
        )

        result = BacktestResult(
            result_id="res-negative",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=200,
            winning_bets=75,
            losing_bets=125,
            initial_bankroll=10000.0,
            final_bankroll=6500.0,
            total_profit=-3500.0,  # Perte
            total_staked=10000.0,
            total_returns=6500.0,
            roi=-35.0,
            max_drawdown=-3500.0,
            max_drawdown_pct=-35.0,
            volatility=0.25,
            avg_stake=50.0,
            avg_odds=2.0,
            avg_edge_pct=-3.0,
            avg_profit_per_bet=-17.5,
            largest_win=100.0,
            largest_loss=-50.0,
            longest_winning_streak=5,
            longest_losing_streak=15,
            total_matches_analyzed=800,
            bets_filtered_out=600,
        )

        assert result.total_return_pct == pytest.approx(-35.0, rel=1e-6)  # -35%

    def test_extreme_number_of_bets(self):
        """Edge case: Nombre de paris extrême (backtest très long)."""
        request = BacktestRequest(
            backtest_id="bt-extreme",
            name="Extreme Bets",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.KELLY,
        )

        result = BacktestResult(
            result_id="res-extreme",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=10000,  # Très nombreux
            winning_bets=5800,
            losing_bets=4200,
            initial_bankroll=10000.0,
            final_bankroll=25000.0,
            total_profit=15000.0,
            total_staked=500000.0,
            total_returns=515000.0,
            roi=3.0,
            max_drawdown=-1200.0,
            max_drawdown_pct=-8.0,
            volatility=0.12,
            avg_stake=50.0,
            avg_odds=2.0,
            avg_edge_pct=5.0,
            avg_profit_per_bet=1.5,
            largest_win=300.0,
            largest_loss=-100.0,
            longest_winning_streak=45,
            longest_losing_streak=22,
            total_matches_analyzed=50000,
            bets_filtered_out=40000,
        )

        assert result.win_rate == pytest.approx(0.58, rel=1e-6)
        assert result.total_return_pct == pytest.approx(150.0, rel=1e-6)

    def test_breakeven_return_zero(self):
        """Edge case: total_return_pct = 0.0 (breakeven - VALIDE)."""
        request = BacktestRequest(
            backtest_id="bt-breakeven",
            name="Breakeven",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.FIXED,
        )

        result = BacktestResult(
            result_id="res-breakeven",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=100,
            winning_bets=50,
            losing_bets=50,
            initial_bankroll=10000.0,
            final_bankroll=10000.0,
            total_profit=0.0,  # Breakeven
            total_staked=5000.0,
            total_returns=5000.0,
            roi=0.0,
            max_drawdown=-200.0,
            max_drawdown_pct=-2.0,
            volatility=0.08,
            avg_stake=50.0,
            avg_odds=2.0,
            avg_edge_pct=0.0,
            avg_profit_per_bet=0.0,
            largest_win=100.0,
            largest_loss=-100.0,
            longest_winning_streak=8,
            longest_losing_streak=8,
            total_matches_analyzed=500,
            bets_filtered_out=400,
        )

        # CRITIQUE: 0.0 valide (breakeven, pas sentinelle)
        assert result.total_return_pct == pytest.approx(0.0, rel=1e-6)

    def test_override_win_rate_to_zero(self):
        """Pattern Hybrid: Override win_rate = 0.0 (valide - doit être respecté)."""
        request = BacktestRequest(
            backtest_id="bt-override-zero",
            name="Override Zero",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.FIXED,
        )

        result = BacktestResult(
            result_id="res-override-zero",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=100,
            winning_bets=5,  # 5% normalement
            losing_bets=95,
            win_rate=0.0,  # Override à 0.0 (ajusté manuellement)
            initial_bankroll=10000.0,
            final_bankroll=8000.0,
            total_profit=-2000.0,
            total_staked=5000.0,
            total_returns=3000.0,
            roi=-40.0,
            max_drawdown=-2000.0,
            max_drawdown_pct=-20.0,
            volatility=0.18,
            avg_stake=50.0,
            avg_odds=2.0,
            avg_edge_pct=-4.0,
            avg_profit_per_bet=-20.0,
            largest_win=50.0,
            largest_loss=-50.0,
            longest_winning_streak=2,
            longest_losing_streak=25,
            total_matches_analyzed=500,
            bets_filtered_out=400,
        )

        # Override doit être respecté (0.0, pas 0.05)
        assert result.win_rate == pytest.approx(0.0, rel=1e-6)

    def test_override_metrics_to_none(self):
        """Pattern Hybrid: Override explicite à None valide (pas de données)."""
        request = BacktestRequest(
            backtest_id="bt-override-none",
            name="Override None",
            strategy_name="test",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=10000.0,
            sizing_strategy=SizingStrategy.FIXED,
        )

        result = BacktestResult(
            result_id="res-override-none",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=100,
            winning_bets=60,
            losing_bets=40,
            win_rate=None,  # Override à None (volontaire - données incomplètes)
            initial_bankroll=10000.0,
            final_bankroll=11000.0,
            total_profit=1000.0,
            total_return_pct=None,  # Override à None
            total_staked=5000.0,
            total_returns=6000.0,
            roi=20.0,
            max_drawdown=-100.0,
            max_drawdown_pct=-1.0,
            volatility=0.05,
            avg_stake=50.0,
            avg_odds=2.0,
            avg_edge_pct=5.0,
            avg_profit_per_bet=10.0,
            largest_win=100.0,
            largest_loss=-50.0,
            longest_winning_streak=10,
            longest_losing_streak=5,
            total_matches_analyzed=500,
            bets_filtered_out=400,
        )

        # Override doit être respecté (None, pas calculé)
        assert result.win_rate is None
        assert result.total_return_pct is None

    def test_extreme_return_percentage(self):
        """Edge case: Rendement extrême (1000%)."""
        request = BacktestRequest(
            backtest_id="bt-extreme-return",
            name="Extreme Return",
            strategy_name="lucky_strategy",
            strategy_version="1.0",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_bankroll=1000.0,  # Petit capital
            sizing_strategy=SizingStrategy.KELLY,
        )

        result = BacktestResult(
            result_id="res-extreme-return",
            request=request,
            status=BacktestStatus.COMPLETED,
            total_bets=20,
            winning_bets=18,
            losing_bets=2,
            initial_bankroll=1000.0,
            final_bankroll=11000.0,  # x11
            total_profit=10000.0,  # +1000%
            total_staked=2000.0,
            total_returns=12000.0,
            roi=500.0,
            max_drawdown=-50.0,
            max_drawdown_pct=-3.0,
            volatility=0.30,
            avg_stake=100.0,
            avg_odds=5.0,  # Hautes cotes
            avg_edge_pct=25.0,
            avg_profit_per_bet=500.0,
            largest_win=2000.0,
            largest_loss=-100.0,
            longest_winning_streak=15,
            longest_losing_streak=2,
            total_matches_analyzed=100,
            bets_filtered_out=80,
        )

        assert result.total_return_pct == pytest.approx(1000.0, rel=1e-6)  # +1000%
