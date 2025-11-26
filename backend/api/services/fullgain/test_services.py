#!/usr/bin/env python3
"""
Test complet des services Full Gain 2.0
"""
import sys
import os

# Ajouter le chemin pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Charger les variables d'environnement depuis .env
from pathlib import Path
env_path = Path('/home/Mon_ps/backend/.env')
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Imports directs (pas relatifs)
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import requests
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# CLASSES INLINE POUR LE TEST
# ============================================================

class APIKeyManager:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', '127.0.0.1'),
            'port': 5432,
            'database': os.getenv('DB_NAME', 'monps_db'),
            'user': os.getenv('DB_USER', 'monps_user'),
            'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
        }
        self.keys = {
            'APIF_MAIN': os.getenv('API_FOOTBALL_KEY_MAIN'),
            'APIF_BACKUP': os.getenv('API_FOOTBALL_KEY_BACKUP'),
            'ODDS_MAIN': os.getenv('ODDS_API_KEY_MAIN'),
            'ODDS_BACKUP': os.getenv('ODDS_API_KEY_BACKUP'),
        }
    
    def _get_conn(self):
        return psycopg2.connect(**self.db_config)
    
    def get_key(self, service: str) -> Optional[Dict]:
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Reset daily quotas
            cur.execute("""
                UPDATE api_keys_manager SET quota_used = 0, quota_reset_at = NOW()
                WHERE quota_type = 'daily'
                AND (quota_reset_at IS NULL OR quota_reset_at::date < CURRENT_DATE)
            """)
            conn.commit()
            
            cur.execute("""
                SELECT key_id, quota_limit, quota_used, is_backup
                FROM api_keys_manager
                WHERE api_service = %s AND is_active = true AND quota_used < quota_limit
                ORDER BY is_backup ASC, priority ASC LIMIT 1
            """, (service,))
            
            row = cur.fetchone()
            if not row:
                return None
            
            return {
                'key_id': row['key_id'],
                'key_value': self.keys.get(row['key_id']),
                'remaining': row['quota_limit'] - row['quota_used']
            }
        finally:
            cur.close()
            conn.close()
    
    def increment_usage(self, key_id: str, success: bool = True):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            if success:
                cur.execute("""
                    UPDATE api_keys_manager
                    SET quota_used = quota_used + 1, total_requests = total_requests + 1, last_used_at = NOW()
                    WHERE key_id = %s
                """, (key_id,))
            else:
                cur.execute("""
                    UPDATE api_keys_manager
                    SET total_errors = total_errors + 1, last_used_at = NOW()
                    WHERE key_id = %s
                """, (key_id,))
            conn.commit()
        finally:
            cur.close()
            conn.close()
    
    def get_stats(self) -> List:
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("""
                SELECT key_id, api_service, quota_limit, quota_used,
                       (quota_limit - quota_used) as remaining, total_requests, is_backup
                FROM api_keys_manager ORDER BY api_service, is_backup
            """)
            return [dict(row) for row in cur.fetchall()]
        finally:
            cur.close()
            conn.close()


class SmartCache:
    TTL = {'team_stats': 24, 'h2h': 168, 'odds': 1, 'fixtures': 6, 'standings': 24}
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', '127.0.0.1'),
            'port': 5432,
            'database': os.getenv('DB_NAME', 'monps_db'),
            'user': os.getenv('DB_USER', 'monps_user'),
            'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
        }
    
    def _get_conn(self):
        return psycopg2.connect(**self.db_config)
    
    def _make_key(self, cache_type: str, params: dict) -> str:
        h = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
        return f"{cache_type}:{h}"
    
    def get(self, cache_type: str, params: dict) -> Optional[Any]:
        key = self._make_key(cache_type, params)
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT data FROM smart_cache WHERE cache_key = %s AND expires_at > NOW()", (key,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE smart_cache SET hit_count = hit_count + 1 WHERE cache_key = %s", (key,))
                conn.commit()
                logger.info(f"✅ Cache HIT: {key}")
                return row['data']
            logger.info(f"❌ Cache MISS: {key}")
            return None
        finally:
            cur.close()
            conn.close()
    
    def set(self, cache_type: str, params: dict, data: Any, api_service: str = None):
        key = self._make_key(cache_type, params)
        ttl = self.TTL.get(cache_type, 24)
        expires = datetime.now() + timedelta(hours=ttl)
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO smart_cache (cache_key, cache_type, data, ttl_hours, expires_at, api_service)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (cache_key) DO UPDATE SET
                    data = EXCLUDED.data, cached_at = NOW(), expires_at = EXCLUDED.expires_at, hit_count = 0
            """, (key, cache_type, Json(data), ttl, expires, api_service))
            conn.commit()
            logger.info(f"💾 Cache SET: {key} (TTL: {ttl}h)")
        finally:
            cur.close()
            conn.close()
    
    def get_stats(self) -> dict:
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("""
                SELECT cache_type, COUNT(*) as entries, SUM(hit_count) as hits
                FROM smart_cache WHERE expires_at > NOW() GROUP BY cache_type
            """)
            return {r['cache_type']: dict(r) for r in cur.fetchall()}
        finally:
            cur.close()
            conn.close()


class APIFootballService:
    BASE_URL = "https://v3.football.api-sports.io"
    
    def __init__(self):
        self.key_manager = APIKeyManager()
        self.cache = SmartCache()
    
    def _request(self, endpoint: str, params: dict, cache_type: str = None):
        if cache_type:
            cached = self.cache.get(cache_type, params)
            if cached:
                return cached
        
        key_info = self.key_manager.get_key('api_football')
        if not key_info or not key_info['key_value']:
            logger.error("Pas de clé API-Football")
            return None
        
        headers = {
            "x-rapidapi-host": "v3.football.api-sports.io",
            "x-rapidapi-key": key_info['key_value']
        }
        
        try:
            response = requests.get(f"{self.BASE_URL}/{endpoint}", headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                self.key_manager.increment_usage(key_info['key_id'], True)
                if cache_type and data.get('response'):
                    self.cache.set(cache_type, params, data, 'api_football')
                logger.info(f"✅ API-Football: {endpoint}")
                return data
            else:
                self.key_manager.increment_usage(key_info['key_id'], False)
                logger.error(f"❌ API-Football error: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return None
    
    def search_team(self, name: str):
        data = self._request("teams", {"search": name})
        return data.get('response', []) if data else None
    
    def get_team_statistics(self, team_id: int, league_id: int, season: int = 2023):
        params = {"team": team_id, "league": league_id, "season": season}
        data = self._request("teams/statistics", params, cache_type="team_stats")
        if data and data.get('response'):
            return self._parse_stats(data['response'])
        return None
    
    def _parse_stats(self, stats: dict) -> dict:
        fixtures = stats.get('fixtures', {})
        goals = stats.get('goals', {})
        
        played_home = fixtures.get('played', {}).get('home', 0) or 0
        played_away = fixtures.get('played', {}).get('away', 0) or 0
        played_total = played_home + played_away
        
        gf_home = goals.get('for', {}).get('total', {}).get('home', 0) or 0
        gf_away = goals.get('for', {}).get('total', {}).get('away', 0) or 0
        ga_home = goals.get('against', {}).get('total', {}).get('home', 0) or 0
        ga_away = goals.get('against', {}).get('total', {}).get('away', 0) or 0
        
        clean_home = stats.get('clean_sheet', {}).get('home', 0) or 0
        clean_away = stats.get('clean_sheet', {}).get('away', 0) or 0
        fts_home = stats.get('failed_to_score', {}).get('home', 0) or 0
        fts_away = stats.get('failed_to_score', {}).get('away', 0) or 0
        
        return {
            'form': stats.get('form', ''),
            'played': {'home': played_home, 'away': played_away, 'total': played_total},
            'goals_for': {'home': gf_home, 'away': gf_away, 'total': gf_home + gf_away},
            'goals_against': {'home': ga_home, 'away': ga_away, 'total': ga_home + ga_away},
            'avg_goals_scored': round((gf_home + gf_away) / max(played_total, 1), 2),
            'clean_sheets': {'home': clean_home, 'away': clean_away, 'total': clean_home + clean_away},
            'clean_sheet_pct': round((clean_home + clean_away) / max(played_total, 1) * 100, 1),
            'failed_to_score': {'home': fts_home, 'away': fts_away, 'total': fts_home + fts_away},
            'failed_to_score_pct': round((fts_home + fts_away) / max(played_total, 1) * 100, 1),
        }


class OddsAPIService:
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    def __init__(self):
        self.key_manager = APIKeyManager()
        self.cache = SmartCache()
    
    def get_odds(self, sport: str = "soccer_france_ligue_one", markets: str = "h2h,totals", regions: str = "eu"):
        cache_params = {'sport': sport, 'markets': markets, 'regions': regions}
        cached = self.cache.get('odds', cache_params)
        if cached:
            return cached
        
        key_info = self.key_manager.get_key('the_odds_api')
        if not key_info or not key_info['key_value']:
            logger.error("Pas de clé Odds API")
            return None
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/sports/{sport}/odds",
                params={'apiKey': key_info['key_value'], 'regions': regions, 'markets': markets, 'oddsFormat': 'decimal'},
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                self.key_manager.increment_usage(key_info['key_id'], True)
                self.cache.set('odds', cache_params, data, 'the_odds_api')
                remaining = response.headers.get('x-requests-remaining', '?')
                logger.info(f"✅ Odds API: {sport} (remaining: {remaining})")
                return data
            else:
                self.key_manager.increment_usage(key_info['key_id'], False)
                return None
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return None


# ============================================================
# TESTS
# ============================================================

def test_api_key_manager():
    print("\n" + "="*60)
    print("🔑 TEST API KEY MANAGER")
    print("="*60)
    
    manager = APIKeyManager()
    
    key_apif = manager.get_key('api_football')
    if key_apif:
        print(f"✅ API-Football: {key_apif['key_id']} (remaining: {key_apif['remaining']})")
    else:
        print("❌ API-Football: Pas de clé")
        return False
    
    key_odds = manager.get_key('the_odds_api')
    if key_odds:
        print(f"✅ Odds API: {key_odds['key_id']} (remaining: {key_odds['remaining']})")
    else:
        print("❌ Odds API: Pas de clé")
        return False
    
    print("\n📊 Stats clés:")
    for s in manager.get_stats():
        print(f"   {s['key_id']}: {s['quota_used']}/{s['quota_limit']}")
    
    return True

def test_smart_cache():
    print("\n" + "="*60)
    print("💾 TEST SMART CACHE")
    print("="*60)
    
    cache = SmartCache()
    test_data = {"test": "ok", "value": 42}
    cache.set("team_stats", {"team": "test123"}, test_data)
    
    result = cache.get("team_stats", {"team": "test123"})
    if result and result.get("test") == "ok":
        print("✅ Cache SET/GET: OK")
        return True
    print("❌ Cache FAILED")
    return False

def test_api_football():
    print("\n" + "="*60)
    print("⚽ TEST API-FOOTBALL")
    print("="*60)
    
    service = APIFootballService()
    
    print("🔍 Recherche 'Paris Saint Germain'...")
    teams = service.search_team("Paris Saint Germain")
    if teams:
        team = teams[0].get('team', {})
        team_id = team.get('id')
        print(f"✅ Trouvé: {team.get('name')} (ID: {team_id})")
        
        print(f"\n📊 Stats équipe...")
        stats = service.get_team_statistics(team_id, league_id=61, season=2023)
        if stats:
            print(f"   Forme: {stats.get('form')}")
            print(f"   Matchs: {stats.get('played', {}).get('total')}")
            print(f"   Buts: {stats.get('goals_for', {}).get('total')}")
            print(f"   Moyenne: {stats.get('avg_goals_scored')}")
            print(f"   Clean sheets: {stats.get('clean_sheet_pct')}%")
            return True
    
    print("❌ Échec")
    return False

def test_odds_api():
    print("\n" + "="*60)
    print("📈 TEST ODDS API")
    print("="*60)
    
    service = OddsAPIService()
    
    print("🎯 Récupération cotes Ligue 1...")
    odds = service.get_odds("soccer_france_ligue_one", "h2h,totals")
    
    if odds and len(odds) > 0:
        print(f"✅ {len(odds)} matchs trouvés")
        match = odds[0]
        print(f"   Ex: {match.get('home_team')} vs {match.get('away_team')}")
        return True
    
    print("❌ Pas de cotes")
    return False

def main():
    print("\n" + "="*60)
    print("�� FULL GAIN 2.0 - TESTS COMPLETS")
    print("="*60)
    
    results = {
        "API Key Manager": test_api_key_manager(),
        "Smart Cache": test_smart_cache(),
        "API-Football": test_api_football(),
        "Odds API": test_odds_api(),
    }
    
    print("\n" + "="*60)
    print("📋 RÉSUMÉ")
    print("="*60)
    
    all_ok = True
    for name, ok in results.items():
        print(f"   {name}: {'✅ PASS' if ok else '❌ FAIL'}")
        if not ok:
            all_ok = False
    
    print("\n" + "="*60)
    if all_ok:
        print("🎉 TOUS LES TESTS PASSÉS !")
    else:
        print("⚠️ Certains tests ont échoué")
    print("="*60)
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
