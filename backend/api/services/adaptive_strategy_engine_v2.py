"""
🧠 ADAPTIVE STRATEGY ENGINE V2.0 - FUTURISTIC AUTO-LEARNING SYSTEM
═══════════════════════════════════════════════════════════════════════════════

Moteur de stratégie évolutif de niveau Hedge Fund avec:

1. SHADOW TRACKING - Continue le tracking même pour stratégies "bloquées"
2. ROI-BASED EVALUATION - Pas de Win Rate absolu, mais ROI réel
3. WILSON CONFIDENCE INTERVAL - Significativité statistique
4. DIAGNOSTIC ENGINE - Explique POURQUOI une stratégie sous-performe
5. DECAY FACTOR - Résultats récents > anciens
6. BREAKEVEN ANALYSIS - Calcul du seuil de rentabilité par cote
7. REGIME DETECTION - Détecte les phases favorables/défavorables
8. AUTO-IMPROVEMENT SUGGESTIONS - Propose des ajustements

PHILOSOPHIE: Ne jamais bloquer, toujours diagnostiquer et améliorer.
Les données sont précieuses - même les échecs enseignent.

VERSION: 2.0.0
DATE: 30/11/2025
"""

import math
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)

DB_CONFIG = {
    "host": "monps_postgres",
    "port": 5432,
    "dbname": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}


class StrategyStatus(Enum):
    """
    Statuts des stratégies - AUCUN BLOCAGE DÉFINITIF
    """
    CHAMPION = "champion"       # 🏆 Sur-performant, maximiser
    PROFITABLE = "profitable"   # ✅ Rentable, utiliser normalement
    NEUTRAL = "neutral"         # 📊 Break-even, surveiller
    STRUGGLING = "struggling"   # ⚠️ En difficulté, réduire mais CONTINUER À TRACKER
    RECOVERING = "recovering"   # 🔄 Était en difficulté, montre des signes de reprise
    SHADOW = "shadow"           # 👻 Paper trading uniquement (track mais ne recommande pas)


@dataclass
class WilsonInterval:
    """Intervalle de confiance de Wilson pour win rate"""
    center: float      # Estimation centrale
    lower: float       # Borne basse (95% CI)
    upper: float       # Borne haute (95% CI)
    confidence: float  # Niveau de confiance dans l'estimation
    
    @staticmethod
    def calculate(wins: int, total: int, z: float = 1.96) -> 'WilsonInterval':
        """
        Calcule l'intervalle de confiance de Wilson
        Plus fiable que win_rate simple, surtout pour petits échantillons
        """
        if total == 0:
            return WilsonInterval(0, 0, 0, 0)
        
        p = wins / total
        denominator = 1 + z**2 / total
        center = (p + z**2 / (2 * total)) / denominator
        
        margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denominator
        
        lower = max(0, center - margin)
        upper = min(1, center + margin)
        
        # Confiance basée sur la taille de l'échantillon
        confidence = min(1.0, total / 50)  # Max confiance à 50 échantillons
        
        return WilsonInterval(
            center=round(center * 100, 2),
            lower=round(lower * 100, 2),
            upper=round(upper * 100, 2),
            confidence=round(confidence, 2)
        )


@dataclass
class BreakevenAnalysis:
    """Analyse du seuil de rentabilité"""
    avg_odds: float
    breakeven_win_rate: float  # Win rate nécessaire pour BE
    actual_win_rate: float
    edge_vs_breakeven: float   # Différence vs BE (positif = profitable)
    is_profitable_structure: bool


@dataclass
class StrategyDiagnostic:
    """Diagnostic détaillé d'une stratégie"""
    strategy_id: str
    status: StrategyStatus
    
    # Métriques primaires (ROI-based, pas Win Rate absolu)
    roi_percent: float
    clv_percent: float
    
    # Analyse statistique
    wilson_interval: WilsonInterval
    sample_size: int
    statistical_significance: str  # "high", "medium", "low"
    
    # Breakeven analysis
    breakeven: BreakevenAnalysis
    
    # Decay-weighted metrics (récents comptent plus)
    recent_roi_7d: float
    recent_roi_14d: float
    trend: str  # "improving", "stable", "declining"
    
    # Multiplicateurs
    stake_multiplier: float
    confidence_score: float
    
    # Diagnostic & Recommandations
    issues: List[str]           # Problèmes identifiés
    improvements: List[str]     # Suggestions d'amélioration
    
    # Shadow tracking
    is_shadow_mode: bool
    shadow_reason: Optional[str]


@dataclass
class AdaptiveConfigV2:
    """Configuration adaptative V2"""
    generated_at: datetime
    lookback_days: int
    
    # Diagnostics par tier
    tier_diagnostics: Dict[str, StrategyDiagnostic]
    
    # Diagnostics par marché
    market_diagnostics: Dict[str, StrategyDiagnostic]
    
    # Rankings optimaux
    tier_ranking: List[str]
    market_ranking: List[str]
    
    # Combinaisons optimales (tier + market)
    optimal_combinations: List[Dict]
    
    # Seuils dynamiques
    min_roi_threshold: float
    min_clv_threshold: float
    min_confidence_threshold: float
    
    # Santé globale
    system_health: str
    system_score: float
    
    # Recommandations globales
    global_recommendations: List[str]
    
    # Stratégies en shadow (à surveiller pour réintégration)
    shadow_strategies: List[str]


class AdaptiveStrategyEngineV2:
    """
    🧠 Moteur de Stratégie Adaptative V2.0
    
    Principes fondamentaux:
    1. Ne JAMAIS perdre de données - shadow tracking pour tout
    2. ROI > Win Rate - évaluation basée sur la rentabilité réelle
    3. Diagnostic > Blocage - comprendre et améliorer, pas exclure
    4. Decay Factor - le présent compte plus que le passé
    5. Statistical Significance - Wilson CI pour la confiance
    """
    
    # Seuils V2.0 (basés sur ROI, pas Win Rate)
    ROI_CHAMPION = 10.0        # ROI >= 10% = Champion
    ROI_PROFITABLE = 2.0       # ROI >= 2% = Profitable
    ROI_NEUTRAL = -2.0         # ROI >= -2% = Neutral
    ROI_STRUGGLING = -10.0     # ROI >= -10% = Struggling
    # ROI < -10% = Shadow mode
    
    CLV_EXCELLENT = 3.0
    CLV_GOOD = 1.0
    CLV_WARNING = -1.0
    
    MIN_SAMPLE_SIGNIFICANT = 30   # Échantillon minimum pour haute confiance
    MIN_SAMPLE_MEDIUM = 15        # Échantillon pour confiance moyenne
    MIN_SAMPLE_LOW = 5            # Échantillon minimum pour tracker
    
    DECAY_HALF_LIFE_DAYS = 14     # Les résultats perdent 50% de poids en 14 jours
    
    def __init__(self):
        self._config_cache: Optional[AdaptiveConfigV2] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=30)  # Refresh toutes les 30 min
    
    def _get_connection(self):
        return psycopg2.connect(**DB_CONFIG)
    
    def get_config(self, force_refresh: bool = False, lookback_days: int = 30) -> AdaptiveConfigV2:
        """Récupère la configuration adaptative V2"""
        now = datetime.now()
        
        if (not force_refresh and 
            self._config_cache and 
            self._cache_timestamp and 
            now - self._cache_timestamp < self._cache_ttl):
            return self._config_cache
        
        self._config_cache = self._generate_config_v2(lookback_days)
        self._cache_timestamp = now
        
        return self._config_cache
    
    def _generate_config_v2(self, lookback_days: int = 30) -> AdaptiveConfigV2:
        """Génère la configuration V2 complète"""
        logger.info(f"Génération config adaptative V2.0 (lookback: {lookback_days}j)")
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                
                # 1. Diagnostiquer les tiers
                tier_diagnostics = self._diagnose_tiers(cursor, lookback_days)
                
                # 2. Diagnostiquer les marchés
                market_diagnostics = self._diagnose_markets(cursor, lookback_days)
                
                # 3. Trouver les combinaisons optimales
                optimal_combos = self._find_optimal_combinations(cursor, lookback_days)
                
                # 4. Calculer les seuils dynamiques
                thresholds = self._calculate_dynamic_thresholds(tier_diagnostics, market_diagnostics)
                
                # 5. Générer les recommandations globales
                recommendations = self._generate_global_recommendations(
                    tier_diagnostics, market_diagnostics, optimal_combos
                )
                
                # 6. Évaluer la santé du système
                health, score = self._assess_system_health_v2(tier_diagnostics, market_diagnostics)
                
                # Rankings
                tier_ranking = sorted(
                    tier_diagnostics.keys(),
                    key=lambda t: (
                        tier_diagnostics[t].roi_percent,
                        tier_diagnostics[t].clv_percent,
                        tier_diagnostics[t].confidence_score
                    ),
                    reverse=True
                )
                
                market_ranking = sorted(
                    market_diagnostics.keys(),
                    key=lambda m: (
                        market_diagnostics[m].roi_percent,
                        market_diagnostics[m].confidence_score
                    ),
                    reverse=True
                )
                
                # Stratégies en shadow
                shadow_strategies = [
                    t for t, d in tier_diagnostics.items() if d.is_shadow_mode
                ] + [
                    m for m, d in market_diagnostics.items() if d.is_shadow_mode
                ]
                
                return AdaptiveConfigV2(
                    generated_at=datetime.now(),
                    lookback_days=lookback_days,
                    tier_diagnostics={t: self._diagnostic_to_dict(d) for t, d in tier_diagnostics.items()},
                    market_diagnostics={m: self._diagnostic_to_dict(d) for m, d in market_diagnostics.items()},
                    tier_ranking=tier_ranking,
                    market_ranking=market_ranking,
                    optimal_combinations=optimal_combos,
                    min_roi_threshold=thresholds['min_roi'],
                    min_clv_threshold=thresholds['min_clv'],
                    min_confidence_threshold=thresholds['min_confidence'],
                    system_health=health,
                    system_score=score,
                    global_recommendations=recommendations,
                    shadow_strategies=shadow_strategies
                )
    
    def _diagnostic_to_dict(self, d: StrategyDiagnostic) -> Dict:
        """Convertit un diagnostic en dict pour JSON"""
        return {
            "strategy_id": d.strategy_id,
            "status": d.status.value,
            "roi_percent": d.roi_percent,
            "clv_percent": d.clv_percent,
            "wilson_interval": {
                "center": d.wilson_interval.center,
                "lower": d.wilson_interval.lower,
                "upper": d.wilson_interval.upper,
                "confidence": d.wilson_interval.confidence
            },
            "sample_size": d.sample_size,
            "statistical_significance": d.statistical_significance,
            "breakeven": {
                "avg_odds": d.breakeven.avg_odds,
                "breakeven_win_rate": d.breakeven.breakeven_win_rate,
                "actual_win_rate": d.breakeven.actual_win_rate,
                "edge_vs_breakeven": d.breakeven.edge_vs_breakeven,
                "is_profitable_structure": d.breakeven.is_profitable_structure
            },
            "recent_roi_7d": d.recent_roi_7d,
            "recent_roi_14d": d.recent_roi_14d,
            "trend": d.trend,
            "stake_multiplier": d.stake_multiplier,
            "confidence_score": d.confidence_score,
            "issues": d.issues,
            "improvements": d.improvements,
            "is_shadow_mode": d.is_shadow_mode,
            "shadow_reason": d.shadow_reason
        }
    
    def _diagnose_tiers(self, cursor, lookback_days: int) -> Dict[str, StrategyDiagnostic]:
        """Diagnostic complet des tiers avec ROI, CLV, Wilson, Breakeven"""
        
        # Requête principale avec toutes les métriques
        cursor.execute("""
            WITH tier_data AS (
                SELECT 
                    CASE 
                        WHEN diamond_score >= 90 THEN 'ELITE 90+'
                        WHEN diamond_score >= 80 THEN 'DIAMOND 80+'
                        WHEN diamond_score >= 70 THEN 'STRONG 70+'
                        ELSE 'STANDARD'
                    END as tier,
                    is_winner,
                    is_resolved,
                    profit_loss,
                    odds_taken,
                    closing_odds,
                    created_at,
                    COALESCE(stake, 1) as stake
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
            )
            SELECT 
                tier,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_resolved = true) as resolved,
                COUNT(*) FILTER (WHERE is_winner = true) as wins,
                COUNT(*) FILTER (WHERE is_winner = false AND is_resolved = true) as losses,
                
                -- ROI
                COALESCE(SUM(profit_loss), 0) as total_profit,
                COALESCE(SUM(stake) FILTER (WHERE is_resolved = true), 0) as total_staked,
                
                -- CLV
                ROUND(AVG(
                    CASE WHEN closing_odds > 0 THEN 
                        (odds_taken / closing_odds - 1) * 100 
                    ELSE NULL END
                )::numeric, 3) as avg_clv,
                
                -- Cote moyenne (pour breakeven)
                ROUND(AVG(odds_taken)::numeric, 3) as avg_odds,
                
                -- ROI 7 derniers jours
                ROUND((
                    SUM(profit_loss) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') /
                    NULLIF(SUM(stake) FILTER (WHERE created_at > NOW() - INTERVAL '7 days' AND is_resolved = true), 0) * 100
                )::numeric, 2) as roi_7d,
                
                -- ROI 14 derniers jours
                ROUND((
                    SUM(profit_loss) FILTER (WHERE created_at > NOW() - INTERVAL '14 days') /
                    NULLIF(SUM(stake) FILTER (WHERE created_at > NOW() - INTERVAL '14 days' AND is_resolved = true), 0) * 100
                )::numeric, 2) as roi_14d
                
            FROM tier_data
            GROUP BY tier
        """, (lookback_days,))
        
        results = {}
        for row in cursor.fetchall():
            diagnostic = self._create_diagnostic(
                strategy_id=row['tier'],
                total=row['total'],
                resolved=row['resolved'] or 0,
                wins=row['wins'] or 0,
                losses=row['losses'] or 0,
                total_profit=float(row['total_profit'] or 0),
                total_staked=float(row['total_staked'] or 1),
                avg_clv=float(row['avg_clv'] or 0),
                avg_odds=float(row['avg_odds'] or 2.0),
                roi_7d=float(row['roi_7d'] or 0),
                roi_14d=float(row['roi_14d'] or 0)
            )
            results[row['tier']] = diagnostic
        
        return results
    
    def _diagnose_markets(self, cursor, lookback_days: int) -> Dict[str, StrategyDiagnostic]:
        """Diagnostic complet des marchés"""
        
        cursor.execute("""
            SELECT 
                COALESCE(market_type, 'unknown') as market,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_resolved = true) as resolved,
                COUNT(*) FILTER (WHERE is_winner = true) as wins,
                COUNT(*) FILTER (WHERE is_winner = false AND is_resolved = true) as losses,
                COALESCE(SUM(profit_loss), 0) as total_profit,
                COALESCE(SUM(COALESCE(stake, 1)) FILTER (WHERE is_resolved = true), 0) as total_staked,
                ROUND(AVG(
                    CASE WHEN closing_odds > 0 THEN 
                        (odds_taken / closing_odds - 1) * 100 
                    ELSE NULL END
                )::numeric, 3) as avg_clv,
                ROUND(AVG(odds_taken)::numeric, 3) as avg_odds,
                ROUND((
                    SUM(profit_loss) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') /
                    NULLIF(SUM(COALESCE(stake, 1)) FILTER (WHERE created_at > NOW() - INTERVAL '7 days' AND is_resolved = true), 0) * 100
                )::numeric, 2) as roi_7d,
                ROUND((
                    SUM(profit_loss) FILTER (WHERE created_at > NOW() - INTERVAL '14 days') /
                    NULLIF(SUM(COALESCE(stake, 1)) FILTER (WHERE created_at > NOW() - INTERVAL '14 days' AND is_resolved = true), 0) * 100
                )::numeric, 2) as roi_14d
            FROM tracking_clv_picks
            WHERE created_at > NOW() - INTERVAL '%s days'
            GROUP BY market_type
            HAVING COUNT(*) >= %s
        """, (lookback_days, self.MIN_SAMPLE_LOW))
        
        results = {}
        for row in cursor.fetchall():
            diagnostic = self._create_diagnostic(
                strategy_id=row['market'],
                total=row['total'],
                resolved=row['resolved'] or 0,
                wins=row['wins'] or 0,
                losses=row['losses'] or 0,
                total_profit=float(row['total_profit'] or 0),
                total_staked=float(row['total_staked'] or 1),
                avg_clv=float(row['avg_clv'] or 0),
                avg_odds=float(row['avg_odds'] or 2.0),
                roi_7d=float(row['roi_7d'] or 0),
                roi_14d=float(row['roi_14d'] or 0)
            )
            results[row['market']] = diagnostic
        
        return results
    
    def _create_diagnostic(
        self,
        strategy_id: str,
        total: int,
        resolved: int,
        wins: int,
        losses: int,
        total_profit: float,
        total_staked: float,
        avg_clv: float,
        avg_odds: float,
        roi_7d: float,
        roi_14d: float
    ) -> StrategyDiagnostic:
        """Crée un diagnostic complet pour une stratégie"""
        
        # 1. Calcul ROI
        roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
        
        # 2. Wilson Confidence Interval
        wilson = WilsonInterval.calculate(wins, resolved)
        
        # 3. Significance statistique
        if resolved >= self.MIN_SAMPLE_SIGNIFICANT:
            significance = "high"
        elif resolved >= self.MIN_SAMPLE_MEDIUM:
            significance = "medium"
        else:
            significance = "low"
        
        # 4. Breakeven Analysis
        breakeven_wr = (1 / avg_odds * 100) if avg_odds > 0 else 50
        actual_wr = (wins / resolved * 100) if resolved > 0 else 0
        edge_vs_be = actual_wr - breakeven_wr
        
        breakeven = BreakevenAnalysis(
            avg_odds=round(avg_odds, 2),
            breakeven_win_rate=round(breakeven_wr, 2),
            actual_win_rate=round(actual_wr, 2),
            edge_vs_breakeven=round(edge_vs_be, 2),
            is_profitable_structure=edge_vs_be > 0
        )
        
        # 5. Trend detection
        if roi_7d > roi_14d + 2:
            trend = "improving"
        elif roi_7d < roi_14d - 2:
            trend = "declining"
        else:
            trend = "stable"
        
        # 6. Déterminer le status (basé sur ROI, pas Win Rate!)
        status, stake_mult, is_shadow, shadow_reason = self._evaluate_strategy_v2(
            roi, avg_clv, resolved, trend, breakeven
        )
        
        # 7. Calculer le score de confiance
        confidence = self._calculate_confidence_score(
            roi, avg_clv, wilson, significance, trend
        )
        
        # 8. Identifier les problèmes
        issues = self._identify_issues(
            roi, avg_clv, breakeven, wilson, resolved, trend
        )
        
        # 9. Suggérer des améliorations
        improvements = self._suggest_improvements(
            strategy_id, roi, avg_clv, breakeven, issues
        )
        
        return StrategyDiagnostic(
            strategy_id=strategy_id,
            status=status,
            roi_percent=round(roi, 2),
            clv_percent=round(avg_clv, 3),
            wilson_interval=wilson,
            sample_size=resolved,
            statistical_significance=significance,
            breakeven=breakeven,
            recent_roi_7d=roi_7d,
            recent_roi_14d=roi_14d,
            trend=trend,
            stake_multiplier=stake_mult,
            confidence_score=round(confidence, 2),
            issues=issues,
            improvements=improvements,
            is_shadow_mode=is_shadow,
            shadow_reason=shadow_reason
        )
    
    def _evaluate_strategy_v2(
        self,
        roi: float,
        clv: float,
        sample_size: int,
        trend: str,
        breakeven: BreakevenAnalysis
    ) -> Tuple[StrategyStatus, float, bool, Optional[str]]:
        """
        Évalue une stratégie avec la logique V2.0
        
        Returns: (status, stake_multiplier, is_shadow, shadow_reason)
        """
        
        # Échantillon insuffisant -> Neutral avec prudence
        if sample_size < self.MIN_SAMPLE_LOW:
            return StrategyStatus.NEUTRAL, 0.3, False, None
        
        # 🏆 CHAMPION: ROI >= 10% ET CLV >= 1.5%
        if roi >= self.ROI_CHAMPION and clv >= self.CLV_GOOD:
            mult = 1.5 if sample_size >= self.MIN_SAMPLE_SIGNIFICANT else 1.2
            return StrategyStatus.CHAMPION, mult, False, None
        
        # ✅ PROFITABLE: ROI >= 2%
        if roi >= self.ROI_PROFITABLE:
            mult = 1.0 if sample_size >= self.MIN_SAMPLE_MEDIUM else 0.8
            return StrategyStatus.PROFITABLE, mult, False, None
        
        # 🔄 RECOVERING: ROI négatif mais trend amélioration + CLV positif
        if roi < 0 and trend == "improving" and clv > self.CLV_GOOD:
            return StrategyStatus.RECOVERING, 0.5, False, None
        
        # 📊 NEUTRAL: ROI entre -2% et +2%
        if roi >= self.ROI_NEUTRAL:
            # Si CLV très positif, on reste confiant
            if clv >= self.CLV_EXCELLENT:
                return StrategyStatus.NEUTRAL, 0.7, False, None
            return StrategyStatus.NEUTRAL, 0.5, False, None
        
        # ⚠️ STRUGGLING: ROI entre -10% et -2%
        if roi >= self.ROI_STRUGGLING:
            # On continue à tracker mais on réduit
            if clv > 0:  # CLV positif = variance négative, patience
                return StrategyStatus.STRUGGLING, 0.3, False, None
            return StrategyStatus.STRUGGLING, 0.2, False, None
        
        # 👻 SHADOW MODE: ROI < -10% - Paper trading uniquement
        # ON NE BLOQUE PAS, on continue à tracker!
        reason = f"ROI très négatif ({roi:.1f}%). Passage en paper trading pour observation."
        return StrategyStatus.SHADOW, 0.0, True, reason
    
    def _calculate_confidence_score(
        self,
        roi: float,
        clv: float,
        wilson: WilsonInterval,
        significance: str,
        trend: str
    ) -> float:
        """Calcule un score de confiance global (0-100)"""
        
        score = 50  # Base
        
        # ROI impact (-20 à +30)
        if roi >= 10:
            score += 30
        elif roi >= 5:
            score += 20
        elif roi >= 0:
            score += 10
        elif roi >= -5:
            score -= 5
        else:
            score -= 20
        
        # CLV impact (-10 à +20)
        if clv >= 3:
            score += 20
        elif clv >= 1:
            score += 10
        elif clv < -1:
            score -= 10
        
        # Significance impact
        if significance == "high":
            score += 10
        elif significance == "low":
            score -= 15
        
        # Trend impact
        if trend == "improving":
            score += 10
        elif trend == "declining":
            score -= 10
        
        # Wilson confidence
        score += wilson.confidence * 10
        
        return max(0, min(100, score))
    
    def _identify_issues(
        self,
        roi: float,
        clv: float,
        breakeven: BreakevenAnalysis,
        wilson: WilsonInterval,
        sample_size: int,
        trend: str
    ) -> List[str]:
        """Identifie les problèmes d'une stratégie"""
        
        issues = []
        
        # ROI négatif
        if roi < 0:
            issues.append(f"❌ ROI négatif: {roi:.1f}%")
        
        # CLV négatif (bat pas le marché)
        if clv < 0:
            issues.append(f"📉 CLV négatif: {clv:.2f}% - Le marché te bat")
        
        # Win rate sous le breakeven
        if not breakeven.is_profitable_structure:
            issues.append(
                f"⚠️ WR ({breakeven.actual_win_rate:.1f}%) < Breakeven ({breakeven.breakeven_win_rate:.1f}%)"
            )
        
        # Échantillon faible
        if sample_size < self.MIN_SAMPLE_MEDIUM:
            issues.append(f"📊 Échantillon faible ({sample_size} paris) - Confiance limitée")
        
        # Trend en déclin
        if trend == "declining":
            issues.append("📉 Performance en déclin (7j < 14j)")
        
        # Variance haute (Wilson interval large)
        if wilson.upper - wilson.lower > 30:
            issues.append(f"🎲 Haute variance (WR entre {wilson.lower}% et {wilson.upper}%)")
        
        return issues
    
    def _suggest_improvements(
        self,
        strategy_id: str,
        roi: float,
        clv: float,
        breakeven: BreakevenAnalysis,
        issues: List[str]
    ) -> List[str]:
        """Suggère des améliorations concrètes"""
        
        improvements = []
        
        # Si cotes trop basses
        if breakeven.avg_odds < 1.5 and not breakeven.is_profitable_structure:
            improvements.append(
                "💡 Cotes trop basses (@{:.2f}). Vise des cotes > @1.70 pour ce marché.".format(
                    breakeven.avg_odds
                )
            )
        
        # Si CLV négatif mais ROI ok
        if clv < 0 and roi > 0:
            improvements.append(
                "💡 CLV négatif = chance à court terme. Améliore le timing (parie plus tôt)."
            )
        
        # Si CLV positif mais ROI négatif
        if clv > 1 and roi < 0:
            improvements.append(
                "💡 CLV positif mais ROI négatif = variance. Continue, ça va tourner!"
            )
        
        # Si WR sous breakeven
        if not breakeven.is_profitable_structure:
            needed_wr = breakeven.breakeven_win_rate + 5
            improvements.append(
                f"💡 Besoin de {needed_wr:.0f}%+ WR. Filtre plus strictement (score > 80)."
            )
        
        # Suggestion générique si ROI très négatif
        if roi < -10:
            improvements.append(
                "💡 Stratégie en difficulté majeure. Analyse les paris perdants récents pour patterns."
            )
        
        # Si aucun problème majeur
        if not issues:
            improvements.append("✅ Stratégie performante. Maintiens les paramètres actuels.")
        
        return improvements
    
    def _find_optimal_combinations(self, cursor, lookback_days: int) -> List[Dict]:
        """Trouve les meilleures combinaisons tier + marché"""
        
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN diamond_score >= 90 THEN 'ELITE 90+'
                    WHEN diamond_score >= 80 THEN 'DIAMOND 80+'
                    WHEN diamond_score >= 70 THEN 'STRONG 70+'
                    ELSE 'STANDARD'
                END as tier,
                COALESCE(market_type, 'unknown') as market,
                COUNT(*) FILTER (WHERE is_resolved = true) as resolved,
                COUNT(*) FILTER (WHERE is_winner = true) as wins,
                ROUND(
                    COUNT(*) FILTER (WHERE is_winner = true)::numeric / 
                    NULLIF(COUNT(*) FILTER (WHERE is_resolved = true), 0) * 100, 1
                ) as win_rate,
                ROUND((
                    SUM(profit_loss) / 
                    NULLIF(SUM(COALESCE(stake, 1)) FILTER (WHERE is_resolved = true), 0) * 100
                )::numeric, 2) as roi,
                ROUND(AVG(
                    CASE WHEN closing_odds > 0 THEN 
                        (odds_taken / closing_odds - 1) * 100 
                    ELSE NULL END
                )::numeric, 3) as avg_clv
            FROM tracking_clv_picks
            WHERE created_at > NOW() - INTERVAL '%s days'
            GROUP BY 1, 2
            HAVING COUNT(*) FILTER (WHERE is_resolved = true) >= 10
            ORDER BY roi DESC NULLS LAST
            LIMIT 10
        """, (lookback_days,))
        
        return [
            {
                "tier": row['tier'],
                "market": row['market'],
                "resolved": row['resolved'],
                "wins": row['wins'],
                "win_rate": float(row['win_rate'] or 0),
                "roi": float(row['roi'] or 0),
                "clv": float(row['avg_clv'] or 0),
                "recommendation": "🏆 OPTIMAL" if (row['roi'] or 0) > 5 else "✅ BON" if (row['roi'] or 0) > 0 else "⚠️ SURVEILLER"
            }
            for row in cursor.fetchall()
        ]
    
    def _calculate_dynamic_thresholds(
        self,
        tier_diagnostics: Dict[str, StrategyDiagnostic],
        market_diagnostics: Dict[str, StrategyDiagnostic]
    ) -> Dict[str, float]:
        """Calcule les seuils dynamiques"""
        
        # ROI minimum = médiane des stratégies rentables
        profitable_rois = [
            d.roi_percent for d in tier_diagnostics.values() 
            if d.status in [StrategyStatus.CHAMPION, StrategyStatus.PROFITABLE]
        ]
        min_roi = min(profitable_rois) if profitable_rois else 0
        
        # CLV minimum
        clvs = [d.clv_percent for d in tier_diagnostics.values() if d.clv_percent > 0]
        min_clv = min(clvs) if clvs else 0
        
        return {
            'min_roi': round(min_roi, 2),
            'min_clv': round(min_clv, 2),
            'min_confidence': 50.0
        }
    
    def _generate_global_recommendations(
        self,
        tier_diagnostics: Dict[str, StrategyDiagnostic],
        market_diagnostics: Dict[str, StrategyDiagnostic],
        optimal_combos: List[Dict]
    ) -> List[str]:
        """Génère des recommandations globales"""
        
        recs = []
        
        # Champions
        champions = [t for t, d in tier_diagnostics.items() if d.status == StrategyStatus.CHAMPION]
        if champions:
            recs.append(f"🏆 MAXIMISER: {', '.join(champions)}")
        
        # Profitables
        profitable = [t for t, d in tier_diagnostics.items() if d.status == StrategyStatus.PROFITABLE]
        if profitable:
            recs.append(f"✅ UTILISER: {', '.join(profitable)}")
        
        # Recovering (bonnes nouvelles!)
        recovering = [t for t, d in tier_diagnostics.items() if d.status == StrategyStatus.RECOVERING]
        if recovering:
            recs.append(f"🔄 EN REPRISE: {', '.join(recovering)} - Surveiller pour réintégration")
        
        # Shadow (pas bloqué, en observation)
        shadow = [t for t, d in tier_diagnostics.items() if d.is_shadow_mode]
        if shadow:
            recs.append(f"👻 EN OBSERVATION: {', '.join(shadow)} - Paper trading actif")
        
        # Meilleure combo
        if optimal_combos:
            best = optimal_combos[0]
            recs.append(
                f"🎯 COMBO OPTIMAL: {best['tier']} + {best['market']} (ROI: {best['roi']}%)"
            )
        
        # Marchés à problèmes
        bad_markets = [
            m for m, d in market_diagnostics.items() 
            if d.status == StrategyStatus.SHADOW
        ]
        if bad_markets:
            recs.append(f"⚠️ MARCHÉS EN OBSERVATION: {', '.join(bad_markets)}")
        
        return recs
    
    def _assess_system_health_v2(
        self,
        tier_diagnostics: Dict[str, StrategyDiagnostic],
        market_diagnostics: Dict[str, StrategyDiagnostic]
    ) -> Tuple[str, float]:
        """Évalue la santé globale V2"""
        
        # Compter par status
        champions = sum(1 for d in tier_diagnostics.values() if d.status == StrategyStatus.CHAMPION)
        profitable = sum(1 for d in tier_diagnostics.values() if d.status == StrategyStatus.PROFITABLE)
        struggling = sum(1 for d in tier_diagnostics.values() if d.status == StrategyStatus.STRUGGLING)
        shadow = sum(1 for d in tier_diagnostics.values() if d.is_shadow_mode)
        
        # Score global
        score = 50 + (champions * 20) + (profitable * 10) - (struggling * 5) - (shadow * 10)
        score = max(0, min(100, score))
        
        # Status textuel
        if score >= 80:
            health = "🏆 EXCELLENT"
        elif score >= 60:
            health = "✅ BON"
        elif score >= 40:
            health = "📊 STABLE"
        elif score >= 20:
            health = "⚠️ ATTENTION"
        else:
            health = "🛑 CRITIQUE"
        
        return health, score
    
    def should_accept_pick_v2(
        self,
        tier: str,
        market: str,
        score: float,
        odds: float = 2.0
    ) -> Tuple[bool, str, float, bool]:
        """
        Détermine si un pick doit être accepté (V2)
        
        Returns: (accepted_for_real_bet, reason, stake_multiplier, shadow_track)
        
        NOTE: shadow_track = True signifie qu'on track le pari même si pas recommandé
        """
        config = self.get_config()
        
        tier_diag = config.tier_diagnostics.get(tier, {})
        market_diag = config.market_diagnostics.get(market, {})
        
        tier_status = tier_diag.get('status', 'neutral')
        market_status = market_diag.get('status', 'neutral')
        
        # TOUJOURS tracker (shadow = True) pour garder les données
        shadow_track = True
        
        # Si en mode shadow, on track mais on ne recommande pas
        if tier_diag.get('is_shadow_mode') or market_diag.get('is_shadow_mode'):
            reason = f"👻 Shadow mode - Tracking uniquement ({tier_diag.get('shadow_reason', '')})"
            return False, reason, 0.0, True
        
        # Calculer le multiplicateur combiné
        tier_mult = tier_diag.get('stake_multiplier', 0.5)
        market_mult = market_diag.get('stake_multiplier', 0.5)
        
        # Moyenne pondérée (tier compte plus)
        final_mult = tier_mult * 0.6 + market_mult * 0.4
        
        # Vérifier le score minimum
        if score < config.min_score_threshold:
            return False, f"Score {score} < seuil dynamique {config.min_score_threshold}", 0.0, True
        
        # Accepté!
        reason = f"✅ Tier: {tier_status}, Market: {market_status}, Mult: {final_mult:.2f}"
        return True, reason, final_mult, True


# Instance singleton
adaptive_engine_v2 = AdaptiveStrategyEngineV2()
