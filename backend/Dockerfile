FROM python:3.11-slim

WORKDIR /app

# Copier requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code
COPY . .

# Lancer l'API directement depuis le module
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
