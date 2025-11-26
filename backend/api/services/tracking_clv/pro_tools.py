"""
TRACKING CLV 2.0 - PRO TOOLS
Outils professionnels pour maximiser les gains
"""
import structlog
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncpg
import math
import random

logger = structlog.get_logger()


# ============================================================
# 1. KELLY CRITERION AVANCÉ
# ============================================================

class KellyMode(str, Enum):
    FULL = "full"           # Kelly complet (trop agressif)
    HALF = "half"           # Demi-Kelly (recommandé)
    QUARTER = "quarter"     # Quart-Kelly (conservateur)
    DYNAMIC = "dynamic"     # Ajusté selon drawdown


@dataclass
class KellyResult:
    """Résultat du calcul Kelly avancé"""
    kelly_full: float           # Kelly complet
    kelly_recommended: float    # Kelly recommandé (ajusté)
    stake_units: float          # Mise en unités
    stake_pct: float            # % de bankroll
    confidence_adjusted: float  # Kelly ajusté par confiance historique
    variance_adjusted: float    # Kelly ajusté par variance
    max_stake_cap: float        # Plafond de mise suggéré
    risk_of_ruin: float         # Risque de ruine à long terme


class AdvancedKellyCalculator:
    """
    Calculateur Kelly Avancé avec:
    - Kelly fractionnel
    - Ajustement selon drawdown actuel
    - Ajustement selon variance historique
    - Protection contre l'overconfidence
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        
        # Paramètres par défaut
        self.default_fraction = 0.25  # Quart-Kelly par défaut
        self.max_stake_pct = 5.0      # Max 5% de bankroll
        self.drawdown_reduction = 0.5  # Réduction de 50% si en drawdown
    
    def calculate_kelly(
        self,
        probability: float,      # 0-100
        odds: float,
        mode: KellyMode = KellyMode.QUARTER
    ) -> float:
        """
        Calcul Kelly de base.
        Kelly = (bp - q) / b
        où b = odds - 1, p = probabilité, q = 1 - p
        """
        p = probability / 100
        q = 1 - p
        b = odds - 1
        
        if b <= 0:
            return 0
        
        kelly = (b * p - q) / b
        kelly = max(0, kelly)  # Pas de Kelly négatif
        
        # Appliquer le mode
        if mode == KellyMode.HALF:
            kelly *= 0.5
        elif mode == KellyMode.QUARTER:
            kelly *= 0.25
        
        return round(kelly * 100, 2)  # En %
    
    async def calculate_advanced_kelly(
        self,
        probability: float,
        odds: float,
        market_type: str,
        bankroll: float = 1000,
        current_drawdown_pct: float = 0
    ) -> KellyResult:
        """
        Calcul Kelly avancé avec tous les ajustements.
        """
        # 1. Kelly de base
        kelly_full = self.calculate_kelly(probability, odds, KellyMode.FULL)
        
        # 2. Récupérer la calibration historique pour ce marché
        calibration_factor = await self._get_calibration_factor(market_type, probability)
        
        # 3. Récupérer la variance historique
        variance_factor = await self._get_variance_factor(market_type)
        
        # 4. Ajustement selon le drawdown
        drawdown_factor = 1.0
        if current_drawdown_pct > 10:
            drawdown_factor = 0.5  # Réduire de 50% si DD > 10%
        elif current_drawdown_pct > 5:
            drawdown_factor = 0.75  # Réduire de 25% si DD > 5%
        
        # 5. Kelly recommandé avec tous les ajustements
        kelly_adjusted = kelly_full * self.default_fraction * calibration_factor * variance_factor * drawdown_factor
        kelly_adjusted = min(kelly_adjusted, self.max_stake_pct)  # Cap
        
        # 6. Calcul du stake
        stake_units = (kelly_adjusted / 100) * bankroll
        
        # 7. Risque de ruine (formule de Thorp)
        # RoR ≈ ((1-edge)/edge)^(bankroll/unit)
        edge = (probability / 100) * odds - 1
        if edge > 0 and kelly_adjusted > 0:
            unit = stake_units
            ror = math.pow((1 - edge) / (1 + edge), bankroll / max(unit, 1))
            ror = min(ror, 1.0)
        else:
            ror = 1.0
        
        return KellyResult(
            kelly_full=kelly_full,
            kelly_recommended=round(kelly_adjusted, 2),
            stake_units=round(stake_units, 2),
            stake_pct=round(kelly_adjusted, 2),
            confidence_adjusted=round(kelly_full * calibration_factor, 2),
            variance_adjusted=round(kelly_full * variance_factor, 2),
            max_stake_cap=self.max_stake_pct,
            risk_of_ruin=round(ror * 100, 4)
        )
    
    async def _get_calibration_factor(
        self, 
        market_type: str, 
        probability: float
    ) -> float:
        """
        Récupère le facteur de calibration basé sur l'historique.
        Si nos prédictions à 80% gagnent seulement 70%, on ajuste.
        """
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT confidence_adjustment
                FROM fg_score_calibration
                WHERE market_type = $1
                AND $2 >= score_min AND $2 <= score_max
            """, market_type, probability)
            
            if row and row['confidence_adjustment']:
                return float(row['confidence_adjustment'])
        
        return 1.0  # Pas d'ajustement par défaut
    
    async def _get_variance_factor(self, market_type: str) -> float:
        """
        Réduit le Kelly si la variance historique est élevée.
        """
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    STDDEV(profit_loss) as std_dev,
                    AVG(profit_loss) as avg_profit
                FROM fg_pick_outcomes
                WHERE market_type = $1
                AND outcome IN ('win', 'loss')
            """, market_type)
            
            if row and row['std_dev'] and row['avg_profit']:
                # Coefficient de variation
                cv = abs(row['std_dev'] / row['avg_profit']) if row['avg_profit'] != 0 else 1
                
                # Plus la variance est haute, plus on réduit
                if cv > 2:
                    return 0.5
                elif cv > 1.5:
                    return 0.7
                elif cv > 1:
                    return 0.85
        
        return 1.0


# ============================================================
# 2. EXPECTED VALUE (EV) CALCULATOR AVANCÉ
# ============================================================

@dataclass
class EVResult:
    """Résultat du calcul EV"""
    ev_raw: float               # EV brut
    ev_no_vig: float            # EV sans vig
    ev_units: float             # EV en unités
    is_positive_ev: bool        # EV+ ?
    edge_pct: float             # Edge en %
    required_win_rate: float    # Win rate requis pour breakeven
    breakeven_odds: float       # Cote breakeven
    value_rating: str           # Classification


class EVCalculator:
    """
    Calculateur d'Expected Value avancé.
    """
    
    def calculate_ev(
        self,
        probability: float,      # 0-100 (notre estimation)
        odds: float,
        stake: float = 1.0
    ) -> EVResult:
        """
        Calcule l'Expected Value.
        EV = (prob × profit) - ((1-prob) × stake)
        """
        p = probability / 100
        q = 1 - p
        
        profit_if_win = (odds - 1) * stake
        loss_if_lose = stake
        
        ev_raw = (p * profit_if_win) - (q * loss_if_lose)
        
        # EV en % du stake
        ev_pct = ev_raw / stake * 100
        
        # Edge = notre prob - prob implicite du marché
        implied_prob = 100 / odds
        edge = probability - implied_prob
        
        # Win rate requis pour breakeven
        required_wr = 100 / odds
        
        # Cote breakeven pour notre probabilité
        breakeven_odds = 100 / probability if probability > 0 else 999
        
        # Classification
        if ev_pct >= 10:
            rating = "💎 EXCEPTIONAL VALUE"
        elif ev_pct >= 5:
            rating = "🔥 STRONG VALUE"
        elif ev_pct >= 2:
            rating = "✅ GOOD VALUE"
        elif ev_pct > 0:
            rating = "🟡 MARGINAL VALUE"
        else:
            rating = "❌ NEGATIVE EV"
        
        return EVResult(
            ev_raw=round(ev_raw, 4),
            ev_no_vig=round(ev_raw * 1.02, 4),  # Approximation +2% pour vig
            ev_units=round(ev_raw, 2),
            is_positive_ev=ev_raw > 0,
            edge_pct=round(edge, 2),
            required_win_rate=round(required_wr, 1),
            breakeven_odds=round(breakeven_odds, 2),
            value_rating=rating
        )
    
    def calculate_ev_with_vig_removal(
        self,
        probability: float,
        odds_selection: float,
        odds_opposite: float
    ) -> EVResult:
        """
        Calcule l'EV avec suppression de la marge bookmaker.
        Plus précis car utilise les vraies probabilités.
        """
        # Calculer les probabilités vraies (sans vig)
        implied_sel = 1 / odds_selection
        implied_opp = 1 / odds_opposite
        total_implied = implied_sel + implied_opp
        
        # Probabilité vraie du marché
        true_market_prob = implied_sel / total_implied * 100
        
        # Cotes vraies (sans vig)
        true_odds = 1 / (implied_sel / total_implied)
        
        # Calculer EV avec les vraies cotes
        return self.calculate_ev(probability, true_odds)


# ============================================================
# 3. STALE LINE FINDER - Trouveur de lignes retardées
# ============================================================

@dataclass
class StaleLine:
    """Ligne retardée détectée"""
    match_id: str
    market_type: str
    bookmaker: str
    current_odds: float
    sharp_odds: float          # Pinnacle
    edge_available: float
    time_since_move: int       # Minutes depuis le mouvement sharp
    is_exploitable: bool


class StaleLineFinder:
    """
    Trouve les lignes qui n'ont pas encore suivi les mouvements sharp.
    
    Quand Pinnacle bouge, les autres bookmakers suivent avec du retard.
    Ce retard = opportunité.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.min_edge_threshold = 2.0  # Minimum 2% d'edge
    
    async def find_stale_lines(self) -> List[StaleLine]:
        """
        Trouve toutes les lignes retardées actuelles.
        """
        stale_lines = []
        
        async with self.db.acquire() as conn:
            # Comparer Pinnacle vs autres bookmakers
            rows = await conn.fetch("""
                SELECT DISTINCT
                    os.match_id,
                    os.market_type,
                    os.odds_pinnacle as sharp_odds,
                    os.odds_best,
                    os.best_bookmaker,
                    os.collected_at,
                    a.home_team,
                    a.away_team,
                    a.commence_time
                FROM fg_odds_snapshots os
                JOIN fg_analyses a ON os.match_id = a.match_id
                WHERE os.snapshot_type = 'analysis'
                AND a.status = 'pending'
                AND a.commence_time > NOW()
                AND os.odds_best > os.odds_pinnacle * 1.02
            """)
            
            for row in rows:
                edge = ((row['odds_best'] / row['sharp_odds']) - 1) * 100
                
                if edge >= self.min_edge_threshold:
                    time_diff = (datetime.now() - row['collected_at']).seconds // 60
                    
                    stale_lines.append(StaleLine(
                        match_id=row['match_id'],
                        market_type=row['market_type'],
                        bookmaker=row['best_bookmaker'],
                        current_odds=float(row['odds_best']),
                        sharp_odds=float(row['sharp_odds']),
                        edge_available=round(edge, 2),
                        time_since_move=time_diff,
                        is_exploitable=edge >= 3.0 and time_diff < 30
                    ))
        
        # Trier par edge disponible
        stale_lines.sort(key=lambda x: -x.edge_available)
        
        return stale_lines


# ============================================================
# 4. MONTE CARLO SIMULATOR - Simulation de scénarios
# ============================================================

@dataclass
class MonteCarloResult:
    """Résultat de simulation Monte Carlo"""
    simulations: int
    expected_profit: float
    median_profit: float
    percentile_5: float         # 5ème percentile (pire cas probable)
    percentile_95: float        # 95ème percentile (meilleur cas probable)
    probability_profit: float   # % de simulations profitables
    probability_double: float   # % de chances de doubler
    probability_ruin: float     # % de chances de ruine
    max_drawdown_avg: float
    bankroll_distribution: List[float]


class MonteCarloSimulator:
    """
    Simule des milliers de scénarios pour évaluer les risques.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def simulate_strategy(
        self,
        initial_bankroll: float = 1000,
        num_simulations: int = 10000,
        num_bets: int = 500,
        market_type: str = None,
        min_score: int = 70
    ) -> MonteCarloResult:
        """
        Simule une stratégie sur N paris.
        """
        # Récupérer les stats historiques
        async with self.db.acquire() as conn:
            where_clause = f"AND p.market_type = '{market_type}'" if market_type else ""
            score_clause = f"AND p.score >= {min_score}"
            
            historical = await conn.fetch(f"""
                SELECT 
                    o.profit_loss,
                    p.odds_at_analysis as odds
                FROM fg_pick_outcomes o
                JOIN fg_market_predictions p ON o.prediction_id = p.id
                WHERE o.outcome IN ('win', 'loss')
                {where_clause}
                {score_clause}
            """)
            
            if len(historical) < 50:
                # Pas assez de données, utiliser des defaults
                win_rate = 0.55
                avg_odds = 1.90
            else:
                wins = sum(1 for r in historical if r['profit_loss'] > 0)
                win_rate = wins / len(historical)
                avg_odds = sum(float(r['odds'] or 1.9) for r in historical) / len(historical)
        
        # Simuler
        final_bankrolls = []
        max_drawdowns = []
        
        for _ in range(num_simulations):
            bankroll = initial_bankroll
            peak = initial_bankroll
            max_dd = 0
            
            for _ in range(num_bets):
                # Stake = 2% de bankroll
                stake = bankroll * 0.02
                
                if random.random() < win_rate:
                    bankroll += stake * (avg_odds - 1)
                else:
                    bankroll -= stake
                
                # Track drawdown
                if bankroll > peak:
                    peak = bankroll
                dd = (peak - bankroll) / peak * 100
                max_dd = max(max_dd, dd)
                
                # Ruine si bankroll < 10% initial
                if bankroll < initial_bankroll * 0.1:
                    break
            
            final_bankrolls.append(bankroll)
            max_drawdowns.append(max_dd)
        
        # Calculer les statistiques
        final_bankrolls.sort()
        
        return MonteCarloResult(
            simulations=num_simulations,
            expected_profit=round(sum(final_bankrolls) / num_simulations - initial_bankroll, 2),
            median_profit=round(final_bankrolls[num_simulations // 2] - initial_bankroll, 2),
            percentile_5=round(final_bankrolls[int(num_simulations * 0.05)] - initial_bankroll, 2),
            percentile_95=round(final_bankrolls[int(num_simulations * 0.95)] - initial_bankroll, 2),
            probability_profit=round(sum(1 for b in final_bankrolls if b > initial_bankroll) / num_simulations * 100, 1),
            probability_double=round(sum(1 for b in final_bankrolls if b >= initial_bankroll * 2) / num_simulations * 100, 1),
            probability_ruin=round(sum(1 for b in final_bankrolls if b < initial_bankroll * 0.1) / num_simulations * 100, 2),
            max_drawdown_avg=round(sum(max_drawdowns) / num_simulations, 1),
            bankroll_distribution=[
                round(final_bankrolls[int(num_simulations * p)] - initial_bankroll, 2)
                for p in [0.1, 0.25, 0.5, 0.75, 0.9]
            ]
        )


# ============================================================
# 5. BIAS DETECTOR - Détection des biais systématiques
# ============================================================

@dataclass
class BiasReport:
    """Rapport de biais détectés"""
    bias_type: str
    severity: str              # 'critical', 'warning', 'info'
    description: str
    impact_estimate: float     # Impact estimé sur le ROI
    recommendation: str


class BiasDetector:
    """
    Détecte les biais systématiques dans les prédictions.
    
    Biais courants:
    - Favorite bias (surestimer les favoris)
    - Home bias (surestimer l'avantage domicile)
    - Overconfidence bias (scores trop hauts)
    - Underdog bias (sous-estimer les outsiders)
    - League bias (certaines ligues mieux prédites)
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def detect_all_biases(self) -> List[BiasReport]:
        """
        Détecte tous les biais.
        """
        biases = []
        
        # 1. Overconfidence Bias
        overconf = await self._detect_overconfidence_bias()
        if overconf:
            biases.append(overconf)
        
        # 2. Market Bias
        market_biases = await self._detect_market_biases()
        biases.extend(market_biases)
        
        # 3. Score Range Bias
        score_bias = await self._detect_score_range_bias()
        if score_bias:
            biases.append(score_bias)
        
        # 4. Timing Bias
        timing_bias = await self._detect_timing_bias()
        if timing_bias:
            biases.append(timing_bias)
        
        return biases
    
    async def _detect_overconfidence_bias(self) -> Optional[BiasReport]:
        """Détecte si les scores sont systématiquement trop optimistes"""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    AVG(p.probability) as avg_predicted,
                    AVG(CASE WHEN o.outcome = 'win' THEN 100 ELSE 0 END) as avg_actual
                FROM fg_market_predictions p
                JOIN fg_pick_outcomes o ON p.id = o.prediction_id
                WHERE o.outcome IN ('win', 'loss')
                AND p.probability >= 60
            """)
            
            if row and row['avg_predicted'] and row['avg_actual']:
                diff = row['avg_predicted'] - row['avg_actual']
                
                if diff > 10:
                    return BiasReport(
                        bias_type="overconfidence",
                        severity="critical",
                        description=f"Prédictions moyennes de {row['avg_predicted']:.1f}% mais win rate réel de {row['avg_actual']:.1f}%",
                        impact_estimate=-diff * 0.1,  # Estimation impact ROI
                        recommendation="Réduire les scores de 10-15% ou ajuster les seuils de confiance"
                    )
                elif diff > 5:
                    return BiasReport(
                        bias_type="overconfidence",
                        severity="warning",
                        description=f"Légère surestimation: prédit {row['avg_predicted']:.1f}%, réel {row['avg_actual']:.1f}%",
                        impact_estimate=-diff * 0.05,
                        recommendation="Surveiller et ajuster si nécessaire"
                    )
        
        return None
    
    async def _detect_market_biases(self) -> List[BiasReport]:
        """Détecte les biais par marché"""
        biases = []
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    p.market_type,
                    AVG(p.probability) as avg_predicted,
                    AVG(CASE WHEN o.outcome = 'win' THEN 100 ELSE 0 END) as avg_actual,
                    COUNT(*) as sample_size
                FROM fg_market_predictions p
                JOIN fg_pick_outcomes o ON p.id = o.prediction_id
                WHERE o.outcome IN ('win', 'loss')
                GROUP BY p.market_type
                HAVING COUNT(*) >= 30
            """)
            
            for row in rows:
                diff = row['avg_predicted'] - row['avg_actual']
                
                if abs(diff) > 15:
                    severity = "critical"
                    bias_dir = "surestimé" if diff > 0 else "sous-estimé"
                    
                    biases.append(BiasReport(
                        bias_type=f"market_bias_{row['market_type']}",
                        severity=severity,
                        description=f"Marché {row['market_type']} {bias_dir}: prédit {row['avg_predicted']:.1f}%, réel {row['avg_actual']:.1f}%",
                        impact_estimate=-abs(diff) * 0.08,
                        recommendation=f"Recalibrer le modèle pour {row['market_type']} ou éviter ce marché"
                    ))
        
        return biases
    
    async def _detect_score_range_bias(self) -> Optional[BiasReport]:
        """Détecte si certaines tranches de score sont problématiques"""
        async with self.db.acquire() as conn:
            # Vérifier si les scores moyens (50-70) sont sur-représentés
            row = await conn.fetchrow("""
                SELECT 
                    SUM(CASE WHEN p.score >= 50 AND p.score < 70 THEN 1 ELSE 0 END) as mid_count,
                    SUM(CASE WHEN p.score >= 70 THEN 1 ELSE 0 END) as high_count,
                    COUNT(*) as total
                FROM fg_market_predictions p
                JOIN fg_pick_outcomes o ON p.id = o.prediction_id
                WHERE o.outcome IN ('win', 'loss')
            """)
            
            if row and row['total'] > 100:
                mid_pct = row['mid_count'] / row['total'] * 100
                
                if mid_pct > 60:
                    return BiasReport(
                        bias_type="score_concentration",
                        severity="warning",
                        description=f"{mid_pct:.0f}% des prédictions entre 50-70% - manque de différenciation",
                        impact_estimate=-2.0,
                        recommendation="Améliorer le modèle pour mieux distinguer les opportunités"
                    )
        
        return None
    
    async def _detect_timing_bias(self) -> Optional[BiasReport]:
        """Détecte si le timing des paris affecte les résultats"""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    AVG(CASE WHEN o.hours_before_match > 24 THEN o.profit_loss END) as early_profit,
                    AVG(CASE WHEN o.hours_before_match <= 24 AND o.hours_before_match > 6 THEN o.profit_loss END) as mid_profit,
                    AVG(CASE WHEN o.hours_before_match <= 6 THEN o.profit_loss END) as late_profit
                FROM fg_pick_outcomes o
                WHERE o.outcome IN ('win', 'loss')
                AND o.hours_before_match IS NOT NULL
            """)
            
            if row:
                profits = {
                    'early': row['early_profit'] or 0,
                    'mid': row['mid_profit'] or 0,
                    'late': row['late_profit'] or 0
                }
                
                best = max(profits.items(), key=lambda x: x[1])
                worst = min(profits.items(), key=lambda x: x[1])
                
                if best[1] - worst[1] > 0.1:
                    return BiasReport(
                        bias_type="timing_bias",
                        severity="info",
                        description=f"Meilleurs résultats en prenant {best[0]} ({best[1]:.3f}/u vs {worst[1]:.3f}/u)",
                        impact_estimate=best[1] - worst[1],
                        recommendation=f"Privilégier les paris {best[0]} timing"
                    )
        
        return None


# ============================================================
# 6. EDGE DECAY ANALYZER - Analyse de la dégradation de l'edge
# ============================================================

@dataclass
class EdgeDecayResult:
    """Résultat d'analyse de décroissance de l'edge"""
    market_type: str
    optimal_window_hours: Tuple[int, int]
    edge_at_48h: float
    edge_at_24h: float
    edge_at_12h: float
    edge_at_6h: float
    edge_at_2h: float
    decay_rate_per_hour: float
    recommendation: str


class EdgeDecayAnalyzer:
    """
    Analyse comment l'edge se dégrade avec le temps.
    
    Important car:
    - Parier trop tôt = risque de mouvement contre nous
    - Parier trop tard = edge déjà capturé par les sharp
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def analyze_edge_decay(self, market_type: str) -> EdgeDecayResult:
        """
        Analyse la décroissance de l'edge pour un marché.
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    CASE
                        WHEN o.hours_before_match >= 48 THEN 48
                        WHEN o.hours_before_match >= 24 THEN 24
                        WHEN o.hours_before_match >= 12 THEN 12
                        WHEN o.hours_before_match >= 6 THEN 6
                        ELSE 2
                    END as hours_bucket,
                    AVG(o.clv_pct) as avg_clv,
                    AVG(o.profit_loss) as avg_profit,
                    COUNT(*) as count
                FROM fg_pick_outcomes o
                WHERE o.market_type = $1
                AND o.hours_before_match IS NOT NULL
                AND o.clv_pct IS NOT NULL
                GROUP BY 1
                ORDER BY 1 DESC
            """, market_type)
            
            edges = {48: 0, 24: 0, 12: 0, 6: 0, 2: 0}
            for row in rows:
                edges[int(row['hours_bucket'])] = float(row['avg_clv'] or 0)
            
            # Trouver la fenêtre optimale
            best_window = max(edges.items(), key=lambda x: x[1])
            
            # Calculer le taux de décroissance
            if edges[48] != 0 and edges[2] != 0:
                decay_rate = (edges[48] - edges[2]) / 46  # 46 heures de différence
            else:
                decay_rate = 0
            
            # Recommandation
            if best_window[0] >= 24:
                rec = "Parier 24-48h avant le match pour capturer le maximum d'edge"
            elif best_window[0] >= 12:
                rec = "Parier 12-24h avant le match, bon compromis edge/info"
            elif best_window[0] >= 6:
                rec = "Parier 6-12h avant, l'edge est encore disponible"
            else:
                rec = "Les mouvements tardifs offrent de la valeur sur ce marché"
            
            return EdgeDecayResult(
                market_type=market_type,
                optimal_window_hours=(best_window[0], best_window[0] - 6 if best_window[0] > 6 else 0),
                edge_at_48h=edges[48],
                edge_at_24h=edges[24],
                edge_at_12h=edges[12],
                edge_at_6h=edges[6],
                edge_at_2h=edges[2],
                decay_rate_per_hour=round(decay_rate, 4),
                recommendation=rec
            )
    
    async def get_optimal_timing_all_markets(self) -> Dict[str, Tuple[int, int]]:
        """
        Retourne la fenêtre de timing optimale pour chaque marché.
        """
        result = {}
        
        async with self.db.acquire() as conn:
            markets = await conn.fetch(
                "SELECT DISTINCT market_type FROM fg_market_stats"
            )
            
            for m in markets:
                decay = await self.analyze_edge_decay(m['market_type'])
                result[m['market_type']] = decay.optimal_window_hours
        
        return result


# ============================================================
# 7. SMART FILTER OPTIMIZER - Optimise les filtres de sélection
# ============================================================

@dataclass
class FilterOptimization:
    """Résultat d'optimisation de filtre"""
    filter_name: str
    current_value: Any
    optimal_value: Any
    current_roi: float
    optimized_roi: float
    improvement_pct: float
    sample_size: int


class SmartFilterOptimizer:
    """
    Trouve les valeurs optimales pour les filtres de sélection.
    
    Optimise:
    - Score minimum
    - Kelly minimum
    - Markets à inclure/exclure
    - Value Rating minimum
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def optimize_min_score(self) -> FilterOptimization:
        """
        Trouve le score minimum optimal.
        """
        async with self.db.acquire() as conn:
            results = []
            
            for min_score in range(50, 95, 5):
                row = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as count,
                        SUM(CASE WHEN o.outcome = 'win' THEN 1 ELSE 0 END) as wins,
                        SUM(o.profit_loss) as profit
                    FROM fg_pick_outcomes o
                    JOIN fg_market_predictions p ON o.prediction_id = p.id
                    WHERE o.outcome IN ('win', 'loss')
                    AND p.score >= $1
                """, min_score)
                
                if row['count'] >= 30:
                    roi = row['profit'] / row['count'] * 100
                    results.append({
                        'min_score': min_score,
                        'count': row['count'],
                        'roi': roi
                    })
            
            if not results:
                return FilterOptimization(
                    filter_name="min_score",
                    current_value=70,
                    optimal_value=70,
                    current_roi=0,
                    optimized_roi=0,
                    improvement_pct=0,
                    sample_size=0
                )
            
            best = max(results, key=lambda x: x['roi'])
            current = next((r for r in results if r['min_score'] == 70), results[0])
            
            return FilterOptimization(
                filter_name="min_score",
                current_value=70,
                optimal_value=best['min_score'],
                current_roi=round(current['roi'], 2),
                optimized_roi=round(best['roi'], 2),
                improvement_pct=round((best['roi'] - current['roi']), 2),
                sample_size=best['count']
            )
    
    async def optimize_min_kelly(self) -> FilterOptimization:
        """
        Trouve le Kelly minimum optimal.
        """
        async with self.db.acquire() as conn:
            results = []
            
            for min_kelly in [0, 1, 2, 3, 4, 5, 7, 10]:
                row = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as count,
                        SUM(o.profit_loss) as profit
                    FROM fg_pick_outcomes o
                    JOIN fg_market_predictions p ON o.prediction_id = p.id
                    WHERE o.outcome IN ('win', 'loss')
                    AND COALESCE(p.kelly_pct, 0) >= $1
                """, min_kelly)
                
                if row['count'] >= 20:
                    roi = row['profit'] / row['count'] * 100
                    results.append({
                        'min_kelly': min_kelly,
                        'count': row['count'],
                        'roi': roi
                    })
            
            if not results:
                return FilterOptimization(
                    filter_name="min_kelly",
                    current_value=0,
                    optimal_value=0,
                    current_roi=0,
                    optimized_roi=0,
                    improvement_pct=0,
                    sample_size=0
                )
            
            best = max(results, key=lambda x: x['roi'])
            current = results[0]  # Current = 0
            
            return FilterOptimization(
                filter_name="min_kelly",
                current_value=0,
                optimal_value=best['min_kelly'],
                current_roi=round(current['roi'], 2),
                optimized_roi=round(best['roi'], 2),
                improvement_pct=round((best['roi'] - current['roi']), 2),
                sample_size=best['count']
            )
    
    async def get_markets_to_exclude(self) -> List[str]:
        """
        Identifie les marchés à exclure car non rentables.
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    market_type,
                    roi_pct,
                    total_resolved
                FROM fg_market_stats
                WHERE total_resolved >= 30
                AND roi_pct < -5
                ORDER BY roi_pct ASC
            """)
            
            return [r['market_type'] for r in rows]
    
    async def optimize_all_filters(self) -> Dict[str, FilterOptimization]:
        """
        Optimise tous les filtres.
        """
        return {
            'min_score': await self.optimize_min_score(),
            'min_kelly': await self.optimize_min_kelly(),
        }
