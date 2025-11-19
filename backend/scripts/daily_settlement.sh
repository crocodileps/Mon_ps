#!/bin/bash
# Script quotidien qui exécute settlement + CLV de manière intelligente

echo "=== $(date) - Settlement & CLV automatique ==="

# Charger les variables d'environnement
export DB_HOST=monps_postgres
export DB_PORT=5432
export DB_NAME=monps_db
export DB_USER=monps_user
export DB_PASSWORD=monps_password
export ODDS_API_KEY=${ODDS_API_KEY}

cd /app

# 1. Calculer CLV (0 requête API)
echo "[1/2] Calcul CLV..."
python3 scripts/auto_clv.py

# 2. Settlement des matchs terminés (requêtes API seulement pour matchs finis)
echo "[2/2] Settlement automatique..."
python3 scripts/auto_settlement.py

echo "=== Terminé ==="
