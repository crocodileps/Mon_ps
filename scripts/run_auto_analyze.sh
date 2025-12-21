#!/bin/bash
# Wrapper pour auto_analyze - Configuration pour exécution HORS Docker
export BACKEND_URL="http://localhost:8001"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="monps_db"
export DB_USER="monps_user"
export DB_PASSWORD="monps_secure_password_2024"

cd /home/Mon_ps
python3 backend/scripts/auto_analyze_all_matches.py
