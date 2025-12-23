#!/bin/bash
# ═══════════════════════════════════════════════════════════
# THE QUANTUM SOVEREIGN V3.8 - BACKUP SCRIPT
# Sauvegarde quotidienne PostgreSQL + JSON critiques
# Créé le: 23 Décembre 2025
#
# CRON recommandé (à ajouter manuellement):
# 0 3 * * * /home/Mon_ps/quantum_sovereign/cron/backup.sh
# ═══════════════════════════════════════════════════════════

# Configuration
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/Mon_ps/backups"
LOG_FILE="/home/Mon_ps/logs/backup.log"
RETENTION_DAYS=7

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo -e "$1"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
}

log_error() {
    log "${RED}❌ $1${NC}"
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

# ═══════════════════════════════════════════════════════════
# DÉBUT DU BACKUP
# ═══════════════════════════════════════════════════════════

log "═══════════════════════════════════════════════════════════"
log "QUANTUM SOVEREIGN V3.8 - BACKUP STARTED"
log "Date: $DATE"
log "═══════════════════════════════════════════════════════════"

# Créer le dossier backup s'il n'existe pas
mkdir -p "$BACKUP_DIR"

# ═══════════════════════════════════════════════════════════
# 1. BACKUP POSTGRESQL
# ═══════════════════════════════════════════════════════════

log "📦 Étape 1/4: Backup PostgreSQL..."

PG_BACKUP_FILE="$BACKUP_DIR/db_$DATE.sql"

docker exec monps_postgres pg_dump -U monps_user monps_db > "$PG_BACKUP_FILE" 2>> "$LOG_FILE"

if [ $? -eq 0 ] && [ -s "$PG_BACKUP_FILE" ]; then
    # Compression
    gzip "$PG_BACKUP_FILE"
    PG_SIZE=$(du -h "${PG_BACKUP_FILE}.gz" | cut -f1)
    log_success "PostgreSQL backup: ${PG_SIZE} → ${PG_BACKUP_FILE}.gz"
else
    log_error "PostgreSQL backup FAILED"
    rm -f "$PG_BACKUP_FILE"
fi

# ═══════════════════════════════════════════════════════════
# 2. BACKUP JSON CRITIQUES (quantum_v2)
# ═══════════════════════════════════════════════════════════

log "📦 Étape 2/4: Backup JSON quantum_v2..."

JSON_BACKUP_FILE="$BACKUP_DIR/json_quantum_$DATE.tar.gz"

tar -czf "$JSON_BACKUP_FILE" \
    -C /home/Mon_ps/data/quantum_v2 \
    team_dna_unified_v3.json \
    microstrategy_dna.json \
    player_dna_unified.json \
    2>> "$LOG_FILE"

if [ $? -eq 0 ] && [ -s "$JSON_BACKUP_FILE" ]; then
    JSON_SIZE=$(du -h "$JSON_BACKUP_FILE" | cut -f1)
    log_success "JSON quantum_v2 backup: ${JSON_SIZE} → $JSON_BACKUP_FILE"
else
    log_error "JSON quantum_v2 backup FAILED"
fi

# ═══════════════════════════════════════════════════════════
# 3. BACKUP JSON GOALS
# ═══════════════════════════════════════════════════════════

log "📦 Étape 3/4: Backup JSON goals..."

GOALS_BACKUP_FILE="$BACKUP_DIR/json_goals_$DATE.tar.gz"

# Vérifier si les fichiers existent avant le backup
if [ -d "/home/Mon_ps/data/goals" ] || [ -d "/home/Mon_ps/data/goal_analysis" ]; then
    tar -czf "$GOALS_BACKUP_FILE" \
        -C /home/Mon_ps/data \
        --ignore-failed-read \
        goals/ \
        goal_analysis/ \
        2>> "$LOG_FILE"

    if [ $? -eq 0 ] && [ -s "$GOALS_BACKUP_FILE" ]; then
        GOALS_SIZE=$(du -h "$GOALS_BACKUP_FILE" | cut -f1)
        log_success "JSON goals backup: ${GOALS_SIZE} → $GOALS_BACKUP_FILE"
    else
        log_warning "JSON goals backup: Certains fichiers manquants"
    fi
else
    log_warning "Dossiers goals non trouvés - skip"
fi

# ═══════════════════════════════════════════════════════════
# 4. CLEANUP VIEUX BACKUPS
# ═══════════════════════════════════════════════════════════

log "🧹 Étape 4/4: Cleanup backups > ${RETENTION_DAYS} jours..."

DELETED_COUNT=$(find "$BACKUP_DIR" -type f -name "*.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
DELETED_SQL=$(find "$BACKUP_DIR" -type f -name "*.sql" -mtime +$RETENTION_DAYS -delete -print | wc -l)

TOTAL_DELETED=$((DELETED_COUNT + DELETED_SQL))

if [ $TOTAL_DELETED -gt 0 ]; then
    log_success "Cleanup: $TOTAL_DELETED vieux fichiers supprimés"
else
    log "Cleanup: Aucun vieux fichier à supprimer"
fi

# ═══════════════════════════════════════════════════════════
# RÉSUMÉ
# ═══════════════════════════════════════════════════════════

TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
FILE_COUNT=$(ls -1 "$BACKUP_DIR" | wc -l)

log "═══════════════════════════════════════════════════════════"
log "BACKUP COMPLETED"
log "Dossier: $BACKUP_DIR"
log "Taille totale: $TOTAL_SIZE"
log "Fichiers: $FILE_COUNT"
log "═══════════════════════════════════════════════════════════"

# Liste des backups créés aujourd'hui
log "Backups créés:"
ls -lh "$BACKUP_DIR"/*$DATE* 2>/dev/null | while read line; do
    log "  $line"
done

exit 0
