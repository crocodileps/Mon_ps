"""
Football-Data.org Service - Matchs saison actuelle GRATUIT
Documentation: https://www.football-data.org/documentation/v4
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class FootballDataService:
    """
    Service Football-Data.org
    - 12 ligues gratuites
    - Saison actuelle 2024-2025
    - 10 req/minute
    """
    
    BASE_URL = "https://api.football-data.org/v4"
    
    # Ligues disponibles gratuitement
    LEAGUES = {
        'PL': 'Premier League',
        'FL1': 'Ligue 1',
        'BL1': 'Bundesliga', 
        'SA': 'Serie A',
        'PD': 'La Liga',
        'CL': 'Champions League',
        'ELC': 'Championship',
        'DED': 'Eredivisie',
        'PPL': 'Primeira Liga',
        'BSA': 'Brasileiro Série A',
        'WC': 'World Cup',
        'EC': 'Euro'
    }
    
    def __init__(self):
        self.api_key = os.getenv('FOOTBALL_DATA_API_KEY')
        self.db_config = {
            'host': os.getenv('DB_HOST', '127.0.0.1'),
            'port': 5432,
            'database': os.getenv('DB_NAME', 'monps_db'),
            'user': os.getenv('DB_USER', 'monps_user'),
            'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
        }
        
        if not self.api_key:
            logger.error("FOOTBALL_DATA_API_KEY non configurée!")
    
    def _get_conn(self):
        return psycopg2.connect(**self.db_config)
    
    def _request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Requête API avec gestion erreurs"""
        if not self.api_key:
            logger.error("Pas de clé API Football-Data")
            return None
        
        headers = {"X-Auth-Token": self.api_key}
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                headers=headers,
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Football-Data: {endpoint}")
                return response.json()
            elif response.status_code == 429:
                logger.warning("⚠️ Rate limit - attendre 60s")
                return None
            else:
                logger.error(f"❌ Football-Data error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return None
    
    def get_matches(self, league_code: str = None, 
                    date_from: str = None, date_to: str = None,
                    status: str = "FINISHED") -> Optional[List]:
        """
        Récupère les matchs
        
        Args:
            league_code: PL, FL1, BL1, SA, PD, CL, etc.
            date_from: YYYY-MM-DD
            date_to: YYYY-MM-DD
            status: SCHEDULED, LIVE, FINISHED
        """
        params = {}
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to
        if status:
            params['status'] = status
        
        if league_code:
            endpoint = f"competitions/{league_code}/matches"
        else:
            endpoint = "matches"
        
        data = self._request(endpoint, params)
        
        if data and 'matches' in data:
            return data['matches']
        return None
    
    def get_standings(self, league_code: str) -> Optional[List]:
        """Classement d'une ligue"""
        data = self._request(f"competitions/{league_code}/standings")
        
        if data and 'standings' in data:
            return data['standings']
        return None
    
    def get_team(self, team_id: int) -> Optional[dict]:
        """Infos d'une équipe"""
        return self._request(f"teams/{team_id}")
    
    def import_recent_matches(self, days: int = 30) -> dict:
        """
        Importe les matchs récents dans match_results
        
        Returns:
            {'imported': X, 'updated': Y, 'errors': Z}
        """
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        date_to = datetime.now().strftime('%Y-%m-%d')
        
        stats = {'imported': 0, 'updated': 0, 'errors': 0, 'leagues': []}
        
        conn = self._get_conn()
        cur = conn.cursor()
        
        # Parcourir les ligues principales
        main_leagues = ['PL', 'FL1', 'BL1', 'SA', 'PD', 'CL']
        
        for league_code in main_leagues:
            logger.info(f"📥 Import {self.LEAGUES.get(league_code, league_code)}...")
            
            matches = self.get_matches(
                league_code=league_code,
                date_from=date_from,
                date_to=date_to,
                status='FINISHED'
            )
            
            if not matches:
                continue
            
            league_count = 0
            
            for match in matches:
                try:
                    match_id = f"fd_{match['id']}"
                    home_team = match['homeTeam']['name']
                    away_team = match['awayTeam']['name']
                    score_home = match['score']['fullTime']['home']
                    score_away = match['score']['fullTime']['away']
                    commence_time = match['utcDate']
                    
                    # Déterminer le résultat
                    if score_home > score_away:
                        outcome = 'home'
                    elif score_away > score_home:
                        outcome = 'away'
                    else:
                        outcome = 'draw'
                    
                    # Insert ou Update
                    cur.execute("""
                        INSERT INTO match_results (
                            match_id, home_team, away_team, sport, league,
                            commence_time, score_home, score_away, outcome, is_finished
                        ) VALUES (%s, %s, %s, 'soccer', %s, %s, %s, %s, %s, true)
                        ON CONFLICT (match_id) DO UPDATE SET
                            score_home = EXCLUDED.score_home,
                            score_away = EXCLUDED.score_away,
                            outcome = EXCLUDED.outcome,
                            is_finished = true,
                            last_updated = NOW()
                    """, (
                        match_id, home_team, away_team,
                        self.LEAGUES.get(league_code, league_code),
                        commence_time, score_home, score_away, outcome
                    ))
                    
                    if cur.rowcount > 0:
                        league_count += 1
                        stats['imported'] += 1
                        
                except Exception as e:
                    logger.error(f"Erreur match {match.get('id')}: {e}")
                    stats['errors'] += 1
            
            conn.commit()
            stats['leagues'].append({
                'code': league_code,
                'name': self.LEAGUES.get(league_code),
                'matches': league_count
            })
            
            logger.info(f"   ✅ {league_count} matchs importés")
        
        cur.close()
        conn.close()
        
        return stats
    
    def refresh_team_statistics(self) -> int:
        """
        Recalcule les stats équipes après import
        """
        conn = self._get_conn()
        cur = conn.cursor()
        
        try:
            # Même requête que précédemment pour recalculer
            cur.execute("""
                INSERT INTO team_statistics_live (
                    team_name, matches_played, wins, draws, losses, goals_for, goals_against,
                    btts_total, btts_pct, over_25, over_25_pct, avg_goals_scored, avg_goals_conceded, form
                )
                SELECT 
                    team,
                    COUNT(*) as mp,
                    SUM(CASE WHEN result = 'W' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as draws,
                    SUM(CASE WHEN result = 'L' THEN 1 ELSE 0 END) as losses,
                    SUM(gf) as goals_for,
                    SUM(ga) as goals_against,
                    SUM(CASE WHEN btts THEN 1 ELSE 0 END) as btts_total,
                    ROUND(SUM(CASE WHEN btts THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as btts_pct,
                    SUM(CASE WHEN total_goals > 2 THEN 1 ELSE 0 END) as over_25,
                    ROUND(SUM(CASE WHEN total_goals > 2 THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as over_25_pct,
                    ROUND(AVG(gf), 2) as avg_gs,
                    ROUND(AVG(ga), 2) as avg_gc,
                    LEFT(string_agg(result, '' ORDER BY match_date DESC), 5) as form
                FROM (
                    SELECT home_team as team, score_home as gf, score_away as ga,
                           score_home + score_away as total_goals,
                           score_home > 0 AND score_away > 0 as btts,
                           CASE WHEN score_home > score_away THEN 'W' 
                                WHEN score_home = score_away THEN 'D' ELSE 'L' END as result,
                           commence_time as match_date
                    FROM match_results WHERE is_finished = true AND score_home IS NOT NULL
                    UNION ALL
                    SELECT away_team as team, score_away as gf, score_home as ga,
                           score_home + score_away as total_goals,
                           score_home > 0 AND score_away > 0 as btts,
                           CASE WHEN score_away > score_home THEN 'W'
                                WHEN score_home = score_away THEN 'D' ELSE 'L' END as result,
                           commence_time as match_date
                    FROM match_results WHERE is_finished = true AND score_home IS NOT NULL
                ) all_matches
                GROUP BY team
                ON CONFLICT (team_name) DO UPDATE SET
                    matches_played = EXCLUDED.matches_played,
                    wins = EXCLUDED.wins, draws = EXCLUDED.draws, losses = EXCLUDED.losses,
                    goals_for = EXCLUDED.goals_for, goals_against = EXCLUDED.goals_against,
                    btts_total = EXCLUDED.btts_total, btts_pct = EXCLUDED.btts_pct,
                    over_25 = EXCLUDED.over_25, over_25_pct = EXCLUDED.over_25_pct,
                    avg_goals_scored = EXCLUDED.avg_goals_scored,
                    avg_goals_conceded = EXCLUDED.avg_goals_conceded,
                    form = EXCLUDED.form, updated_at = NOW()
            """)
            
            count = cur.rowcount
            conn.commit()
            logger.info(f"✅ {count} équipes mises à jour")
            return count
            
        finally:
            cur.close()
            conn.close()
