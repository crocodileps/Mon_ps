#!/bin/bash

# Récupérer l'UID de la datasource Prometheus
DATASOURCE_UID=$(curl -s -u admin:SuperSecure2025Grafana19 "http://localhost:3000/api/datasources" | jq -r '.[0].uid')

echo "Datasource UID: $DATASOURCE_UID"

# Mettre à jour le Dashboard Performance
curl -X POST -u admin:SuperSecure2025Grafana19 \
  -H "Content-Type: application/json" \
  -d "{
    \"dashboard\": {
      \"title\": \"Mon_PS - Performance Analysis\",
      \"uid\": \"monps-performance\",
      \"panels\": [
        {
          \"datasource\": {\"uid\": \"$DATASOURCE_UID\", \"type\": \"prometheus\"},
          \"gridPos\": {\"h\": 9, \"w\": 12, \"x\": 0, \"y\": 0},
          \"id\": 1,
          \"targets\": [{\"expr\": \"monps_bankroll\", \"refId\": \"A\"}],
          \"title\": \"�� Évolution Bankroll\",
          \"type\": \"timeseries\"
        },
        {
          \"datasource\": {\"uid\": \"$DATASOURCE_UID\", \"type\": \"prometheus\"},
          \"gridPos\": {\"h\": 9, \"w\": 12, \"x\": 12, \"y\": 0},
          \"id\": 2,
          \"targets\": [{\"expr\": \"monps_roi\", \"refId\": \"A\"}],
          \"title\": \"📈 Évolution ROI\",
          \"type\": \"timeseries\"
        },
        {
          \"datasource\": {\"uid\": \"$DATASOURCE_UID\", \"type\": \"prometheus\"},
          \"gridPos\": {\"h\": 8, \"w\": 8, \"x\": 0, \"y\": 9},
          \"id\": 3,
          \"targets\": [{\"expr\": \"monps_win_rate\", \"refId\": \"A\"}],
          \"title\": \"🎯 Win Rate\",
          \"type\": \"gauge\"
        },
        {
          \"datasource\": {\"uid\": \"$DATASOURCE_UID\", \"type\": \"prometheus\"},
          \"gridPos\": {\"h\": 8, \"w\": 8, \"x\": 8, \"y\": 9},
          \"id\": 4,
          \"targets\": [{\"expr\": \"monps_total_bets\", \"refId\": \"A\"}],
          \"title\": \"🎲 Total Paris\",
          \"type\": \"stat\"
        },
        {
          \"datasource\": {\"uid\": \"$DATASOURCE_UID\", \"type\": \"prometheus\"},
          \"gridPos\": {\"h\": 8, \"w\": 8, \"x\": 16, \"y\": 9},
          \"id\": 5,
          \"targets\": [{\"expr\": \"monps_roi\", \"refId\": \"A\"}],
          \"title\": \"📊 ROI Actuel\",
          \"type\": \"gauge\"
        }
      ]
    },
    \"overwrite\": true
  }" \
  http://localhost:3000/api/dashboards/db

echo "✅ Dashboard Performance mis à jour"

# Mettre à jour le Dashboard Health
curl -X POST -u admin:SuperSecure2025Grafana19 \
  -H "Content-Type: application/json" \
  -d "{
    \"dashboard\": {
      \"title\": \"Mon_PS - System Health\",
      \"uid\": \"monps-health\",
      \"panels\": [
        {
          \"datasource\": {\"uid\": \"$DATASOURCE_UID\", \"type\": \"prometheus\"},
          \"gridPos\": {\"h\": 9, \"w\": 12, \"x\": 0, \"y\": 0},
          \"id\": 1,
          \"targets\": [{\"expr\": \"monps_total_bets\", \"refId\": \"A\"}],
          \"title\": \"🎲 Activité Paris\",
          \"type\": \"timeseries\"
        },
        {
          \"datasource\": {\"uid\": \"$DATASOURCE_UID\", \"type\": \"prometheus\"},
          \"gridPos\": {\"h\": 9, \"w\": 12, \"x\": 12, \"y\": 0},
          \"id\": 2,
          \"targets\": [{\"expr\": \"monps_win_rate\", \"refId\": \"A\"}],
          \"title\": \"🎯 Performance Win Rate\",
          \"type\": \"timeseries\"
        },
        {
          \"datasource\": {\"uid\": \"$DATASOURCE_UID\", \"type\": \"prometheus\"},
          \"gridPos\": {\"h\": 8, \"w\": 8, \"x\": 0, \"y\": 9},
          \"id\": 3,
          \"targets\": [{\"expr\": \"monps_bankroll\", \"refId\": \"A\"}],
          \"title\": \"💰 Bankroll Santé\",
          \"type\": \"stat\"
        },
        {
          \"datasource\": {\"uid\": \"$DATASOURCE_UID\", \"type\": \"prometheus\"},
          \"gridPos\": {\"h\": 8, \"w\": 8, \"x\": 8, \"y\": 9},
          \"id\": 4,
          \"targets\": [{\"expr\": \"monps_roi\", \"refId\": \"A\"}],
          \"title\": \"📈 ROI Performance\",
          \"type\": \"gauge\"
        },
        {
          \"datasource\": {\"uid\": \"$DATASOURCE_UID\", \"type\": \"prometheus\"},
          \"gridPos\": {\"h\": 8, \"w\": 8, \"x\": 16, \"y\": 9},
          \"id\": 5,
          \"targets\": [{\"expr\": \"monps_total_bets\", \"refId\": \"A\"}],
          \"title\": \"📊 Volume Total\",
          \"type\": \"stat\"
        }
      ]
    },
    \"overwrite\": true
  }" \
  http://localhost:3000/api/dashboards/db

echo "✅ Dashboard Health mis à jour"
echo ""
echo "🎉 Rafraîchis Grafana : http://91.98.131.218:3000"
