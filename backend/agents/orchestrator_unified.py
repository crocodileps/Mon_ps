"""
Ferrari Ultimate 2.0 - Unified Orchestrator (CORRIGÉ)
Orchestrateur intelligent compatible avec les vraies signatures des agents
"""

import sys
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Imports agents
from agent_anomaly import AnomalyDetectorAgent
from agent_pattern import PatternMatcherAgent
from agent_backtest import BacktestAgent
from agent_spread import SpreadOptimizerAgent
from agent_spread_ferrari import SpreadOptimizerFerrari

# Imports services Ferrari
sys.path.append('/app')
from services.ferrari_smart_router import (
    get_smart_router,
    EngineType,
    RouterStrategy
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration DB
DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}


class UnifiedOrchestrator:
    """Orchestrateur Unifié Ferrari Ultimate 2.0 (Compatible)"""
    
    def __init__(
        self,
        db_config: Dict,
        router_strategy: RouterStrategy = RouterStrategy.AUTO,
        shadow_mode: bool = False
    ):
        self.db_config = db_config
        self.shadow_mode = shadow_mode
        self.bankroll = 5000.0
        
        # Initialiser agents (ils utilisent generate_signals(), pas analyze())
        logger.info("🎯 Initialisation agents...")
        self.agents = {
            'Agent A': AnomalyDetectorAgent(db_config),
            'Agent C': PatternMatcherAgent(db_config),
            'Agent D': BacktestAgent(db_config),
            'Agent B Baseline': SpreadOptimizerAgent(db_config),
        }
        
        # Agent B Ferrari
        self.ferrari_agent = None
        self.ferrari_enabled = False
        
        # Smart Router
        self.smart_router = get_smart_router(strategy=router_strategy)
        
        # Stats
        self.execution_stats = {
            'total_matches': 0,
            'ferrari_matches': 0,
            'baseline_matches': 0,
            'shadow_matches': 0,
            'signals_generated': {
                'Agent A': 0,
                'Agent C': 0,
                'Agent D': 0,
                'Agent B Baseline': 0,
                'Agent B Ferrari': 0
            },
            'errors': []
        }
        
        logger.info(f"✅ Unified Orchestrator initialisé")
        logger.info(f"   Strategy: {router_strategy.value}")
        logger.info(f"   Shadow Mode: {shadow_mode}")
    
    
    def initialize_ferrari(self):
        """Initialise Agent B Ferrari (sans improvement_id)"""
        try:
            logger.info("🏎️ Initialisation Ferrari...")
            
            # Config pour Ferrari avec facteurs additionnels
            ferrari_config = {
                'facteurs_additionnels': {
                    'forme_récente_des_équipes': 0.10,
                    'blessures_clés': 0.08,
                    'conditions_météorologiques': 0.05,
                    'historique_des_confrontations_directes': 0.075
                },
                'seuils': {
                    'confidence_threshold': 0.70,
                    'kelly_fraction': 0.25,
                    'min_spread': 2.0
                }
            }
            
            self.ferrari_agent = SpreadOptimizerFerrari(
                db_config=self.db_config,
                config=ferrari_config
            )
            
            self.ferrari_enabled = True
            logger.info("✅ Ferrari initialisé avec succès")
            
        except Exception as e:
            logger.error(f"❌ Erreur init Ferrari: {e}", exc_info=True)
            self.ferrari_enabled = False
    
    
    def analyze_match(
        self,
        match_data: Dict,
        force_engine: Optional[EngineType] = None
    ) -> Dict:
        """Analyse un match avec tous les agents"""
        start_time = datetime.now()
        match_id = f"{match_data.get('sport', 'unknown')}_{match_data.get('home_team', 'home')}_{match_data.get('away_team', 'away')}"
        
        logger.info("=" * 80)
        logger.info(f"🎯 ANALYSE: {match_data.get('home_team')} vs {match_data.get('away_team')}")
        logger.info("=" * 80)
        
        results = {
            'match_id': match_id,
            'match_data': match_data,
            'timestamp': start_time.isoformat(),
            'signals': {
                'Agent A': [],
                'Agent C': [],
                'Agent D': [],
                'Agent B Baseline': [],
                'Agent B Ferrari': []
            },
            'routing': {},
            'shadow_comparison': None,
            'duration': 0,
            'error': None
        }
        
        try:
            # 1. Agents A, C, D (génèrent leurs propres signaux)
            try:
                results['signals']['Agent A'] = self.agents['Agent A'].generate_signals(top_n=5)
                logger.info(f"✅ Agent A: {len(results['signals']['Agent A'])} signaux")
            except Exception as e:
                logger.error(f"❌ Agent A: {e}")
            
            try:
                results['signals']['Agent C'] = self.agents['Agent C'].generate_signals(top_n=5)
                logger.info(f"✅ Agent C: {len(results['signals']['Agent C'])} signaux")
            except Exception as e:
                logger.error(f"❌ Agent C: {e}")
            
            try:
                results['signals']['Agent D'] = self.agents['Agent D'].generate_signals(top_n=5)
                logger.info(f"✅ Agent D: {len(results['signals']['Agent D'])} signaux")
            except Exception as e:
                logger.error(f"❌ Agent D: {e}")
            
            # 2. Agent B avec Smart Routing
            if self.shadow_mode:
                # Mode Shadow
                baseline_signals = self._run_baseline()
                ferrari_signals = self._run_ferrari()
                
                results['signals']['Agent B Baseline'] = baseline_signals
                results['signals']['Agent B Ferrari'] = ferrari_signals
                results['shadow_comparison'] = self._compare_signals(baseline_signals, ferrari_signals)
                results['routing']['mode'] = 'shadow'
                self.execution_stats['shadow_matches'] += 1
                
            else:
                # Smart Router décide
                engine, routing_meta = self.smart_router.route_match_analysis(match_data, force_engine)
                results['routing'] = routing_meta
                
                if engine == EngineType.FERRARI and self.ferrari_enabled:
                    results['signals']['Agent B Ferrari'] = self._run_ferrari()
                    self.execution_stats['ferrari_matches'] += 1
                else:
                    results['signals']['Agent B Baseline'] = self._run_baseline()
                    self.execution_stats['baseline_matches'] += 1
            
            # Stats
            self.execution_stats['total_matches'] += 1
            for agent_name, signals in results['signals'].items():
                if signals and agent_name in self.execution_stats['signals_generated']:
                    self.execution_stats['signals_generated'][agent_name] += len(signals)
            
            # Durée
            results['duration'] = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Analyse terminée en {results['duration']:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Erreur analyse: {e}", exc_info=True)
            results['error'] = str(e)
            results['duration'] = (datetime.now() - start_time).total_seconds()
            self.execution_stats['errors'].append(str(e))
        
        return results
    
    
    def _run_baseline(self) -> List[Dict]:
        """Exécute Agent B Baseline"""
        try:
            signals = self.agents['Agent B Baseline'].generate_signals(top_n=10)
            logger.info(f"✅ Baseline: {len(signals)} signaux")
            return signals
        except Exception as e:
            logger.error(f"❌ Baseline: {e}")
            return []
    
    
    def _run_ferrari(self) -> List[Dict]:
        """Exécute Agent B Ferrari"""
        try:
            if not self.ferrari_agent:
                logger.warning("⚠️ Ferrari non initialisé, fallback baseline")
                return self._run_baseline()
            
            signals = self.ferrari_agent.generate_signals(top_n=10)
            logger.info(f"🏎️ Ferrari: {len(signals)} signaux")
            return signals
            
        except Exception as e:
            logger.error(f"❌ Ferrari: {e}")
            return self._run_baseline()
    
    
    def _compare_signals(self, baseline: List[Dict], ferrari: List[Dict]) -> Dict:
        """Compare signaux Baseline vs Ferrari"""
        return {
            'baseline_count': len(baseline),
            'ferrari_count': len(ferrari),
            'difference': len(ferrari) - len(baseline)
        }
    
    
    def get_execution_summary(self) -> Dict:
        """Résumé exécution"""
        router_stats = self.smart_router.get_routing_stats()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'bankroll': self.bankroll,
            'ferrari_enabled': self.ferrari_enabled,
            'shadow_mode': self.shadow_mode,
            'execution_stats': self.execution_stats,
            'router_stats': router_stats
        }
    
    
    def print_summary(self):
        """Affiche résumé"""
        summary = self.get_execution_summary()
        
        print("\n" + "=" * 80)
        print("🏎️ FERRARI ULTIMATE 2.0 - UNIFIED ORCHESTRATOR")
        print("=" * 80)
        print(f"Bankroll: {summary['bankroll']}€")
        print(f"Ferrari: {'✅ ACTIVÉ' if summary['ferrari_enabled'] else '❌ DÉSACTIVÉ'}")
        print(f"Shadow Mode: {'✅ ACTIVÉ' if summary['shadow_mode'] else '❌ DÉSACTIVÉ'}")
        print()
        
        print("📊 STATISTIQUES")
        print("-" * 80)
        stats = summary['execution_stats']
        print(f"Total matchs: {stats['total_matches']}")
        print(f"Ferrari: {stats['ferrari_matches']}")
        print(f"Baseline: {stats['baseline_matches']}")
        print(f"Shadow: {stats['shadow_matches']}")
        print()
        
        print("🎯 SIGNAUX PAR AGENT")
        print("-" * 80)
        for agent, count in stats['signals_generated'].items():
            print(f"  {agent}: {count}")
        print()
        
        print("�� SMART ROUTER")
        print("-" * 80)
        router = summary['router_stats']
        print(f"Total routé: {router['total_routed']}")
        print(f"Ferrari: {router['ferrari_count']} ({router['ferrari_percent']:.1f}%)")
        print(f"Baseline: {router['baseline_count']}")
        print(f"Stratégie: {router['current_strategy']}")
        print("=" * 80)


def main():
    """Point d'entrée"""
    parser = argparse.ArgumentParser(description='Ferrari Ultimate 2.0')
    parser.add_argument('--strategy', choices=['auto', 'ferrari', 'baseline', 'split', 'gradual'], default='auto')
    parser.add_argument('--shadow', action='store_true')
    parser.add_argument('--test-match', action='store_true')
    
    args = parser.parse_args()
    
    strategy_map = {
        'auto': RouterStrategy.AUTO,
        'ferrari': RouterStrategy.FERRARI_ONLY,
        'baseline': RouterStrategy.BASELINE_ONLY,
        'split': RouterStrategy.SPLIT_TEST,
        'gradual': RouterStrategy.GRADUAL_ROLLOUT
    }
    
    orchestrator = UnifiedOrchestrator(
        db_config=DB_CONFIG,
        router_strategy=strategy_map[args.strategy],
        shadow_mode=args.shadow
    )
    
    orchestrator.initialize_ferrari()
    
    if args.test_match:
        logger.info("🧪 Test mode")
        
        test_match = {
            'match_id': 'test_123',
            'sport': 'soccer_epl',
            'home_team': 'Manchester United',
            'away_team': 'Liverpool',
            'commence_time': datetime.now().isoformat()
        }
        
        result = orchestrator.analyze_match(test_match)
        
        print("\n" + "=" * 80)
        print("🧪 RÉSULTAT TEST")
        print("=" * 80)
        print(f"Match: {result['match_data']['home_team']} vs {result['match_data']['away_team']}")
        print(f"Durée: {result['duration']:.2f}s")
        print()
        
        for agent, signals in result['signals'].items():
            if signals:
                print(f"{agent}: {len(signals)} signaux")
        
        if result.get('shadow_comparison'):
            print("\n👥 SHADOW COMPARISON:")
            comp = result['shadow_comparison']
            print(f"  Baseline: {comp['baseline_count']}")
            print(f"  Ferrari: {comp['ferrari_count']}")
        
        print("=" * 80)
    
    orchestrator.print_summary()


if __name__ == "__main__":
    main()
