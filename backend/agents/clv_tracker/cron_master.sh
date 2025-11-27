#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║     🤖 CRON MASTER V4 PRO - CLV TRACKER COMPLET                      ║
# ║     Exécute: Collect PRO → Resolve → CLV → Auto-Learning             ║
# ╚══════════════════════════════════════════════════════════════════════╝

set -e

SCRIPT_DIR="/home/Mon_ps/backend/agents/clv_tracker"
LOG_DIR="/home/Mon_ps/logs/clv_tracker"
mkdir -p "$LOG_DIR"

LOG="$LOG_DIR/master_$(date +%Y%m%d_%H%M%S).log"

echo "╔══════════════════════════════════════════════════════════════════════╗" >> "$LOG"
echo "║  🤖 CRON MASTER V4 PRO - $(date '+%Y-%m-%d %H:%M:%S')                         ║" >> "$LOG"
echo "╚══════════════════════════════════════════════════════════════════════╝" >> "$LOG"

cd /home/Mon_ps

# 1. COLLECT PRO - Nouveaux picks avec analyse multi-facteurs
echo "" >> "$LOG"
echo "=== 1. COLLECT V4 PRO ===" >> "$LOG"
python3 "$SCRIPT_DIR/orchestrator_v4_pro.py" collect >> "$LOG" 2>&1

# 2. RESOLVE - Résoudre matchs terminés
echo "" >> "$LOG"
echo "=== 2. RESOLVE ===" >> "$LOG"
python3 "$SCRIPT_DIR/orchestrator_v4_pro.py" resolve >> "$LOG" 2>&1

# 3. CLV - Calculer CLV pour matchs terminés
echo "" >> "$LOG"
echo "=== 3. CLV CALCULATION ===" >> "$LOG"
python3 "$SCRIPT_DIR/clv_calculator.py" >> "$LOG" 2>&1

# 4. AUTO-LEARNING - Analyser et ajuster (1x par jour à minuit)
HOUR=$(date +%H)
if [ "$HOUR" == "00" ]; then
    echo "" >> "$LOG"
    echo "=== 4. AUTO-LEARNING (daily) ===" >> "$LOG"
    python3 "$SCRIPT_DIR/auto_learner.py" >> "$LOG" 2>&1
fi

echo "" >> "$LOG"
echo "✅ CRON MASTER V4 PRO TERMINÉ - $(date '+%H:%M:%S')" >> "$LOG"

# Cleanup vieux logs (>14 jours)
find "$LOG_DIR" -name "*.log" -mtime +14 -delete 2>/dev/null || true
