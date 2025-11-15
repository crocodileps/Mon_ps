"""
Collector Optimisé v2.0 - Structure DB correcte
"""
import os
import logging
import json
from datetime import datetime, timezone
from pathlib import Path
import requests
import psycopg2

# Configuration
API_KEY = os.getenv('ODDS_API_KEY')
API_BASE_URL = 'https://api.the-odds-api.com/v4'
SPORTS = os.getenv('SPORTS', 'soccer_epl,soccer_spain_la_liga,soccer_france_ligue_one').split(',')
MIN_COLLECT_INTERVAL = 7200
CACHE_DIR = Path('/home/Mon_ps/monitoring/collector/cache')
CACHE_DIR.mkdir(exist_ok=True)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'monps_db'),
    'user': os.getenv('DB_USER', 'monps_user'),
    'password': os.getenv('DB_PASSWORD')
}

log_file = f'/home/Mon_ps/monitoring/collector/logs/collector_{datetime.now().strftime("%Y%m%d")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class SmartCollector:
    def __init__(self):
        self.conn = None
        self.stats = {'api_calls': 0, 'skipped': 0, 'saved_odds': 0}
    
    def _get_last_collect_time(self, sport):
        cache_file = CACHE_DIR / f'{sport}_last.json'
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                return datetime.fromisoformat(data['timestamp'])
            except:
                return None
        return None
    
    def _save_last_collect_time(self, sport):
        cache_file = CACHE_DIR / f'{sport}_last.json'
        cache_file.write_text(json.dumps({
            'timestamp': datetime.now().isoformat(),
            'sport': sport
        }))
    
    def should_collect(self, sport):
        last = self._get_last_collect_time(sport)
        if not last:
            logger.info(f"🆕 {sport}: Première collecte")
            return True
        
        elapsed = (datetime.now() - last).total_seconds()
        if elapsed < MIN_COLLECT_INTERVAL:
            logger.info(f"⏭️  {sport}: SKIP ({elapsed/3600:.1f}h)")
            self.stats['skipped'] += 1
            return False
        
        logger.info(f"✅ {sport}: OK ({elapsed/3600:.1f}h)")
        return True
    
    def fetch_odds(self, sport):
        url = f"{API_BASE_URL}/sports/{sport}/odds"
        params = {
            'apiKey': API_KEY,
            'regions': 'eu',
            'markets': 'h2h',  # Seulement h2h pour la structure actuelle
            'oddsFormat': 'decimal'
        }
        
        try:
            logger.info(f"🌐 API CALL → {sport}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            self.stats['api_calls'] += 1
            
            remaining = response.headers.get('x-requests-remaining', '?')
            logger.info(f"📊 Quota restant: {remaining}")
            return response.json()
        except Exception as e:
            logger.error(f"❌ {sport}: {e}")
            return []
    
    def save_to_db(self, sport, matches):
        if not matches:
            return 0
        
        cursor = self.conn.cursor()
        now = datetime.now(timezone.utc)
        saved = 0
        
        for match in matches:
            match_id = match['id']
            home = match['home_team']
            away = match['away_team']
            commence = match['commence_time']
            match_time = datetime.fromisoformat(commence.replace('Z', '+00:00'))
            
            # Skip matchs passés
            if match_time < now:
                continue
            
            # Traiter chaque bookmaker
            for bookie in match.get('bookmakers', []):
                bookmaker = bookie['title']
                
                # Extraire home/away/draw odds
                home_odds = None
                away_odds = None
                draw_odds = None
                
                for market in bookie.get('markets', []):
                    if market['key'] == 'h2h':
                        for outcome in market.get('outcomes', []):
                            if outcome['name'] == home:
                                home_odds = float(outcome['price'])
                            elif outcome['name'] == away:
                                away_odds = float(outcome['price'])
                            elif outcome['name'] == 'Draw':
                                draw_odds = float(outcome['price'])
                
                # Insérer
                if home_odds and away_odds:
                    try:
                        cursor.execute("""
                            INSERT INTO odds_history 
                            (match_id, sport, home_team, away_team, commence_time,
                             bookmaker, home_odds, away_odds, draw_odds, collected_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (match_id, bookmaker, collected_at) DO NOTHING
                        """, (
                            match_id, sport, home, away, commence,
                            bookmaker, home_odds, away_odds, draw_odds, now
                        ))
                        saved += 1
                    except Exception as e:
                        logger.error(f"❌ Erreur INSERT: {e}")
                        continue
        
        self.conn.commit()
        self.stats['saved_odds'] = saved
        logger.info(f"💾 {saved} cotes ({len(matches)} matchs)")
        return saved
    
    def run(self):
        logger.info("="*70)
        logger.info("🚀 COLLECTOR OPTIMISÉ v2.0")
        logger.info("="*70)
        
        self.conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ Connecté PostgreSQL")
        
        for sport in SPORTS:
            if not self.should_collect(sport):
                continue
            data = self.fetch_odds(sport)
            self.save_to_db(sport, data)
            self._save_last_collect_time(sport)
        
        self.conn.close()
        logger.info("="*70)
        logger.info(f"📊 API: {self.stats['api_calls']} | Saved: {self.stats['saved_odds']}")
        logger.info("="*70)

if __name__ == '__main__':
    collector = SmartCollector()
    collector.run()
