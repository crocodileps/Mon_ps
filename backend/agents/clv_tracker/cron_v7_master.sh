#!/bin/bash
#══════════════════════════════════════════════════════════════════════════════
# 🤖 CRON MASTER V7 - SYSTÈME INTELLIGENT ET ROBUSTE
#══════════════════════════════════════════════════════════════════════════════
#
# FONCTIONNALITÉS:
# ├── Lock files pour éviter exécutions simultanées
# ├── Logging professionnel avec rotation
# ├── Health checks avant exécution
# ├── Gestion des erreurs avec retry
# ├── Notifications optionnelles (Telegram/Email)
# ├── Métriques de performance
# └── Cleanup automatique
#
# USAGE:
#   ./cron_v7_master.sh [action]
#   Actions: collect | resolve | learn | clv | health | full | smart
#
# CRONTAB SUGGÉRÉ:
#   */4 * * * * /home/Mon_ps/backend/agents/clv_tracker/cron_v7_master.sh smart
#   0 6 * * *   /home/Mon_ps/backend/agents/clv_tracker/cron_v7_master.sh learn
#══════════════════════════════════════════════════════════════════════════════

set -o pipefail

#──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
#──────────────────────────────────────────────────────────────────────────────

SCRIPT_NAME="cron_v7_master"
VERSION="7.0.0"
BASE_DIR="/home/Mon_ps"
SCRIPT_DIR="$BASE_DIR/backend/agents/clv_tracker"
LOG_DIR="$BASE_DIR/logs/clv_v7"
LOCK_DIR="/var/run/monps"
PID_FILE="$LOCK_DIR/cron_v7.pid"
HEALTH_FILE="$LOCK_DIR/cron_v7_health.json"

# Timeouts (secondes)
COLLECT_TIMEOUT=300
RESOLVE_TIMEOUT=180
LEARN_TIMEOUT=120
CLV_TIMEOUT=120

# Retry configuration
MAX_RETRIES=3
RETRY_DELAY=10

# Notifications (optionnel - configurer si besoin)
ENABLE_NOTIFICATIONS=false
TELEGRAM_BOT_TOKEN=""
TELEGRAM_CHAT_ID=""

# DB Health check
DB_HOST="localhost"
DB_NAME="monps_db"
DB_USER="monps_user"

#──────────────────────────────────────────────────────────────────────────────
# FONCTIONS UTILITAIRES
#──────────────────────────────────────────────────────────────────────────────

# Couleurs pour logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Timestamp
timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Logging professionnel
log() {
    local level="$1"
    local message="$2"
    local ts=$(timestamp)
    
    case $level in
        INFO)  prefix="ℹ️ " ;;
        OK)    prefix="✅ " ;;
        WARN)  prefix="⚠️ " ;;
        ERROR) prefix="❌ " ;;
        START) prefix="🚀 " ;;
        END)   prefix="🏁 " ;;
        *)     prefix="" ;;
    esac
    
    echo "[$ts] [$level] $prefix$message" >> "$LOG_FILE"
    
    # Aussi afficher en console si interactif
    if [ -t 1 ]; then
        echo -e "[$ts] [$level] $prefix$message"
    fi
}

# Créer le fichier de log du jour
init_log() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$LOCK_DIR"
    
    LOG_FILE="$LOG_DIR/cron_v7_$(date +%Y%m%d).log"
    
    # Rotation si trop gros (>10MB)
    if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt 10485760 ]; then
        mv "$LOG_FILE" "${LOG_FILE}.$(date +%H%M%S).bak"
    fi
}

# Lock file management
acquire_lock() {
    local lock_name="$1"
    local lock_file="$LOCK_DIR/${lock_name}.lock"
    
    if [ -f "$lock_file" ]; then
        local pid=$(cat "$lock_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            log WARN "Process $lock_name already running (PID: $pid)"
            return 1
        else
            log WARN "Stale lock file found, removing"
            rm -f "$lock_file"
        fi
    fi
    
    echo $$ > "$lock_file"
    return 0
}

release_lock() {
    local lock_name="$1"
    local lock_file="$LOCK_DIR/${lock_name}.lock"
    rm -f "$lock_file"
}

# Notification (optionnel)
notify() {
    local message="$1"
    local level="${2:-INFO}"
    
    if [ "$ENABLE_NOTIFICATIONS" = true ] && [ -n "$TELEGRAM_BOT_TOKEN" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="$TELEGRAM_CHAT_ID" \
            -d text="🤖 MonPS CRON V7 [$level]: $message" \
            -d parse_mode="HTML" > /dev/null 2>&1
    fi
}

# Exécuter avec timeout et retry
run_with_retry() {
    local cmd="$1"
    local timeout="$2"
    local name="$3"
    local retries=0
    
    while [ $retries -lt $MAX_RETRIES ]; do
        log INFO "Executing $name (attempt $((retries+1))/$MAX_RETRIES)"
        
        local start_time=$(date +%s)
        
        if timeout "$timeout" bash -c "$cmd" >> "$LOG_FILE" 2>&1; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            log OK "$name completed successfully in ${duration}s"
            return 0
        else
            local exit_code=$?
            retries=$((retries + 1))
            
            if [ $exit_code -eq 124 ]; then
                log ERROR "$name timed out after ${timeout}s"
            else
                log ERROR "$name failed with exit code $exit_code"
            fi
            
            if [ $retries -lt $MAX_RETRIES ]; then
                log WARN "Retrying in ${RETRY_DELAY}s..."
                sleep $RETRY_DELAY
            fi
        fi
    done
    
    log ERROR "$name failed after $MAX_RETRIES attempts"
    notify "$name failed after $MAX_RETRIES attempts" "ERROR"
    return 1
}

#──────────────────────────────────────────────────────────────────────────────
# HEALTH CHECKS
#──────────────────────────────────────────────────────────────────────────────

check_db_health() {
    log INFO "Checking database health..."
    
    if docker exec monps_postgres psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        log OK "Database is healthy"
        return 0
    else
        log ERROR "Database is not responding"
        return 1
    fi
}

check_disk_space() {
    log INFO "Checking disk space..."
    
    local usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -lt 90 ]; then
        log OK "Disk usage: ${usage}%"
        return 0
    else
        log WARN "Disk usage critical: ${usage}%"
        notify "Disk usage critical: ${usage}%" "WARN"
        return 1
    fi
}

check_memory() {
    log INFO "Checking memory..."
    
    local mem_free=$(free -m | awk 'NR==2 {print $7}')
    
    if [ "$mem_free" -gt 500 ]; then
        log OK "Free memory: ${mem_free}MB"
        return 0
    else
        log WARN "Low memory: ${mem_free}MB"
        return 1
    fi
}

run_health_checks() {
    log INFO "Running health checks..."
    
    local health_status="healthy"
    local checks_passed=0
    local checks_total=3
    
    check_db_health && checks_passed=$((checks_passed + 1))
    check_disk_space && checks_passed=$((checks_passed + 1))
    check_memory && checks_passed=$((checks_passed + 1))
    
    if [ $checks_passed -lt $checks_total ]; then
        health_status="degraded"
    fi
    
    # Sauvegarder le statut
    cat > "$HEALTH_FILE" << EOF
{
    "timestamp": "$(timestamp)",
    "status": "$health_status",
    "checks_passed": $checks_passed,
    "checks_total": $checks_total
}
EOF
    
    log INFO "Health check: $checks_passed/$checks_total passed ($health_status)"
    
    if [ "$health_status" = "healthy" ]; then
        return 0
    else
        return 1
    fi
}

#──────────────────────────────────────────────────────────────────────────────
# ACTIONS PRINCIPALES
#──────────────────────────────────────────────────────────────────────────────

# Collecte V7 Smart
do_collect() {
    log START "=== COLLECT V7 SMART ==="
    
    cd "$BASE_DIR"
    
    local cmd="python3 $SCRIPT_DIR/orchestrator_v7_smart.py --hours 48"
    
    if run_with_retry "$cmd" "$COLLECT_TIMEOUT" "V7 Collect"; then
        # Récupérer les stats
        local picks=$(docker exec monps_postgres psql -U "$DB_USER" -d "$DB_NAME" -t -c \
            "SELECT COUNT(*) FROM tracking_clv_picks WHERE source='orchestrator_v7_smart' AND created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
        
        log OK "Collected $picks new picks"
        return 0
    else
        return 1
    fi
}

# Résolution des picks
do_resolve() {
    log START "=== RESOLVE PICKS ==="
    
    cd "$BASE_DIR"
    
    local cmd="python3 $SCRIPT_DIR/smart_resolver.py"
    
    if run_with_retry "$cmd" "$RESOLVE_TIMEOUT" "Smart Resolver"; then
        # Stats résolution
        local resolved=$(docker exec monps_postgres psql -U "$DB_USER" -d "$DB_NAME" -t -c \
            "SELECT COUNT(*) FROM tracking_clv_picks WHERE is_resolved AND resolved_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
        
        log OK "Resolved $resolved picks"
        return 0
    else
        return 1
    fi
}

# Calcul CLV
do_clv() {
    log START "=== CLV CALCULATION ==="
    
    cd "$BASE_DIR"
    
    local cmd="python3 $SCRIPT_DIR/clv_calculator.py"
    
    if run_with_retry "$cmd" "$CLV_TIMEOUT" "CLV Calculator"; then
        log OK "CLV calculation completed"
        return 0
    else
        return 1
    fi
}

# Auto-learning
do_learn() {
    log START "=== AUTO-LEARNING V7 ==="
    
    cd "$BASE_DIR"
    
    # Mode dry-run d'abord pour voir les propositions
    log INFO "Running auto-learning analysis..."
    python3 "$SCRIPT_DIR/auto_learning_v7.py" --days 14 >> "$LOG_FILE" 2>&1
    
    # Appliquer seulement si assez de données (>50 picks résolus)
    local resolved=$(docker exec monps_postgres psql -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM tracking_clv_picks WHERE is_resolved AND resolved_at > NOW() - INTERVAL '7 days';" 2>/dev/null | tr -d ' ')
    
    if [ "${resolved:-0}" -gt 50 ]; then
        log INFO "Applying auto-learning adjustments ($resolved resolved picks)..."
        python3 "$SCRIPT_DIR/auto_learning_v7.py" --days 14 --apply >> "$LOG_FILE" 2>&1
        log OK "Auto-learning adjustments applied"
    else
        log WARN "Not enough data for auto-learning ($resolved < 50 picks)"
    fi
    
    return 0
}

# Mode SMART - Exécution intelligente selon l'heure
do_smart() {
    log START "=== SMART MODE ==="
    
    local hour=$(date +%H)
    local minute=$(date +%M)
    local day_of_week=$(date +%u)  # 1=Monday, 7=Sunday
    
    log INFO "Current time: ${hour}:${minute}, Day: $day_of_week"
    
    # 1. Toujours faire la collecte
    do_collect
    
    # 2. Résolution toutes les 4 heures ou si beaucoup de matchs terminés
    if [ "$((10#$hour % 4))" -eq 0 ] || [ "$minute" -lt 10 ]; then
        do_resolve
        do_clv
    fi
    
    # 3. Auto-learning 1x/jour à 6h
    if [ "$hour" = "06" ] && [ "$minute" -lt 15 ]; then
        do_learn
    fi
    
    # 4. Cleanup vieux logs le dimanche à minuit
    if [ "$day_of_week" = "7" ] && [ "$hour" = "00" ]; then
        do_cleanup
    fi
    
    log END "Smart mode completed"
}

# Mode FULL - Tout exécuter
do_full() {
    log START "=== FULL MODE ==="
    
    do_collect
    do_resolve
    do_clv
    
    # Auto-learning seulement si beaucoup de données
    local hour=$(date +%H)
    if [ "$hour" = "06" ]; then
        do_learn
    fi
    
    log END "Full mode completed"
}

# Cleanup
do_cleanup() {
    log INFO "Running cleanup..."
    
    # Supprimer les logs > 14 jours
    find "$LOG_DIR" -name "*.log" -mtime +14 -delete 2>/dev/null
    find "$LOG_DIR" -name "*.bak" -mtime +7 -delete 2>/dev/null
    
    # Supprimer les lock files stale
    find "$LOCK_DIR" -name "*.lock" -mmin +60 -delete 2>/dev/null
    
    log OK "Cleanup completed"
}

# Afficher le statut
do_status() {
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║     📊 CRON V7 STATUS                                                    ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    
    echo ""
    echo "=== HEALTH ==="
    if [ -f "$HEALTH_FILE" ]; then
        cat "$HEALTH_FILE"
    else
        echo "No health data"
    fi
    
    echo ""
    echo "=== LOCKS ==="
    ls -la "$LOCK_DIR"/*.lock 2>/dev/null || echo "No active locks"
    
    echo ""
    echo "=== RECENT LOGS ==="
    if [ -f "$LOG_FILE" ]; then
        tail -20 "$LOG_FILE"
    else
        echo "No logs today"
    fi
    
    echo ""
    echo "=== PICKS STATS ==="
    docker exec monps_postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT 
            source,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as last_24h,
            COUNT(*) FILTER (WHERE is_resolved) as resolved
        FROM tracking_clv_picks
        WHERE source LIKE 'orchestrator_v%'
        GROUP BY source
        ORDER BY source DESC
        LIMIT 5;
    " 2>/dev/null
}

#──────────────────────────────────────────────────────────────────────────────
# MAIN
#──────────────────────────────────────────────────────────────────────────────

main() {
    local action="${1:-smart}"
    
    # Initialiser le log
    init_log
    
    log START "══════════════════════════════════════════════════════════════"
    log START "🤖 CRON V7 MASTER v$VERSION - Action: $action"
    log START "══════════════════════════════════════════════════════════════"
    
    # Acquérir le lock (sauf pour status)
    if [ "$action" != "status" ] && [ "$action" != "health" ]; then
        if ! acquire_lock "cron_v7_$action"; then
            log WARN "Could not acquire lock, exiting"
            exit 1
        fi
        trap "release_lock 'cron_v7_$action'" EXIT
    fi
    
    # Health check avant exécution (sauf pour health/status)
    if [ "$action" != "status" ] && [ "$action" != "health" ]; then
        if ! run_health_checks; then
            log WARN "Health checks failed, proceeding with caution"
        fi
    fi
    
    # Exécuter l'action
    local start_time=$(date +%s)
    local exit_code=0
    
    case "$action" in
        collect)
            do_collect || exit_code=$?
            ;;
        resolve)
            do_resolve || exit_code=$?
            ;;
        clv)
            do_clv || exit_code=$?
            ;;
        learn)
            do_learn || exit_code=$?
            ;;
        smart)
            do_smart || exit_code=$?
            ;;
        full)
            do_full || exit_code=$?
            ;;
        health)
            run_health_checks || exit_code=$?
            ;;
        status)
            do_status
            ;;
        cleanup)
            do_cleanup || exit_code=$?
            ;;
        *)
            echo "Usage: $0 {collect|resolve|clv|learn|smart|full|health|status|cleanup}"
            exit 1
            ;;
    esac
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ $exit_code -eq 0 ]; then
        log END "✅ CRON V7 completed successfully in ${duration}s"
    else
        log END "❌ CRON V7 completed with errors (exit: $exit_code) in ${duration}s"
        notify "CRON V7 $action failed (exit: $exit_code)" "ERROR"
    fi
    
    exit $exit_code
}

# Exécuter
main "$@"
