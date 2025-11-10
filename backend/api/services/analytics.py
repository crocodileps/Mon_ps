"""
Service d'analytics avancé pour Mon_PS
"""
from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import Any, Dict, Iterable, List, Optional, Sequence

from api.services.logging import logger

try:  # pragma: no cover - typage souple selon les modules disponibles
    from api.models.schemas import Bet  # type: ignore  # noqa: F401
except (ImportError, AttributeError):  # pragma: no cover
    Bet = Any  # type: ignore


def _safe_get(item: Any, key: str, default: Any = None) -> Any:
    """Récupère une valeur sur dict/objet avec fallback."""
    if item is None:
        return default
    if isinstance(item, dict):
        return item.get(key, default)
    if hasattr(item, key):
        return getattr(item, key, default)
    mapping = getattr(item, "_mapping", None)
    if mapping and isinstance(mapping, dict):
        return mapping.get(key, default)
    try:
        return item[key]  # type: ignore[index]
    except Exception:  # pragma: no cover - comportement défensif
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    """Convertit en float de manière sûre."""
    if value in (None, "", "null"):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _collect(values: Iterable[Any]) -> List[Any]:
    """Convertit un iterable en liste sans None."""
    return [v for v in values if v is not None]


class AnalyticsService:
    """Service pour les analytics avancés de paris sportifs"""

    # CATÉGORIE 1 : QUALITÉ DES PRÉDICTIONS

    @staticmethod
    def log_clv_by_bookmaker(request_id: str, bets: Sequence[Any]) -> None:
        """Log CLV par bookmaker."""
        bookmaker_stats: Dict[str, Dict[str, List[float]]] = {}

        for bet in bets:
            bookmaker = _safe_get(bet, "bookmaker", "unknown")
            if bookmaker not in bookmaker_stats:
                bookmaker_stats[bookmaker] = {
                    "clvs": [],
                    "odds_accepted": [],
                    "odds_close": [],
                }

            clv = _safe_get(bet, "clv")
            if clv is not None:
                bookmaker_stats[bookmaker]["clvs"].append(_to_float(clv))
                bookmaker_stats[bookmaker]["odds_accepted"].append(
                    _to_float(_safe_get(bet, "odds_value"))
                )
                odds_close = _safe_get(bet, "odds_close")
                if odds_close is not None:
                    bookmaker_stats[bookmaker]["odds_close"].append(_to_float(odds_close))

        for bookmaker, stats in bookmaker_stats.items():
            clvs = stats["clvs"]
            if len(clvs) >= 10:  # Minimum 10 paris
                clv_avg = mean(clvs)
                clv_trend = "improving" if clv_avg > 0 else "declining"

                recommendation = (
                    "increase_stakes"
                    if clv_avg > 0.02
                    else "decrease_stakes"
                    if clv_avg < -0.01
                    else "maintain"
                )

                logger.info(
                    "clv_by_bookmaker",
                    request_id=request_id,
                    bookmaker=bookmaker,
                    clv_last_30_bets=round(clv_avg * 100, 2),
                    clv_trend=clv_trend,
                    bet_count=len(clvs),
                    avg_odds_accepted=round(mean(stats["odds_accepted"]), 2)
                    if stats["odds_accepted"]
                    else None,
                    avg_odds_close=round(mean(stats["odds_close"]), 2)
                    if stats["odds_close"]
                    else None,
                    recommendation=recommendation,
                )

    @staticmethod
    def log_clv_by_market(request_id: str, bets: Sequence[Any]) -> None:
        """Log CLV par type de marché."""
        market_stats: Dict[str, List[float]] = {}

        for bet in bets:
            if _safe_get(bet, "clv") is None:
                continue

            market = _safe_get(bet, "market_type") or "unknown"
            market_stats.setdefault(market, []).append(_to_float(_safe_get(bet, "clv")))

        if not market_stats:
            return

        def _mean(values: List[float]) -> float:
            return mean(values) if values else 0.0

        best_market = max(market_stats.items(), key=lambda x: _mean(x[1]))
        worst_market = min(market_stats.items(), key=lambda x: _mean(x[1]))

        for market, clvs in market_stats.items():
            if len(clvs) >= 5:
                logger.info(
                    "clv_by_market",
                    request_id=request_id,
                    market_type=market,
                    clv_avg=round(_mean(clvs) * 100, 2),
                    clv_std=round(stdev(clvs) * 100, 2) if len(clvs) > 1 else 0,
                    sample_size=len(clvs),
                    best_performing_market=best_market[0],
                    worst_performing_market=worst_market[0],
                )

    @staticmethod
    def log_model_calibration(
        request_id: str, predictions: List[Dict[str, float]], results: List[bool]
    ) -> None:
        """Log calibration du modèle (ECE)."""
        if not predictions or not results:
            return

        n_bins = 10
        bin_boundaries = [i / n_bins for i in range(n_bins + 1)]

        ece = 0.0
        total_predictions = len(predictions)
        for i in range(n_bins):
            lower, upper = bin_boundaries[i], bin_boundaries[i + 1]
            bucket_indices = [
                idx
                for idx, p in enumerate(predictions)
                if lower <= p.get("probability", 0.0) < upper
            ]

            if not bucket_indices:
                continue

            bin_accuracy = sum(results[idx] for idx in bucket_indices) / len(bucket_indices)
            bin_confidence = mean(predictions[idx]["probability"] for idx in bucket_indices)
            ece += abs(bin_accuracy - bin_confidence) * len(bucket_indices) / total_predictions

        action = "retrain" if ece > 0.03 else "ok"
        severity = (
            "critical"
            if ece > 0.05
            else "warning"
            if ece > 0.03
            else "info"
        )

        logger.info(
            "model_calibration_check",
            request_id=request_id,
            model_name="xgboost_v1",
            ece_score=round(ece, 4),
            ece_threshold=0.03,
            predictions_count=len(predictions),
            bins_analyzed=n_bins,
            action_required=action,
            severity=severity,
        )

    # CATÉGORIE 2 : GESTION DE BANKROLL

    @staticmethod
    def log_kelly_analysis(
        request_id: str,
        bet_id: int,
        kelly_full: float,
        kelly_fraction: float,
        stake_recommended: float,
        stake_actual: float,
        bankroll: float,
    ) -> None:
        """Log analyse Kelly Criterion."""
        if bankroll <= 0:
            return

        pct_risked = (stake_actual / bankroll) * 100
        overbetting = pct_risked > 5.0

        logger.info(
            "kelly_stake_analysis",
            request_id=request_id,
            bet_id=bet_id,
            kelly_full=round(kelly_full, 4),
            kelly_fraction=kelly_fraction,
            stake_recommended=round(stake_recommended, 2),
            stake_actual=round(stake_actual, 2),
            bankroll_current=round(bankroll, 2),
            bankroll_pct_risked=round(pct_risked, 2),
            overbetting_alert=overbetting,
        )

    @staticmethod
    def log_bankroll_snapshot(
        request_id: str,
        bankroll_current: float,
        bankroll_start_week: float,
        bankroll_peak: float,
        bankroll_valley: float,
    ) -> None:
        """Log snapshot de bankroll."""
        if bankroll_peak <= 0 or bankroll_current <= 0:
            return

        drawdown_current = ((bankroll_peak - bankroll_current) / bankroll_peak) * 100
        drawdown_max = ((bankroll_peak - bankroll_valley) / bankroll_peak) * 100
        recovery_needed = ((bankroll_peak - bankroll_current) / bankroll_current) * 100

        risk_level = (
            "critical"
            if drawdown_current > 15
            else "high"
            if drawdown_current > 10
            else "medium"
            if drawdown_current > 5
            else "low"
        )

        logger.info(
            "bankroll_snapshot",
            date=datetime.now().isoformat(),
            request_id=request_id,
            bankroll_current=round(bankroll_current, 2),
            bankroll_start_week=round(bankroll_start_week, 2),
            bankroll_peak=round(bankroll_peak, 2),
            bankroll_valley=round(bankroll_valley, 2),
            drawdown_current=round(drawdown_current, 2),
            drawdown_max=round(drawdown_max, 2),
            recovery_needed_pct=round(recovery_needed, 2),
            kill_switch_level=18.0,
            risk_level=risk_level,
        )

    # CATÉGORIE 3 : STRATÉGIE HYBRIDE

    @staticmethod
    def log_daily_allocation(
        request_id: str,
        opportunities: List[Dict[str, Any]],
        tabac_bets: List[Dict[str, Any]],
        ligne_bets: List[Dict[str, Any]],
    ) -> None:
        """Log allocation quotidienne Tabac vs Ligne."""
        tabac_edges = [o.get("edge_pct") for o in tabac_bets if o.get("edge_pct") is not None]
        ligne_edges = [o.get("edge_pct") for o in ligne_bets if o.get("edge_pct") is not None]

        tabac_avg_edge = mean(tabac_edges) if tabac_edges else 0
        ligne_avg_edge = mean(ligne_edges) if ligne_edges else 0

        missed_high_edge = len(
            [
                o
                for o in opportunities
                if o.get("edge_pct", 0) > 10 and o not in tabac_bets and o not in ligne_bets
            ]
        )

        allocation_quality = (
            "optimal"
            if len(tabac_bets) == 10 and len(ligne_bets) == 10
            else "suboptimal"
        )

        logger.info(
            "daily_bet_allocation",
            request_id=request_id,
            date=datetime.now().date().isoformat(),
            total_opportunities=len(opportunities),
            selected_count=len(tabac_bets) + len(ligne_bets),
            tabac_bets_count=len(tabac_bets),
            ligne_bets_count=len(ligne_bets),
            tabac_avg_edge=round(tabac_avg_edge, 2),
            ligne_avg_edge=round(ligne_avg_edge, 2),
            tabac_markets=["h2h", "totals", "btts"],
            ligne_markets=["asian_handicap", "corner_markets"],
            allocation_quality=allocation_quality,
            missed_opportunities=missed_high_edge,
        )

    @staticmethod
    def log_strategy_comparison(
        request_id: str, tabac_bets: Sequence[Any], ligne_bets: Sequence[Any]
    ) -> None:
        """Log comparaison Tabac vs Ligne."""

        def _total_profit(bets: Sequence[Any]) -> float:
            profits = [
                _to_float(_safe_get(b, "actual_profit"), _to_float(_safe_get(b, "profit_loss")))
                for b in bets
            ]
            return sum(profits)

        def _total_stake(bets: Sequence[Any]) -> float:
            return sum(_to_float(_safe_get(b, "stake")) for b in bets)

        def _avg_clv(bets: Sequence[Any]) -> float:
            clvs = [_to_float(_safe_get(b, "clv")) for b in bets if _safe_get(b, "clv") is not None]
            return mean(clvs) if clvs else 0.0

        def _win_count(bets: Sequence[Any]) -> int:
            return sum(1 for b in bets if _safe_get(b, "result") == "won")

        tabac_total_stake = _total_stake(tabac_bets)
        ligne_total_stake = _total_stake(ligne_bets)

        tabac_roi = (
            (_total_profit(tabac_bets) / tabac_total_stake) * 100
            if tabac_total_stake
            else 0
        )
        ligne_roi = (
            (_total_profit(ligne_bets) / ligne_total_stake) * 100
            if ligne_total_stake
            else 0
        )

        tabac_clv = _avg_clv(tabac_bets) * 100
        ligne_clv = _avg_clv(ligne_bets) * 100

        tabac_wins = _win_count(tabac_bets)
        ligne_wins = _win_count(ligne_bets)

        better_strategy = (
            "tabac"
            if tabac_roi > ligne_roi
            else "ligne"
            if ligne_roi > tabac_roi
            else "balanced"
        )

        recommendation = (
            f"increase_{better_strategy}"
            if better_strategy in {"tabac", "ligne"} and abs(tabac_roi - ligne_roi) > 5
            else "keep_balanced"
        )

        logger.info(
            "strategy_comparison",
            request_id=request_id,
            period="last_30_days",
            tabac_bets_count=len(tabac_bets),
            tabac_roi=round(tabac_roi, 2),
            tabac_clv=round(tabac_clv, 2),
            tabac_win_rate=round((tabac_wins / len(tabac_bets)) * 100, 2)
            if tabac_bets
            else 0,
            ligne_bets_count=len(ligne_bets),
            ligne_roi=round(ligne_roi, 2),
            ligne_clv=round(ligne_clv, 2),
            ligne_win_rate=round((ligne_wins / len(ligne_bets)) * 100, 2)
            if ligne_bets
            else 0,
            better_strategy=better_strategy,
            recommendation=recommendation,
        )

    # CATÉGORIE 4 : ANALYSE DES MARCHÉS

    @staticmethod
    def log_market_efficiency(
        request_id: str,
        match_id: str,
        home_team: str,
        away_team: str,
        market_type: str,
        spread: float,
        odds_movement: float,
        liquidity_score: int,
    ) -> None:
        """Log efficience du marché."""
        market_efficiency = "inefficient" if spread > 10 else "efficient"
        edge_sustainability = (
            "high"
            if spread > 15 and abs(odds_movement) < 5
            else "medium"
            if spread > 10
            else "low"
        )

        recommendation = (
            "bet_now"
            if edge_sustainability == "high"
            else "wait"
            if odds_movement > 5
            else "skip"
        )

        logger.info(
            "market_efficiency_score",
            request_id=request_id,
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            market_type=market_type,
            bookmaker_spread=round(spread, 2),
            odds_movement=round(odds_movement, 2),
            liquidity_score=liquidity_score,
            market_efficiency=market_efficiency,
            expected_edge_sustainability=edge_sustainability,
            recommendation=recommendation,
        )

    # CATÉGORIE 5 : DÉTECTION D'ANOMALIES

    @staticmethod
    def log_losing_streak(request_id: str, recent_bets: Sequence[Any]) -> None:
        """Log détection de losing streak."""
        current_streak = 0
        for bet in reversed(list(recent_bets)):
            if _safe_get(bet, "result") == "lost":
                current_streak += 1
            else:
                break

        if current_streak < 5:
            return

        losing_bets = []
        for bet in reversed(list(recent_bets)):
            if _safe_get(bet, "result") == "lost":
                losing_bets.append(bet)
            else:
                break

        clv_values = [
            _to_float(_safe_get(b, "clv")) for b in losing_bets if _safe_get(b, "clv") is not None
        ]
        clv_during_streak = mean(clv_values) if clv_values else 0

        win_rate = 0.5  # Hypothèse de base
        probability = (1 - win_rate) ** current_streak

        recommendation = (
            "continue_betting" if clv_during_streak > 0 else "pause_betting"
        )
        severity = "critical" if current_streak > 10 else "warning"

        logger.warning(
            "losing_streak_alert",
            request_id=request_id,
            current_streak=current_streak,
            longest_streak=max(current_streak, 15),  # Placeholder
            probability_by_chance=round(probability, 4),
            clv_during_streak=round(clv_during_streak * 100, 2),
            recommendation=recommendation,
            severity=severity,
        )

    # CATÉGORIE 6 : MÉTRIQUES AVANCÉES

    @staticmethod
    def log_sharpe_ratio(request_id: str, bets: Sequence[Any], period_days: int = 90) -> None:
        """Log Sharpe Ratio."""
        if len(bets) < 30:
            return

        returns = []
        for bet in bets:
            profit = _safe_get(bet, "actual_profit")
            if profit is None:
                profit = _safe_get(bet, "profit_loss")
            stake = _to_float(_safe_get(bet, "stake"))
            profit_float = _to_float(profit)
            if stake > 0:
                returns.append(profit_float / stake)

        if not returns:
            return

        avg_return = mean(returns)
        std_return = stdev(returns) if len(returns) > 1 else 0

        sharpe_ratio = (avg_return - 0) / std_return if std_return > 0 else 0

        performance = (
            "excellent"
            if sharpe_ratio > 1.5
            else "good"
            if sharpe_ratio > 1.0
            else "poor"
        )

        recommendation = "increase_volume" if sharpe_ratio > 1.5 else "optimize_strategy"

        logger.info(
            "sharpe_ratio_calculation",
            request_id=request_id,
            period=f"last_{period_days}_days",
            total_bets=len(bets),
            avg_return=round(avg_return * 100, 2),
            std_return=round(std_return * 100, 2),
            sharpe_ratio=round(sharpe_ratio, 3),
            sharpe_threshold=1.0,
            risk_adjusted_performance=performance,
            recommendation=recommendation,
        )

