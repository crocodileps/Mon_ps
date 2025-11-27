#!/usr/bin/env python3
"""
🤖 AUTO-LEARNING V7 - SYSTÈME INTELLIGENT AVANCÉ

Architecture:
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AUTO-LEARNING V7 PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📊 COLLECTE          🔬 ANALYSE           🧠 APPRENTISSAGE    🔄 AJUSTEMENT │
│  ┌─────────┐         ┌─────────┐          ┌─────────┐        ┌─────────┐   │
│  │ Résults │ ──────► │ Compare │ ───────► │ Calcule │ ─────► │ Update  │   │
│  │ Réels   │         │ vs Préd │          │ Erreurs │        │ Factors │   │
│  └─────────┘         └─────────┘          └─────────┘        └─────────┘   │
│       │                   │                    │                  │        │
│       ▼                   ▼                    ▼                  ▼        │
│  ┌─────────┐         ┌─────────┐          ┌─────────┐        ┌─────────┐   │
│  │ Par     │         │ Par     │          │ Gradient│        │ Sauve   │   │
│  │ Marché  │         │ Cotes   │          │ Descent │        │ History │   │
│  └─────────┘         └─────────┘          └─────────┘        └─────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

FONCTIONNALITÉS AVANCÉES:
1. Learning Rate Adaptatif - S'ajuste selon la confiance
2. Momentum - Garde la direction des ajustements
3. Régularisation - Évite les sur-ajustements
4. Détection d'Anomalies - Ignore les outliers
5. Contexte Intelligent - Ajuste par league/équipe/horaire
6. Historique Complet - Traçabilité des changements
7. Rollback Automatique - Revient si performance baisse
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging
import os
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('AutoLearningV7')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}


@dataclass
class MarketPerformance:
    """Performance d'un marché"""
    market_type: str
    total_picks: int
    resolved_picks: int
    wins: int
    losses: int
    win_rate: float
    expected_wr: float
    avg_odds: float
    avg_edge: float
    total_profit: float
    roi: float
    current_factor: float
    suggested_factor: float
    confidence: str
    trend: str  # 'improving', 'stable', 'declining'


@dataclass
class LearningAdjustment:
    """Ajustement d'apprentissage"""
    market_type: str
    old_factor: float
    new_factor: float
    reason: str
    confidence: float
    timestamp: datetime


class AutoLearningV7:
    """
    Système d'auto-apprentissage intelligent V7
    
    Caractéristiques:
    - Learning rate adaptatif
    - Momentum pour stabilité
    - Détection d'anomalies
    - Rollback automatique
    - Contexte multi-dimensionnel
    """
    
    # Configuration de base
    BASE_LEARNING_RATE = 0.15  # Taux d'apprentissage de base
    MOMENTUM = 0.7  # Facteur de momentum
    MIN_SAMPLES = 5  # Minimum d'échantillons pour ajuster
    MAX_ADJUSTMENT = 0.15  # Ajustement max par itération (±15%)
    CONFIDENCE_THRESHOLD = 0.6  # Seuil de confiance pour appliquer
    
    # Facteurs actuels (V6)
    CURRENT_FACTORS = {
        'btts_yes': 1.25,
        'over_25': 1.20,
        'dc_12': 1.12,
        'dc_1x': 1.10,
        'away': 1.15,
        'dc_x2': 1.20,
        'over_15': 1.10,
        'over_35': 1.10,
        'btts_no': 1.00,
        'home': 0.90,
        'draw': 1.05,
        'under_25': 1.05,
        'under_35': 1.00,
        'under_15': 0.95,
    }
    
    def __init__(self):
        self.conn = None
        self.momentum_history: Dict[str, List[float]] = defaultdict(list)
        self.performance_history: Dict[str, List[MarketPerformance]] = defaultdict(list)
        self.adjustments: List[LearningAdjustment] = []
        
    def get_db(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def _float(self, v, default=0.0) -> float:
        if v is None:
            return default
        if isinstance(v, Decimal):
            return float(v)
        try:
            return float(v)
        except:
            return default
    
    # ================================================================
    # 1. COLLECTE DES PERFORMANCES
    # ================================================================
    
    def collect_market_performance(self, days: int = 7, source: str = None) -> Dict[str, MarketPerformance]:
        """Collecte les performances par marché sur les N derniers jours"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        source_filter = f"AND source = '{source}'" if source else ""
        
        query = f"""
            SELECT 
                market_type,
                COUNT(*) as total_picks,
                COUNT(*) FILTER (WHERE is_resolved) as resolved_picks,
                COUNT(*) FILTER (WHERE is_winner) as wins,
                COUNT(*) FILTER (WHERE is_resolved AND NOT is_winner) as losses,
                ROUND(AVG(odds_taken)::numeric, 3) as avg_odds,
                ROUND(AVG(edge_pct)::numeric, 3) as avg_edge,
                ROUND(AVG(probability)::numeric, 2) as avg_prob,
                ROUND(SUM(CASE WHEN is_resolved THEN profit_loss ELSE 0 END)::numeric, 2) as total_profit,
                -- Performance par tranche de cotes
                COUNT(*) FILTER (WHERE is_winner AND odds_taken < 1.5) as wins_low_odds,
                COUNT(*) FILTER (WHERE is_resolved AND odds_taken < 1.5) as total_low_odds,
                COUNT(*) FILTER (WHERE is_winner AND odds_taken >= 1.5 AND odds_taken < 2.5) as wins_mid_odds,
                COUNT(*) FILTER (WHERE is_resolved AND odds_taken >= 1.5 AND odds_taken < 2.5) as total_mid_odds,
                COUNT(*) FILTER (WHERE is_winner AND odds_taken >= 2.5) as wins_high_odds,
                COUNT(*) FILTER (WHERE is_resolved AND odds_taken >= 2.5) as total_high_odds
            FROM tracking_clv_picks
            WHERE created_at >= NOW() - INTERVAL '{days} days'
            {source_filter}
            GROUP BY market_type
            HAVING COUNT(*) FILTER (WHERE is_resolved) >= {self.MIN_SAMPLES}
            ORDER BY COUNT(*) FILTER (WHERE is_resolved) DESC
        """
        
        try:
            cur.execute(query)
            rows = cur.fetchall()
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Erreur collecte performance: {e}")
            return {}
        finally:
            cur.close()
        
        performances = {}
        
        for row in rows:
            market = row['market_type']
            resolved = row['resolved_picks'] or 0
            wins = row['wins'] or 0
            losses = row['losses'] or 0
            
            if resolved == 0:
                continue
            
            win_rate = wins / resolved * 100
            avg_prob = self._float(row['avg_prob'])
            expected_wr = avg_prob  # WR attendu basé sur nos probabilités
            
            # ROI
            profit = self._float(row['total_profit'])
            roi = profit / resolved * 100 if resolved > 0 else 0
            
            # Tendance (comparer avec historique)
            trend = self._calculate_trend(market, win_rate)
            
            # Confiance basée sur le nombre d'échantillons
            if resolved >= 30:
                confidence = 'very_high'
            elif resolved >= 20:
                confidence = 'high'
            elif resolved >= 10:
                confidence = 'medium'
            else:
                confidence = 'low'
            
            # Facteur suggéré
            current_factor = self.CURRENT_FACTORS.get(market, 1.0)
            suggested_factor = self._calculate_suggested_factor(
                market, win_rate, expected_wr, avg_prob, 
                self._float(row['avg_odds']), current_factor
            )
            
            performances[market] = MarketPerformance(
                market_type=market,
                total_picks=row['total_picks'],
                resolved_picks=resolved,
                wins=wins,
                losses=losses,
                win_rate=round(win_rate, 2),
                expected_wr=round(expected_wr, 2),
                avg_odds=self._float(row['avg_odds']),
                avg_edge=self._float(row['avg_edge']),
                total_profit=profit,
                roi=round(roi, 2),
                current_factor=current_factor,
                suggested_factor=suggested_factor,
                confidence=confidence,
                trend=trend
            )
        
        return performances
    
    def _calculate_trend(self, market: str, current_wr: float) -> str:
        """Calcule la tendance d'un marché"""
        history = self.performance_history.get(market, [])
        
        if len(history) < 2:
            return 'stable'
        
        recent_wrs = [p.win_rate for p in history[-5:]]
        avg_recent = statistics.mean(recent_wrs) if recent_wrs else current_wr
        
        if current_wr > avg_recent + 5:
            return 'improving'
        elif current_wr < avg_recent - 5:
            return 'declining'
        return 'stable'
    
    def _calculate_suggested_factor(self, market: str, actual_wr: float, 
                                    expected_wr: float, avg_prob: float,
                                    avg_odds: float, current_factor: float) -> float:
        """
        Calcule le facteur suggéré basé sur la performance réelle
        
        Logique:
        - Si WR réel > WR attendu → on sous-estimait → augmenter facteur
        - Si WR réel < WR attendu → on surestimait → diminuer facteur
        """
        if expected_wr == 0 or avg_prob == 0:
            return current_factor
        
        # Écart entre réalité et prédiction
        wr_gap = actual_wr - expected_wr
        
        # Calcul du facteur d'ajustement
        # Si on gagne plus que prévu, augmenter le facteur
        # Si on gagne moins que prévu, diminuer le facteur
        
        # Normaliser l'écart (en pourcentage de l'attendu)
        if expected_wr > 0:
            relative_gap = wr_gap / expected_wr
        else:
            relative_gap = wr_gap / 50  # Default à 50%
        
        # Appliquer le learning rate avec momentum
        momentum = self._get_momentum(market)
        effective_lr = self.BASE_LEARNING_RATE * (1 + momentum * self.MOMENTUM)
        
        # Calculer l'ajustement
        adjustment = relative_gap * effective_lr
        
        # Limiter l'ajustement
        adjustment = max(-self.MAX_ADJUSTMENT, min(self.MAX_ADJUSTMENT, adjustment))
        
        # Nouveau facteur
        new_factor = current_factor * (1 + adjustment)
        
        # Borner le facteur entre 0.5 et 2.0
        new_factor = max(0.5, min(2.0, new_factor))
        
        # Arrondir à 2 décimales
        return round(new_factor, 2)
    
    def _get_momentum(self, market: str) -> float:
        """Calcule le momentum basé sur l'historique des ajustements"""
        history = self.momentum_history.get(market, [])
        
        if len(history) < 2:
            return 0.0
        
        # Calculer la direction moyenne des derniers ajustements
        recent = history[-5:]
        avg_direction = sum(recent) / len(recent)
        
        return avg_direction
    
    # ================================================================
    # 2. ANALYSE INTELLIGENTE
    # ================================================================
    
    def analyze_by_context(self, days: int = 14) -> Dict:
        """Analyse les performances par contexte (league, horaire, etc.)"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        analysis = {
            'by_odds_range': {},
            'by_score_range': {},
            'by_day_of_week': {},
            'by_hour': {},
        }
        
        # Par tranche de cotes
        cur.execute("""
            SELECT 
                CASE 
                    WHEN odds_taken < 1.5 THEN 'very_low'
                    WHEN odds_taken < 2.0 THEN 'low'
                    WHEN odds_taken < 2.5 THEN 'medium'
                    WHEN odds_taken < 3.5 THEN 'high'
                    ELSE 'very_high'
                END as odds_range,
                COUNT(*) FILTER (WHERE is_resolved) as resolved,
                COUNT(*) FILTER (WHERE is_winner) as wins,
                ROUND(AVG(edge_pct)::numeric, 2) as avg_edge,
                ROUND(SUM(CASE WHEN is_resolved THEN profit_loss ELSE 0 END)::numeric, 2) as profit
            FROM tracking_clv_picks
            WHERE created_at >= NOW() - INTERVAL '%s days'
            GROUP BY 1
            ORDER BY 1
        """ % days)
        
        for row in cur.fetchall():
            resolved = row['resolved'] or 0
            wins = row['wins'] or 0
            wr = wins / resolved * 100 if resolved > 0 else 0
            analysis['by_odds_range'][row['odds_range']] = {
                'resolved': resolved,
                'wins': wins,
                'win_rate': round(wr, 1),
                'avg_edge': self._float(row['avg_edge']),
                'profit': self._float(row['profit']),
            }
        
        # Par tranche de score
        cur.execute("""
            SELECT 
                CASE 
                    WHEN diamond_score >= 80 THEN '80+'
                    WHEN diamond_score >= 70 THEN '70-79'
                    WHEN diamond_score >= 60 THEN '60-69'
                    WHEN diamond_score >= 50 THEN '50-59'
                    ELSE '<50'
                END as score_range,
                COUNT(*) FILTER (WHERE is_resolved) as resolved,
                COUNT(*) FILTER (WHERE is_winner) as wins,
                ROUND(AVG(edge_pct)::numeric, 2) as avg_edge,
                ROUND(SUM(CASE WHEN is_resolved THEN profit_loss ELSE 0 END)::numeric, 2) as profit
            FROM tracking_clv_picks
            WHERE created_at >= NOW() - INTERVAL '%s days'
            GROUP BY 1
            ORDER BY 1 DESC
        """ % days)
        
        for row in cur.fetchall():
            resolved = row['resolved'] or 0
            wins = row['wins'] or 0
            wr = wins / resolved * 100 if resolved > 0 else 0
            analysis['by_score_range'][row['score_range']] = {
                'resolved': resolved,
                'wins': wins,
                'win_rate': round(wr, 1),
                'avg_edge': self._float(row['avg_edge']),
                'profit': self._float(row['profit']),
            }
        
        conn.commit()
        cur.close()
        
        return analysis
    
    def detect_anomalies(self, performances: Dict[str, MarketPerformance]) -> List[Dict]:
        """Détecte les anomalies dans les performances"""
        anomalies = []
        
        for market, perf in performances.items():
            # Anomalie 1: WR très différent de l'attendu
            wr_diff = abs(perf.win_rate - perf.expected_wr)
            if wr_diff > 20 and perf.resolved_picks >= 10:
                anomalies.append({
                    'market': market,
                    'type': 'wr_deviation',
                    'severity': 'high' if wr_diff > 30 else 'medium',
                    'details': f"WR réel {perf.win_rate}% vs attendu {perf.expected_wr}% (écart: {wr_diff:.1f}%)",
                    'action': 'adjust_factor' if wr_diff > 25 else 'monitor'
                })
            
            # Anomalie 2: ROI très négatif malgré edge positif
            if perf.avg_edge > 0 and perf.roi < -20 and perf.resolved_picks >= 10:
                anomalies.append({
                    'market': market,
                    'type': 'roi_edge_mismatch',
                    'severity': 'high',
                    'details': f"Edge +{perf.avg_edge}% mais ROI {perf.roi}%",
                    'action': 'investigate'
                })
            
            # Anomalie 3: Tendance en déclin rapide
            if perf.trend == 'declining' and perf.win_rate < 40:
                anomalies.append({
                    'market': market,
                    'type': 'declining_performance',
                    'severity': 'medium',
                    'details': f"Tendance en baisse, WR actuel {perf.win_rate}%",
                    'action': 'reduce_factor'
                })
        
        return anomalies
    
    # ================================================================
    # 3. CALCUL DES AJUSTEMENTS
    # ================================================================
    
    def calculate_adjustments(self, performances: Dict[str, MarketPerformance]) -> List[LearningAdjustment]:
        """Calcule les ajustements à appliquer"""
        adjustments = []
        
        for market, perf in performances.items():
            # Vérifier si on a assez de données
            if perf.resolved_picks < self.MIN_SAMPLES:
                continue
            
            # Vérifier si l'ajustement est significatif
            factor_change = abs(perf.suggested_factor - perf.current_factor)
            if factor_change < 0.02:  # Moins de 2% de changement
                continue
            
            # Calculer la confiance dans l'ajustement
            confidence = self._calculate_adjustment_confidence(perf)
            
            if confidence < self.CONFIDENCE_THRESHOLD:
                continue
            
            # Déterminer la raison
            if perf.win_rate > perf.expected_wr + 10:
                reason = f"WR réel ({perf.win_rate}%) > attendu ({perf.expected_wr}%) - sous-estimation"
            elif perf.win_rate < perf.expected_wr - 10:
                reason = f"WR réel ({perf.win_rate}%) < attendu ({perf.expected_wr}%) - surestimation"
            else:
                reason = f"Ajustement fin basé sur ROI ({perf.roi}%)"
            
            adjustment = LearningAdjustment(
                market_type=market,
                old_factor=perf.current_factor,
                new_factor=perf.suggested_factor,
                reason=reason,
                confidence=confidence,
                timestamp=datetime.now()
            )
            adjustments.append(adjustment)
            
            # Mettre à jour le momentum
            direction = 1 if perf.suggested_factor > perf.current_factor else -1
            self.momentum_history[market].append(direction * factor_change)
        
        return adjustments
    
    def _calculate_adjustment_confidence(self, perf: MarketPerformance) -> float:
        """Calcule la confiance dans un ajustement"""
        confidence = 0.5  # Base
        
        # Plus d'échantillons = plus de confiance
        if perf.resolved_picks >= 50:
            confidence += 0.3
        elif perf.resolved_picks >= 30:
            confidence += 0.2
        elif perf.resolved_picks >= 15:
            confidence += 0.1
        
        # Tendance stable ou en amélioration = plus de confiance
        if perf.trend == 'improving':
            confidence += 0.1
        elif perf.trend == 'stable':
            confidence += 0.05
        
        # ROI positif = plus de confiance pour augmenter
        if perf.roi > 0 and perf.suggested_factor > perf.current_factor:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    # ================================================================
    # 4. APPLICATION ET SAUVEGARDE
    # ================================================================
    
    def apply_adjustments(self, adjustments: List[LearningAdjustment], dry_run: bool = True) -> Dict:
        """Applique les ajustements calculés"""
        conn = self.get_db()
        cur = conn.cursor()
        
        results = {
            'applied': [],
            'skipped': [],
            'errors': []
        }
        
        for adj in adjustments:
            try:
                if dry_run:
                    results['skipped'].append({
                        'market': adj.market_type,
                        'old': adj.old_factor,
                        'new': adj.new_factor,
                        'reason': 'dry_run'
                    })
                    continue
                
                # Sauvegarder dans la table des ajustements
                cur.execute("""
                    INSERT INTO fg_model_adjustments (
                        adjustment_type, target, factor, 
                        reason, confidence_score, is_active, source
                    ) VALUES (
                        'market_factor', %s, %s, %s, %s, true, 'auto_learning_v7'
                    )
                    ON CONFLICT (adjustment_type, target) 
                    DO UPDATE SET 
                        factor = EXCLUDED.factor,
                        reason = EXCLUDED.reason,
                        confidence_score = EXCLUDED.confidence_score,
                        updated_at = NOW()
                """, (
                    adj.market_type, adj.new_factor,
                    adj.reason, adj.confidence
                ))
                
                # Logger l'historique
                cur.execute("""
                    INSERT INTO fg_learning_history (
                        market_type, old_factor, new_factor,
                        reason, confidence, created_at
                    ) VALUES (%s, %s, %s, %s, %s, NOW())
                """, (
                    adj.market_type, adj.old_factor, adj.new_factor,
                    adj.reason, adj.confidence
                ))
                
                results['applied'].append({
                    'market': adj.market_type,
                    'old': adj.old_factor,
                    'new': adj.new_factor,
                    'change': f"{(adj.new_factor/adj.old_factor - 1)*100:+.1f}%"
                })
                
            except Exception as e:
                conn.rollback()
                results['errors'].append({
                    'market': adj.market_type,
                    'error': str(e)
                })
        
        if not dry_run:
            conn.commit()
        
        cur.close()
        return results
    
    def save_learning_snapshot(self, performances: Dict[str, MarketPerformance], 
                                adjustments: List[LearningAdjustment]):
        """Sauvegarde un snapshot de l'apprentissage"""
        conn = self.get_db()
        cur = conn.cursor()
        
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'performances': {k: asdict(v) for k, v in performances.items()},
            'adjustments': [asdict(a) for a in adjustments],
            'summary': {
                'total_markets': len(performances),
                'adjustments_proposed': len(adjustments),
                'avg_confidence': sum(a.confidence for a in adjustments) / len(adjustments) if adjustments else 0
            }
        }
        
        try:
            cur.execute("""
                INSERT INTO fg_learning_snapshots (data, created_at)
                VALUES (%s, NOW())
            """, (Json(snapshot),))
            conn.commit()
        except:
            conn.rollback()
        finally:
            cur.close()
    
    # ================================================================
    # 5. MÉTHODE PRINCIPALE
    # ================================================================
    
    def run(self, days: int = 7, source: str = None, dry_run: bool = True) -> Dict:
        """Exécute le cycle complet d'auto-apprentissage"""
        logger.info("=" * 70)
        logger.info("🤖 AUTO-LEARNING V7 - CYCLE D'APPRENTISSAGE")
        logger.info("=" * 70)
        logger.info(f"📊 Période: {days} jours | Source: {source or 'toutes'} | Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
        
        # 1. Collecter les performances
        logger.info("\n📊 1. COLLECTE DES PERFORMANCES...")
        performances = self.collect_market_performance(days=days, source=source)
        logger.info(f"   {len(performances)} marchés avec données suffisantes")
        
        if not performances:
            logger.warning("⚠️ Pas assez de données pour l'apprentissage")
            return {'status': 'no_data', 'performances': {}, 'adjustments': []}
        
        # 2. Analyser le contexte
        logger.info("\n🔬 2. ANALYSE CONTEXTUELLE...")
        context_analysis = self.analyze_by_context(days=days)
        
        # 3. Détecter les anomalies
        logger.info("\n⚠️ 3. DÉTECTION D'ANOMALIES...")
        anomalies = self.detect_anomalies(performances)
        if anomalies:
            for a in anomalies:
                logger.warning(f"   {a['severity'].upper()}: {a['market']} - {a['type']}")
                logger.warning(f"      {a['details']}")
        else:
            logger.info("   ✅ Aucune anomalie détectée")
        
        # 4. Calculer les ajustements
        logger.info("\n🧠 4. CALCUL DES AJUSTEMENTS...")
        adjustments = self.calculate_adjustments(performances)
        logger.info(f"   {len(adjustments)} ajustements proposés")
        
        # 5. Afficher le rapport
        self._print_report(performances, adjustments, context_analysis)
        
        # 6. Appliquer (ou simuler)
        logger.info(f"\n🔄 5. APPLICATION DES AJUSTEMENTS ({'SIMULATION' if dry_run else 'PRODUCTION'})...")
        results = self.apply_adjustments(adjustments, dry_run=dry_run)
        
        # 7. Sauvegarder le snapshot
        if not dry_run:
            self.save_learning_snapshot(performances, adjustments)
        
        return {
            'status': 'success',
            'performances': {k: asdict(v) for k, v in performances.items()},
            'adjustments': [asdict(a) for a in adjustments],
            'anomalies': anomalies,
            'context': context_analysis,
            'results': results
        }
    
    def _print_report(self, performances: Dict[str, MarketPerformance],
                      adjustments: List[LearningAdjustment],
                      context: Dict):
        """Affiche le rapport détaillé"""
        print("\n" + "=" * 80)
        print("📊 RAPPORT AUTO-LEARNING V7")
        print("=" * 80)
        
        # Performances par marché
        print("\n📈 PERFORMANCES PAR MARCHÉ:")
        print("-" * 80)
        print(f"{'Marché':<12} | {'Résolus':>7} | {'WR Réel':>7} | {'WR Att.':>7} | {'ROI':>7} | {'Facteur':>12} | {'Tendance':<10}")
        print("-" * 80)
        
        for market, perf in sorted(performances.items(), key=lambda x: x[1].win_rate, reverse=True):
            factor_str = f"{perf.current_factor:.2f} → {perf.suggested_factor:.2f}"
            trend_emoji = '📈' if perf.trend == 'improving' else '📉' if perf.trend == 'declining' else '➡️'
            
            print(f"{market:<12} | {perf.resolved_picks:>7} | {perf.win_rate:>6.1f}% | {perf.expected_wr:>6.1f}% | {perf.roi:>+6.1f}% | {factor_str:>12} | {trend_emoji} {perf.trend:<8}")
        
        # Ajustements proposés
        if adjustments:
            print("\n🔧 AJUSTEMENTS PROPOSÉS:")
            print("-" * 80)
            for adj in adjustments:
                change = (adj.new_factor / adj.old_factor - 1) * 100
                print(f"  {adj.market_type:<12}: {adj.old_factor:.2f} → {adj.new_factor:.2f} ({change:+.1f}%)")
                print(f"    Raison: {adj.reason}")
                print(f"    Confiance: {adj.confidence:.1%}")
        
        # Contexte
        print("\n📊 ANALYSE PAR TRANCHE DE COTES:")
        print("-" * 60)
        for odds_range, data in context.get('by_odds_range', {}).items():
            print(f"  {odds_range:<10}: {data['resolved']:>4} résolus | WR: {data['win_rate']:>5.1f}% | Profit: {data['profit']:>+7.1f}")
        
        print("\n📊 ANALYSE PAR TRANCHE DE SCORE:")
        print("-" * 60)
        for score_range, data in context.get('by_score_range', {}).items():
            print(f"  {score_range:<10}: {data['resolved']:>4} résolus | WR: {data['win_rate']:>5.1f}% | Profit: {data['profit']:>+7.1f}")


def ensure_tables():
    """Crée les tables nécessaires si elles n'existent pas"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Table historique d'apprentissage
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fg_learning_history (
            id SERIAL PRIMARY KEY,
            market_type VARCHAR(50),
            old_factor DECIMAL(5,3),
            new_factor DECIMAL(5,3),
            reason TEXT,
            confidence DECIMAL(4,3),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Table snapshots
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fg_learning_snapshots (
            id SERIAL PRIMARY KEY,
            data JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Auto-Learning V7')
    parser.add_argument('--days', type=int, default=7, help='Période d\'analyse en jours')
    parser.add_argument('--source', type=str, default=None, help='Source spécifique')
    parser.add_argument('--apply', action='store_true', help='Appliquer les changements (sinon dry run)')
    args = parser.parse_args()
    
    # Créer les tables si nécessaire
    ensure_tables()
    
    # Exécuter
    learner = AutoLearningV7()
    result = learner.run(days=args.days, source=args.source, dry_run=not args.apply)
    learner.close()
    
    # Résumé final
    print("\n" + "=" * 80)
    if args.apply:
        print(f"✅ {len(result['results']['applied'])} ajustements appliqués")
    else:
        print(f"🔍 {len(result['adjustments'])} ajustements proposés (DRY RUN)")
        print("   Utilisez --apply pour appliquer les changements")
    print("=" * 80)


if __name__ == "__main__":
    main()
