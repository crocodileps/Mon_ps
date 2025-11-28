#!/usr/bin/env python3
"""
🏎️ FERRARI CRON - Mise à jour quotidienne team_intelligence
============================================================
Exécution: Quotidien à 06:00

Actions:
1. Recalcule les stats depuis match_results (derniers 30 jours)
2. Met à jour les tags et alertes
3. Log les changements
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
        logging.FileHandler('/var/log/ferrari/team_intelligence.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("🏎️ FERRARI CRON - Update Team Intelligence")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Exécuter le script V3 de peuplement
        script_path = "/app/scripts/ferrari/populate_team_intelligence_v3.py"
        
        result = subprocess.run(
            ["python3", script_path, "--min-matches", "3"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes max
        )
        
        if result.returncode == 0:
            logger.info("✅ Mise à jour réussie")
            logger.info(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
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
