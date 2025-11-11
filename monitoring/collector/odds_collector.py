"""
Service de collecte automatique des cotes depuis The Odds API
"""
import os
import requests
import logging
from datetime import datetime
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import execute_values
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration
API_KEY = os.getenv("ODDS_API_KEY", "e62b647a1714eafcda7adc07f59cdb0d")
API_BASE_URL = "https://api.the-odds-api.com/v4"
SPORTS = ["soccer_epl", "soccer_spain_la_liga", "soccer_france_ligue_one"]
REGIONS = "eu"
MARKETS = "h2h"
ODDS_FORMAT = "decimal"
MIN_SPREAD_THRESHOLD = 2.0

# Database
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "host.docker.internal"),
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_FROM = "karouche.myriam@gmail.com"
EMAIL_TO = "karouche.myriam@gmail.com"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "vozuzectmdzgfymx")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OddsCollector:
    def __init__(self):
        self.session = requests.Session()
        self.db_conn = None
        
    def connect_db(self):
        try:
            self.db_conn = psycopg2.connect(**DB_CONFIG)
            logger.info("Connecté à PostgreSQL")
        except Exception as e:
            logger.error(f"Erreur connexion DB: {e}")
            raise
            
    def close_db(self):
        if self.db_conn:
            self.db_conn.close()
            logger.info("Connexion DB fermée")
    
    def get_sports_odds(self, sport: str) -> Optional[List[Dict]]:
        url = f"{API_BASE_URL}/sports/{sport}/odds/"
        params = {
            "apiKey": API_KEY,
            "regions": REGIONS,
            "markets": MARKETS,
            "oddsFormat": ODDS_FORMAT
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            remaining = response.headers.get('x-requests-remaining', 'unknown')
            used = response.headers.get('x-requests-used', 'unknown')
            logger.info(f"API requests - Used: {used}, Remaining: {remaining}")
            
            data = response.json()
            logger.info(f"Récupéré {len(data)} matchs pour {sport}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur API pour {sport}: {e}")
            return None
    
    def store_odds(self, sport: str, matches_data: List[Dict]):
        if not matches_data:
            return
            
        cursor = self.db_conn.cursor()
        odds_data = []
        
        for match in matches_data:
            match_id = match.get('id')
            home_team = match.get('home_team')
            away_team = match.get('away_team')
            commence_time = match.get('commence_time')
            
            for bookmaker in match.get('bookmakers', []):
                bookmaker_name = bookmaker.get('key')
                
                for market in bookmaker.get('markets', []):
                    if market.get('key') != 'h2h':
                        continue
                        
                    outcomes = market.get('outcomes', [])
                    odds_dict = {outcome['name']: outcome['price'] for outcome in outcomes}
                    
                    odds_data.append((
                        match_id, sport, home_team, away_team, commence_time,
                        bookmaker_name,
                        odds_dict.get(home_team),
                        odds_dict.get(away_team),
                        odds_dict.get('Draw'),
                        datetime.utcnow()
                    ))
        
        if odds_data:
            insert_query = """
                INSERT INTO odds_history 
                (match_id, sport, home_team, away_team, commence_time, 
                 bookmaker, home_odds, away_odds, draw_odds, collected_at)
                VALUES %s
                ON CONFLICT (match_id, bookmaker, collected_at) 
                DO UPDATE SET
                    home_odds = EXCLUDED.home_odds,
                    away_odds = EXCLUDED.away_odds,
                    draw_odds = EXCLUDED.draw_odds
            """
            
            execute_values(cursor, insert_query, odds_data)
            self.db_conn.commit()
            logger.info(f"Stocké {len(odds_data)} cotes dans la DB")
        
        cursor.close()
    
    def detect_opportunities(self, sport: str) -> List[Dict]:
        cursor = self.db_conn.cursor()
        
        query = """
            WITH latest_odds AS (
                SELECT DISTINCT ON (match_id, bookmaker)
                    match_id, sport, home_team, away_team, commence_time,
                    bookmaker, home_odds, away_odds, draw_odds, collected_at
                FROM odds_history
                WHERE sport = %s
                  AND collected_at >= NOW() - INTERVAL '1 hour'
                ORDER BY match_id, bookmaker, collected_at DESC
            ),
            match_stats AS (
                SELECT 
                    match_id, home_team, away_team, commence_time,
                    MAX(home_odds) as max_home_odds,
                    MIN(home_odds) as min_home_odds,
                    MAX(away_odds) as max_away_odds,
                    MIN(away_odds) as min_away_odds,
                    MAX(draw_odds) as max_draw_odds,
                    MIN(draw_odds) as min_draw_odds,
                    COUNT(DISTINCT bookmaker) as bookmaker_count
                FROM latest_odds
                GROUP BY match_id, home_team, away_team, commence_time
                HAVING COUNT(DISTINCT bookmaker) >= 2
            )
            SELECT 
                match_id, home_team, away_team, commence_time,
                max_home_odds, min_home_odds,
                max_away_odds, min_away_odds,
                max_draw_odds, min_draw_odds,
                bookmaker_count,
                ((max_home_odds - min_home_odds) / min_home_odds * 100) as home_spread,
                ((max_away_odds - min_away_odds) / min_away_odds * 100) as away_spread,
                ((max_draw_odds - min_draw_odds) / NULLIF(min_draw_odds, 0) * 100) as draw_spread
            FROM match_stats
            WHERE 
                ((max_home_odds - min_home_odds) / min_home_odds * 100) >= %s OR
                ((max_away_odds - min_away_odds) / min_away_odds * 100) >= %s OR
                ((max_draw_odds - min_draw_odds) / NULLIF(min_draw_odds, 0) * 100) >= %s
            ORDER BY home_spread DESC, away_spread DESC
        """
        
        cursor.execute(query, (sport, MIN_SPREAD_THRESHOLD, MIN_SPREAD_THRESHOLD, MIN_SPREAD_THRESHOLD))
        opportunities = []
        
        for row in cursor.fetchall():
            opportunities.append({
                'match_id': row[0],
                'home_team': row[1],
                'away_team': row[2],
                'commence_time': row[3],
                'max_home_odds': float(row[4]) if row[4] else None,
                'min_home_odds': float(row[5]) if row[5] else None,
                'max_away_odds': float(row[6]) if row[6] else None,
                'min_away_odds': float(row[7]) if row[7] else None,
                'max_draw_odds': float(row[8]) if row[8] else None,
                'min_draw_odds': float(row[9]) if row[9] else None,
                'bookmaker_count': row[10],
                'home_spread': float(row[11]) if row[11] else 0,
                'away_spread': float(row[12]) if row[12] else 0,
                'draw_spread': float(row[13]) if row[13] else 0
            })
        
        cursor.close()
        logger.info(f"Détecté {len(opportunities)} opportunités pour {sport}")
        return opportunities
    
    def send_opportunity_alert(self, opportunities: List[Dict]):
        if not opportunities or not EMAIL_PASSWORD:
            return
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .opportunity {{ 
                    border: 1px solid #ddd; 
                    padding: 15px; 
                    margin: 10px 0;
                    background-color: #f9f9f9;
                }}
                .match {{ font-size: 18px; font-weight: bold; color: #2c3e50; }}
                .spread {{ color: #27ae60; font-weight: bold; }}
                .odds {{ margin: 5px 0; }}
                .high {{ color: #e74c3c; }}
            </style>
        </head>
        <body>
            <h2>🚨 Nouvelles opportunités de trading détectées !</h2>
            <p>Mon_PS a détecté <strong>{len(opportunities)}</strong> opportunité(s) avec un spread > {MIN_SPREAD_THRESHOLD}%</p>
        """
        
        for opp in opportunities[:5]:
            html_content += f"""
            <div class="opportunity">
                <div class="match">{opp['home_team']} vs {opp['away_team']}</div>
                <div>Date: {opp['commence_time']}</div>
                <div>Bookmakers: {opp['bookmaker_count']}</div>
                <div class="odds">
                    Home: <span class="high">{opp['max_home_odds']:.2f}</span> - {opp['min_home_odds']:.2f} 
                    | Spread: <span class="spread">{opp['home_spread']:.2f}%</span>
                </div>
                <div class="odds">
                    Away: <span class="high">{opp['max_away_odds']:.2f}</span> - {opp['min_away_odds']:.2f} 
                    | Spread: <span class="spread">{opp['away_spread']:.2f}%</span>
                </div>
                <div class="odds">
                    Draw: <span class="high">{opp['max_draw_odds']:.2f}</span> - {opp['min_draw_odds']:.2f} 
                    | Spread: <span class="spread">{opp['draw_spread']:.2f}%</span>
                </div>
            </div>
            """
        
        html_content += """
            <p><em>Connectez-vous à Mon_PS pour plus de détails.</em></p>
        </body>
        </html>
        """
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'🎯 Mon_PS: {len(opportunities)} opportunité(s) détectée(s)'
            msg['From'] = EMAIL_FROM
            msg['To'] = EMAIL_TO
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Alerte email envoyée pour {len(opportunities)} opportunités")
            
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
    
    def collect_all_sports(self):
        logger.info("=== Début collecte cotes ===")
        all_opportunities = []
        
        try:
            self.connect_db()
            
            for sport in SPORTS:
                logger.info(f"Traitement sport: {sport}")
                
                matches_data = self.get_sports_odds(sport)
                
                if matches_data:
                    self.store_odds(sport, matches_data)
                    opportunities = self.detect_opportunities(sport)
                    all_opportunities.extend(opportunities)
            
            if all_opportunities:
                self.send_opportunity_alert(all_opportunities)
            
            logger.info(f"=== Collecte terminée: {len(all_opportunities)} opportunités ===")
            
        except Exception as e:
            logger.error(f"Erreur collecte: {e}", exc_info=True)
            
        finally:
            self.close_db()


def main():
    collector = OddsCollector()
    collector.collect_all_sports()


if __name__ == "__main__":
    main()
