#!/usr/bin/env python3
"""
🏎️ FERRARI CRON - Mise à jour quotidienne scorer_intelligence
==============================================================
Exécution: Quotidien à 07:00

Actions:
1. Récupère les top scorers depuis Football-Data.org
2. Met à jour les stats (goals, assists, goals_per_match)
3. Log les nouveaux entrants
"""

import os
import sys
import subprocess
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [FERRARI-CRON] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/ferrari/scorer_intelligence.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("🏎️ FERRARI CRON - Update Scorer Intelligence")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Exécuter le script de collecte
        script_path = "/app/scripts/ferrari/scorers/collect_scorers_football_data.py"
        
        result = subprocess.run(
            ["python3", script_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes max
        )
        
        if result.returncode == 0:
            logger.info("✅ Mise à jour réussie")
            # Extraire les stats du log
            for line in result.stdout.split('\n'):
                if 'buteurs' in line.lower() or 'insérés' in line.lower() or '✅' in line:
                    logger.info(line)
        else:
            logger.error(f"❌ Erreur: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Timeout - script trop long")
    except Exception as e:
        logger.error(f"❌ Exception: {e}")
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"⏱️ Durée: {duration:.1f}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
