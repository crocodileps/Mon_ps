"""
Ferrari Real-Time Performance Tracker
Tracking temps réel des performances avec WebSocket, alertes et métriques live
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Niveaux d'alerte"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types d'alerte"""
    PERFORMANCE_DROP = "performance_drop"
    HIGH_PERFORMANCE = "high_performance"
    ANOMALY_DETECTED = "anomaly_detected"
    PROMOTION_RECOMMENDED = "promotion_recommended"
    ROLLBACK_NEEDED = "rollback_needed"


class RealtimePerformanceTracker:
    """
    Tracker de performance temps réel Ferrari Ultimate 2.0
    
    Responsabilités:
    - Track performances en temps réel
    - Calcul métriques à la volée
    - Détection anomalies
    - Génération alertes automatiques
    - Push updates via callbacks
    """
    
    def __init__(
        self,
        db_session=None,
        alert_callback=None,
        performance_drop_threshold: float = -0.10,  # -10%
        anomaly_threshold: float = 2.0  # 2 std deviations
    ):
        self.db = db_session
        self.alert_callback = alert_callback
        self.performance_drop_threshold = performance_drop_threshold
        self.anomaly_threshold = anomaly_threshold
        
        # Cache temps réel
        self.realtime_metrics = {}
        self.alert_history = []
        
        # Baseline pour détection anomalies
        self.performance_baseline = {}
        
        logger.info("📊 Real-Time Tracker initialisé")
    
    
    def track_bet_result(
        self,
        variation_id: int,
        outcome: str,
        profit: float,
        stake: float,
        odds: float,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Track un résultat de pari en temps réel
        
        Args:
            variation_id: ID de la variation
            outcome: 'win', 'loss', ou 'void'
            profit: Profit/perte
            stake: Mise
            odds: Cote
            metadata: Métadonnées additionnelles
            
        Returns:
            Métriques mises à jour + alertes générées
        """
        try:
            timestamp = datetime.now()
            
            logger.info(f"📊 Track: Variation {variation_id} - {outcome} - {profit}€")
            
            # 1. Update métriques
            updated_metrics = self._update_metrics(
                variation_id,
                outcome,
                profit,
                stake,
                odds,
                timestamp
            )
            
            # 2. Détection anomalies
            anomalies = self._detect_anomalies(variation_id, updated_metrics)
            
            # 3. Génération alertes
            alerts = self._generate_alerts(variation_id, updated_metrics, anomalies)
            
            # 4. Callback si configuré
            if self.alert_callback and alerts:
                for alert in alerts:
                    self.alert_callback(alert)
            
            # 5. Résultat
            result = {
                'timestamp': timestamp.isoformat(),
                'variation_id': variation_id,
                'outcome': outcome,
                'profit': profit,
                'updated_metrics': updated_metrics,
                'anomalies': anomalies,
                'alerts': alerts
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur track result: {e}", exc_info=True)
            return {'error': str(e)}
    
    
    def _update_metrics(
        self,
        variation_id: int,
        outcome: str,
        profit: float,
        stake: float,
        odds: float,
        timestamp: datetime
    ) -> Dict:
        """Update métriques en temps réel"""
        
        # Initialiser si première fois
        if variation_id not in self.realtime_metrics:
            self.realtime_metrics[variation_id] = {
                'total_bets': 0,
                'wins': 0,
                'losses': 0,
                'voids': 0,
                'total_profit': 0.0,
                'total_stake': 0.0,
                'win_rate': 0.0,
                'roi': 0.0,
                'avg_odds': 0.0,
                'last_10_results': [],
                'last_update': None
            }
        
        metrics = self.realtime_metrics[variation_id]
        
        # Update compteurs
        metrics['total_bets'] += 1
        
        if outcome == 'win':
            metrics['wins'] += 1
        elif outcome == 'loss':
            metrics['losses'] += 1
        elif outcome == 'void':
            metrics['voids'] += 1
        
        metrics['total_profit'] += profit
        metrics['total_stake'] += stake
        
        # Recalcul métriques
        total_completed = metrics['wins'] + metrics['losses']
        
        if total_completed > 0:
            metrics['win_rate'] = metrics['wins'] / total_completed
        
        if metrics['total_stake'] > 0:
            metrics['roi'] = metrics['total_profit'] / metrics['total_stake']
        
        # Moyenne cotes (weighted)
        total_odds_sum = metrics.get('_odds_sum', 0.0) + odds
        metrics['_odds_sum'] = total_odds_sum
        metrics['avg_odds'] = total_odds_sum / metrics['total_bets']
        
        # Derniers 10 résultats (pour streak analysis)
        metrics['last_10_results'].append({
            'outcome': outcome,
            'profit': profit,
            'timestamp': timestamp.isoformat()
        })
        
        if len(metrics['last_10_results']) > 10:
            metrics['last_10_results'].pop(0)
        
        metrics['last_update'] = timestamp.isoformat()
        
        return metrics.copy()
    
    
    def _detect_anomalies(self, variation_id: int, metrics: Dict) -> List[Dict]:
        """Détecte les anomalies dans les performances"""
        anomalies = []
        
        try:
            # 1. Baseline performance
            if variation_id not in self.performance_baseline:
                # Établir baseline après 10 paris
                if metrics['total_bets'] >= 10:
                    self.performance_baseline[variation_id] = {
                        'win_rate': metrics['win_rate'],
                        'roi': metrics['roi'],
                        'established_at': datetime.now().isoformat()
                    }
                return []  # Pas d'anomalie sans baseline
            
            baseline = self.performance_baseline[variation_id]
            
            # 2. Déviations significatives
            wr_deviation = metrics['win_rate'] - baseline['win_rate']
            roi_deviation = metrics['roi'] - baseline['roi']
            
            # Win rate drop
            if abs(wr_deviation) > 0.15:  # 15% deviation
                anomalies.append({
                    'type': 'win_rate_deviation',
                    'severity': 'high' if wr_deviation < -0.15 else 'low',
                    'current': metrics['win_rate'],
                    'baseline': baseline['win_rate'],
                    'deviation': wr_deviation
                })
            
            # ROI drop
            if roi_deviation < -0.10:  # -10% ROI drop
                anomalies.append({
                    'type': 'roi_drop',
                    'severity': 'critical',
                    'current': metrics['roi'],
                    'baseline': baseline['roi'],
                    'deviation': roi_deviation
                })
            
            # 3. Losing streak
            last_10 = metrics.get('last_10_results', [])
            if len(last_10) >= 5:
                last_5_outcomes = [r['outcome'] for r in last_10[-5:]]
                if all(o == 'loss' for o in last_5_outcomes):
                    anomalies.append({
                        'type': 'losing_streak',
                        'severity': 'high',
                        'streak_length': 5
                    })
            
            # 4. Winning streak (positive anomaly)
            if len(last_10) >= 5:
                last_5_outcomes = [r['outcome'] for r in last_10[-5:]]
                if all(o == 'win' for o in last_5_outcomes):
                    anomalies.append({
                        'type': 'winning_streak',
                        'severity': 'positive',
                        'streak_length': 5
                    })
            
        except Exception as e:
            logger.error(f"❌ Erreur détection anomalies: {e}")
        
        return anomalies
    
    
    def _generate_alerts(
        self,
        variation_id: int,
        metrics: Dict,
        anomalies: List[Dict]
    ) -> List[Dict]:
        """Génère des alertes basées sur métriques et anomalies"""
        alerts = []
        
        try:
            # 1. Alertes basées sur anomalies
            for anomaly in anomalies:
                if anomaly['type'] == 'roi_drop' and anomaly['severity'] == 'critical':
                    alerts.append({
                        'level': AlertLevel.CRITICAL.value,
                        'type': AlertType.ROLLBACK_NEEDED.value,
                        'variation_id': variation_id,
                        'message': f"ROI drop critique détecté: {anomaly['deviation']:.1%}",
                        'data': anomaly,
                        'timestamp': datetime.now().isoformat()
                    })
                
                elif anomaly['type'] == 'losing_streak':
                    alerts.append({
                        'level': AlertLevel.WARNING.value,
                        'type': AlertType.PERFORMANCE_DROP.value,
                        'variation_id': variation_id,
                        'message': f"Losing streak de {anomaly['streak_length']} paris",
                        'data': anomaly,
                        'timestamp': datetime.now().isoformat()
                    })
                
                elif anomaly['type'] == 'winning_streak':
                    alerts.append({
                        'level': AlertLevel.INFO.value,
                        'type': AlertType.HIGH_PERFORMANCE.value,
                        'variation_id': variation_id,
                        'message': f"Winning streak de {anomaly['streak_length']} paris!",
                        'data': anomaly,
                        'timestamp': datetime.now().isoformat()
                    })
            
            # 2. Alertes basées sur métriques
            # Performance exceptionnelle
            if metrics['roi'] > 0.30 and metrics['total_bets'] >= 20:
                alerts.append({
                    'level': AlertLevel.INFO.value,
                    'type': AlertType.PROMOTION_RECOMMENDED.value,
                    'variation_id': variation_id,
                    'message': f"Performance exceptionnelle: ROI {metrics['roi']:.1%}",
                    'data': {'roi': metrics['roi'], 'sample_size': metrics['total_bets']},
                    'timestamp': datetime.now().isoformat()
                })
            
            # Sauvegarder dans historique
            self.alert_history.extend(alerts)
            
            # Limiter historique à 100 dernières alertes
            if len(self.alert_history) > 100:
                self.alert_history = self.alert_history[-100:]
            
        except Exception as e:
            logger.error(f"❌ Erreur génération alertes: {e}")
        
        return alerts
    
    
    def get_realtime_metrics(self, variation_id: Optional[int] = None) -> Dict:
        """Récupère métriques temps réel"""
        if variation_id:
            return self.realtime_metrics.get(variation_id, {})
        else:
            return self.realtime_metrics.copy()
    
    
    def get_alert_history(
        self,
        variation_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Récupère historique des alertes"""
        alerts = self.alert_history
        
        if variation_id:
            alerts = [a for a in alerts if a.get('variation_id') == variation_id]
        
        return alerts[-limit:]
    
    
    def get_performance_summary(self) -> Dict:
        """Résumé global des performances"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_variations': len(self.realtime_metrics),
            'variations': {},
            'top_performers': [],
            'underperformers': [],
            'total_alerts': len(self.alert_history),
            'critical_alerts': len([a for a in self.alert_history if a['level'] == AlertLevel.CRITICAL.value])
        }
        
        # Métriques par variation
        for var_id, metrics in self.realtime_metrics.items():
            summary['variations'][var_id] = {
                'total_bets': metrics['total_bets'],
                'win_rate': metrics['win_rate'],
                'roi': metrics['roi'],
                'profit': metrics['total_profit']
            }
        
        # Top performers (top 3 ROI)
        sorted_vars = sorted(
            self.realtime_metrics.items(),
            key=lambda x: x[1].get('roi', 0),
            reverse=True
        )
        
        summary['top_performers'] = [
            {'variation_id': var_id, **metrics}
            for var_id, metrics in sorted_vars[:3]
        ]
        
        # Underperformers (ROI < 0)
        summary['underperformers'] = [
            {'variation_id': var_id, **metrics}
            for var_id, metrics in self.realtime_metrics.items()
            if metrics.get('roi', 0) < 0
        ]
        
        return summary
    
    
    def reset_metrics(self, variation_id: Optional[int] = None):
        """Reset métriques (pour tests ou nouveau cycle)"""
        if variation_id:
            if variation_id in self.realtime_metrics:
                del self.realtime_metrics[variation_id]
            if variation_id in self.performance_baseline:
                del self.performance_baseline[variation_id]
            logger.info(f"🔄 Metrics reset pour variation {variation_id}")
        else:
            self.realtime_metrics = {}
            self.performance_baseline = {}
            self.alert_history = []
            logger.info("🔄 Toutes les métriques reset")


# Instance singleton
_realtime_tracker = None

def get_realtime_tracker(db_session=None, alert_callback=None) -> RealtimePerformanceTracker:
    """Récupère l'instance singleton"""
    global _realtime_tracker
    if _realtime_tracker is None:
        _realtime_tracker = RealtimePerformanceTracker(db_session, alert_callback)
    return _realtime_tracker
