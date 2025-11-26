#!/bin/bash
# Collecte automatique des cotes - 3x/jour (8h, 14h, 20h)
source /home/Mon_ps/monitoring/.env
cd /home/Mon_ps/monitoring
docker exec -e ODDS_API_KEY="$ODDS_API_KEY" monps_backend python3 /app/scripts/collect_all_odds.py >> /var/log/odds_collect.log 2>&1
echo "$(date): Collecte terminée" >> /var/log/odds_collect.log
