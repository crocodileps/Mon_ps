#!/bin/bash
# FULL GAIN 2.0 - Refresh stats équipes
# À exécuter après import ou sur demande

echo "🔄 Refresh stats équipes..."

docker exec monps_postgres psql -U monps_user -d monps_db -f /tmp/calculate_all_stats.sql

echo "🔄 Refresh H2H..."
docker exec monps_postgres psql -U monps_user -d monps_db -f /tmp/calculate_h2h.sql

echo "✅ Refresh terminé!"
