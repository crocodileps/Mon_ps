#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
# TEAM MARKET PROFILER V3 - CRON RUNNER
# Copie le script dans le container et l'exécute
#═══════════════════════════════════════════════════════════════════════════════

LOG_FILE="/home/Mon_ps/logs/team_market_profiler_v3.log"
SCRIPT_PATH="/home/Mon_ps/backend/ml/profilers/team_market_profiler_v3.py"
CONTAINER="monps_backend"

echo "═══════════════════════════════════════════════════════════════════" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Team Market Profiler V3" >> "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════════════" >> "$LOG_FILE"

# Ensure profilers directory exists in container
docker exec "$CONTAINER" mkdir -p /app/ml/profilers 2>> "$LOG_FILE"

# Copy the script to container
docker cp "$SCRIPT_PATH" "$CONTAINER":/app/ml/profilers/ 2>> "$LOG_FILE"

if [ $? -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Failed to copy script to container" >> "$LOG_FILE"
    exit 1
fi

# Execute the script
docker exec "$CONTAINER" python3 /app/ml/profilers/team_market_profiler_v3.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: Profiler completed" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Profiler failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
exit $EXIT_CODE
