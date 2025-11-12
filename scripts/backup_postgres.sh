#!/bin/bash

# Configuration
BACKUP_DIR="/home/Mon_ps/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="monps_db_${TIMESTAMP}.sql"
CONTAINER_NAME="monps_postgres"
DB_NAME="monps_db"
DB_USER="monps_user"
KEEP_DAYS=70000

# Créer backup
echo "📦 Creating backup: ${BACKUP_FILE}"
docker exec -t ${CONTAINER_NAME} pg_dump -U ${DB_USER} ${DB_NAME} > ${BACKUP_DIR}/${BACKUP_FILE}

# Compresser
echo "🗜️ Compressing backup..."
gzip ${BACKUP_DIR}/${BACKUP_FILE}

# Nettoyer vieux backups (> 7 jours)
echo "🧹 Cleaning old backups..."
find ${BACKUP_DIR} -name "monps_db_*.sql.gz" -mtime +${KEEP_DAYS} -delete

echo "✅ Backup completed: ${BACKUP_FILE}.gz"
echo "📊 Current backups:"
ls -lh ${BACKUP_DIR}
