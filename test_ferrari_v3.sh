#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  🧪  TEST FERRARI V3 - SIMPLIFIÉ                         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Charger API key
if [ -f .env ]; then
    export $(cat .env | grep API_FOOTBALL_KEY | xargs)
fi

if [ -z "$API_FOOTBALL_KEY" ]; then
    echo "❌ API_FOOTBALL_KEY non trouvée"
    exit 1
fi

echo "🔑 API Key chargée"
echo ""

# Lancer test simplifié
docker exec -e API_FOOTBALL_KEY="$API_FOOTBALL_KEY" \
    monps_backend python3 /app/agents/orchestrator_ferrari_v3_simple.py

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  ✅  TEST TERMINÉ !                                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
