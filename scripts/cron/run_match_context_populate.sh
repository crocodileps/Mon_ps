#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# MATCH CONTEXT POPULATOR CRON V4.1
# ═══════════════════════════════════════════════════════════════════════════
# Exécution: 05:45 quotidien (après goals 05:30, avant calculator 06:00)
# Service: services/match_context/populator.py
# Source: odds_history (7 jours)
# Destination: match_context
# ═══════════════════════════════════════════════════════════════════════════

set -e

# Configuration
MONPS_DIR="/home/Mon_ps"
LOG_DIR="/home/Mon_ps/logs"
LOG_FILE="$LOG_DIR/match_context_populate_cron.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Créer répertoire logs si nécessaire
mkdir -p "$LOG_DIR"

echo "═══════════════════════════════════════════════════════════════════════════" >> "$LOG_FILE"
echo "[$TIMESTAMP] DÉBUT MATCH CONTEXT POPULATE V4.1" >> "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════════════════════" >> "$LOG_FILE"

# Se placer dans le répertoire
cd "$MONPS_DIR"

# Exécuter le populator
export PYTHONPATH="$MONPS_DIR"
python3 -c "
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from services.match_context import MatchContextPopulator

populator = MatchContextPopulator()
stats = populator.populate(dry_run=False)
print(f'Insérés: {stats[\"inserted\"]}, Mis à jour: {stats[\"updated\"]}, Erreurs: {stats[\"errors\"]}')
populator.close()
" >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

TIMESTAMP_END=$(date '+%Y-%m-%d %H:%M:%S')

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$TIMESTAMP_END] ✅ MATCH CONTEXT POPULATE TERMINÉ AVEC SUCCÈS" >> "$LOG_FILE"
else
    echo "[$TIMESTAMP_END] ❌ ERREUR MATCH CONTEXT POPULATE (code: $EXIT_CODE)" >> "$LOG_FILE"
fi

echo "═══════════════════════════════════════════════════════════════════════════" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

exit $EXIT_CODE
