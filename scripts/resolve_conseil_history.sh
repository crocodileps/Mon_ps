#!/bin/bash
# Script de résolution automatique des recommandations Agent Conseil Ultim
# Exécuté quotidiennement à 6h du matin

LOG_FILE="/home/Mon_ps/logs/conseil_resolve.log"
API_URL="http://91.98.131.218:8001"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Début résolution Conseil Ultim" >> $LOG_FILE

# Appeler l'endpoint resolve
RESULT=$(curl -s -X POST "$API_URL/agents/conseil-ultim/resolve")

echo "$(date '+%Y-%m-%d %H:%M:%S') - Résultat: $RESULT" >> $LOG_FILE

# Extraire les stats
RESOLVED=$(echo $RESULT | python3 -c "import sys,json; print(json.load(sys.stdin).get('resolved', 0))" 2>/dev/null)
WINS=$(echo $RESULT | python3 -c "import sys,json; print(json.load(sys.stdin).get('wins', 0))" 2>/dev/null)
LOSSES=$(echo $RESULT | python3 -c "import sys,json; print(json.load(sys.stdin).get('losses', 0))" 2>/dev/null)

echo "$(date '+%Y-%m-%d %H:%M:%S') - Résolu: $RESOLVED | Wins: $WINS | Losses: $LOSSES" >> $LOG_FILE
echo "---" >> $LOG_FILE
