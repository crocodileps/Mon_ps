#!/bin/bash
set -e

CONTAINER_NAME="monps_odds_collector"
LOG_DIR="/home/Mon_ps/monitoring/collector/logs"
LOG_FILE="${LOG_DIR}/collector_$(date +%Y%m%d).log"

mkdir -p "${LOG_DIR}"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') - Démarrage collecte ===" >> "${LOG_FILE}"

if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Erreur: Conteneur ${CONTAINER_NAME} introuvable" >> "${LOG_FILE}"
    exit 1
fi

docker exec "${CONTAINER_NAME}" python /app/odds_collector.py >> "${LOG_FILE}" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') - Collecte terminée avec succès ===" >> "${LOG_FILE}"
else
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') - Erreur collecte (code: ${EXIT_CODE}) ===" >> "${LOG_FILE}"
fi

find "${LOG_DIR}" -name "collector_*.log" -type f -mtime +30 -delete

exit $EXIT_CODE
