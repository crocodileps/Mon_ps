FROM python:3.11-slim

WORKDIR /app

# Copier requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code
COPY . .

# Lancer l'API directement depuis le module
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Installer cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Copier le crontab
COPY crontab /etc/cron.d/settlement-cron
RUN chmod 0644 /etc/cron.d/settlement-cron && crontab /etc/cron.d/settlement-cron

# Créer les logs
RUN touch /var/log/settlement.log /var/log/clv.log

# Installer cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Copier les scripts
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.sh /app/scripts/*.py

# Copier et activer le crontab
COPY crontab /etc/cron.d/settlement-cron
RUN chmod 0644 /etc/cron.d/settlement-cron && \
    crontab /etc/cron.d/settlement-cron && \
    touch /var/log/settlement.log /var/log/clv.log

# Démarrer cron avec le backend
CMD service cron start && uvicorn api.main:app --host 0.0.0.0 --port 8001
