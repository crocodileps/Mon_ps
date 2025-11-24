#!/bin/bash
#
# Script: run_ferrari_ab_test.sh
# Description: Lance Ferrari V3 A/B Testing quotidien
# Usage: bash run_ferrari_ab_test.sh
#

set -e

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_DIR="/var/log/ferrari"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/ferrari_ab_test_${TIMESTAMP}.log"

# Créer répertoire logs si nécessaire
mkdir -p "$LOG_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "🏎️  FERRARI V3 - A/B TESTING QUOTIDIEN" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "📅 Date: $(date)" | tee -a "$LOG_FILE"
echo "📊 Log: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Vérifier API key
if [ -z "$API_FOOTBALL_KEY" ]; then
    echo "❌ Erreur: API_FOOTBALL_KEY non définie" | tee -a "$LOG_FILE"
    exit 1
fi

# Lancer orchestrator
echo "🚀 Lancement orchestrator Ferrari V3..." | tee -a "$LOG_FILE"
python3 /app/agents/orchestrator_ferrari_v3.py 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo "" | tee -a "$LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ SUCCÈS - Ferrari A/B test terminé" | tee -a "$LOG_FILE"
    
    # Extraire métriques
    BASELINE_COUNT=$(grep "Baseline:" "$LOG_FILE" | grep "signaux" | grep -oE "[0-9]+" | head -1)
    echo "📊 Baseline: $BASELINE_COUNT signaux" | tee -a "$LOG_FILE"
    
    # Compter signaux Ferrari
    FERRARI_TOTAL=$(grep "Ferrari.*: [0-9]* signaux" "$LOG_FILE" | grep -oE "[0-9]+" | awk '{sum+=$1} END {print sum}')
    echo "🏎️  Ferrari Total: $FERRARI_TOTAL signaux" | tee -a "$LOG_FILE"
    
else
    echo "⚠️  ERREUR - Code retour: $EXIT_CODE" | tee -a "$LOG_FILE"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG_FILE"

# Garder seulement les 30 derniers logs
find "$LOG_DIR" -name "ferrari_ab_test_*.log" -type f -mtime +30 -delete

exit $EXIT_CODE
