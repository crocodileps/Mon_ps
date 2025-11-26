"""
API Football Service - Toutes les fonctions en 1 service
Documentation: https://www.api-football.com/documentation-v3
"""
import requests
from typing import Optional, Dict, List
import logging
from .api_key_manager import APIKeyManager
from .smart_cache import SmartCache

logger = logging.getLogger(__name__)

class APIFootballService:
    """
    Service unifié API-Football
    - Cache intelligent intégré
    - Gestion automatique des clés
    - 1 requête = données complètes
    """
    
    BASE_URL = "https://v3.football.api-sports.io"
    
    def __init__(self):
        self.key_manager = APIKeyManager()
        self.cache = SmartCache()
    
    def _request(self, endpoint: str, params: dict, cache_type: str = None) -> Optional[dict]:
        """Requête avec cache et gestion clés"""
        
        # 1. Vérifier cache
        if cache_type:
            cached = self.cache.get(cache_type, params)
            if cached:
                return cached
        
        # 2. Obtenir clé API
        key_info = self.key_manager.get_key('api_football')
        if not key_info or not key_info['key_value']:
            logger.error("Pas de clé API-Football disponible")
            return None
        
        # 3. Faire requête
        headers = {
            "x-rapidapi-host": "v3.football.api-sports.io",
            "x-rapidapi-key": key_info['key_value']
        }
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                headers=headers,
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                self.key_manager.increment_usage(key_info['key_id'], True)
                
                # 4. Stocker en cache
                if cache_type and data.get('response'):
                    self.cache.set(cache_type, params, data, 'api_football')
                
                logger.info(f"✅ API-Football: {endpoint} (remaining: {key_info['remaining']-1})")
                return data
            else:
                self.key_manager.increment_usage(key_info['key_id'], False)
                logger.error(f"❌ API-Football error: {response.status_code}")
                return None
                
        except Exception as e:
            self.key_manager.increment_usage(key_info['key_id'], False)
            logger.error(f"❌ API-Football exception: {e}")
            return None
    
    def get_team_statistics(self, team_id: int, league_id: int, season: int = 2023) -> Optional[dict]:
        """
        Stats complètes d'une équipe (1 requête = TOUT)
        Inclut: forme, buts, clean sheets, failed to score, etc.
        """
        params = {"team": team_id, "league": league_id, "season": season}
        data = self._request("teams/statistics", params, cache_type="team_stats")
        
        if data and data.get('response'):
            return self._parse_team_stats(data['response'])
        return None
    
    def get_head_to_head(self, team1_id: int, team2_id: int, last: int = 10) -> Optional[dict]:
        """
        Confrontations directes (H2H)
        """
        params = {"h2h": f"{team1_id}-{team2_id}", "last": last}
        data = self._request("fixtures/headtohead", params, cache_type="h2h")
        
        if data and data.get('response'):
            return self._parse_h2h(data['response'], team1_id, team2_id)
        return None
    
    def get_fixtures(self, league_id: int = None, team_id: int = None, 
                     date: str = None, season: int = 2023) -> Optional[List]:
        """
        Matchs (à venir ou passés)
        """
        params = {"season": season}
        if league_id:
            params["league"] = league_id
        if team_id:
            params["team"] = team_id
        if date:
            params["date"] = date
        
        data = self._request("fixtures", params, cache_type="fixtures")
        return data.get('response', []) if data else None
    
    def get_standings(self, league_id: int, season: int = 2023) -> Optional[List]:
        """Classement d'une ligue"""
        params = {"league": league_id, "season": season}
        data = self._request("standings", params, cache_type="standings")
        
        if data and data.get('response'):
            return data['response'][0].get('league', {}).get('standings', [])
        return None
    
    def get_injuries(self, team_id: int = None, fixture_id: int = None) -> Optional[List]:
        """Blessures et suspensions"""
        params = {}
        if team_id:
            params["team"] = team_id
        if fixture_id:
            params["fixture"] = fixture_id
        
        data = self._request("injuries", params, cache_type="injuries")
        return data.get('response', []) if data else None
    
    def search_team(self, name: str) -> Optional[List]:
        """Rechercher une équipe par nom"""
        params = {"search": name}
        data = self._request("teams", params)
        return data.get('response', []) if data else None
    
    def _parse_team_stats(self, stats: dict) -> dict:
        """Parse les stats brutes en format utilisable"""
        fixtures = stats.get('fixtures', {})
        goals = stats.get('goals', {})
        
        # Calculer totaux
        played_home = fixtures.get('played', {}).get('home', 0) or 0
        played_away = fixtures.get('played', {}).get('away', 0) or 0
        played_total = played_home + played_away
        
        wins_home = fixtures.get('wins', {}).get('home', 0) or 0
        wins_away = fixtures.get('wins', {}).get('away', 0) or 0
        draws_home = fixtures.get('draws', {}).get('home', 0) or 0
        draws_away = fixtures.get('draws', {}).get('away', 0) or 0
        losses_home = fixtures.get('loses', {}).get('home', 0) or 0
        losses_away = fixtures.get('loses', {}).get('away', 0) or 0
        
        gf_home = goals.get('for', {}).get('total', {}).get('home', 0) or 0
        gf_away = goals.get('for', {}).get('total', {}).get('away', 0) or 0
        ga_home = goals.get('against', {}).get('total', {}).get('home', 0) or 0
        ga_away = goals.get('against', {}).get('total', {}).get('away', 0) or 0
        
        clean_home = stats.get('clean_sheet', {}).get('home', 0) or 0
        clean_away = stats.get('clean_sheet', {}).get('away', 0) or 0
        fts_home = stats.get('failed_to_score', {}).get('home', 0) or 0
        fts_away = stats.get('failed_to_score', {}).get('away', 0) or 0
        
        return {
            'team': stats.get('team', {}),
            'league': stats.get('league', {}),
            'form': stats.get('form', ''),
            
            # Matchs
            'played': {'home': played_home, 'away': played_away, 'total': played_total},
            'wins': {'home': wins_home, 'away': wins_away, 'total': wins_home + wins_away},
            'draws': {'home': draws_home, 'away': draws_away, 'total': draws_home + draws_away},
            'losses': {'home': losses_home, 'away': losses_away, 'total': losses_home + losses_away},
            
            # Buts
            'goals_for': {'home': gf_home, 'away': gf_away, 'total': gf_home + gf_away},
            'goals_against': {'home': ga_home, 'away': ga_away, 'total': ga_home + ga_away},
            
            # Moyennes
            'avg_goals_scored': round((gf_home + gf_away) / max(played_total, 1), 2),
            'avg_goals_conceded': round((ga_home + ga_away) / max(played_total, 1), 2),
            'avg_goals_scored_home': round(gf_home / max(played_home, 1), 2),
            'avg_goals_scored_away': round(gf_away / max(played_away, 1), 2),
            
            # Clean Sheets & FTS
            'clean_sheets': {'home': clean_home, 'away': clean_away, 'total': clean_home + clean_away},
            'failed_to_score': {'home': fts_home, 'away': fts_away, 'total': fts_home + fts_away},
            
            # Pourcentages
            'clean_sheet_pct': round((clean_home + clean_away) / max(played_total, 1) * 100, 1),
            'failed_to_score_pct': round((fts_home + fts_away) / max(played_total, 1) * 100, 1),
            
            # Données brutes
            'raw': stats
        }
    
    def _parse_h2h(self, matches: list, team1_id: int, team2_id: int) -> dict:
        """Parse les données H2H"""
        team1_wins = 0
        team2_wins = 0
        draws = 0
        team1_goals = 0
        team2_goals = 0
        btts_count = 0
        over_25_count = 0
        
        history = []
        
        for match in matches:
            home = match['teams']['home']
            away = match['teams']['away']
            goals = match['goals']
            
            home_goals = goals['home'] or 0
            away_goals = goals['away'] or 0
            total_goals = home_goals + away_goals
            
            # Identifier qui est team1/team2
            if home['id'] == team1_id:
                t1_goals = home_goals
                t2_goals = away_goals
            else:
                t1_goals = away_goals
                t2_goals = home_goals
            
            team1_goals += t1_goals
            team2_goals += t2_goals
            
            # Résultat
            if t1_goals > t2_goals:
                team1_wins += 1
                winner = 'team_a'
            elif t2_goals > t1_goals:
                team2_wins += 1
                winner = 'team_b'
            else:
                draws += 1
                winner = 'draw'
            
            # BTTS
            if home_goals > 0 and away_goals > 0:
                btts_count += 1
            
            # Over 2.5
            if total_goals > 2:
                over_25_count += 1
            
            history.append({
                'date': match['fixture']['date'][:10],
                'home': home['name'],
                'away': away['name'],
                'score': f"{home_goals}-{away_goals}",
                'winner': winner
            })
        
        total = len(matches)
        
        return {
            'total_matches': total,
            'team_a_wins': team1_wins,
            'team_b_wins': team2_wins,
            'draws': draws,
            'team_a_goals': team1_goals,
            'team_b_goals': team2_goals,
            'avg_goals': round((team1_goals + team2_goals) / max(total, 1), 2),
            'btts_count': btts_count,
            'btts_pct': round(btts_count / max(total, 1) * 100, 1),
            'over_25_count': over_25_count,
            'over_25_pct': round(over_25_count / max(total, 1) * 100, 1),
            'history': history
        }
