#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
# FBREF INGESTION SERVICE - CRON RUNNER
#═══════════════════════════════════════════════════════════════════════════════
#
# Remplace fbref_json_to_db.py par FBRefIngestionService
# Ajoute: Validation (min 500 joueurs) + Backup automatique
#
# Usage:
#   ./run_fbref_ingestion.sh              # Mode production
#   ./run_fbref_ingestion.sh --dry-run    # Mode simulation
#
# Auteur: Mon_PS Team
# Date: 2025-12-24
#═══════════════════════════════════════════════════════════════════════════════

set -e

LOG_FILE="/home/Mon_ps/logs/fbref_ingestion_cron.log"
JSON_PATH="/home/Mon_ps/data/fbref/fbref_players_clean_2025_26.json"

echo "═══════════════════════════════════════════════════════════════════" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting FBRef Ingestion Service" >> "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════════════" >> "$LOG_FILE"

# Vérifier que le JSON existe
if [ ! -f "$JSON_PATH" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: JSON file not found: $JSON_PATH" >> "$LOG_FILE"
    exit 1
fi

# Afficher la taille du fichier JSON
JSON_SIZE=$(du -h "$JSON_PATH" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] JSON file: $JSON_PATH ($JSON_SIZE)" >> "$LOG_FILE"

# Aller dans le bon répertoire
cd /home/Mon_ps

# Exécuter le service d'ingestion
PYTHONPATH=/home/Mon_ps python3 << 'PYTHON_SCRIPT' 2>&1 | tee -a "$LOG_FILE"
import logging
from pathlib import Path
from services.fbref import FBRefIngestionService

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Chemin du JSON scrapé
json_path = Path("/home/Mon_ps/data/fbref/fbref_players_clean_2025_26.json")

print(f"🚀 Starting FBRefIngestionService")
print(f"📂 JSON path: {json_path}")

# Créer le service et lancer l'ingestion
service = FBRefIngestionService()
result = service.ingest_from_json(json_path)

# Afficher le résultat
if result.is_valid:
    print(f"✅ SUCCESS: {result.total_players} players ingested")
    print(f"   Leagues: {result.players_by_league}")
    if result.warnings:
        print(f"   Warnings: {result.warnings}")
else:
    print(f"❌ FAILED: Validation errors")
    for error in result.errors:
        print(f"   - {error}")
    exit(1)
PYTHON_SCRIPT

INGESTION_EXIT=$?

if [ $INGESTION_EXIT -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: FBRef Ingestion completed" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: FBRef Ingestion failed with exit code $INGESTION_EXIT" >> "$LOG_FILE"
    exit $INGESTION_EXIT
fi

echo "" >> "$LOG_FILE"
