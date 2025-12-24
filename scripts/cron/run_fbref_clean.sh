#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
# FBREF CLEAN DATA - CRON RUNNER
#═══════════════════════════════════════════════════════════════════════════════
#
# Transforme fbref_players_complete (nested) en fbref_players_clean (flat)
# Doit tourner APRÈS le scraper (06:00) et AVANT l'ingestion (06:15)
#
# Auteur: Mon_PS Team
# Date: 2025-12-24
#═══════════════════════════════════════════════════════════════════════════════

set -e

LOG_FILE="/home/Mon_ps/logs/fbref_clean_cron.log"

echo "═══════════════════════════════════════════════════════════════════" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting FBRef Clean Data" >> "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════════════" >> "$LOG_FILE"

cd /home/Mon_ps

# Vérifier que le fichier complete existe et est récent (moins de 1 heure)
COMPLETE_FILE="/home/Mon_ps/data/fbref/fbref_players_complete_2025_26.json"
if [ ! -f "$COMPLETE_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Complete file not found" >> "$LOG_FILE"
    exit 1
fi

# Exécuter le script de nettoyage
python3 scripts/clean_fbref_data.py >> "$LOG_FILE" 2>&1
CLEAN_EXIT=$?

if [ $CLEAN_EXIT -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: FBRef Clean completed" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: FBRef Clean failed with exit code $CLEAN_EXIT" >> "$LOG_FILE"
    exit $CLEAN_EXIT
fi

echo "" >> "$LOG_FILE"
