"""Test de l'API The Odds"""
import requests
import json
import sys
from datetime import datetime

API_KEY = "e62b647a1714eafcda7adc07f59cdb0d"
BASE_URL = "https://api.the-odds-api.com/v4"

def test_api():
    """Test de connexion à l'API"""
    print("🔍 Test de l'API The Odds...")
    
    url = f"{BASE_URL}/sports"
    params = {"apiKey": API_KEY}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Connexion réussie : {len(data)} sports disponibles")
        
        # Afficher les requêtes restantes
        remaining = response.headers.get('x-requests-remaining')
        if remaining:
            print(f"ℹ️  Requêtes restantes : {remaining}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return False

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
