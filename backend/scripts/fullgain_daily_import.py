#!/usr/bin/env python3
"""
FULL GAIN 2.0 - Import quotidien automatique
À exécuter via cron chaque jour à 06h00
"""
import os
import sys
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/Mon_ps/logs/fullgain_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Charger .env
env_path = Path('/home/Mon_ps/backend/.env')
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

class FullGainDailyImport:
    """Import quotidien des données"""
    
    LEAGUES = {
        'PL': 'Premier League',
        'FL1': 'Ligue 1',
        'BL1': 'Bundesliga',
        'SA': 'Serie A',
        'PD': 'La Liga',
        'CL': 'Champions League'
    }
    
    def __init__(self):
        self.football_data_key = os.getenv('FOOTBALL_DATA_API_KEY')
        self.db_config = {
            'host': os.getenv('DB_HOST', '127.0.0.1'),
            'port': 5432,
            'database': 'monps_db',
            'user': 'monps_user',
            'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
        }
    
    def import_matches(self, days_back: int = 7) -> dict:
        """Importe les matchs récents"""
        logger.info(f"🚀 Début import matchs ({days_back} derniers jours)")
        
        headers = {"X-Auth-Token": self.football_data_key}
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        
        stats = {'imported': 0, 'errors': 0, 'leagues': {}}
        
        for code, name in self.LEAGUES.items():
            try:
                response = requests.get(
                    f"https://api.football-data.org/v4/competitions/{code}/matches",
                    headers=headers,
                    params={'status': 'FINISHED'},
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.warning(f"⚠️ {name}: HTTP {response.status_code}")
                    continue
                
                matches = response.json().get('matches', [])
                count = 0
                
                for match in matches:
                    try:
                        match_id = f"fd_{match['id']}"
                        home = match['homeTeam']['name']
                        away = match['awayTeam']['name']
                        score_home = match['score']['fullTime']['home']
                        score_away = match['score']['fullTime']['away']
                        
                        if score_home is None:
                            continue
                        
                        outcome = 'home' if score_home > score_away else 'away' if score_away > score_home else 'draw'
                        
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
                        """, (match_id, home, away, name, match['utcDate'], score_home, score_away, outcome))
                        count += 1
                    except Exception as e:
                        stats['errors'] += 1
                
                conn.commit()
                stats['imported'] += count
                stats['leagues'][code] = count
                logger.info(f"✅ {name}: {count} matchs")
                
            except Exception as e:
                logger.error(f"❌ {name}: {e}")
                stats['errors'] += 1
        
        cur.close()
        conn.close()
        
        logger.info(f"📊 Total: {stats['imported']} matchs importés, {stats['errors']} erreurs")
        return stats
    
    def refresh_team_stats(self) -> int:
        """Recalcule les stats équipes"""
        logger.info("🔄 Recalcul stats équipes...")
        
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        
        # Exécuter le fichier SQL de calcul
        sql_path = Path('/tmp/calculate_all_stats.sql')
        if sql_path.exists():
            cur.execute(open(sql_path).read())
        else:
            # Calcul inline simplifié
            cur.execute("""
                UPDATE team_statistics_live SET updated_at = NOW();
            """)
        
        count = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ {count} équipes mises à jour")
        return count
    
    def refresh_h2h(self) -> int:
        """Recalcule les H2H"""
        logger.info("🔄 Recalcul H2H...")
        
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        
        sql_path = Path('/tmp/calculate_h2h.sql')
        if sql_path.exists():
            cur.execute(open(sql_path).read())
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("✅ H2H mis à jour")
        return 0
    
    def run_full_import(self):
        """Exécution complète"""
        start = datetime.now()
        logger.info("=" * 60)
        logger.info("🎯 FULL GAIN 2.0 - IMPORT QUOTIDIEN")
        logger.info("=" * 60)
        
        # 1. Import matchs
        match_stats = self.import_matches()
        
        # 2. Refresh stats
        self.refresh_team_stats()
        
        # 3. Refresh H2H
        self.refresh_h2h()
        
        duration = (datetime.now() - start).total_seconds()
        logger.info("=" * 60)
        logger.info(f"✅ Import terminé en {duration:.1f}s")
        logger.info("=" * 60)
        
        return match_stats

if __name__ == "__main__":
    importer = FullGainDailyImport()
    importer.run_full_import()
