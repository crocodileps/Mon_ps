#!/bin/bash
# CRON SMART pour Agent CLV Tracker V3
# Exécute uniquement si nécessaire

LOG_DIR="/home/Mon_ps/logs/clv_tracker"
mkdir -p $LOG_DIR

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/run_$TIMESTAMP.log"

cd /home/Mon_ps

# Vérifier si une exécution est déjà en cours
LOCKFILE="/tmp/clv_tracker.lock"
if [ -f "$LOCKFILE" ]; then
    echo "Exécution déjà en cours, skip" >> $LOG_FILE
    exit 0
fi

touch $LOCKFILE

# Exécuter l'agent
python3 backend/agents/clv_tracker/agent_clv_tracker_v3.py >> $LOG_FILE 2>&1

rm -f $LOCKFILE

# Nettoyer les vieux logs (garder 7 jours)
find $LOG_DIR -name "*.log" -mtime +7 -delete
