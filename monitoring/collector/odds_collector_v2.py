"""
🎯 COLLECTOR V2.0 - TOUS LES MARCHÉS
══════════════════════════════════════════════════════════════════════════════

Collecte TOUS les marchés disponibles:
- h2h (1X2)
- totals (Over/Under 2.5)
- btts (Both Teams To Score)

VERSION: 2.0.0
DATE: 29/11/2025
"""
import os
import logging
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuration
API_KEY = os.getenv('ODDS_API_KEY', '')
API_BASE_URL = 'https://api.the-odds-api.com/v4'

# TOUS les sports à collecter
SPORTS = [
    'soccer_epl',           # Premier League
    'soccer_spain_la_liga', # La Liga
    'soccer_france_ligue_one', # Ligue 1
    'soccer_germany_bundesliga', # Bundesliga
    'soccer_italy_serie_a', # Serie A
    'soccer_portugal_primeira_liga', # Liga Portugal
    'soccer_belgium_first_div', # Belgique
    'soccer_netherlands_eredivisie', # Eredivisie
    'soccer_turkey_super_league', # Turquie
]

# TOUS les marchés à collecter
MARKETS = 'h2h,totals,btts'

MIN_COLLECT_INTERVAL = 3600  # 1 heure minimum entre collectes
CACHE_DIR = Path('/home/Mon_ps/monitoring/collector/cache')
CACHE_DIR.mkdir(exist_ok=True)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'monps_postgres'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'monps_db'),
    'user': os.getenv('DB_USER', 'monps_user'),
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

# Logging
log_dir = Path('/home/Mon_ps/monitoring/collector/logs')
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'collector_v2_{datetime.now().strftime("%Y%m%d")}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class OddsCollectorV2:
    """Collecteur complet - Tous les marchés"""
    
    def __init__(self):
        self.conn = None
        self.stats = {
            'api_calls': 0,
            'matches_processed': 0,
            'odds_saved': 0,
            'btts_saved': 0,
            'errors': 0
        }
    
    def connect_db(self):
        """Connexion à la base de données"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("✅ Connexion DB établie")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur connexion DB: {e}")
            return False
    
    def fetch_odds(self, sport: str) -> list:
        """Récupère les cotes pour un sport - TOUS les marchés"""
        url = f"{API_BASE_URL}/sports/{sport}/odds"
        params = {
            'apiKey': API_KEY,
            'regions': 'eu',
            'markets': MARKETS,  # h2h,totals,btts
            'oddsFormat': 'decimal'
        }
        
        try:
            logger.info(f"🌐 API CALL → {sport} (marchés: {MARKETS})")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            self.stats['api_calls'] += 1
            
            remaining = response.headers.get('x-requests-remaining', '?')
            used = response.headers.get('x-requests-used', '?')
            logger.info(f"📊 Quota API: {remaining} restant / {used} utilisé")
            
            return response.json()
        except Exception as e:
            logger.error(f"❌ {sport}: {e}")
            self.stats['errors'] += 1
            return []
    
    def process_match(self, match: dict, sport: str):
        """Traite un match et extrait toutes les cotes"""
        match_id = match['id']
        home = match['home_team']
        away = match['away_team']
        commence = match['commence_time']
        now = datetime.now(timezone.utc)
        
        # Vérifier si match pas encore passé
        match_time = datetime.fromisoformat(commence.replace('Z', '+00:00'))
        if match_time < now:
            return
        
        self.stats['matches_processed'] += 1
        
        # Collecter les meilleures cotes par marché
        best_odds = {
            'home': None, 'draw': None, 'away': None,
            'over_25': None, 'under_25': None,
            'btts_yes': None, 'btts_no': None
        }
        
        for bookie in match.get('bookmakers', []):
            bookmaker = bookie['title']
            
            for market in bookie.get('markets', []):
                market_key = market['key']
                
                # 1X2 (h2h)
                if market_key == 'h2h':
                    for outcome in market.get('outcomes', []):
                        price = float(outcome['price'])
                        if outcome['name'] == home:
                            if best_odds['home'] is None or price > best_odds['home']:
                                best_odds['home'] = price
                        elif outcome['name'] == away:
                            if best_odds['away'] is None or price > best_odds['away']:
                                best_odds['away'] = price
                        elif outcome['name'] == 'Draw':
                            if best_odds['draw'] is None or price > best_odds['draw']:
                                best_odds['draw'] = price
                
                # Over/Under (totals)
                elif market_key == 'totals':
                    for outcome in market.get('outcomes', []):
                        price = float(outcome['price'])
                        point = float(outcome.get('point', 2.5))
                        
                        if point == 2.5:  # On ne garde que Over/Under 2.5
                            if outcome['name'] == 'Over':
                                if best_odds['over_25'] is None or price > best_odds['over_25']:
                                    best_odds['over_25'] = price
                            elif outcome['name'] == 'Under':
                                if best_odds['under_25'] is None or price > best_odds['under_25']:
                                    best_odds['under_25'] = price
                
                # BTTS (Both Teams To Score)
                elif market_key == 'btts':
                    for outcome in market.get('outcomes', []):
                        price = float(outcome['price'])
                        if outcome['name'] == 'Yes':
                            if best_odds['btts_yes'] is None or price > best_odds['btts_yes']:
                                best_odds['btts_yes'] = price
                        elif outcome['name'] == 'No':
                            if best_odds['btts_no'] is None or price > best_odds['btts_no']:
                                best_odds['btts_no'] = price
        
        # Sauvegarder en DB
        self.save_odds(match_id, sport, home, away, commence, best_odds)
    
    def save_odds(self, match_id: str, sport: str, home: str, away: str, 
                  commence: str, odds: dict):
        """Sauvegarde les cotes dans la table odds_latest"""
        cursor = self.conn.cursor()
        now = datetime.now(timezone.utc)
        
        try:
            # Table odds_latest (mise à jour ou insertion)
            cursor.execute("""
                INSERT INTO odds_latest 
                (match_id, sport, home_team, away_team, commence_time,
                 home_odds, draw_odds, away_odds,
                 over_25_odds, under_25_odds,
                 btts_yes_odds, btts_no_odds,
                 updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id) DO UPDATE SET
                    home_odds = EXCLUDED.home_odds,
                    draw_odds = EXCLUDED.draw_odds,
                    away_odds = EXCLUDED.away_odds,
                    over_25_odds = EXCLUDED.over_25_odds,
                    under_25_odds = EXCLUDED.under_25_odds,
                    btts_yes_odds = EXCLUDED.btts_yes_odds,
                    btts_no_odds = EXCLUDED.btts_no_odds,
                    updated_at = EXCLUDED.updated_at
            """, (
                match_id, sport, home, away, commence,
                odds['home'], odds['draw'], odds['away'],
                odds['over_25'], odds['under_25'],
                odds['btts_yes'], odds['btts_no'],
                now
            ))
            
            self.stats['odds_saved'] += 1
            if odds['btts_yes'] or odds['btts_no']:
                self.stats['btts_saved'] += 1
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde {home} vs {away}: {e}")
            self.conn.rollback()
            self.stats['errors'] += 1
    
    def ensure_table_exists(self):
        """Crée la table odds_latest si elle n'existe pas"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS odds_latest (
                match_id VARCHAR(100) PRIMARY KEY,
                sport VARCHAR(100),
                home_team VARCHAR(200),
                away_team VARCHAR(200),
                commence_time TIMESTAMPTZ,
                home_odds DECIMAL(6,2),
                draw_odds DECIMAL(6,2),
                away_odds DECIMAL(6,2),
                over_25_odds DECIMAL(6,2),
                under_25_odds DECIMAL(6,2),
                btts_yes_odds DECIMAL(6,2),
                btts_no_odds DECIMAL(6,2),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Index pour les recherches
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_odds_latest_commence 
            ON odds_latest(commence_time)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_odds_latest_teams 
            ON odds_latest(home_team, away_team)
        """)
        
        self.conn.commit()
        logger.info("✅ Table odds_latest prête")
    
    def run(self):
        """Exécute la collecte complète"""
        logger.info("=" * 60)
        logger.info("🚀 COLLECTOR V2.0 - DÉMARRAGE")
        logger.info(f"📋 Sports: {len(SPORTS)}")
        logger.info(f"📊 Marchés: {MARKETS}")
        logger.info("=" * 60)
        
        if not self.connect_db():
            return
        
        self.ensure_table_exists()
        
        for sport in SPORTS:
            logger.info(f"\n{'='*40}")
            logger.info(f"⚽ {sport}")
            logger.info("=" * 40)
            
            matches = self.fetch_odds(sport)
            logger.info(f"📥 {len(matches)} matchs récupérés")
            
            for match in matches:
                self.process_match(match, sport)
        
        # Résumé
        logger.info("\n" + "=" * 60)
        logger.info("📊 RÉSUMÉ COLLECTE")
        logger.info("=" * 60)
        logger.info(f"🌐 Appels API: {self.stats['api_calls']}")
        logger.info(f"⚽ Matchs traités: {self.stats['matches_processed']}")
        logger.info(f"💾 Cotes sauvegardées: {self.stats['odds_saved']}")
        logger.info(f"🎯 BTTS collectés: {self.stats['btts_saved']}")
        logger.info(f"❌ Erreurs: {self.stats['errors']}")
        
        if self.conn:
            self.conn.close()
        
        return self.stats


if __name__ == "__main__":
    collector = OddsCollectorV2()
    collector.run()
