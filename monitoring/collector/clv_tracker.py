"""
CLV Tracker v1.0 - Calcul automatique du Closing Line Value
Utilise les données Pinnacle collectées dans odds_history et odds_totals
"""
import os
import logging
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuration base de données
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'monps_db'),
    'user': os.getenv('DB_USER', 'monps_user'),
    'password': os.getenv('DB_PASSWORD')
}

# Logging
log_file = f'/home/Mon_ps/monitoring/collector/logs/clv_tracker_{datetime.now().strftime("%Y%m%d")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class CLVTracker:
    def __init__(self):
        self.conn = None
        self.stats = {
            'processed': 0,
            'updated': 0,
            'no_pinnacle_data': 0,
            'errors': 0
        }

    def connect(self):
        """Connexion à PostgreSQL"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("✅ Connecté à PostgreSQL")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur connexion DB: {e}")
            return False

    def get_pending_bets(self):
        """Récupère les paris qui n'ont pas encore de CLV calculé ET dont le kickoff est passé"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT id, match_id, match_name, sport, kickoff_time, 
                   market_type, selection, line, odds_obtained
            FROM manual_bets
            WHERE closing_odds IS NULL
              AND kickoff_time < NOW()
            ORDER BY kickoff_time ASC
        """
        
        cursor.execute(query)
        bets = cursor.fetchall()
        cursor.close()
        
        logger.info(f"📋 {len(bets)} paris en attente de CLV")
        return bets

    def get_closing_line_h2h(self, match_id, selection, kickoff_time):
        """
        Récupère la dernière cote Pinnacle AVANT le kickoff pour un marché h2h
        
        Args:
            match_id: ID du match
            selection: 'Home', 'Away', ou 'Draw'
            kickoff_time: Heure du kickoff
        
        Returns:
            Cote Pinnacle ou None
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        # Mapper la sélection vers la colonne
        column_map = {
            'Home': 'home_odds',
            'Away': 'away_odds',
            'Draw': 'draw_odds'
        }
        
        if selection not in column_map:
            logger.warning(f"⚠️ Sélection h2h inconnue: {selection}")
            return None
        
        column = column_map[selection]
        
        query = f"""
            SELECT {column} as closing_odds, collected_at
            FROM odds_history
            WHERE match_id = %s
              AND bookmaker = 'Pinnacle'
              AND collected_at < %s
            ORDER BY collected_at DESC
            LIMIT 1
        """
        
        cursor.execute(query, (match_id, kickoff_time))
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            logger.debug(f"📊 Pinnacle h2h trouvé: {result['closing_odds']} @ {result['collected_at']}")
            return float(result['closing_odds'])
        
        return None

    def get_closing_line_totals(self, match_id, selection, line, kickoff_time):
        """
        Récupère la dernière cote Pinnacle AVANT le kickoff pour un marché totals
        
        Args:
            match_id: ID du match
            selection: 'Over' ou 'Under'
            line: Ligne (ex: 2.5, 3.0)
            kickoff_time: Heure du kickoff
        
        Returns:
            Cote Pinnacle ou None
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        # Déterminer quelle colonne utiliser
        if 'Over' in selection:
            column = 'over_odds'
        elif 'Under' in selection:
            column = 'under_odds'
        else:
            logger.warning(f"⚠️ Sélection totals inconnue: {selection}")
            return None
        
        query = f"""
            SELECT {column} as closing_odds, collected_at
            FROM odds_totals
            WHERE match_id = %s
              AND bookmaker = 'Pinnacle'
              AND line = %s
              AND collected_at < %s
            ORDER BY collected_at DESC
            LIMIT 1
        """
        
        cursor.execute(query, (match_id, line, kickoff_time))
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            logger.debug(f"📊 Pinnacle totals trouvé: {result['closing_odds']} @ {result['collected_at']}")
            return float(result['closing_odds'])
        
        return None

    def calculate_clv(self, odds_obtained, closing_odds):
        """
        Calcule le Closing Line Value en pourcentage
        
        CLV = (odds_obtained - closing_odds) / closing_odds * 100
        
        Positif = tu as battu la closing line (BIEN)
        Négatif = tu as pris une cote moins bonne que la closing line
        """
        if not closing_odds or closing_odds <= 1:
            return None
        
        clv = ((odds_obtained - closing_odds) / closing_odds) * 100
        return round(clv, 4)

    def update_bet_clv(self, bet_id, closing_odds, clv_percent):
        """Met à jour le CLV dans la table manual_bets"""
        cursor = self.conn.cursor()
        
        query = """
            UPDATE manual_bets
            SET closing_odds = %s,
                clv_percent = %s,
                clv_calculated_at = NOW()
            WHERE id = %s
        """
        
        cursor.execute(query, (closing_odds, clv_percent, bet_id))
        self.conn.commit()
        cursor.close()

    def process_bet(self, bet):
        """Traite un pari et calcule son CLV"""
        bet_id = bet['id']
        match_id = bet['match_id']
        market_type = bet['market_type']
        selection = bet['selection']
        line = bet['line']
        odds_obtained = float(bet['odds_obtained'])
        kickoff_time = bet['kickoff_time']
        match_name = bet['match_name']
        
        logger.info(f"🔍 Traitement: {match_name} - {selection}")
        
        # Récupérer la closing line Pinnacle
        if market_type == 'h2h':
            closing_odds = self.get_closing_line_h2h(match_id, selection, kickoff_time)
        elif market_type == 'totals':
            closing_odds = self.get_closing_line_totals(match_id, selection, line, kickoff_time)
        else:
            logger.warning(f"⚠️ Type de marché inconnu: {market_type}")
            self.stats['errors'] += 1
            return
        
        if not closing_odds:
            logger.warning(f"⚠️ Pas de données Pinnacle pour {match_name}")
            self.stats['no_pinnacle_data'] += 1
            return
        
        # Calculer le CLV
        clv_percent = self.calculate_clv(odds_obtained, closing_odds)
        
        # Mettre à jour la base
        self.update_bet_clv(bet_id, closing_odds, clv_percent)
        
        # Log le résultat
        clv_emoji = "🟢" if clv_percent > 0 else "🔴"
        logger.info(f"  {clv_emoji} CLV: {clv_percent:.2f}% (Obtenu: {odds_obtained} | Pinnacle: {closing_odds})")
        
        self.stats['updated'] += 1

    def run(self):
        """Exécution principale"""
        logger.info("=" * 70)
        logger.info("🎯 CLV TRACKER v1.0 - Calcul automatique")
        logger.info("=" * 70)
        
        if not self.connect():
            return
        
        # Récupérer les paris en attente
        bets = self.get_pending_bets()
        
        if not bets:
            logger.info("✅ Aucun pari en attente de CLV")
            self.conn.close()
            return
        
        # Traiter chaque pari
        for bet in bets:
            self.stats['processed'] += 1
            try:
                self.process_bet(bet)
            except Exception as e:
                logger.error(f"❌ Erreur traitement pari {bet['id']}: {e}")
                self.stats['errors'] += 1
        
        self.conn.close()
        
        # Résumé
        logger.info("=" * 70)
        logger.info("📊 RÉSUMÉ CLV TRACKER:")
        logger.info(f"   • Paris traités: {self.stats['processed']}")
        logger.info(f"   • CLV calculés: {self.stats['updated']}")
        logger.info(f"   • Sans données Pinnacle: {self.stats['no_pinnacle_data']}")
        logger.info(f"   • Erreurs: {self.stats['errors']}")
        logger.info("=" * 70)


if __name__ == '__main__':
    tracker = CLVTracker()
    tracker.run()
