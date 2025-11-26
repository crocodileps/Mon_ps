"""
TRACKING CLV 2.0 - Stats Aggregator AVANCÉ
Agrégation et calcul de toutes les statistiques
"""
import structlog
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, date
from dataclasses import dataclass
import asyncpg
import math

logger = structlog.get_logger()


@dataclass
class RiskMetrics:
    """Métriques de risque calculées"""
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration: int
    current_drawdown_pct: float
    profit_factor: float
    win_loss_ratio: float
    kelly_optimal: float
    volatility: float


class StatsAggregator:
    """
    Agrégateur de statistiques professionnel.
    
    Calcule et met à jour:
    - Stats par marché
    - Stats par ligue
    - Stats journalières
    - Métriques de risque (Sharpe, Sortino, Drawdown)
    - Calibration des scores
    - Performance du modèle
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================
    # MISE À JOUR DES STATS MARCHÉ
    # ========================================================
    
    async def update_market_stats(self, market_type: str = None):
        """
        Met à jour les statistiques agrégées par marché.
        Si market_type est None, met à jour tous les marchés.
        """
        async with self.db.acquire() as conn:
            markets = [market_type] if market_type else await self._get_all_markets(conn)
            
            for market in markets:
                stats = await conn.fetchrow("""
                    WITH market_data AS (
                        SELECT
                            o.outcome,
                            o.profit_loss,
                            o.clv_pct,
                            p.confidence,
                            p.value_rating,
                            p.kelly_pct,
                            p.score,
                            p.odds_at_analysis
                        FROM fg_pick_outcomes o
                        JOIN fg_market_predictions p ON o.prediction_id = p.id
                        WHERE o.market_type = $1
                        AND o.outcome IN ('win', 'loss', 'push')
                    )
                    SELECT
                        COUNT(*) as total_resolved,
                        SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN outcome = 'push' THEN 1 ELSE 0 END) as pushes,
                        
                        -- Win rate
                        ROUND(
                            SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END)::numeric /
                            NULLIF(SUM(CASE WHEN outcome IN ('win', 'loss') THEN 1 ELSE 0 END), 0) * 100,
                            2
                        ) as win_rate,
                        
                        -- ROI
                        ROUND(
                            SUM(profit_loss)::numeric /
                            NULLIF(COUNT(CASE WHEN outcome IN ('win', 'loss') THEN 1 END), 0) * 100,
                            2
                        ) as roi_pct,
                        
                        -- Moyennes
                        ROUND(AVG(odds_at_analysis)::numeric, 2) as avg_odds,
                        ROUND(AVG(kelly_pct)::numeric, 2) as avg_kelly,
                        ROUND(AVG(clv_pct)::numeric, 2) as avg_clv,
                        ROUND(
                            SUM(CASE WHEN clv_pct > 0 THEN 1 ELSE 0 END)::numeric /
                            NULLIF(COUNT(clv_pct), 0) * 100,
                            2
                        ) as clv_positive_rate,
                        ROUND(SUM(clv_pct)::numeric, 2) as total_clv_edge,
                        
                        -- Par confiance HIGH
                        SUM(CASE WHEN confidence = 'HIGH' THEN 1 ELSE 0 END) as high_conf_count,
                        SUM(CASE WHEN confidence = 'HIGH' AND outcome = 'win' THEN 1 ELSE 0 END) as high_conf_wins,
                        
                        -- Par confiance MEDIUM
                        SUM(CASE WHEN confidence = 'MEDIUM' THEN 1 ELSE 0 END) as medium_conf_count,
                        SUM(CASE WHEN confidence = 'MEDIUM' AND outcome = 'win' THEN 1 ELSE 0 END) as medium_conf_wins,
                        
                        -- Par confiance LOW
                        SUM(CASE WHEN confidence = 'LOW' THEN 1 ELSE 0 END) as low_conf_count,
                        SUM(CASE WHEN confidence = 'LOW' AND outcome = 'win' THEN 1 ELSE 0 END) as low_conf_wins,
                        
                        -- Par Value Rating DIAMOND
                        SUM(CASE WHEN value_rating LIKE '%%DIAMOND%%' THEN 1 ELSE 0 END) as diamond_count,
                        SUM(CASE WHEN value_rating LIKE '%%DIAMOND%%' AND outcome = 'win' THEN 1 ELSE 0 END) as diamond_wins,
                        
                        -- Par Value Rating STRONG
                        SUM(CASE WHEN value_rating LIKE '%%STRONG%%' THEN 1 ELSE 0 END) as strong_count,
                        SUM(CASE WHEN value_rating LIKE '%%STRONG%%' AND outcome = 'win' THEN 1 ELSE 0 END) as strong_wins,
                        
                        -- Par tranche de score
                        SUM(CASE WHEN score >= 90 THEN 1 ELSE 0 END) as score_90_100_count,
                        SUM(CASE WHEN score >= 90 AND outcome = 'win' THEN 1 ELSE 0 END) as score_90_100_wins,
                        SUM(CASE WHEN score >= 80 AND score < 90 THEN 1 ELSE 0 END) as score_80_90_count,
                        SUM(CASE WHEN score >= 80 AND score < 90 AND outcome = 'win' THEN 1 ELSE 0 END) as score_80_90_wins,
                        SUM(CASE WHEN score >= 70 AND score < 80 THEN 1 ELSE 0 END) as score_70_80_count,
                        SUM(CASE WHEN score >= 70 AND score < 80 AND outcome = 'win' THEN 1 ELSE 0 END) as score_70_80_wins,
                        SUM(CASE WHEN score >= 60 AND score < 70 THEN 1 ELSE 0 END) as score_60_70_count,
                        SUM(CASE WHEN score >= 60 AND score < 70 AND outcome = 'win' THEN 1 ELSE 0 END) as score_60_70_wins,
                        SUM(CASE WHEN score < 60 THEN 1 ELSE 0 END) as score_below_60_count,
                        SUM(CASE WHEN score < 60 AND outcome = 'win' THEN 1 ELSE 0 END) as score_below_60_wins
                        
                    FROM market_data
                """, market)
                
                if stats and stats['total_resolved']:
                    # Calculer ROI par confiance
                    high_roi = await self._calculate_roi_for_filter(
                        conn, market, "confidence = 'HIGH'"
                    )
                    medium_roi = await self._calculate_roi_for_filter(
                        conn, market, "confidence = 'MEDIUM'"
                    )
                    low_roi = await self._calculate_roi_for_filter(
                        conn, market, "confidence = 'LOW'"
                    )
                    diamond_roi = await self._calculate_roi_for_filter(
                        conn, market, "value_rating LIKE '%DIAMOND%'"
                    )
                    strong_roi = await self._calculate_roi_for_filter(
                        conn, market, "value_rating LIKE '%STRONG%'"
                    )
                    
                    # Calculer le streak courant
                    current_streak = await self._calculate_current_streak(conn, market)
                    best_streak, worst_streak = await self._calculate_best_worst_streak(conn, market)
                    
                    # Mettre à jour
                    await conn.execute("""
                        UPDATE fg_market_stats SET
                            total_resolved = $2,
                            wins = $3,
                            losses = $4,
                            pushes = $5,
                            win_rate = $6,
                            roi_pct = $7,
                            avg_odds = $8,
                            avg_kelly = $9,
                            avg_clv = $10,
                            clv_positive_rate = $11,
                            total_clv_edge = $12,
                            high_conf_count = $13,
                            high_conf_wins = $14,
                            high_conf_roi = $15,
                            medium_conf_count = $16,
                            medium_conf_wins = $17,
                            medium_conf_roi = $18,
                            low_conf_count = $19,
                            low_conf_wins = $20,
                            low_conf_roi = $21,
                            diamond_count = $22,
                            diamond_wins = $23,
                            diamond_roi = $24,
                            strong_count = $25,
                            strong_wins = $26,
                            strong_roi = $27,
                            score_90_100_count = $28,
                            score_90_100_wins = $29,
                            score_80_90_count = $30,
                            score_80_90_wins = $31,
                            score_70_80_count = $32,
                            score_70_80_wins = $33,
                            score_60_70_count = $34,
                            score_60_70_wins = $35,
                            score_below_60_count = $36,
                            score_below_60_wins = $37,
                            current_streak = $38,
                            best_streak = $39,
                            worst_streak = $40,
                            last_updated = NOW()
                        WHERE market_type = $1
                    """,
                        market,
                        stats['total_resolved'],
                        stats['wins'],
                        stats['losses'],
                        stats['pushes'],
                        stats['win_rate'],
                        stats['roi_pct'],
                        stats['avg_odds'],
                        stats['avg_kelly'],
                        stats['avg_clv'],
                        stats['clv_positive_rate'],
                        stats['total_clv_edge'],
                        stats['high_conf_count'],
                        stats['high_conf_wins'],
                        high_roi,
                        stats['medium_conf_count'],
                        stats['medium_conf_wins'],
                        medium_roi,
                        stats['low_conf_count'],
                        stats['low_conf_wins'],
                        low_roi,
                        stats['diamond_count'],
                        stats['diamond_wins'],
                        diamond_roi,
                        stats['strong_count'],
                        stats['strong_wins'],
                        strong_roi,
                        stats['score_90_100_count'],
                        stats['score_90_100_wins'],
                        stats['score_80_90_count'],
                        stats['score_80_90_wins'],
                        stats['score_70_80_count'],
                        stats['score_70_80_wins'],
                        stats['score_60_70_count'],
                        stats['score_60_70_wins'],
                        stats['score_below_60_count'],
                        stats['score_below_60_wins'],
                        current_streak,
                        best_streak,
                        worst_streak
                    )
                    
                    logger.debug(
                        "market_stats_updated",
                        market=market,
                        wins=stats['wins'],
                        losses=stats['losses'],
                        roi=stats['roi_pct']
                    )
    
    async def _get_all_markets(self, conn) -> List[str]:
        """Récupère tous les types de marchés"""
        rows = await conn.fetch("SELECT market_type FROM fg_market_stats")
        return [r['market_type'] for r in rows]
    
    async def _calculate_roi_for_filter(
        self, 
        conn, 
        market: str, 
        filter_condition: str
    ) -> Optional[float]:
        """Calcule le ROI pour un filtre spécifique"""
        row = await conn.fetchrow(f"""
            SELECT ROUND(
                SUM(o.profit_loss)::numeric /
                NULLIF(COUNT(CASE WHEN o.outcome IN ('win', 'loss') THEN 1 END), 0) * 100,
                2
            ) as roi
            FROM fg_pick_outcomes o
            JOIN fg_market_predictions p ON o.prediction_id = p.id
            WHERE o.market_type = $1
            AND o.outcome IN ('win', 'loss')
            AND {filter_condition}
        """, market)
        return row['roi'] if row else None
    
    async def _calculate_current_streak(self, conn, market: str) -> int:
        """Calcule la série en cours (positif = wins, négatif = losses)"""
        rows = await conn.fetch("""
            SELECT outcome
            FROM fg_pick_outcomes
            WHERE market_type = $1
            AND outcome IN ('win', 'loss')
            ORDER BY resolved_at DESC
            LIMIT 50
        """, market)
        
        if not rows:
            return 0
        
        first_outcome = rows[0]['outcome']
        streak = 0
        
        for row in rows:
            if row['outcome'] == first_outcome:
                streak += 1
            else:
                break
        
        return streak if first_outcome == 'win' else -streak
    
    async def _calculate_best_worst_streak(
        self, 
        conn, 
        market: str
    ) -> tuple:
        """Calcule les meilleures et pires séries historiques"""
        rows = await conn.fetch("""
            SELECT outcome
            FROM fg_pick_outcomes
            WHERE market_type = $1
            AND outcome IN ('win', 'loss')
            ORDER BY resolved_at ASC
        """, market)
        
        if not rows:
            return 0, 0
        
        best_win_streak = 0
        worst_loss_streak = 0
        current_win = 0
        current_loss = 0
        
        for row in rows:
            if row['outcome'] == 'win':
                current_win += 1
                current_loss = 0
                best_win_streak = max(best_win_streak, current_win)
            else:
                current_loss += 1
                current_win = 0
                worst_loss_streak = max(worst_loss_streak, current_loss)
        
        return best_win_streak, -worst_loss_streak
    
    # ========================================================
    # STATS JOURNALIÈRES
    # ========================================================
    
    async def update_daily_performance(self, target_date: date = None):
        """Met à jour les stats journalières"""
        if target_date is None:
            target_date = date.today()
        
        async with self.db.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(DISTINCT a.match_id) as total_analyses,
                    COUNT(o.id) as total_predictions,
                    SUM(CASE WHEN o.outcome IS NOT NULL THEN 1 ELSE 0 END) as resolved_predictions,
                    SUM(CASE WHEN o.outcome = 'win' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN o.outcome = 'loss' THEN 1 ELSE 0 END) as losses,
                    ROUND(
                        SUM(CASE WHEN o.outcome = 'win' THEN 1 ELSE 0 END)::numeric /
                        NULLIF(SUM(CASE WHEN o.outcome IN ('win', 'loss') THEN 1 ELSE 0 END), 0) * 100,
                        2
                    ) as win_rate,
                    SUM(CASE WHEN o.outcome IN ('win', 'loss') THEN 1 ELSE 0 END) as total_staked,
                    ROUND(SUM(COALESCE(o.profit_loss, 0))::numeric, 2) as total_profit,
                    ROUND(AVG(o.clv_pct)::numeric, 2) as avg_clv,
                    SUM(CASE WHEN o.clv_pct > 0 THEN 1 ELSE 0 END) as clv_positive_count
                FROM fg_analyses a
                LEFT JOIN fg_market_predictions p ON a.analysis_id = p.analysis_id
                LEFT JOIN fg_pick_outcomes o ON p.id = o.prediction_id
                WHERE DATE(a.commence_time) = $1
            """, target_date)
            
            if stats['total_analyses']:
                # Calculer ROI journalier
                daily_roi = None
                if stats['total_staked'] and stats['total_staked'] > 0:
                    daily_roi = round(
                        (stats['total_profit'] / stats['total_staked']) * 100, 2
                    )
                
                # Calculer le cumul
                cumul = await conn.fetchrow("""
                    SELECT 
                        COALESCE(SUM(total_profit), 0) as cumulative_profit
                    FROM fg_daily_performance
                    WHERE date < $1
                """, target_date)
                
                cumulative_profit = (cumul['cumulative_profit'] or 0) + (stats['total_profit'] or 0)
                
                # Trouver best/worst market du jour
                best_worst = await conn.fetchrow("""
                    SELECT
                        (SELECT market_type FROM fg_pick_outcomes 
                         WHERE DATE(resolved_at) = $1 
                         GROUP BY market_type 
                         ORDER BY SUM(profit_loss) DESC LIMIT 1) as best_market,
                        (SELECT ROUND(SUM(profit_loss)::numeric, 2) FROM fg_pick_outcomes 
                         WHERE DATE(resolved_at) = $1 
                         GROUP BY market_type 
                         ORDER BY SUM(profit_loss) DESC LIMIT 1) as best_market_roi,
                        (SELECT market_type FROM fg_pick_outcomes 
                         WHERE DATE(resolved_at) = $1 
                         GROUP BY market_type 
                         ORDER BY SUM(profit_loss) ASC LIMIT 1) as worst_market,
                        (SELECT ROUND(SUM(profit_loss)::numeric, 2) FROM fg_pick_outcomes 
                         WHERE DATE(resolved_at) = $1 
                         GROUP BY market_type 
                         ORDER BY SUM(profit_loss) ASC LIMIT 1) as worst_market_roi
                """, target_date)
                
                await conn.execute("""
                    INSERT INTO fg_daily_performance (
                        date, total_analyses, total_predictions, resolved_predictions,
                        wins, losses, win_rate,
                        total_staked, total_profit, daily_roi, cumulative_profit,
                        avg_clv, clv_positive_count,
                        best_market, best_market_roi, worst_market, worst_market_roi
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                    ON CONFLICT (date) DO UPDATE SET
                        total_analyses = EXCLUDED.total_analyses,
                        wins = EXCLUDED.wins,
                        losses = EXCLUDED.losses,
                        total_profit = EXCLUDED.total_profit,
                        cumulative_profit = EXCLUDED.cumulative_profit,
                        created_at = NOW()
                """,
                    target_date,
                    stats['total_analyses'],
                    stats['total_predictions'],
                    stats['resolved_predictions'],
                    stats['wins'],
                    stats['losses'],
                    stats['win_rate'],
                    stats['total_staked'],
                    stats['total_profit'],
                    daily_roi,
                    cumulative_profit,
                    stats['avg_clv'],
                    stats['clv_positive_count'],
                    best_worst['best_market'] if best_worst else None,
                    best_worst['best_market_roi'] if best_worst else None,
                    best_worst['worst_market'] if best_worst else None,
                    best_worst['worst_market_roi'] if best_worst else None
                )
                
                logger.info(
                    "daily_performance_updated",
                    date=str(target_date),
                    profit=stats['total_profit'],
                    cumulative=cumulative_profit
                )
    
    # ========================================================
    # MÉTRIQUES DE RISQUE
    # ========================================================
    
    async def calculate_risk_metrics(
        self,
        scope_type: str = "global",
        scope_value: str = None,
        days: int = 90
    ) -> RiskMetrics:
        """
        Calcule les métriques de risque avancées.
        """
        async with self.db.acquire() as conn:
            # Récupérer les returns journaliers
            where_clause = ""
            if scope_type == "market" and scope_value:
                where_clause = f"AND o.market_type = '{scope_value}'"
            elif scope_type == "league" and scope_value:
                where_clause = f"AND a.league = '{scope_value}'"
            
            daily_returns = await conn.fetch(f"""
                SELECT
                    DATE(o.resolved_at) as date,
                    SUM(o.profit_loss) as daily_pnl,
                    COUNT(*) as num_bets
                FROM fg_pick_outcomes o
                JOIN fg_market_predictions p ON o.prediction_id = p.id
                JOIN fg_analyses a ON p.analysis_id = a.analysis_id
                WHERE o.outcome IN ('win', 'loss')
                AND o.resolved_at >= CURRENT_DATE - INTERVAL '{days} days'
                {where_clause}
                GROUP BY DATE(o.resolved_at)
                ORDER BY date
            """)
            
            if len(daily_returns) < 5:
                return RiskMetrics(
                    sharpe_ratio=0, sortino_ratio=0,
                    max_drawdown_pct=0, max_drawdown_duration=0,
                    current_drawdown_pct=0, profit_factor=1,
                    win_loss_ratio=1, kelly_optimal=0, volatility=0
                )
            
            returns = [float(r['daily_pnl']) for r in daily_returns]
            
            # Calculs
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            volatility = math.sqrt(variance)
            
            # Sharpe Ratio (annualisé)
            sharpe = (avg_return / volatility * math.sqrt(252)) if volatility > 0 else 0
            
            # Sortino Ratio (seulement downside volatility)
            negative_returns = [r for r in returns if r < 0]
            downside_variance = sum(r ** 2 for r in negative_returns) / len(returns) if negative_returns else 0
            downside_vol = math.sqrt(downside_variance)
            sortino = (avg_return / downside_vol * math.sqrt(252)) if downside_vol > 0 else sharpe
            
            # Max Drawdown
            equity_curve = []
            cumulative = 0
            for r in returns:
                cumulative += r
                equity_curve.append(cumulative)
            
            peak = equity_curve[0]
            max_dd = 0
            dd_start = 0
            max_dd_duration = 0
            current_dd_start = 0
            
            for i, equity in enumerate(equity_curve):
                if equity > peak:
                    peak = equity
                    dd_start = i
                dd = (peak - equity) / max(abs(peak), 1) * 100 if peak != 0 else 0
                if dd > max_dd:
                    max_dd = dd
                    max_dd_duration = i - dd_start
            
            # Current drawdown
            current_dd = (peak - equity_curve[-1]) / max(abs(peak), 1) * 100 if peak != 0 else 0
            
            # Profit Factor
            gross_profit = sum(r for r in returns if r > 0)
            gross_loss = abs(sum(r for r in returns if r < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Win/Loss Ratio
            wins = [r for r in returns if r > 0]
            losses = [abs(r) for r in returns if r < 0]
            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 1
            win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
            
            # Kelly Optimal
            win_rate = len(wins) / len(returns) if returns else 0
            kelly = 0
            if avg_loss > 0 and win_loss_ratio > 0:
                kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
                kelly = max(0, min(kelly * 100, 25))  # Cap à 25%
            
            metrics = RiskMetrics(
                sharpe_ratio=round(sharpe, 3),
                sortino_ratio=round(sortino, 3),
                max_drawdown_pct=round(max_dd, 2),
                max_drawdown_duration=max_dd_duration,
                current_drawdown_pct=round(current_dd, 2),
                profit_factor=round(profit_factor, 2),
                win_loss_ratio=round(win_loss_ratio, 2),
                kelly_optimal=round(kelly, 2),
                volatility=round(volatility, 4)
            )
            
            # Sauvegarder en base
            await conn.execute("""
                INSERT INTO fg_risk_metrics (
                    scope_type, scope_value, period_days,
                    sharpe_ratio, sortino_ratio,
                    max_drawdown_pct, max_drawdown_duration, current_drawdown_pct,
                    profit_factor, win_loss_ratio, optimal_kelly, volatility
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (scope_type, scope_value, period_days) DO UPDATE SET
                    sharpe_ratio = EXCLUDED.sharpe_ratio,
                    sortino_ratio = EXCLUDED.sortino_ratio,
                    max_drawdown_pct = EXCLUDED.max_drawdown_pct,
                    calculated_at = NOW()
            """,
                scope_type,
                scope_value,
                days,
                metrics.sharpe_ratio,
                metrics.sortino_ratio,
                metrics.max_drawdown_pct,
                metrics.max_drawdown_duration,
                metrics.current_drawdown_pct,
                metrics.profit_factor,
                metrics.win_loss_ratio,
                metrics.kelly_optimal,
                metrics.volatility
            )
            
            return metrics
    
    # ========================================================
    # CALIBRATION
    # ========================================================
    
    async def calculate_score_calibration(self):
        """
        Calcule la calibration des scores.
        Compare les probabilités prédites aux résultats réels.
        """
        async with self.db.acquire() as conn:
            buckets = [
                (90, 100), (80, 89), (70, 79), 
                (60, 69), (50, 59), (0, 49)
            ]
            
            for min_score, max_score in buckets:
                for market_type in [None] + list(await self._get_all_markets(conn)):
                    market_filter = f"AND p.market_type = '{market_type}'" if market_type else ""
                    
                    stats = await conn.fetchrow(f"""
                        SELECT
                            COUNT(*) as total_predictions,
                            SUM(CASE WHEN o.outcome = 'win' THEN 1 ELSE 0 END) as actual_wins,
                            SUM(p.probability / 100) as expected_wins,
                            ROUND(
                                SUM(CASE WHEN o.outcome = 'win' THEN 1 ELSE 0 END)::numeric /
                                NULLIF(COUNT(*), 0) * 100,
                                2
                            ) as actual_win_rate,
                            ROUND(AVG(p.probability)::numeric, 2) as expected_win_rate
                        FROM fg_market_predictions p
                        JOIN fg_pick_outcomes o ON p.id = o.prediction_id
                        WHERE p.score >= {min_score} AND p.score <= {max_score}
                        AND o.outcome IN ('win', 'loss')
                        {market_filter}
                    """)
                    
                    if stats['total_predictions'] and stats['total_predictions'] >= 10:
                        calibration_error = abs(
                            (stats['actual_win_rate'] or 0) - (stats['expected_win_rate'] or 0)
                        )
                        is_overconfident = (stats['actual_win_rate'] or 0) < (stats['expected_win_rate'] or 0)
                        
                        # Facteur de correction suggéré
                        if stats['expected_win_rate'] and stats['expected_win_rate'] > 0:
                            adjustment = (stats['actual_win_rate'] or 0) / stats['expected_win_rate']
                        else:
                            adjustment = 1.0
                        
                        await conn.execute("""
                            INSERT INTO fg_score_calibration (
                                score_min, score_max, market_type,
                                total_predictions, actual_wins, expected_wins,
                                actual_win_rate, expected_win_rate, calibration_error,
                                is_overconfident, is_underconfident, confidence_adjustment
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                            ON CONFLICT (score_min, score_max, market_type) DO UPDATE SET
                                total_predictions = EXCLUDED.total_predictions,
                                actual_wins = EXCLUDED.actual_wins,
                                calibration_error = EXCLUDED.calibration_error,
                                calculated_at = NOW()
                        """,
                            min_score,
                            max_score,
                            market_type,
                            stats['total_predictions'],
                            stats['actual_wins'],
                            stats['expected_wins'],
                            stats['actual_win_rate'],
                            stats['expected_win_rate'],
                            calibration_error,
                            is_overconfident,
                            not is_overconfident,
                            round(adjustment, 2)
                        )
        
        logger.info("score_calibration_updated")
    
    # ========================================================
    # AGRÉGATION COMPLÈTE
    # ========================================================
    
    async def run_full_aggregation(self):
        """
        Lance toutes les agrégations.
        À appeler via cron quotidien.
        """
        logger.info("starting_full_aggregation")
        
        try:
            # 1. Stats par marché
            await self.update_market_stats()
            
            # 2. Stats journalières (aujourd'hui + hier)
            await self.update_daily_performance(date.today())
            await self.update_daily_performance(date.today() - timedelta(days=1))
            
            # 3. Métriques de risque
            await self.calculate_risk_metrics("global", None, 30)
            await self.calculate_risk_metrics("global", None, 90)
            
            # 4. Calibration
            await self.calculate_score_calibration()
            
            logger.info("full_aggregation_completed")
            
        except Exception as e:
            logger.error("aggregation_error", error=str(e))
            raise
