#!/bin/bash
# UNDERSTAT DAILY UPDATE V2.2 FINAL
# Pipeline complet de mise à jour des données Understat
# Exécution: 05h30 quotidien

LOG_FILE="/var/log/monps/understat_update.log"
SCRIPTS_DIR="/home/Mon_ps/scripts"
V8_DIR="/home/Mon_ps/scripts/v8_enrichment"

echo "========================================" >> $LOG_FILE
echo "$(date '+%Y-%m-%d %H:%M:%S') - DÉBUT UPDATE UNDERSTAT V2.2" >> $LOG_FILE

# 1. Master scraper (teams, players, goals DNA)
echo "$(date '+%H:%M:%S') - Étape 1/7: Master scraper..." >> $LOG_FILE
python3 $SCRIPTS_DIR/understat_master_v2.py >> $LOG_FILE 2>&1

# 2. Full enrichment (formations, gamestates, timing DNA)
echo "$(date '+%H:%M:%S') - Étape 2/7: Full enrichment..." >> $LOG_FILE
python3 $SCRIPTS_DIR/understat_full_enrichment.py >> $LOG_FILE 2>&1

# 3. Shots scraper (all_shots_against) - PREND ~5-8 MIN
echo "$(date '+%H:%M:%S') - Étape 3/7: Shots scraper..." >> $LOG_FILE
python3 $SCRIPTS_DIR/understat_shots_scraper.py >> $LOG_FILE 2>&1

# 4. Defense DNA base (depuis shots)
echo "$(date '+%H:%M:%S') - Étape 4/7: Defense DNA base..." >> $LOG_FILE
python3 $SCRIPTS_DIR/generate_defense_dna_from_shots.py >> $LOG_FILE 2>&1

# 5. Quantum Full Analysis (zones, actions, exploits)
echo "$(date '+%H:%M:%S') - Étape 5/7: Quantum Full Analysis..." >> $LOG_FILE
python3 $V8_DIR/quantum_full_analysis.py >> $LOG_FILE 2>&1

# 6. Defense DNA V5.1 (enrichi avec edges)
echo "$(date '+%H:%M:%S') - Étape 6/7: Defense DNA V5.1..." >> $LOG_FILE
python3 $V8_DIR/defense_dna_v5_1_corrected.py >> $LOG_FILE 2>&1

# 7. Goalkeeper DNA V2 (par équipe)
echo "$(date '+%H:%M:%S') - Étape 7/7: Goalkeeper DNA V2..." >> $LOG_FILE
python3 $V8_DIR/goalkeeper_dna_v2.py >> $LOG_FILE 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') - FIN UPDATE UNDERSTAT V2.2" >> $LOG_FILE
echo "========================================" >> $LOG_FILE
