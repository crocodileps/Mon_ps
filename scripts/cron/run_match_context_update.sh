#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# MATCH CONTEXT CRON - EffectiveRestIndex Daily Update
# ═══════════════════════════════════════════════════════════════════════════
# Exécution: 06:00 quotidien (après understat 05:00, avant picks 07:00)
# Service: services/match_context/service.py
# Méthode: update_upcoming_matches()
# ═══════════════════════════════════════════════════════════════════════════

set -e

# Configuration
MONPS_DIR="/home/Mon_ps"
LOG_DIR="/home/Mon_ps/logs"
LOG_FILE="$LOG_DIR/match_context_cron.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Créer répertoire logs si nécessaire
mkdir -p "$LOG_DIR"

echo "═══════════════════════════════════════════════════════════════════════════" >> "$LOG_FILE"
echo "[$TIMESTAMP] DÉBUT MATCH CONTEXT UPDATE" >> "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════════════════════" >> "$LOG_FILE"

# Se placer dans le répertoire
cd "$MONPS_DIR"

# Exécuter le service
export PYTHONPATH="$MONPS_DIR"
python3 -c "
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from services.match_context import MatchContextService

service = MatchContextService()
updated = service.update_upcoming_matches()
print(f'Matchs mis à jour: {updated}')
service.close()
" >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

TIMESTAMP_END=$(date '+%Y-%m-%d %H:%M:%S')

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$TIMESTAMP_END] ✅ MATCH CONTEXT UPDATE TERMINÉ AVEC SUCCÈS" >> "$LOG_FILE"
else
    echo "[$TIMESTAMP_END] ❌ ERREUR MATCH CONTEXT UPDATE (code: $EXIT_CODE)" >> "$LOG_FILE"
fi

echo "═══════════════════════════════════════════════════════════════════════════" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

exit $EXIT_CODE
