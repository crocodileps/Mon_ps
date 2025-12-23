#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
# GOALS INGESTION SERVICE - CRON RUNNER
#═══════════════════════════════════════════════════════════════════════════════
#
# Remplace la partie "goals" de understat_master_v2.py
# PostgreSQL est maintenant la source unique de verite (SSOT)
#
# Usage:
#   ./run_goals_ingestion.sh           # Mode production
#   ./run_goals_ingestion.sh --dry-run # Mode simulation
#
# Auteur: Mon_PS Team
# Date: 2025-12-23
#═══════════════════════════════════════════════════════════════════════════════

set -e

LOG_FILE="/home/Mon_ps/logs/goals_ingestion_cron.log"
SERVICE_DIR="/home/Mon_ps/services/goals"

echo "═══════════════════════════════════════════════════════════════════" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Goals Ingestion Service" >> "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════════════" >> "$LOG_FILE"

# Aller dans le bon repertoire
cd /home/Mon_ps

# Executer le service
PYTHONPATH=/home/Mon_ps python3 -m services.goals.ingestion_service "$@" >> "$LOG_FILE" 2>&1
INGESTION_EXIT=$?

if [ $INGESTION_EXIT -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ingestion OK - Starting Legacy Export" >> "$LOG_FILE"
    
    # Exporter vers JSON pour compatibilite legacy
    PYTHONPATH=/home/Mon_ps python3 -m services.goals.legacy_exporter >> "$LOG_FILE" 2>&1
    EXPORT_EXIT=$?
    
    if [ $EXPORT_EXIT -eq 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: Ingestion + Export completed" >> "$LOG_FILE"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: Ingestion OK but Export failed" >> "$LOG_FILE"
    fi
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Ingestion failed with exit code $INGESTION_EXIT" >> "$LOG_FILE"
    exit $INGESTION_EXIT
fi

echo "" >> "$LOG_FILE"
