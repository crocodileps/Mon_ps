"""
Orchestrator Ferrari V3 - Simplifié (sans baseline pour test)
"""

import sys
sys.path.append('/app')

import os
import logging
from typing import Dict, List

from services.api_football_service import get_api_football_service
from services.team_resolver import get_team_resolver
from agents.agent_spread_ferrari_v3 import SpreadOptimizerFerrariV3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DB_CONFIG = {
    'host': 'monps_postgres',
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}


class OrchestratorFerrariV3Simple:
    """Orchestrator simplifié - test Ferrari V3 uniquement"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.db_config = DB_CONFIG
        
        # Services
        self.api_service = get_api_football_service(api_key, DB_CONFIG)
        self.team_resolver = get_team_resolver(DB_CONFIG)
        
        logger.info("🏎️ Orchestrator Ferrari V3 (Simple) initialisé")
    
    
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
            AND v.id != 2  -- Skip baseline
            ORDER BY v.id
        """
        
        cursor.execute(query)
        variations = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return variations
    
    
    def test_single_variation(self, variation: Dict, top_n: int = 5) -> Dict:
        """
        Test une seule variation
        """
        logger.info("=" * 80)
        logger.info(f"🧪 TEST: {variation['variation_name']}")
        logger.info("=" * 80)
        logger.info("")
        
        config = variation['config']
        factors = config.get('facteurs_additionnels', {})
        seuils = config.get('seuils', {})
        
        logger.info("📊 Configuration:")
        logger.info(f"   Facteurs: {list(factors.keys())}")
        logger.info(f"   Poids: {factors}")
        logger.info(f"   Min spread: {seuils.get('min_spread', 0)}%")
        logger.info(f"   Confidence: {seuils.get('confidence_threshold', 0):.0%}")
        logger.info("")
        
        try:
            # Créer agent Ferrari V3
            ferrari = SpreadOptimizerFerrariV3(
                db_config=self.db_config,
                api_key=self.api_key,
                config=config
            )
            
            # Générer signaux
            logger.info("🔍 Génération signaux...")
            signals = ferrari.generate_signals(top_n=top_n)
            
            logger.info("")
            logger.info(f"✅ {len(signals)} signaux générés")
            logger.info("")
            
            if signals:
                logger.info("📋 Top 3 signaux:")
                for i, signal in enumerate(signals[:3], 1):
                    logger.info(f"\n   {i}. {signal['home_team']} vs {signal['away_team']}")
                    logger.info(f"      Spread: {signal['spread_pct']}%")
                    logger.info(f"      Confidence: {signal['confidence']:.1%}")
                    logger.info(f"      Best odds: Home {signal['best_odds']['home']}, Away {signal['best_odds']['away']}")
            
            return {
                'success': True,
                'signals': signals,
                'count': len(signals)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'signals': [],
                'count': 0
            }
    
    
    def run_test(self, top_n: int = 5) -> Dict:
        """
        Test toutes les variations
        """
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║" + " " * 20 + "🏎️  FERRARI V3 - TEST COMPLET" + " " * 28 + "║")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        # Load variations
        variations = self.load_variations()
        logger.info(f"📊 {len(variations)} variations à tester")
        logger.info("")
        
        if not variations:
            logger.warning("⚠️  Aucune variation trouvée")
            return {'results': [], 'api_requests': 0}
        
        results = []
        
        for variation in variations:
            result = self.test_single_variation(variation, top_n=top_n)
            result['variation_id'] = variation['id']
            result['variation_name'] = variation['variation_name']
            results.append(result)
            
            logger.info("")
            logger.info("─" * 80)
            logger.info("")
        
        # Résumé final
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║" + " " * 32 + "📊 RÉSUMÉ" + " " * 37 + "║")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        for result in results:
            status = "✅" if result['success'] else "❌"
            logger.info(f"{status} {result['variation_name']}: {result['count']} signaux")
        
        logger.info("")
        logger.info(f"📊 Requêtes API utilisées: {self.api_service.daily_requests}/100")
        logger.info("")
        
        return {
            'results': results,
            'api_requests': self.api_service.daily_requests
        }


def main():
    # Load API key
    api_key = os.environ.get('API_FOOTBALL_KEY')
    
    if not api_key:
        logger.error("❌ API_FOOTBALL_KEY non trouvée")
        return 1
    
    logger.info(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
    logger.info("")
    
    orchestrator = OrchestratorFerrariV3Simple(api_key)
    
    # Run test
    results = orchestrator.run_test(top_n=3)
    
    # Success si au moins une variation a fonctionné
    success = any(r['success'] for r in results['results'])
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
