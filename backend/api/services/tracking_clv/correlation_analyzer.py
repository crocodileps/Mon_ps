"""
TRACKING CLV 2.0 - Correlation Analyzer
Analyse des corrélations entre marchés
"""
import structlog
from typing import Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass
import asyncpg
import math

logger = structlog.get_logger()


@dataclass
class CorrelationInsight:
    """Insight sur une corrélation"""
    market_a: str
    market_b: str
    correlation: float
    strength: str           # 'strong_positive', 'moderate', 'weak', 'negative'
    sample_size: int
    both_win_rate: float
    lift: float             # Ratio observé/attendu
    combo_recommendation: str
    confidence_interval: Tuple[float, float]


class CorrelationAnalyzer:
    """
    Analyseur de corrélations entre marchés.
    
    Calcule:
    - Matrice de corrélation 13x13
    - Probabilités conditionnelles P(B|A)
    - Lift et support pour chaque paire
    - Recommandations de combos
    - Détection d'opportunités
    """
    
    # Seuils de corrélation
    STRONG_POSITIVE = 0.7
    MODERATE_POSITIVE = 0.4
    WEAK = 0.2
    MODERATE_NEGATIVE = -0.4
    STRONG_NEGATIVE = -0.7
    
    # Minimum d'échantillons pour calcul fiable
    MIN_SAMPLE_SIZE = 30
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================
    # CALCUL DE CORRÉLATION
    # ========================================================
    
    def pearson_correlation(
        self, 
        x: List[int], 
        y: List[int]
    ) -> Tuple[float, float]:
        """
        Calcule la corrélation de Pearson et son intervalle de confiance.
        
        Returns:
            Tuple (correlation, p_value_approximation)
        """
        n = len(x)
        if n < 3:
            return 0.0, 1.0
        
        # Moyennes
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        # Covariance et écarts-types
        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)
        
        if std_x == 0 or std_y == 0:
            return 0.0, 1.0
        
        correlation = cov / (std_x * std_y)
        
        # P-value approximation (Fisher z-transformation)
        if abs(correlation) >= 0.99:
            p_value = 0.001
        else:
            z = 0.5 * math.log((1 + correlation) / (1 - correlation))
            se = 1 / math.sqrt(n - 3)
            z_score = abs(z) / se
            # Approximation simple
            p_value = max(0.001, math.exp(-0.5 * z_score ** 2))
        
        return round(correlation, 4), round(p_value, 4)
    
    def calculate_lift(
        self,
        p_a: float,
        p_b: float,
        p_ab: float
    ) -> float:
        """
        Calcule le lift: P(A∩B) / (P(A) × P(B))
        
        - Lift > 1: A et B apparaissent ensemble plus que par hasard
        - Lift = 1: Indépendants
        - Lift < 1: A et B sont mutuellement exclusifs
        """
        expected = p_a * p_b
        if expected == 0:
            return 1.0
        return round(p_ab / expected, 3)
    
    def get_correlation_strength(self, corr: float) -> str:
        """Classifie la force de la corrélation"""
        if corr >= self.STRONG_POSITIVE:
            return "strong_positive"
        elif corr >= self.MODERATE_POSITIVE:
            return "moderate_positive"
        elif corr >= self.WEAK:
            return "weak_positive"
        elif corr >= -self.WEAK:
            return "independent"
        elif corr >= self.MODERATE_NEGATIVE:
            return "weak_negative"
        elif corr >= self.STRONG_NEGATIVE:
            return "moderate_negative"
        else:
            return "strong_negative"
    
    def get_combo_recommendation(
        self,
        correlation: float,
        both_win_rate: float,
        lift: float
    ) -> str:
        """Génère une recommandation pour le combo"""
        # Corrélation trop forte = mauvais combo (pas de diversification)
        if correlation > 0.7:
            return "❌ ÉVITER - Trop corrélés, pas de diversification"
        
        # Corrélation négative forte = très mauvais combo
        if correlation < -0.5:
            return "❌ ÉVITER - Corrélation négative, un gagne l'autre perd"
        
        # Combo idéal: faible corrélation + bon win rate combiné
        if abs(correlation) < 0.3 and both_win_rate > 0.30:
            return "✅ EXCELLENT - Faible corrélation, bon win rate combiné"
        
        if abs(correlation) < 0.4 and both_win_rate > 0.25:
            return "🟢 BON - Diversification acceptable"
        
        if abs(correlation) < 0.5 and both_win_rate > 0.20:
            return "🟡 ACCEPTABLE - À considérer avec prudence"
        
        return "⚪ NEUTRE - Pas de recommandation particulière"
    
    # ========================================================
    # CALCUL MATRICE COMPLÈTE
    # ========================================================
    
    async def calculate_correlation_matrix(
        self,
        period_days: int = 90
    ) -> Dict[str, Dict[str, float]]:
        """
        Calcule la matrice de corrélation 13x13.
        """
        async with self.db.acquire() as conn:
            # Récupérer tous les outcomes par analyse
            rows = await conn.fetch("""
                SELECT 
                    p.analysis_id,
                    p.market_type,
                    CASE WHEN o.outcome = 'win' THEN 1 ELSE 0 END as won
                FROM fg_market_predictions p
                JOIN fg_pick_outcomes o ON p.id = o.prediction_id
                WHERE o.outcome IN ('win', 'loss')
                AND o.resolved_at >= CURRENT_DATE - INTERVAL '%s days'
            """ % period_days)
            
            # Organiser par analyse
            by_analysis: Dict[str, Dict[str, int]] = {}
            for row in rows:
                aid = str(row['analysis_id'])
                if aid not in by_analysis:
                    by_analysis[aid] = {}
                by_analysis[aid][row['market_type']] = row['won']
            
            # Calculer les corrélations
            markets = sorted(set(row['market_type'] for row in rows))
            matrix: Dict[str, Dict[str, float]] = {}
            
            for m1 in markets:
                matrix[m1] = {}
                for m2 in markets:
                    if m1 == m2:
                        matrix[m1][m2] = 1.0
                        continue
                    
                    # Trouver les analyses communes
                    x = []
                    y = []
                    for aid, outcomes in by_analysis.items():
                        if m1 in outcomes and m2 in outcomes:
                            x.append(outcomes[m1])
                            y.append(outcomes[m2])
                    
                    if len(x) >= self.MIN_SAMPLE_SIZE:
                        corr, _ = self.pearson_correlation(x, y)
                        matrix[m1][m2] = corr
                    else:
                        matrix[m1][m2] = None
            
            return matrix
    
    async def analyze_all_pairs(
        self,
        period_days: int = 90
    ) -> List[CorrelationInsight]:
        """
        Analyse toutes les paires de marchés.
        """
        insights = []
        
        async with self.db.acquire() as conn:
            # Récupérer les stats par paire
            rows = await conn.fetch("""
                WITH outcomes AS (
                    SELECT 
                        p.analysis_id,
                        p.market_type,
                        CASE WHEN o.outcome = 'win' THEN 1 ELSE 0 END as won
                    FROM fg_market_predictions p
                    JOIN fg_pick_outcomes o ON p.id = o.prediction_id
                    WHERE o.outcome IN ('win', 'loss')
                    AND o.resolved_at >= CURRENT_DATE - INTERVAL '%s days'
                )
                SELECT 
                    a.market_type as market_a,
                    b.market_type as market_b,
                    COUNT(*) as sample_size,
                    SUM(CASE WHEN a.won = 1 AND b.won = 1 THEN 1 ELSE 0 END) as both_win,
                    SUM(a.won) as a_wins,
                    SUM(b.won) as b_wins,
                    CORR(a.won, b.won) as correlation
                FROM outcomes a
                JOIN outcomes b ON a.analysis_id = b.analysis_id 
                    AND a.market_type < b.market_type
                GROUP BY a.market_type, b.market_type
                HAVING COUNT(*) >= %s
            """ % (period_days, self.MIN_SAMPLE_SIZE))
            
            for row in rows:
                n = row['sample_size']
                p_a = row['a_wins'] / n
                p_b = row['b_wins'] / n
                p_ab = row['both_win'] / n
                
                corr = float(row['correlation']) if row['correlation'] else 0
                lift = self.calculate_lift(p_a, p_b, p_ab)
                strength = self.get_correlation_strength(corr)
                recommendation = self.get_combo_recommendation(corr, p_ab, lift)
                
                # Intervalle de confiance approximatif
                se = 1 / math.sqrt(n - 3) if n > 3 else 0.5
                ci = (round(corr - 1.96 * se, 3), round(corr + 1.96 * se, 3))
                
                insights.append(CorrelationInsight(
                    market_a=row['market_a'],
                    market_b=row['market_b'],
                    correlation=round(corr, 4),
                    strength=strength,
                    sample_size=n,
                    both_win_rate=round(p_ab, 4),
                    lift=lift,
                    combo_recommendation=recommendation,
                    confidence_interval=ci
                ))
            
            # Trier par potentiel combo (faible corrélation + bon win rate)
            insights.sort(key=lambda x: (-x.both_win_rate, abs(x.correlation)))
        
        return insights
    
    async def save_correlation_matrix(
        self,
        period_type: str = "last_90d"
    ):
        """
        Sauvegarde la matrice de corrélation en base.
        """
        days = {"last_30d": 30, "last_90d": 90, "all_time": 365 * 10}.get(period_type, 90)
        
        matrix = await self.calculate_correlation_matrix(days)
        insights = await self.analyze_all_pairs(days)
        
        # Trouver les extremes
        strongest_positive = sorted(
            [i for i in insights if i.correlation > 0],
            key=lambda x: -x.correlation
        )[:5]
        
        strongest_negative = sorted(
            [i for i in insights if i.correlation < 0],
            key=lambda x: x.correlation
        )[:5]
        
        best_combos = sorted(
            [i for i in insights if abs(i.correlation) < 0.4],
            key=lambda x: -x.both_win_rate
        )[:10]
        
        avoid_combos = sorted(
            [i for i in insights if i.correlation > 0.6],
            key=lambda x: -x.correlation
        )[:10]
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO fg_market_correlations_matrix (
                    period_type, period_date, correlation_matrix,
                    strongest_positive, strongest_negative,
                    best_combo_pairs, avoid_combo_pairs,
                    sample_size, min_matches_per_pair
                ) VALUES ($1, CURRENT_DATE, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (period_type, period_date) DO UPDATE SET
                    correlation_matrix = EXCLUDED.correlation_matrix,
                    strongest_positive = EXCLUDED.strongest_positive,
                    best_combo_pairs = EXCLUDED.best_combo_pairs,
                    calculated_at = NOW()
            """,
                period_type,
                matrix,
                [{"pair": [i.market_a, i.market_b], "corr": i.correlation} for i in strongest_positive],
                [{"pair": [i.market_a, i.market_b], "corr": i.correlation} for i in strongest_negative],
                [{"pair": [i.market_a, i.market_b], "win_rate": i.both_win_rate, "corr": i.correlation} for i in best_combos],
                [{"pair": [i.market_a, i.market_b], "corr": i.correlation} for i in avoid_combos],
                len(insights) * self.MIN_SAMPLE_SIZE,
                self.MIN_SAMPLE_SIZE
            )
        
        logger.info(
            "correlation_matrix_saved",
            period=period_type,
            pairs_analyzed=len(insights)
        )
    
    # ========================================================
    # PROBABILITÉS CONDITIONNELLES
    # ========================================================
    
    async def calculate_conditional_probabilities(self):
        """
        Calcule P(B gagne | A gagne) pour toutes les paires.
        Utile pour prédire le résultat d'un marché connaissant un autre.
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                WITH outcomes AS (
                    SELECT 
                        p.analysis_id,
                        p.market_type,
                        o.outcome
                    FROM fg_market_predictions p
                    JOIN fg_pick_outcomes o ON p.id = o.prediction_id
                    WHERE o.outcome IN ('win', 'loss')
                )
                SELECT 
                    a.market_type as condition_market,
                    a.outcome as condition_outcome,
                    b.market_type as target_market,
                    COUNT(*) as total,
                    SUM(CASE WHEN b.outcome = 'win' THEN 1 ELSE 0 END) as target_wins,
                    SUM(CASE WHEN b.outcome = 'loss' THEN 1 ELSE 0 END) as target_losses
                FROM outcomes a
                JOIN outcomes b ON a.analysis_id = b.analysis_id 
                    AND a.market_type != b.market_type
                GROUP BY a.market_type, a.outcome, b.market_type
                HAVING COUNT(*) >= 20
            """)
            
            # Calculer les probabilités non conditionnelles pour le lift
            base_probs = await conn.fetch("""
                SELECT 
                    market_type,
                    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END)::float / COUNT(*) as p_win
                FROM fg_pick_outcomes
                WHERE outcome IN ('win', 'loss')
                GROUP BY market_type
            """)
            base_probs_dict = {r['market_type']: r['p_win'] for r in base_probs}
            
            for row in rows:
                p_target_win = row['target_wins'] / row['total']
                p_target_loss = row['target_losses'] / row['total']
                
                base_prob = base_probs_dict.get(row['target_market'], 0.5)
                lift_win = p_target_win / base_prob if base_prob > 0 else 1
                lift_loss = p_target_loss / (1 - base_prob) if base_prob < 1 else 1
                
                # Intervalle de confiance (Wilson)
                n = row['total']
                z = 1.96
                p = p_target_win
                ci_width = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
                
                await conn.execute("""
                    INSERT INTO fg_conditional_probabilities (
                        condition_market, condition_outcome, target_market,
                        p_target_win, p_target_loss,
                        lift_win, lift_loss,
                        sample_size, confidence_interval
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (condition_market, condition_outcome, target_market) 
                    DO UPDATE SET
                        p_target_win = EXCLUDED.p_target_win,
                        lift_win = EXCLUDED.lift_win,
                        calculated_at = NOW()
                """,
                    row['condition_market'],
                    row['condition_outcome'],
                    row['target_market'],
                    round(p_target_win, 4),
                    round(p_target_loss, 4),
                    round(lift_win, 2),
                    round(lift_loss, 2),
                    row['total'],
                    round(ci_width * 100, 1)
                )
        
        logger.info("conditional_probabilities_calculated")
    
    async def get_best_combos(self, min_win_rate: float = 0.25) -> List[Dict[str, Any]]:
        """
        Retourne les meilleurs combos basés sur les corrélations.
        """
        async with self.db.acquire() as conn:
            return await conn.fetch("""
                SELECT * FROM v_fg_best_combos
                WHERE both_win_rate >= $1
                ORDER BY both_win_rate DESC
                LIMIT 20
            """, min_win_rate)
