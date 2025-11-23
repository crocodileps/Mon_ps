"""
Ferrari 2.0 Middleware
Intercepte les matchs et route vers les variations appropriées
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
sys.path.append('/app')

from services.ferrari_integration import ferrari_service
from agents.agent_spread_ferrari import SpreadOptimizerFerrari
from agents.agent_spread import SpreadOptimizerAgent

logger = logging.getLogger(__name__)

class FerrariMiddleware:
    """
    Middleware qui orchestre l'intégration Ferrari 2.0
    Intercepte les matchs et applique les variations
    """
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.ferrari_service = ferrari_service
        
        # Cache des agents par variation
        self.agent_cache: Dict[int, SpreadOptimizerFerrari] = {}
        
        # Agent baseline (sans Ferrari)
        self.baseline_agent = SpreadOptimizerAgent(db_config)
    
    def process_opportunities(self) -> List[Dict]:
        """
        Point d'entrée principal : traite les opportunités avec ou sans Ferrari
        
        Returns:
            Liste de signaux générés (avec info variation si Ferrari actif)
        """
        # Vérifier si Ferrari est activé
        if not self.ferrari_service.is_enabled():
            logger.info("Ferrari 2.0 désactivé - Mode baseline")
            return self.baseline_agent.generate_signals()
        
        # Ferrari activé : récupérer améliorations actives
        active_improvements = self.ferrari_service.get_active_improvements()
        
        if not active_improvements:
            logger.info("Aucune amélioration active - Mode baseline")
            return self.baseline_agent.generate_signals()
        
        # Pour chaque amélioration active, traiter avec variations
        all_signals = []
        
        for improvement in active_improvements:
            improvement_id = improvement['id']
            logger.info(f"Traitement amélioration #{improvement_id}: {improvement['agent_name']}")
            
            # Récupérer opportunités
            opportunities = self._fetch_opportunities()
            
            # Traiter chaque opportunité
            for opp in opportunities:
                signal = self._process_single_opportunity(
                    improvement_id, 
                    opp
                )
                
                if signal:
                    all_signals.append(signal)
        
        return all_signals
    
    def _fetch_opportunities(self) -> List[Dict]:
        """Récupère les opportunités actuelles"""
        # Utiliser agent baseline pour fetch
        df = self.baseline_agent.fetch_opportunities()
        
        opportunities = []
        for idx, row in df.iterrows():
            opportunities.append({
                'match_id': f"{row['sport']}_{row['home_team']}_{row['away_team']}",
                'home_team': row['home_team'],
                'away_team': row['away_team'],
                'sport': row['sport'],
                'commence_time': datetime.now().isoformat(),
                'data': row.to_dict()
            })
        
        return opportunities
    
    def _process_single_opportunity(
        self, 
        improvement_id: int,
        opportunity: Dict
    ) -> Optional[Dict]:
        """
        Traite une opportunité unique avec Ferrari
        
        Steps:
        1. Assigner à variation via Thompson Sampling
        2. Créer agent avec config variation
        3. Générer signal
        4. Enregistrer assignation
        """
        try:
            # Step 1: Assigner à variation
            assignment = self.ferrari_service.assign_match_to_variation(
                improvement_id=improvement_id,
                match_id=opportunity['match_id'],
                home_team=opportunity['home_team'],
                away_team=opportunity['away_team'],
                sport=opportunity['sport'],
                commence_time=opportunity['commence_time']
            )
            
            if not assignment:
                logger.warning(f"Échec assignation match {opportunity['match_id']}")
                return None
            
            variation_id = assignment['variation_id']
            variation_config = assignment['variation_config']
            
            logger.info(f"Match {opportunity['match_id']} → Variation {variation_id}")
            
            # Step 2: Créer/récupérer agent avec config
            agent = self._get_agent_for_variation(variation_id, variation_config)
            
            # Step 3: Générer signal avec cet agent
            # Créer un mini-DataFrame pour cet match
            import pandas as pd
            df = pd.DataFrame([opportunity['data']])
            
            # Injecter dans agent temporairement
            agent_signals = []
            for idx, row in df.iterrows():
                # Déterminer meilleure opportunité
                spreads = {
                    'home': row['home_spread_pct'],
                    'away': row['away_spread_pct'],
                    'draw': row.get('draw_spread_pct', 0)
                }
                
                best_outcome = max(spreads, key=spreads.get)
                best_spread = spreads[best_outcome]
                
                if best_outcome == 'home':
                    max_odds = row['max_home_odds']
                    min_odds = row['min_home_odds']
                    direction = 'BACK_HOME'
                elif best_outcome == 'away':
                    max_odds = row['max_away_odds']
                    min_odds = row['min_away_odds']
                    direction = 'BACK_AWAY'
                else:
                    max_odds = row['max_draw_odds']
                    min_odds = row['min_draw_odds']
                    direction = 'BACK_DRAW'
                
                # Calculer avec agent Ferrari
                win_prob = agent.estimate_win_probability(max_odds, min_odds, best_spread)
                kelly = agent.calculate_kelly_criterion(max_odds, win_prob)
                ev = agent.calculate_expected_value(max_odds, win_prob)
                
                confidence = min((best_spread * 10) + (ev * 50), 100) / 100
                
                # Filtrer selon seuil
                if confidence < agent.confidence_threshold:
                    logger.debug(f"Match filtré par seuil: {confidence:.1%} < {agent.confidence_threshold:.1%}")
                    continue
                
                signal = {
                    'agent': agent.name,
                    'match': f"{row['home_team']} vs {row['away_team']}",
                    'sport': row['sport'],
                    'direction': direction,
                    'confidence': confidence * 100,
                    'odds': {
                        'max': max_odds,
                        'min': min_odds,
                        'avg': (max_odds + min_odds) / 2
                    },
                    'spread_pct': best_spread,
                    'win_probability': win_prob,
                    'kelly_fraction': kelly,
                    'expected_value': ev,
                    'recommended_stake_pct': kelly * 100,
                    'bookmaker_count': row['bookmaker_count'],
                    # Info Ferrari
                    'ferrari_enabled': True,
                    'improvement_id': improvement_id,
                    'variation_id': variation_id,
                    'assignment_id': assignment['assignment_id'],
                    'variation_config': variation_config,
                    'reason': f"Spread {best_spread:.2f}%, EV={ev:.3f}, Kelly={kelly*100:.1f}%, Variation {variation_id}"
                }
                
                agent_signals.append(signal)
            
            if agent_signals:
                return agent_signals[0]  # Retourner premier signal
            else:
                return None
                
        except Exception as e:
            logger.error(f"Erreur traitement opportunité Ferrari: {e}", exc_info=True)
            return None
    
    def _get_agent_for_variation(
        self, 
        variation_id: int, 
        variation_config: Dict
    ) -> SpreadOptimizerFerrari:
        """
        Récupère ou crée agent pour une variation
        Utilise cache pour éviter recréation
        """
        if variation_id in self.agent_cache:
            return self.agent_cache[variation_id]
        
        # Créer config pour agent
        agent_config = self._build_agent_config(variation_config)
        
        # Créer agent Ferrari
        agent = SpreadOptimizerFerrari(self.db_config, agent_config)
        
        # Cacher
        self.agent_cache[variation_id] = agent
        
        logger.info(f"Agent créé pour variation {variation_id}: {agent_config}")
        
        return agent
    
    def _build_agent_config(self, variation_config: Dict) -> Dict:
        """
        Construit configuration agent depuis config variation
        
        Args:
            variation_config: Config de la variation (enabled_factors, etc.)
        
        Returns:
            Config pour SpreadOptimizerFerrari
        """
        config = {}
        
        # Facteurs activés
        if variation_config.get('enabled_factors'):
            config['enabled_factors'] = variation_config['enabled_factors']
        
        # Nouveau seuil
        if variation_config.get('use_new_threshold') and variation_config.get('custom_threshold'):
            config['confidence_threshold'] = variation_config['custom_threshold'] / 100.0
        
        # Ajustements (TODO: parser et appliquer)
        if variation_config.get('enabled_adjustments'):
            config['adjustments'] = variation_config['enabled_adjustments']
        
        return config
    
    def record_bet_result(
        self,
        assignment_id: int,
        outcome: str,
        profit: float,
        stake: float,
        odds: float
    ) -> bool:
        """
        Enregistre résultat d'un pari Ferrari
        Met à jour stats Bayésiennes automatiquement
        """
        return self.ferrari_service.record_match_result(
            assignment_id=assignment_id,
            outcome=outcome,
            profit=profit,
            stake=stake,
            odds=odds
        )

# Instance globale
ferrari_middleware = None

def get_ferrari_middleware(db_config: Dict) -> FerrariMiddleware:
    """Récupère instance singleton du middleware"""
    global ferrari_middleware
    if ferrari_middleware is None:
        ferrari_middleware = FerrariMiddleware(db_config)
    return ferrari_middleware

