
# 🔧 PROBLÈME : Backend redémarré sans variables DB

## Date : 2025-11-28

## Symptôme
- API retourne "Internal Server Error"
- Logs : `fe_sendauth: no password supplied`

## Cause
Le backend a été relancé avec seulement `DB_HOST`, sans les autres variables.

## Solution
```bash
docker stop monps_backend && docker rm monps_backend

docker run -d \
  --name monps_backend \
  --network monitoring_monps_network \
  -p 8001:8000 \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -e DB_HOST="monps_postgres" \
  -e DB_PORT="5432" \
  -e DB_NAME="monps_db" \
  -e DB_USER="monps_user" \
  -e DB_PASSWORD="monps_secure_password_2024" \
  monitoring-backend
```

## Leçon
Toujours utiliser docker-compose ou un script avec TOUTES les variables.
