"""
Collector Optimisé v3.0 - Support h2h + totals
Collecte les marchés 1X2 (h2h) ET Over/Under (totals)
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
MIN_COLLECT_INTERVAL = 7200  # 2 heures minimum entre collectes
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
        self.stats = {
            'api_calls': 0,
            'skipped': 0,
            'saved_h2h': 0,
            'saved_totals': 0
        }

    def _get_last_collect_time(self, sport):
        cache_file = CACHE_DIR / f'{sport}_last.json'
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                return datetime.fromisoformat(data['timestamp'])
            except Exception:
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
            logger.info(f"⏭️  {sport}: SKIP ({elapsed/3600:.1f}h depuis dernière collecte)")
            self.stats['skipped'] += 1
            return False

        logger.info(f"✅ {sport}: OK pour collecte ({elapsed/3600:.1f}h écoulées)")
        return True

    def fetch_odds(self, sport):
        """Récupère les cotes h2h ET totals depuis The Odds API"""
        url = f"{API_BASE_URL}/sports/{sport}/odds"
        params = {
            'apiKey': API_KEY,
            'regions': 'eu',
            'markets': 'h2h,totals',  # MODIFIÉ: Ajout des totals
            'oddsFormat': 'decimal'
        }

        try:
            logger.info(f"🌐 API CALL → {sport} (h2h + totals)")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            self.stats['api_calls'] += 1

            remaining = response.headers.get('x-requests-remaining', '?')
            used = response.headers.get('x-requests-used', '?')
            logger.info(f"📊 Quota API: {remaining} restant / {used} utilisé")

            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"❌ {sport}: Timeout API (30s)")
            return []
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ {sport}: Erreur HTTP {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"❌ {sport}: {e}")
            return []

    def save_h2h_to_db(self, sport, matches, now):
        """Sauvegarde les cotes 1X2 dans odds_history (existant)"""
        cursor = self.conn.cursor()
        saved = 0

        for match in matches:
            match_id = match['id']
            home = match['home_team']
            away = match['away_team']
            commence = match['commence_time']

            # Vérifier si match pas encore passé
            match_time = datetime.fromisoformat(commence.replace('Z', '+00:00'))
            if match_time < now:
                continue

            for bookie in match.get('bookmakers', []):
                bookmaker = bookie['title']
                home_odds = None
                away_odds = None
                draw_odds = None

                # Extraire les cotes h2h
                for market in bookie.get('markets', []):
                    if market['key'] == 'h2h':
                        for outcome in market.get('outcomes', []):
                            if outcome['name'] == home:
                                home_odds = float(outcome['price'])
                            elif outcome['name'] == away:
                                away_odds = float(outcome['price'])
                            elif outcome['name'] == 'Draw':
                                draw_odds = float(outcome['price'])

                # Insérer si on a les cotes
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
                        logger.error(f"❌ H2H INSERT error: {e}")
                        continue

        self.conn.commit()
        return saved

    def save_totals_to_db(self, sport, matches, now):
        """Sauvegarde les cotes Over/Under dans odds_totals (nouvelle table)"""
        cursor = self.conn.cursor()
        saved = 0

        for match in matches:
            match_id = match['id']
            home = match['home_team']
            away = match['away_team']
            commence = match['commence_time']

            # Vérifier si match pas encore passé
            match_time = datetime.fromisoformat(commence.replace('Z', '+00:00'))
            if match_time < now:
                continue

            for bookie in match.get('bookmakers', []):
                bookmaker = bookie['title']

                # Extraire les cotes totals (Over/Under)
                for market in bookie.get('markets', []):
                    if market['key'] == 'totals':
                        over_odds = None
                        under_odds = None
                        line = None

                        for outcome in market.get('outcomes', []):
                            if outcome['name'] == 'Over':
                                over_odds = float(outcome['price'])
                                line = float(outcome.get('point', 0))
                            elif outcome['name'] == 'Under':
                                under_odds = float(outcome['price'])
                                if line is None:
                                    line = float(outcome.get('point', 0))

                        # Insérer si on a toutes les données
                        if over_odds and under_odds and line:
                            try:
                                cursor.execute("""
                                    INSERT INTO odds_totals
                                    (match_id, sport, home_team, away_team, commence_time,
                                     bookmaker, line, over_odds, under_odds, collected_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (match_id, bookmaker, line, collected_at) DO NOTHING
                                """, (
                                    match_id, sport, home, away, commence,
                                    bookmaker, line, over_odds, under_odds, now
                                ))
                                saved += 1
                            except Exception as e:
                                logger.error(f"❌ TOTALS INSERT error: {e}")
                                continue

        self.conn.commit()
        return saved

    def save_to_db(self, sport, matches):
        """Sauvegarde les données dans les deux tables"""
        if not matches:
            return 0, 0

        now = datetime.now(timezone.utc)

        # Sauvegarder h2h (1X2)
        saved_h2h = self.save_h2h_to_db(sport, matches, now)
        self.stats['saved_h2h'] += saved_h2h

        # Sauvegarder totals (Over/Under)
        saved_totals = self.save_totals_to_db(sport, matches, now)
        self.stats['saved_totals'] += saved_totals

        logger.info(f"💾 {sport}: {saved_h2h} h2h + {saved_totals} totals ({len(matches)} matchs)")

        return saved_h2h, saved_totals

    def run(self):
        logger.info("=" * 70)
        logger.info("🚀 COLLECTOR OPTIMISÉ v3.0 - H2H + TOTALS")
        logger.info("=" * 70)

        # Connexion DB
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("✅ Connecté à PostgreSQL")
        except Exception as e:
            logger.error(f"❌ Impossible de se connecter à PostgreSQL: {e}")
            return

        # Collecter pour chaque sport
        for sport in SPORTS:
            if not self.should_collect(sport):
                continue

            data = self.fetch_odds(sport)
            if data:
                self.save_to_db(sport, data)
                self._save_last_collect_time(sport)
            else:
                logger.warning(f"⚠️ {sport}: Aucune donnée reçue")

        # Fermer connexion
        self.conn.close()

        # Résumé final
        logger.info("=" * 70)
        logger.info("📊 RÉSUMÉ COLLECTE:")
        logger.info(f"   • Appels API: {self.stats['api_calls']}")
        logger.info(f"   • Cotes H2H sauvées: {self.stats['saved_h2h']}")
        logger.info(f"   • Cotes Totals sauvées: {self.stats['saved_totals']}")
        logger.info(f"   • Sports ignorés (cache): {self.stats['skipped']}")
        logger.info("=" * 70)


if __name__ == '__main__':
    collector = SmartCollector()
    collector.run()
