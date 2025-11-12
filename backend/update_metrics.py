import os
import psycopg2
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# Connexion DB
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='monps_db',
    user='monps_user',
    password='monps_secure_password_2024'
)

cursor = conn.cursor()

# Compter opportunités
cursor.execute("""
    SELECT COUNT(*), MAX(home_spread_pct)
    FROM v_current_opportunities
    WHERE home_spread_pct > 5
""")

count, max_spread = cursor.fetchone()

print(f"Opportunités: {count}")
print(f"Max spread: {max_spread}%")

# Mettre à jour via API backend
import requests
try:
    # Appeler endpoint refresh si existe
    r = requests.post('http://localhost:8001/metrics/refresh')
    print(f"Refresh: {r.status_code}")
except:
    print("Pas d'endpoint refresh")

conn.close()
