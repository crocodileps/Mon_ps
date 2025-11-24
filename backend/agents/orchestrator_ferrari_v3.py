"""
Orchestrator Ferrari V3 - A/B Testing avec API-Football
"""

import sys
sys.path.append('/app')

import os
import logging
from typing import Dict, List
import random

from services.api_football_service import get_api_football_service
from services.team_resolver import get_team_resolver
from agents.agent_spread_ferrari_v3 import SpreadOptimizerFerrariV3
from agents.agent_spread import SpreadOptimizerAgent as SpreadOptimizer  # Baseline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DB_CONFIG = {
    'host': 'monps_postgres',
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}


class OrchestratorFerrariV3:
    """Orchestrator avec A/B testing Ferrari V3"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.db_config = DB_CONFIG
        
        # Services
        self.api_service = get_api_football_service(api_key, DB_CONFIG)
        self.team_resolver = get_team_resolver(DB_CONFIG)
        
        # Agent baseline
        self.baseline = SpreadOptimizer(
            db_config=DB_CONFIG,
            min_spread=2.0,
            confidence_threshold=0.70
        )
        
        logger.info("🏎️ Orchestrator Ferrari V3 initialisé")
    
    
    def load_variations(self) -> List[Dict]:
        """Charge variations actives depuis DB"""
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                v.id,
                v.variation_name,
                v.config,
                COALESCE(vta.allocation_percent, 20.0) as allocation
            FROM agent_b_variations v
            LEFT JOIN variation_traffic_allocation vta ON v.id = vta.variation_id
            WHERE v.status = 'active'
            ORDER BY v.id
        """
        
        cursor.execute(query)
        variations = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return variations
    
    
    def select_variation(self, variations: List[Dict]) -> Dict:
        """Sélectionne variation selon Thompson Sampling"""
        # Simplification: random weighted par allocation
        total = sum(v['allocation'] for v in variations)
        weights = [v['allocation'] / total for v in variations]
        
        selected = random.choices(variations, weights=weights)[0]
        
        return selected
    
    
    def run_ab_test(self, top_n: int = 10) -> Dict:
        """
        Exécute A/B test complet
        """
        logger.info("=" * 80)
        logger.info("🧪 A/B TEST FERRARI V3")
        logger.info("=" * 80)
        logger.info("")
        
        # Load variations
        variations = self.load_variations()
        logger.info(f"📊 {len(variations)} variations actives")
        for v in variations:
            logger.info(f"   • {v['variation_name']}: {v['allocation']:.1f}% traffic")
        logger.info("")
        
        # Baseline signals
        logger.info("=== BASELINE ===")
        baseline_signals = self.baseline.generate_signals(top_n=top_n)
        logger.info(f"✅ {len(baseline_signals)} signaux Baseline")
        logger.info("")
        
        # Ferrari V3 variations
        ferrari_results = {}
        
        for variation in variations:
            if variation['id'] == 2:  # Skip baseline
                continue
            
            logger.info(f"=== {variation['variation_name']} ===")
            
            try:
                # Créer agent Ferrari V3 avec config
                ferrari = SpreadOptimizerFerrariV3(
                    db_config=self.db_config,
                    api_key=self.api_key,
                    config=variation['config']
                )
                
                # Générer signaux
                signals = ferrari.generate_signals(top_n=top_n)
                
                ferrari_results[variation['id']] = {
                    'name': variation['variation_name'],
                    'signals': signals,
                    'count': len(signals)
                }
                
                logger.info(f"✅ {len(signals)} signaux générés")
                
            except Exception as e:
                logger.error(f"❌ Erreur: {e}")
                ferrari_results[variation['id']] = {
                    'name': variation['variation_name'],
                    'signals': [],
                    'count': 0,
                    'error': str(e)
                }
            
            logger.info("")
        
        # Comparaison
        logger.info("=" * 80)
        logger.info("📊 COMPARAISON")
        logger.info("=" * 80)
        logger.info("")
        
        logger.info(f"Baseline: {len(baseline_signals)} signaux")
        for vid, result in ferrari_results.items():
            logger.info(f"{result['name']}: {result['count']} signaux")
        
        logger.info("")
        logger.info("=" * 80)
        
        return {
            'baseline': baseline_signals,
            'variations': ferrari_results,
            'api_requests_used': self.api_service.daily_requests
        }


def main():
    # Load API key
    api_key = os.environ.get('API_FOOTBALL_KEY')
    
    if not api_key:
        logger.error("❌ API_FOOTBALL_KEY non trouvée")
        return 1
    
    orchestrator = OrchestratorFerrariV3(api_key)
    
    # Run A/B test
    results = orchestrator.run_ab_test(top_n=5)
    
    logger.info("")
    logger.info(f"📊 API Requests utilisées: {results['api_requests_used']}/100")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
