#!/usr/bin/env python3
"""
SYSTÈME D'AUTOMATISATION COMPLET
Collecte tous les matchs → Analyse par les 4 agents → Save
"""
import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging
import time
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ODDS_API_KEY = os.getenv('ODDS_API_KEY', '0ded7830ebf698618017c92e51cfcffc')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')

DB_CONFIG = {
    "host": os.getenv('DB_HOST', 'monps_postgres'),
    "database": os.getenv('DB_NAME', 'monps_db'),
    "user": os.getenv('DB_USER', 'monps_user'),
    "password": os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

# Ligues à surveiller
SPORTS = [
    'soccer_epl',                    # Premier League
    'soccer_france_ligue_one',       # Ligue 1
    'soccer_italy_serie_a',          # Serie A
    'soccer_spain_la_liga',          # La Liga
    'soccer_germany_bundesliga'      # Bundesliga
]

def get_upcoming_matches():
    """Récupère TOUS les matchs à venir depuis The Odds API"""
    all_matches = []
    
    for sport in SPORTS:
        url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds/'
        
        params = {
            'apiKey': ODDS_API_KEY,
            'regions': 'eu',
            'markets': 'h2h',
            'oddsFormat': 'decimal',
            'bookmakers': 'pinnacle,bet365,betclic,unibet'
        }
        
        try:
            logger.info(f"📡 Récupération {sport}...")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            matches = response.json()
            logger.info(f"✅ {sport}: {len(matches)} matchs trouvés")
            
            for match in matches:
                # Enrichir avec sport/league
                match['sport'] = sport
                all_matches.append(match)
            
            # Pause pour respecter rate limits
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Erreur {sport}: {e}")
            continue
    
    logger.info(f"📊 TOTAL: {len(all_matches)} matchs collectés")
    return all_matches

def check_if_already_analyzed(match_id):
    """Vérifie si un match a déjà été analysé récemment"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM agent_analyses 
            WHERE match_id = %s 
            AND analyzed_at > NOW() - INTERVAL '6 hours'
        """, (match_id,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
        
    except Exception as e:
        logger.error(f"❌ Erreur check DB: {e}")
        return False

def analyze_match_with_all_agents(match):
    """Analyse un match avec les 4 agents"""
    match_id = match['id']
    home_team = match['home_team']
    away_team = match['away_team']
    
    logger.info(f"🔍 Analyse: {home_team} vs {away_team}")
    
    # Vérifier si déjà analysé
    if check_if_already_analyzed(match_id):
        logger.info(f"⏭️  Déjà analysé récemment, skip")
        return False
    
    # Appeler l'endpoint d'analyse (qui déclenche les 4 agents)
    try:
        url = f"{BACKEND_URL}/agents/analyze/{match_id}"
        
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Analyse complète: 4 agents OK")
            return True
        else:
            logger.warning(f"⚠️ HTTP {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur analyse: {e}")
        return False

def main():
    """Fonction principale"""
    start_time = datetime.now()
    logger.info("="*80)
    logger.info("🚀 DÉMARRAGE ANALYSE AUTOMATIQUE TOUS LES MATCHS")
    logger.info("="*80)
    
    # 1. Collecte des matchs
    logger.info("\n📡 PHASE 1: COLLECTE MATCHS")
    logger.info("-"*80)
    matches = get_upcoming_matches()
    
    if not matches:
        logger.warning("⚠️ Aucun match trouvé")
        return
    
    # 2. Analyse par les 4 agents
    logger.info(f"\n🧠 PHASE 2: ANALYSE PAR LES 4 AGENTS")
    logger.info("-"*80)
    
    analyzed = 0
    skipped = 0
    errors = 0
    
    for i, match in enumerate(matches, 1):
        logger.info(f"\n[{i}/{len(matches)}] {match['home_team']} vs {match['away_team']}")
        
        result = analyze_match_with_all_agents(match)
        
        if result:
            analyzed += 1
        elif result is False:
            errors += 1
        else:
            skipped += 1
        
        # Pause entre matchs pour ne pas surcharger
        time.sleep(1)
    
    # 3. Résumé
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info("\n" + "="*80)
    logger.info("📊 RÉSUMÉ DE L'EXÉCUTION")
    logger.info("="*80)
    logger.info(f"⏱️  Durée: {duration:.1f}s")
    logger.info(f"📊 Matchs collectés: {len(matches)}")
    logger.info(f"✅ Matchs analysés: {analyzed}")
    logger.info(f"⏭️  Matchs skippés: {skipped}")
    logger.info(f"❌ Erreurs: {errors}")
    
    # Stats DB
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT agent_name, COUNT(*) as count
            FROM agent_analyses
            WHERE analyzed_at > NOW() - INTERVAL '24 hours'
            GROUP BY agent_name
            ORDER BY agent_name
        """)
        
        stats = cursor.fetchall()
        conn.close()
        
        logger.info("\n📈 ANALYSES 24H:")
        for stat in stats:
            logger.info(f"  {stat['agent_name']}: {stat['count']} analyses")
        
    except Exception as e:
        logger.error(f"❌ Erreur stats: {e}")
    
    logger.info("="*80)
    logger.info("✅ TERMINÉ")
    logger.info("="*80)

if __name__ == "__main__":
    main()
