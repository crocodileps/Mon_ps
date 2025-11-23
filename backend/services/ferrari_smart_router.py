"""
Ferrari Smart Router - Cerveau Central Intelligent
Routes automatiquement vers le meilleur moteur (Ferrari vs Baseline)
avec fallback, load balancing et décisions basées sur stats
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import random

logger = logging.getLogger(__name__)


class EngineType(Enum):
    """Types de moteurs disponibles"""
    FERRARI = "ferrari"          # Ferrari 2.0 avec A/B testing
    BASELINE = "baseline"        # Agent B classique stable
    SHADOW = "shadow"            # Mode shadow (exécute les 2, compare)


class RouterStrategy(Enum):
    """Stratégies de routing"""
    AUTO = "auto"                # Décision automatique basée sur stats
    FERRARI_ONLY = "ferrari"     # Force Ferrari uniquement
    BASELINE_ONLY = "baseline"   # Force Baseline uniquement
    SPLIT_TEST = "split"         # Split 50/50 pour tests
    GRADUAL_ROLLOUT = "gradual"  # Rollout progressif Ferrari


class FerrariSmartRouter:
    """
    Smart Router - Cerveau du système Ferrari Ultimate 2.0
    
    Responsabilités:
    - Décide quel moteur utiliser pour chaque analyse
    - Load balancing intelligent
    - Fallback automatique si erreur
    - Promotion automatique basée sur performance
    - Rollback automatique si régression
    """
    
    def __init__(self, db_session=None, strategy: RouterStrategy = RouterStrategy.AUTO):
        self.db = db_session
        self.strategy = strategy
        
        # Configuration
        self.ferrari_rollout_percent = 20  # % de trafic vers Ferrari initialement
        self.min_samples_for_promotion = 50  # Minimum matchs avant promotion
        self.confidence_threshold = 0.95  # Seuil confiance pour promotion
        self.rollback_threshold = -0.10  # -10% performance = rollback
        
        # Cache de performances
        self._performance_cache = {
            'ferrari': {'last_update': None, 'metrics': {}},
            'baseline': {'last_update': None, 'metrics': {}}
        }
        
        # Compteurs
        self.routing_stats = {
            'ferrari': 0,
            'baseline': 0,
            'shadow': 0,
            'fallbacks': 0
        }
        
        logger.info(f"🏎️ Smart Router initialisé - Strategy: {strategy.value}")
    
    
    def route_match_analysis(
        self,
        match_data: Dict,
        force_engine: Optional[EngineType] = None
    ) -> Tuple[EngineType, Dict]:
        """
        Route l'analyse d'un match vers le bon moteur
        
        Args:
            match_data: Données du match à analyser
            force_engine: Force un moteur spécifique (pour tests)
            
        Returns:
            (engine_type, routing_metadata)
        """
        try:
            # Mode forcé (pour tests)
            if force_engine:
                logger.info(f"🎯 Mode forcé: {force_engine.value}")
                return force_engine, {'reason': 'forced', 'forced_by': 'manual'}
            
            # Décision basée sur stratégie
            engine = self._decide_engine(match_data)
            metadata = self._get_routing_metadata(engine, match_data)
            
            # Log routing
            self.routing_stats[engine.value] += 1
            logger.info(f"📍 Routing: {match_data.get('home_team')} vs {match_data.get('away_team')} → {engine.value}")
            
            return engine, metadata
            
        except Exception as e:
            logger.error(f"❌ Erreur routing: {e}", exc_info=True)
            # Fallback vers baseline en cas d'erreur
            self.routing_stats['fallbacks'] += 1
            return EngineType.BASELINE, {'reason': 'error_fallback', 'error': str(e)}
    
    
    def _decide_engine(self, match_data: Dict) -> EngineType:
        """Décide quel moteur utiliser basé sur la stratégie"""
        
        if self.strategy == RouterStrategy.FERRARI_ONLY:
            return EngineType.FERRARI
        
        elif self.strategy == RouterStrategy.BASELINE_ONLY:
            return EngineType.BASELINE
        
        elif self.strategy == RouterStrategy.SPLIT_TEST:
            # 50/50 random split
            return EngineType.FERRARI if random.random() < 0.5 else EngineType.BASELINE
        
        elif self.strategy == RouterStrategy.GRADUAL_ROLLOUT:
            # Rollout progressif basé sur pourcentage
            return EngineType.FERRARI if random.random() * 100 < self.ferrari_rollout_percent else EngineType.BASELINE
        
        elif self.strategy == RouterStrategy.AUTO:
            return self._auto_decide(match_data)
        
        else:
            logger.warning(f"⚠️ Stratégie inconnue: {self.strategy}, fallback baseline")
            return EngineType.BASELINE
    
    
    def _auto_decide(self, match_data: Dict) -> EngineType:
        """
        Décision automatique intelligente basée sur:
        - Performances historiques
        - Confidence statistique
        - Contexte du match
        """
        try:
            # Refresh cache si nécessaire
            self._refresh_performance_cache()
            
            ferrari_metrics = self._performance_cache['ferrari']['metrics']
            baseline_metrics = self._performance_cache['baseline']['metrics']
            
            # Si pas assez de données Ferrari, gradual rollout
            if ferrari_metrics.get('total_matches', 0) < self.min_samples_for_promotion:
                logger.debug(f"📊 Pas assez de données Ferrari ({ferrari_metrics.get('total_matches', 0)}/{self.min_samples_for_promotion}), gradual rollout")
                return EngineType.FERRARI if random.random() * 100 < self.ferrari_rollout_percent else EngineType.BASELINE
            
            # Comparer performances
            ferrari_roi = ferrari_metrics.get('roi', 0)
            baseline_roi = baseline_metrics.get('roi', 0)
            
            improvement = ferrari_roi - baseline_roi
            
            # Si Ferrari significativement meilleur (>10% ROI), utiliser Ferrari
            if improvement > 0.10:
                logger.debug(f"🚀 Ferrari meilleur (+{improvement:.1%}), routing Ferrari")
                return EngineType.FERRARI
            
            # Si Ferrari underperform (<-10% ROI), utiliser Baseline
            elif improvement < self.rollback_threshold:
                logger.warning(f"⚠️ Ferrari underperform ({improvement:.1%}), fallback Baseline")
                return EngineType.BASELINE
            
            # Performances similaires, gradual rollout
            else:
                logger.debug(f"📊 Performances similaires ({improvement:.1%}), gradual rollout")
                return EngineType.FERRARI if random.random() * 100 < self.ferrari_rollout_percent else EngineType.BASELINE
                
        except Exception as e:
            logger.error(f"❌ Erreur décision auto: {e}")
            return EngineType.BASELINE
    
    
    def _refresh_performance_cache(self):
        """Refresh cache des performances si nécessaire"""
        if not self.db:
            return
        
        now = datetime.now()
        
        # Refresh si cache > 5 minutes
        for engine in ['ferrari', 'baseline']:
            cache = self._performance_cache[engine]
            if not cache['last_update'] or (now - cache['last_update']).seconds > 300:
                try:
                    metrics = self._fetch_engine_metrics(engine)
                    cache['metrics'] = metrics
                    cache['last_update'] = now
                    logger.debug(f"🔄 Cache refreshed: {engine}")
                except Exception as e:
                    logger.error(f"❌ Erreur refresh cache {engine}: {e}")
    
    
    def _fetch_engine_metrics(self, engine: str) -> Dict:
        """Récupère les métriques de performance d'un moteur"""
        if not self.db:
            return {}
        
        try:
            from models.ferrari_models import VariationAssignment
            from sqlalchemy import func, case
            
            # Query basée sur assignments
            query = self.db.query(
                func.count(VariationAssignment.id).label('total_matches'),
                func.sum(case((VariationAssignment.outcome == 'win', 1), else_=0)).label('wins'),
                func.sum(VariationAssignment.profit).label('total_profit'),
                func.sum(VariationAssignment.stake).label('total_stake')
            )
            
            if engine == 'ferrari':
                # Ferrari = toutes les variations
                query = query.filter(VariationAssignment.assignment_method == 'thompson_sampling')
            else:
                # Baseline = variation contrôle (ID 2)
                query = query.filter(VariationAssignment.variation_id == 2)
            
            result = query.one()
            
            total_matches = result.total_matches or 0
            wins = result.wins or 0
            total_profit = float(result.total_profit or 0)
            total_stake = float(result.total_stake or 0)
            
            win_rate = wins / total_matches if total_matches > 0 else 0
            roi = total_profit / total_stake if total_stake > 0 else 0
            
            return {
                'total_matches': total_matches,
                'wins': wins,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'total_stake': total_stake,
                'roi': roi
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur fetch metrics {engine}: {e}")
            return {}
    
    
    def _get_routing_metadata(self, engine: EngineType, match_data: Dict) -> Dict:
        """Génère metadata pour le routing"""
        return {
            'engine': engine.value,
            'strategy': self.strategy.value,
            'timestamp': datetime.now().isoformat(),
            'match_id': match_data.get('match_id'),
            'home_team': match_data.get('home_team'),
            'away_team': match_data.get('away_team'),
            'rollout_percent': self.ferrari_rollout_percent
        }
    
    
    def should_promote_ferrari(self) -> Tuple[bool, Dict]:
        """
        Détermine si Ferrari devrait être promu en production
        
        Returns:
            (should_promote, reasoning)
        """
        try:
            self._refresh_performance_cache()
            
            ferrari_metrics = self._performance_cache['ferrari']['metrics']
            baseline_metrics = self._performance_cache['baseline']['metrics']
            
            # Vérifications
            checks = {
                'enough_samples': ferrari_metrics.get('total_matches', 0) >= self.min_samples_for_promotion,
                'positive_roi': ferrari_metrics.get('roi', 0) > 0,
                'better_than_baseline': ferrari_metrics.get('roi', 0) > baseline_metrics.get('roi', 0),
                'significant_improvement': (ferrari_metrics.get('roi', 0) - baseline_metrics.get('roi', 0)) > 0.10
            }
            
            should_promote = all(checks.values())
            
            reasoning = {
                'checks': checks,
                'ferrari_metrics': ferrari_metrics,
                'baseline_metrics': baseline_metrics,
                'improvement': ferrari_metrics.get('roi', 0) - baseline_metrics.get('roi', 0),
                'confidence': self.confidence_threshold
            }
            
            return should_promote, reasoning
            
        except Exception as e:
            logger.error(f"❌ Erreur promotion check: {e}")
            return False, {'error': str(e)}
    
    
    def increase_ferrari_traffic(self, percent: int):
        """Augmente progressivement le trafic vers Ferrari"""
        old_percent = self.ferrari_rollout_percent
        self.ferrari_rollout_percent = min(100, percent)
        logger.info(f"📈 Trafic Ferrari: {old_percent}% → {self.ferrari_rollout_percent}%")
    
    
    def get_routing_stats(self) -> Dict:
        """Retourne les statistiques de routing"""
        total = sum(self.routing_stats.values())
        
        return {
            'total_routed': total,
            'ferrari_count': self.routing_stats['ferrari'],
            'baseline_count': self.routing_stats['baseline'],
            'ferrari_percent': (self.routing_stats['ferrari'] / total * 100) if total > 0 else 0,
            'fallbacks': self.routing_stats['fallbacks'],
            'current_strategy': self.strategy.value,
            'ferrari_rollout_percent': self.ferrari_rollout_percent
        }


# Instance singleton
_router_instance = None

def get_smart_router(db_session=None, strategy: RouterStrategy = RouterStrategy.AUTO) -> FerrariSmartRouter:
    """Récupère l'instance singleton du Smart Router"""
    global _router_instance
    if _router_instance is None:
        _router_instance = FerrariSmartRouter(db_session, strategy)
    return _router_instance
