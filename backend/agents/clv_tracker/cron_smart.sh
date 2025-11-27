#!/bin/bash
# 🤖 CRON CLV V3 - 0 API externe

SCRIPT="/home/Mon_ps/backend/agents/clv_tracker/orchestrator_v3.py"
LOG_DIR="/home/Mon_ps/logs/clv_tracker"
mkdir -p "$LOG_DIR"

LOG="$LOG_DIR/cron_$(date +%Y%m%d_%H%M%S).log"

echo "[$(date)] 🚀 CRON V3" >> "$LOG"
cd /home/Mon_ps
python3 "$SCRIPT" smart >> "$LOG" 2>&1
echo "[$(date)] ✅ FIN" >> "$LOG"

# Cleanup
find "$LOG_DIR" -name "*.log" -mtime +14 -delete 2>/dev/null
