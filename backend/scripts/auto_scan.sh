#!/bin/bash
# Script de scan automatique des cotes

# Aller dans le dossier du projet
cd /home/root/mon_ps

# Activer l'environnement virtuel
source venv/bin/activate

# Charger les variables d'environnement
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=monps_prod
export DB_USER=monps_user
export DB_PASSWORD=MonPS2025Secure
export THE_ODDS_API_KEY=e62b647a1714eafcda7adc07f59cdb0d

# Exécuter l'import
echo "=========================================="
echo "SCAN AUTOMATIQUE - $(date)"
echo "=========================================="

python3 backend/scripts/import_odds.py

echo ""
echo "Scan terminé à $(date)"
echo "=========================================="
