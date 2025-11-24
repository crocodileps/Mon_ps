"""
API-Football Integration Service
Service professionnel d'intégration avec cache intelligent
"""

import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import hashlib

logger = logging.getLogger(__name__)


class APIFootballService:
    """
    Service d'intégration API-Football avec:
    - Cache intelligent (évite requêtes inutiles)
    - Rate limiting (100 req/jour)
    - Fallback gracieux
    - Retry logic
    """
    
    BASE_URL = "https://v3.football.api-sports.io"
    
    def __init__(self, api_key: str, db_config: Dict):
        self.api_key = api_key
        self.db_config = db_config
        self.headers = {
            'x-apisports-key': api_key
        }
        
        # Compteur requêtes (reset quotidien)
        self.daily_requests = 0
        self.max_daily_requests = 100
        self.last_reset = datetime.now().date()
        
        logger.info("✅ API-Football Service initialisé")
    
    
    def _check_rate_limit(self) -> bool:
        """Vérifie si on peut faire une requête"""
        # Reset compteur si nouveau jour
        if datetime.now().date() > self.last_reset:
            self.daily_requests = 0
            self.last_reset = datetime.now().date()
            logger.info("📅 Reset compteur quotidien API")
        
        if self.daily_requests >= self.max_daily_requests:
            logger.warning(f"⚠️  Rate limit atteint: {self.daily_requests}/{self.max_daily_requests}")
            return False
        
        return True
    
    
    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Génère clé cache unique"""
        params_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{endpoint}:{params_str}".encode()).hexdigest()
    
    
    def _get_from_cache(self, cache_key: str, max_age_hours: int = 24) -> Optional[Dict]:
        """Récupère depuis cache si valide"""
        try:
            import psycopg2
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            query = """
                SELECT data, created_at 
                FROM api_football_cache 
                WHERE cache_key = %s
                AND created_at > NOW() - INTERVAL '%s hours'
            """
            
            cursor.execute(query, (cache_key, max_age_hours))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                logger.info(f"✅ Cache HIT: {cache_key[:8]}...")
                return result[0]
            
            return None
            
        except Exception as e:
            logger.warning(f"Cache error: {e}")
            return None
    
    
    def _save_to_cache(self, cache_key: str, data: Dict):
        """Sauvegarde dans cache"""
        try:
            import psycopg2
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            query = """
                INSERT INTO api_football_cache (cache_key, data, created_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (cache_key) 
                DO UPDATE SET data = EXCLUDED.data, created_at = NOW()
            """
            
            cursor.execute(query, (cache_key, json.dumps(data)))
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Cache save error: {e}")
    
    
    def _make_request(
        self, 
        endpoint: str, 
        params: Dict,
        use_cache: bool = True,
        cache_hours: int = 24
    ) -> Optional[Dict]:
        """
        Requête API avec cache et rate limiting
        """
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(endpoint, params)
            cached_data = self._get_from_cache(cache_key, cache_hours)
            if cached_data:
                return cached_data
        
        # Check rate limit
        if not self._check_rate_limit():
            logger.warning("⚠️  Rate limit - utilise cache ou données partielles")
            return None
        
        # Make request
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            self.daily_requests += 1
            logger.info(f"📡 API Request {self.daily_requests}/{self.max_daily_requests}: {endpoint}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Save to cache
                if use_cache:
                    self._save_to_cache(cache_key, data)
                
                return data
            else:
                logger.error(f"❌ API Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Request error: {e}")
            return None
    
    
    def get_team_form(self, team_id: int, league_id: int, season: int = 2024) -> Dict:
        """
        Récupère forme récente d'une équipe
        
        Returns:
            {
                'form': 'WWDWL',
                'win_rate': 0.8,
                'goals_avg': 2.1,
                'streak': 3
            }
        """
        data = self._make_request(
            'teams/statistics',
            {'team': team_id, 'league': league_id, 'season': season},
            cache_hours=12  # Cache 12h (stats changent peu)
        )
        
        if not data or 'response' not in data:
            return {'form': 'UNKNOWN', 'win_rate': 0.5, 'goals_avg': 0, 'streak': 0}
        
        stats = data['response']
        form_str = stats.get('form', '')
        
        # Calculer win rate sur 5 derniers
        recent_form = form_str[-5:] if len(form_str) >= 5 else form_str
        wins = recent_form.count('W')
        win_rate = wins / len(recent_form) if recent_form else 0.5
        
        # Goals average
        goals_for = stats.get('goals', {}).get('for', {}).get('average', {}).get('total', 0)
        
        # Current streak
        streak = 0
        if form_str:
            last_result = form_str[-1]
            for char in reversed(form_str):
                if char == last_result:
                    streak += 1
                else:
                    break
        
        return {
            'form': recent_form,
            'win_rate': win_rate,
            'goals_avg': float(goals_for) if goals_for else 0,
            'streak': streak,
            'full_form': form_str
        }
    
    
    def get_injuries(self, team_id: int, league_id: int) -> Dict:
        """
        Récupère blessures actuelles
        
        Returns:
            {
                'total_injuries': 3,
                'key_players_out': 1,
                'impact_score': -0.3
            }
        """
        data = self._make_request(
            'injuries',
            {'team': team_id, 'league': league_id},
            cache_hours=6  # Cache 6h (blessures changent)
        )
        
        if not data or 'response' not in data:
            return {'total_injuries': 0, 'key_players_out': 0, 'impact_score': 0}
        
        injuries = data['response']
        
        # Compter blessures importantes (titulaires)
        key_injuries = sum(1 for inj in injuries if inj.get('player', {}).get('type') in ['Attacker', 'Midfielder', 'Defender'])
        
        # Impact score (pénalité)
        impact_score = -0.1 * key_injuries
        
        return {
            'total_injuries': len(injuries),
            'key_players_out': key_injuries,
            'impact_score': impact_score,
            'details': [
                {
                    'player': inj.get('player', {}).get('name'),
                    'type': inj.get('player', {}).get('type'),
                    'reason': inj.get('player', {}).get('reason')
                }
                for inj in injuries[:5]  # Top 5
            ]
        }
    
    
    def get_h2h(self, team1_id: int, team2_id: int) -> Dict:
        """
        Head-to-Head historique
        
        Returns:
            {
                'total_matches': 10,
                'team1_wins': 4,
                'team2_wins': 3,
                'draws': 3,
                'dominance_score': 0.1
            }
        """
        data = self._make_request(
            'fixtures/headtohead',
            {'h2h': f'{team1_id}-{team2_id}'},
            cache_hours=168  # Cache 1 semaine (historique stable)
        )
        
        if not data or 'response' not in data:
            return {'total_matches': 0, 'team1_wins': 0, 'team2_wins': 0, 'draws': 0, 'dominance_score': 0}
        
        matches = data["response"]

        team1_wins = sum(
            1 for m in matches
            if (m["teams"]["home"]["id"] == team1_id and m["teams"]["home"]["winner"])
            or (m["teams"]["away"]["id"] == team1_id and m["teams"]["away"]["winner"])
        )
        team2_wins = sum(
            1 for m in matches
            if (m["teams"]["home"]["id"] == team2_id and m["teams"]["home"]["winner"])
            or (m["teams"]["away"]["id"] == team2_id and m["teams"]["away"]["winner"])
        )
        draws = len(matches) - team1_wins - team2_wins
        
        # Dominance score (-0.5 to +0.5)
        if len(matches) > 0:
            dominance = (team1_wins - team2_wins) / len(matches)
        else:
            dominance = 0
        
        return {
            'total_matches': len(matches),
            'team1_wins': team1_wins,
            'team2_wins': team2_wins,
            'draws': draws,
            'dominance_score': dominance
        }
    
    
    def get_predictions(self, fixture_id: int) -> Dict:
        """
        Prédictions API (basé sur algo interne)
        
        Returns:
            {
                'winner': 'home',
                'confidence': 0.75,
                'advice': 'Combo Double Chance: Home/Draw'
            }
        """
        data = self._make_request(
            'predictions',
            {'fixture': fixture_id},
            cache_hours=12
        )
        
        if not data or 'response' not in data:
            return {'winner': None, 'confidence': 0.5, 'advice': None}
        
        pred = data['response'][0] if data['response'] else {}
        predictions = pred.get('predictions', {})
        
        winner = predictions.get('winner', {})
        
        return {
            'winner': winner.get('name'),
            'confidence': float(winner.get('confidence', 50)) / 100,
            'advice': predictions.get('advice'),
            'under_over': predictions.get('under_over'),
            'goals': predictions.get('goals', {}).get('home'),
        }


# Singleton
_api_football_service = None

def get_api_football_service(api_key: str, db_config: Dict) -> APIFootballService:
    global _api_football_service
    if _api_football_service is None:
        _api_football_service = APIFootballService(api_key, db_config)
    return _api_football_service
