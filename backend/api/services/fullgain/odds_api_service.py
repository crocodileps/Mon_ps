"""
The Odds API Service - Cotes multi-marchés
Documentation: https://the-odds-api.com/liveapi/guides/v4/
"""
import requests
from typing import Optional, List
import logging
from .api_key_manager import APIKeyManager
from .smart_cache import SmartCache

logger = logging.getLogger(__name__)

class OddsAPIService:
    """
    Service unifié The Odds API
    - 1 requête = TOUS les matchs d'un sport
    - Multi-marchés: h2h, totals, spreads
    """
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    def __init__(self):
        self.key_manager = APIKeyManager()
        self.cache = SmartCache()
    
    def _request(self, endpoint: str, params: dict) -> Optional[dict]:
        """Requête API avec gestion clés"""
        
        # Obtenir clé
        key_info = self.key_manager.get_key('the_odds_api')
        if not key_info or not key_info['key_value']:
            logger.error("Pas de clé Odds API disponible")
            return None
        
        params['apiKey'] = key_info['key_value']
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                self.key_manager.increment_usage(key_info['key_id'], True)
                
                # Log remaining
                remaining = response.headers.get('x-requests-remaining', '?')
                logger.info(f"✅ Odds API: {endpoint} (remaining: {remaining})")
                
                return response.json()
            else:
                self.key_manager.increment_usage(key_info['key_id'], False)
                logger.error(f"❌ Odds API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Odds API exception: {e}")
            return None
    
    def get_sports(self) -> Optional[List]:
        """Liste des sports disponibles"""
        return self._request("sports", {})
    
    def get_odds(self, sport: str = "soccer_epl", 
                 markets: str = "h2h,totals",
                 regions: str = "eu") -> Optional[List]:
        """
        Cotes pour un sport (1 req = TOUS les matchs)
        
        Args:
            sport: ex "soccer_epl", "soccer_france_ligue_one"
            markets: "h2h", "totals", "spreads" ou combinés
            regions: "eu", "uk", "us"
        """
        # Vérifier cache (1h pour les cotes)
        cache_params = {'sport': sport, 'markets': markets, 'regions': regions}
        cached = self.cache.get('odds', cache_params)
        if cached:
            return cached
        
        params = {
            'regions': regions,
            'markets': markets,
            'oddsFormat': 'decimal'
        }
        
        data = self._request(f"sports/{sport}/odds", params)
        
        if data:
            self.cache.set('odds', cache_params, data, 'the_odds_api')
        
        return data
    
    def get_all_soccer_odds(self, markets: str = "h2h,totals") -> dict:
        """
        Récupère les cotes de TOUTES les ligues soccer configurées
        """
        leagues = [
            "soccer_epl",              # Premier League
            "soccer_france_ligue_one", # Ligue 1
            "soccer_germany_bundesliga",
            "soccer_italy_serie_a",
            "soccer_spain_la_liga",
            "soccer_uefa_champs_league",
            "soccer_uefa_europa_league",
        ]
        
        all_odds = {}
        for league in leagues:
            odds = self.get_odds(league, markets)
            if odds:
                all_odds[league] = odds
        
        return all_odds
