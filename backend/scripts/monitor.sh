#!/bin/bash
# Script de monitoring Mon_PS

echo "=========================================="
echo "  MONITORING MON_PS"
echo "  $(date)"
echo "=========================================="

# Variables
export DB_PASSWORD=MonPS2025Secure

# 1. État du système
echo ""
echo "📊 SYSTÈME"
echo "------------------------------------------"
echo "CPU Load: $(uptime | awk -F'load average:' '{ print $2 }')"
echo "RAM: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "Disque: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 ")"}')"

# 2. PostgreSQL
echo ""
echo "🗄️  BASE DE DONNÉES"
echo "------------------------------------------"
PG_STATUS=$(systemctl is-active postgresql)
echo "PostgreSQL: $PG_STATUS"

if [ "$PG_STATUS" = "active" ]; then
    # Nombre de connexions
    CONNECTIONS=$(PGPASSWORD=$DB_PASSWORD psql -h localhost -U monps_user -d monps_prod -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='monps_prod';" 2>/dev/null)
    echo "Connexions actives: $CONNECTIONS"
    
    # Taille de la base
    DB_SIZE=$(PGPASSWORD=$DB_PASSWORD psql -h localhost -U monps_user -d monps_prod -t -c "SELECT pg_size_pretty(pg_database_size('monps_prod'));" 2>/dev/null)
    echo "Taille DB: $DB_SIZE"
fi

# 3. Données
echo ""
echo "📈 DONNÉES"
echo "------------------------------------------"
PGPASSWORD=$DB_PASSWORD psql -h localhost -U monps_user -d monps_prod << SQL
-- Statistiques par sport
SELECT 
    sport,
    COUNT(*) as total_cotes,
    COUNT(DISTINCT match_id) as nb_matchs,
    COUNT(DISTINCT bookmaker) as nb_bookmakers,
    MAX(created_at) as derniere_maj
FROM odds
GROUP BY sport
ORDER BY total_cotes DESC;

-- Total global
SELECT 
    COUNT(*) as total_cotes,
    COUNT(DISTINCT match_id) as total_matchs,
    COUNT(DISTINCT bookmaker) as total_bookmakers,
    MIN(created_at) as premiere_insertion,
    MAX(created_at) as derniere_insertion
FROM odds;
SQL

# 4. Derniers logs
echo ""
echo "📋 DERNIERS LOGS"
echo "------------------------------------------"
if [ -f /home/root/mon_ps/data/logs/scan.log ]; then
    echo "10 dernières lignes du scan.log:"
    tail -10 /home/root/mon_ps/data/logs/scan.log
else
    echo "Aucun log trouvé"
fi

echo ""
echo "=========================================="
echo "  FIN DU MONITORING"
echo "=========================================="
