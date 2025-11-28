#!/bin/bash
# ============================================================
# 🎰 CRON COMBOS - Automatisation complète
# ============================================================
# À exécuter toutes les 2 heures

LOG_FILE="/var/log/monps_combos.log"
API_BASE="http://localhost:8001"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "========== DÉBUT CRON COMBOS =========="

# 1. Générer et sauvegarder les nouvelles suggestions
log "📊 Génération des suggestions..."
SUGGESTIONS=$(curl -s "${API_BASE}/api/combos/suggestions?limit=20&auto_save=true")
SAVED=$(echo $SUGGESTIONS | python3 -c "import sys,json; print(json.load(sys.stdin).get('saved_count', 0))" 2>/dev/null)
log "  → $SAVED nouveaux combos sauvegardés"

# 2. Auto-résolution des combos terminés
log "🔄 Auto-résolution..."
RESOLVED=$(curl -s -X POST "${API_BASE}/api/combos/auto-resolve")
RESOLVED_COUNT=$(echo $RESOLVED | python3 -c "import sys,json; print(json.load(sys.stdin).get('resolved_count', 0))" 2>/dev/null)
log "  → $RESOLVED_COUNT combos résolus"

# 3. Stats actuelles
log "📈 Stats actuelles..."
STATS=$(curl -s "${API_BASE}/api/combos/history?limit=1")
TOTAL=$(echo $STATS | python3 -c "import sys,json; s=json.load(sys.stdin).get('stats',{}); print(f\"Total: {s.get('total',0)} | Won: {s.get('won',0)} | Lost: {s.get('lost',0)} | Profit: {s.get('total_profit',0)}u\")" 2>/dev/null)
log "  → $TOTAL"

log "========== FIN CRON COMBOS =========="
