#!/bin/bash
#══════════════════════════════════════════════════════════════════════════════
# 📊 CRON V7 MONITOR - Dashboard et Alertes
#══════════════════════════════════════════════════════════════════════════════

BASE_DIR="/home/Mon_ps"
LOG_DIR="$BASE_DIR/logs/clv_v7"
SCRIPT_DIR="$BASE_DIR/backend/agents/clv_tracker"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     📊 CRON V7 MONITORING DASHBOARD                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📅 $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1. Statut des processus
echo "=== 1. PROCESSUS ACTIFS ==="
ps aux | grep -E "(orchestrator_v7|auto_learning|cron_v7)" | grep -v grep || echo "   Aucun processus actif"
echo ""

# 2. Locks actifs
echo "=== 2. LOCKS ACTIFS ==="
if ls /var/run/monps/*.lock 2>/dev/null; then
    for lock in /var/run/monps/*.lock; do
        pid=$(cat "$lock")
        name=$(basename "$lock" .lock)
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "   ${GREEN}✅ $name (PID: $pid) - Running${NC}"
        else
            echo -e "   ${RED}❌ $name (PID: $pid) - Stale${NC}"
        fi
    done
else
    echo "   Aucun lock actif"
fi
echo ""

# 3. Dernières exécutions
echo "=== 3. DERNIÈRES EXÉCUTIONS ==="
if [ -f "$LOG_DIR/cron_v7_$(date +%Y%m%d).log" ]; then
    grep -E "(START|END|OK|ERROR)" "$LOG_DIR/cron_v7_$(date +%Y%m%d).log" | tail -15
else
    echo "   Pas de log aujourd'hui"
fi
echo ""

# 4. Stats DB
echo "=== 4. STATISTIQUES PICKS ==="
docker exec monps_postgres psql -U monps_user -d monps_db -c "
SELECT 
    source,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '4 hours') as last_4h,
    COUNT(*) FILTER (WHERE is_resolved) as resolved,
    ROUND(AVG(diamond_score)::numeric, 1) as avg_score
FROM tracking_clv_picks
WHERE source LIKE 'orchestrator_v%'
GROUP BY source
ORDER BY source DESC;
" 2>/dev/null
echo ""

# 5. Performance
echo "=== 5. PERFORMANCE DERNIÈRES 24H ==="
docker exec monps_postgres psql -U monps_user -d monps_db -c "
SELECT 
    source,
    COUNT(*) FILTER (WHERE is_resolved) as resolved,
    COUNT(*) FILTER (WHERE is_winner) as wins,
    ROUND(
        COUNT(*) FILTER (WHERE is_winner)::numeric / 
        NULLIF(COUNT(*) FILTER (WHERE is_resolved), 0) * 100, 1
    ) as win_rate,
    ROUND(SUM(CASE WHEN is_resolved THEN profit_loss ELSE 0 END)::numeric, 2) as profit
FROM tracking_clv_picks
WHERE source LIKE 'orchestrator_v%'
AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY source
ORDER BY win_rate DESC NULLS LAST;
" 2>/dev/null
echo ""

# 6. Health status
echo "=== 6. HEALTH STATUS ==="
if [ -f "/var/run/monps/cron_v7_health.json" ]; then
    cat /var/run/monps/cron_v7_health.json
else
    echo "   Pas de données de santé"
fi
echo ""

# 7. Espace disque
echo "=== 7. ESPACE DISQUE ==="
df -h / | head -2
echo ""

# 8. Prochaines exécutions (basé sur crontab)
echo "=== 8. CRONTAB ACTUEL ==="
crontab -l 2>/dev/null | grep -E "cron_v7|clv" || echo "   Pas de cron V7 configuré"
