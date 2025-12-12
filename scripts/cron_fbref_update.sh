#!/bin/bash
# ============================================================================
# CRON WRAPPER - MISE A JOUR HEBDOMADAIRE FBREF
# Execution: Chaque mardi a 6h (apres weekend de matchs)
# ============================================================================

set -e

# Configuration
LOG_DIR="/home/Mon_ps/logs"
DATA_DIR="/home/Mon_ps/data/fbref"
SCRIPTS_DIR="/home/Mon_ps/scripts"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$DATA_DIR/backups"

# Creer dossiers si necessaire
mkdir -p $LOG_DIR
mkdir -p $BACKUP_DIR

# Fichier log de cette execution
LOG_FILE="$LOG_DIR/fbref_cron_${DATE}.log"

echo "[$DATE] ======================================" | tee -a $LOG_FILE
echo "[$DATE] DEBUT MISE A JOUR FBREF" | tee -a $LOG_FILE
echo "[$DATE] ======================================" | tee -a $LOG_FILE

# 1. BACKUP des fichiers existants
echo "[$DATE] Backup creation..." | tee -a $LOG_FILE

if [ -f "$DATA_DIR/fbref_players_complete_2025_26.json" ]; then
    cp "$DATA_DIR/fbref_players_complete_2025_26.json" \
       "$BACKUP_DIR/fbref_players_complete_${DATE}.json"
    echo "[$DATE]    Backup raw cree" | tee -a $LOG_FILE
fi

if [ -f "$DATA_DIR/fbref_players_clean_2025_26.json" ]; then
    cp "$DATA_DIR/fbref_players_clean_2025_26.json" \
       "$BACKUP_DIR/fbref_players_clean_${DATE}.json"
    echo "[$DATE]    Backup clean cree" | tee -a $LOG_FILE
fi

# 2. SCRAPING FBRef
echo "[$DATE] Scraping FBRef..." | tee -a $LOG_FILE
cd $SCRIPTS_DIR

python3 scrape_fbref_complete_2025_26.py >> $LOG_FILE 2>&1
SCRAPE_EXIT=$?

if [ $SCRAPE_EXIT -ne 0 ]; then
    echo "[$DATE] ERREUR SCRAPING (code: $SCRAPE_EXIT)" | tee -a $LOG_FILE
    exit 1
fi
echo "[$DATE]    Scraping termine" | tee -a $LOG_FILE

# 3. NETTOYAGE donnees
echo "[$DATE] Nettoyage donnees..." | tee -a $LOG_FILE
python3 clean_fbref_data.py >> $LOG_FILE 2>&1
CLEAN_EXIT=$?

if [ $CLEAN_EXIT -ne 0 ]; then
    echo "[$DATE] ERREUR NETTOYAGE (code: $CLEAN_EXIT)" | tee -a $LOG_FILE
    exit 1
fi
echo "[$DATE]    Nettoyage termine" | tee -a $LOG_FILE

# 4. FUSION avec player_dna_unified
echo "[$DATE] Fusion avec unified..." | tee -a $LOG_FILE
python3 merge_fbref_to_unified.py >> $LOG_FILE 2>&1
MERGE_EXIT=$?

if [ $MERGE_EXIT -ne 0 ]; then
    echo "[$DATE] ERREUR FUSION (code: $MERGE_EXIT)" | tee -a $LOG_FILE
    exit 1
fi
echo "[$DATE]    Fusion terminee" | tee -a $LOG_FILE

# 5. ARCHIVAGE (PAS DE SUPPRESSION - historique complet conserve!)
echo "[$DATE] Archivage backups..." | tee -a $LOG_FILE

# Compter les backups
NB_BACKUPS=$(ls -1 $BACKUP_DIR/fbref_players_complete_*.json 2>/dev/null | wc -l)
NB_BACKUPS_GZ=$(ls -1 $BACKUP_DIR/*.gz 2>/dev/null | wc -l)
echo "[$DATE]    Backups JSON: $NB_BACKUPS" | tee -a $LOG_FILE
echo "[$DATE]    Backups compresses: $NB_BACKUPS_GZ" | tee -a $LOG_FILE

# Compression des vieux backups (>30 jours) pour economiser l'espace
find $BACKUP_DIR -name "*.json" -mtime +30 -exec gzip -f {} \; 2>/dev/null || true
echo "[$DATE]    Vieux backups compresses (>30j)" | tee -a $LOG_FILE

# AUCUNE SUPPRESSION - on garde tout l'historique pour analyse temporelle

# 6. VALIDATION
echo "[$DATE] Validation..." | tee -a $LOG_FILE
PLAYERS=$(python3 -c "import json; d=json.load(open('$DATA_DIR/fbref_players_clean_2025_26.json')); print(len(d['players']))")
echo "[$DATE]    Joueurs FBRef: $PLAYERS" | tee -a $LOG_FILE

if [ "$PLAYERS" -lt 2000 ]; then
    echo "[$DATE] WARNING: Moins de 2000 joueurs scrappes!" | tee -a $LOG_FILE
fi

# 7. RESUME
echo "[$DATE] ======================================" | tee -a $LOG_FILE
echo "[$DATE] MISE A JOUR TERMINEE AVEC SUCCES" | tee -a $LOG_FILE
echo "[$DATE] ======================================" | tee -a $LOG_FILE

# Lien vers dernier log
ln -sf $LOG_FILE $LOG_DIR/fbref_cron_latest.log

exit 0
