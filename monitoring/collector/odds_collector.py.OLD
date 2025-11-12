"""
Collector de cotes optimisé avec cache intelligent
Phase 10.1 - Économie quota API
"""
import os
import logging
import time
from datetime import datetime, timedelta
import requests
import psycopg2
from psycopg2.extras import execute_values
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration
API_KEY = os.getenv('ODDS_API_KEY')
API_BASE_URL = 'https://api.the-odds-api.com/v4'
SPORTS = ['soccer_epl', 'soccer_spain_la_liga', 'soccer_france_ligue_one']
SPREAD_THRESHOLD = 2.0

# Configuration DB
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'monps_postgres'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'monps_db'),
    'user': os.getenv('DB_USER', 'monps_user'),
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

# Configuration Email
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_TO = os.getenv('EMAIL_TO')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# Configuration collecte
COLLECTION_INTERVAL = 14400  # 4 heures en secondes
CACHE_TTL = 3600  # 1 heure de cache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OddsCollector:
    def __init__(self):
        self.conn = None
        self.last_collection_times = {}  # Cache des dernières collectes
        
    def connect_db(self):
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("Connecté à PostgreSQL")
        except Exception as e:
            logger.error(f"Erreur connexion DB: {e}")
            raise
    
    def close_db(self):
        if self.conn:
            self.conn.close()
            logger.info("Connexion DB fermée")
    
    def should_collect(self, sport):
        """
        Vérifie si on doit collecter ce sport
        - Collecte si jamais collecté
        - Collecte si dernière collecte > 4h
        - Collecte si proche du début des matchs
        """
        if sport not in self.last_collection_times:
            logger.info(f"{sport}: Première collecte")
            return True
        
        last_time = self.last_collection_times[sport]
        elapsed = (datetime.now() - last_time).total_seconds()
        
        if elapsed < COLLECTION_INTERVAL:
            logger.info(f"{sport}: Dernière collecte il y a {int(elapsed/60)}min - SKIP")
            return False
        
        # Vérifier s'il y a des matchs dans les prochaines 24h
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM odds_history 
                WHERE sport = %s 
                AND commence_time > NOW() 
                AND commence_time < NOW() + INTERVAL '24 hours'
                AND collected_at > NOW() - INTERVAL '6 hours'
            """, (sport,))
            upcoming_matches = cursor.fetchone()[0]
            
            if upcoming_matches == 0:
                logger.info(f"{sport}: Aucun match dans les 24h - SKIP")
                return False
                
        except Exception as e:
            logger.warning(f"Erreur vérification matchs: {e}")
        
        logger.info(f"{sport}: Collecte nécessaire (dernière: {int(elapsed/3600)}h ago)")
        return True
    
    def get_sports_odds(self, sport):
        """Récupère les cotes via l'API"""
        try:
            url = f"{API_BASE_URL}/sports/{sport}/odds"
            params = {
                'apiKey': API_KEY,
                'regions': 'eu',
                'markets': 'h2h',
                'oddsFormat': 'decimal'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Quota info
            used = response.headers.get('x-requests-used', 'N/A')
            remaining = response.headers.get('x-requests-remaining', 'N/A')
            logger.info(f"API requests - Used: {used}, Remaining: {remaining}")
            
            data = response.json()
            logger.info(f"Récupéré {len(data)} matchs pour {sport}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur API pour {sport}: {e}")
            return None
    
    def store_odds(self, sport, matches_data):
        """Stocke les cotes dans PostgreSQL"""
        if not matches_data:
            return
        
        try:
            cursor = self.conn.cursor()
            values_list = []
            
            for match in matches_data:
                match_id = match['id']
                home_team = match['home_team']
                away_team = match['away_team']
                commence_time = match['commence_time']
                
                for bookmaker in match.get('bookmakers', []):
                    bookmaker_name = bookmaker['key']
                    for market in bookmaker.get('markets', []):
                        if market['key'] == 'h2h':
                            outcomes = {o['name']: o['price'] for o in market['outcomes']}
                            home_odds = outcomes.get(home_team)
                            away_odds = outcomes.get(away_team)
                            draw_odds = outcomes.get('Draw')
                            
                            if home_odds and away_odds:
                                values_list.append((
                                    match_id, sport, home_team, away_team,
                                    commence_time, bookmaker_name,
                                    home_odds, away_odds, draw_odds
                                ))
            
            if values_list:
                execute_values(
                    cursor,
                    """
                    INSERT INTO odds_history 
                    (match_id, sport, home_team, away_team, commence_time, 
                     bookmaker, home_odds, away_odds, draw_odds)
                    VALUES %s
                    ON CONFLICT (match_id, bookmaker, collected_at) DO NOTHING
                    """,
                    values_list
                )
                self.conn.commit()
                logger.info(f"Stocké {len(values_list)} cotes dans la DB")
                
        except Exception as e:
            logger.error(f"Erreur stockage odds: {e}")
            self.conn.rollback()
    
    def detect_opportunities(self, sport):
        """Détecte les opportunités de spread > seuil"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT sport, home_team, away_team, 
                       home_spread_pct, away_spread_pct, draw_spread_pct,
                       bookmaker_count
                FROM v_current_opportunities
                WHERE sport = %s
                AND GREATEST(
                    home_spread_pct, 
                    away_spread_pct, 
                    COALESCE(draw_spread_pct, 0)
                ) > %s
                ORDER BY GREATEST(
                    home_spread_pct, 
                    away_spread_pct, 
                    COALESCE(draw_spread_pct, 0)
                ) DESC
            """, (sport, SPREAD_THRESHOLD))
            
            opportunities = cursor.fetchall()
            logger.info(f"Détecté {len(opportunities)} opportunités pour {sport}")
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Erreur détection opportunités: {e}")
            return []
    
    def send_opportunity_alert(self, opportunities):
        """Envoie un email d'alerte pour les opportunités"""
        if not opportunities or not EMAIL_TO:
            return
        
        try:
            # Créer email HTML
            html_content = f"""
            <html>
            <body>
                <h2>🎯 {len(opportunities)} Opportunités de Trading Détectées</h2>
                <p>Collecte du {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <table border="1" style="border-collapse: collapse;">
                    <tr>
                        <th>Sport</th>
                        <th>Match</th>
                        <th>Max Spread %</th>
                        <th>Bookmakers</th>
                    </tr>
            """
            
            for opp in opportunities[:10]:  # Top 10
                sport, home, away, h_spread, a_spread, d_spread, bk_count = opp
                max_spread = max(h_spread or 0, a_spread or 0, d_spread or 0)
                
                html_content += f"""
                    <tr>
                        <td>{sport}</td>
                        <td>{home} vs {away}</td>
                        <td><strong>{max_spread:.2f}%</strong></td>
                        <td>{bk_count}</td>
                    </tr>
                """
            
            html_content += """
                </table>
            </body>
            </html>
            """
            
            msg = MIMEMultipart()
            msg['From'] = EMAIL_FROM
            msg['To'] = EMAIL_TO
            msg['Subject'] = f"🎯 {len(opportunities)} Opportunités de Trading"
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Alerte email envoyée pour {len(opportunities)} opportunités")
            
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
    
    def collect_sport(self, sport):
        """Collecte un sport si nécessaire"""
        if not self.should_collect(sport):
            return []
        
        logger.info(f"Traitement sport: {sport}")
        matches_data = self.get_sports_odds(sport)
        
        if matches_data:
            self.store_odds(sport, matches_data)
            opportunities = self.detect_opportunities(sport)
            self.last_collection_times[sport] = datetime.now()
            return opportunities
        
        return []
    
    def collect_all_sports(self):
        """Collecte tous les sports avec optimisation"""
        logger.info("=== Début cycle collecte ===")
        all_opportunities = []
        
        try:
            self.connect_db()
            
            for sport in SPORTS:
                opportunities = self.collect_sport(sport)
                all_opportunities.extend(opportunities)
                
                # Pause entre sports pour ne pas surcharger l'API
                time.sleep(2)
            
            if all_opportunities:
                self.send_opportunity_alert(all_opportunities)
            
            logger.info(f"=== Cycle terminé: {len(all_opportunities)} opportunités ===")
            
        except Exception as e:
            logger.error(f"Erreur collecte: {e}", exc_info=True)
        finally:
            self.close_db()
    
    def run_forever(self):
        """Boucle principale avec collecte toutes les 4h"""
        logger.info(f"🚀 Démarrage collector - Intervalle: {COLLECTION_INTERVAL/3600}h")
        
        while True:
            try:
                self.collect_all_sports()
                
                next_run = datetime.now() + timedelta(seconds=COLLECTION_INTERVAL)
                logger.info(f"⏰ Prochaine collecte: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"💤 Sleep {COLLECTION_INTERVAL/3600}h...")
                
                time.sleep(COLLECTION_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Arrêt demandé par utilisateur")
                break
            except Exception as e:
                logger.error(f"Erreur inattendue: {e}", exc_info=True)
                logger.info("Retry dans 5 minutes...")
                time.sleep(300)


def main():
    collector = OddsCollector()
    collector.run_forever()


if __name__ == "__main__":
    main()
