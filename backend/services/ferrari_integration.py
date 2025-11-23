"""
Ferrari 2.0 Integration Service
Gère l'assignation des matchs aux variations et l'application des paramètres
"""

import logging
import requests
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class FerrariIntegrationService:
    """Service d'intégration Ferrari 2.0 avec Agent B"""
    
    def __init__(self, api_base_url: str = "http://monps_backend:8000"):
        self.api_base_url = api_base_url
        self.enabled = True  # Flag pour activer/désactiver Ferrari
        
    def is_enabled(self) -> bool:
        """Vérifie si Ferrari 2.0 est activé"""
        return self.enabled
    
    def set_enabled(self, enabled: bool):
        """Active/désactive Ferrari 2.0"""
        self.enabled = enabled
        logger.info(f"Ferrari 2.0 {'activé' if enabled else 'désactivé'}")
    
    def assign_match_to_variation(
        self, 
        improvement_id: int,
        match_id: str,
        home_team: str,
        away_team: str,
        sport: str,
        commence_time: str
    ) -> Optional[Dict]:
        """
        Assigne un match à une variation via Thompson Sampling
        
        Returns:
            {
                'assignment_id': int,
                'variation_id': int,
                'variation_config': {...}  # Configuration à appliquer
            }
        """
        if not self.enabled:
            return None
        
        try:
            # Appeler API Ferrari pour sélection variation
            response = requests.post(
                f"{self.api_base_url}/ferrari/improvements/{improvement_id}/assign-match",
                json={
                    "match_id": match_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "sport": sport,
                    "commence_time": commence_time
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Récupérer configuration de la variation
                variation_config = self._get_variation_config(data['variation_id'])
                
                logger.info(f"Match {match_id} assigné à variation {data['variation_id']}")
                
                return {
                    'assignment_id': data['assignment_id'],
                    'variation_id': data['variation_id'],
                    'variation_config': variation_config
                }
            else:
                logger.error(f"Erreur assignation match: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erreur Ferrari assignation: {e}")
            return None
    
    def _get_variation_config(self, variation_id: int) -> Dict:
        """Récupère la configuration d'une variation"""
        try:
            response = requests.get(
                f"{self.api_base_url}/strategies/variations/{variation_id}/stats",
                timeout=5
            )
            
            if response.status_code == 200:
                variation = response.json()['variation']
                
                return {
                    'enabled_factors': variation.get('enabled_factors', []),
                    'enabled_adjustments': variation.get('enabled_adjustments', []),
                    'use_new_threshold': variation.get('use_new_threshold', False),
                    'custom_threshold': variation.get('custom_threshold'),
                    'is_control': variation.get('is_control', False)
                }
            else:
                logger.warning(f"Config variation {variation_id} non trouvée")
                return {}
                
        except Exception as e:
            logger.error(f"Erreur get variation config: {e}")
            return {}
    
    def apply_variation_to_agent_params(
        self, 
        base_params: Dict[str, Any],
        variation_config: Dict
    ) -> Dict[str, Any]:
        """
        Applique les paramètres d'une variation aux paramètres de l'agent
        
        Args:
            base_params: Paramètres par défaut de l'Agent B
            variation_config: Configuration de la variation à appliquer
        
        Returns:
            Nouveaux paramètres modifiés
        """
        modified_params = base_params.copy()
        
        # Si variation contrôle, retourner paramètres originaux
        if variation_config.get('is_control'):
            logger.info("Variation contrôle - Paramètres inchangés")
            return modified_params
        
        # Appliquer facteurs manquants
        enabled_factors = variation_config.get('enabled_factors', [])
        if enabled_factors:
            modified_params['enabled_factors'] = enabled_factors
            logger.info(f"Facteurs activés: {enabled_factors}")
        
        # Appliquer nouveau seuil si configuré
        if variation_config.get('use_new_threshold'):
            new_threshold = variation_config.get('custom_threshold')
            if new_threshold:
                modified_params['confidence_threshold'] = new_threshold / 100.0
                logger.info(f"Seuil modifié: {new_threshold}%")
        
        # Appliquer ajustements recommandés
        adjustments = variation_config.get('enabled_adjustments', [])
        if adjustments:
            modified_params['adjustments'] = adjustments
            logger.info(f"Ajustements appliqués: {len(adjustments)}")
        
        return modified_params
    
    def record_match_result(
        self,
        assignment_id: int,
        outcome: str,
        profit: float,
        stake: float,
        odds: float
    ) -> bool:
        """
        Enregistre le résultat d'un match et met à jour les stats Bayésiennes
        
        Args:
            assignment_id: ID de l'assignation
            outcome: 'win', 'loss', ou 'void'
            profit: Profit réalisé
            stake: Mise
            odds: Cote
        
        Returns:
            True si succès
        """
        if not self.enabled:
            return False
        
        try:
            response = requests.post(
                f"{self.api_base_url}/ferrari/assignments/{assignment_id}/result",
                json={
                    "assignment_id": assignment_id,
                    "outcome": outcome,
                    "profit": profit,
                    "stake": stake,
                    "odds": odds
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Résultat enregistré - Variation {data['variation_id']}, Outcome: {outcome}")
                
                # Log si événements safeguard
                if data.get('critical_events', 0) > 0:
                    logger.warning(f"⚠️ {data['critical_events']} événements critiques détectés")
                
                return True
            else:
                logger.error(f"Erreur enregistrement résultat: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur Ferrari record result: {e}")
            return False
    
    def get_active_improvements(self) -> list:
        """Récupère la liste des améliorations actives avec tests A/B"""
        try:
            response = requests.get(
                f"{self.api_base_url}/strategies/improvements",
                timeout=5
            )
            
            if response.status_code == 200:
                improvements = response.json().get('improvements', [])
                # Filtrer celles avec tests A/B actifs
                active = [imp for imp in improvements if imp.get('ab_test_active')]
                return active
            else:
                return []
                
        except Exception as e:
            logger.error(f"Erreur get active improvements: {e}")
            return []

# Instance globale
ferrari_service = FerrariIntegrationService()

