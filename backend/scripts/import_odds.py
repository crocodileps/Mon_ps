"""Import des cotes dans la base de données"""
import requests
import psycopg2
from psycopg2.extras import execute_values
import os
import sys
from datetime import datetime

API_KEY = "e62b647a1714eafcda7adc07f59cdb0d"
BASE_URL = "https://api.the-odds-api.com/v4"

# Configuration de la base de données (depuis les variables d'environnement)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "monps_prod"),
    "user": os.getenv("DB_USER", "monps_user"),
    "password": os.getenv("DB_PASSWORD")
}

def fetch_odds(sport="soccer_epl"):
    """Récupère les cotes depuis l'API"""
    print(f"🔍 Récupération des cotes pour {sport}...")
    
    url = f"{BASE_URL}/sports/{sport}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "eu,us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ {len(data)} matchs récupérés")
        return data
        
    except Exception as e:
        print(f"❌ Erreur API : {e}")
        return []

def parse_odds_data(matches):
    """Parse les données en format SQL"""
    rows = []
    
    for match in matches:
        for bookmaker in match.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                for outcome in market["outcomes"]:
                    row = (
                        match["sport_key"],
                        match["sport_title"],
                        match["id"],
                        match["home_team"],
                        match["away_team"],
                        match["commence_time"],
                        bookmaker["title"],
                        market["key"],
                        outcome["name"],
                        float(outcome["price"]),
                        float(outcome["point"]) if outcome.get("point") else None,
                        bookmaker["last_update"]
                    )
                    rows.append(row)
    
    return rows

def insert_odds(rows):
    """Insère les cotes dans la base de données"""
    print(f"💾 Insertion de {len(rows)} cotes...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        insert_query = """
        INSERT INTO odds (
            sport, league, match_id, home_team, away_team,
            commence_time, bookmaker, market_type, outcome_name,
            odds_value, point, last_update
        ) VALUES %s
        ON CONFLICT (match_id, bookmaker, market_type, outcome_name)
        DO UPDATE SET
            odds_value = EXCLUDED.odds_value,
            point = EXCLUDED.point,
            last_update = EXCLUDED.last_update
        """
        
        execute_values(cur, insert_query, rows)
        conn.commit()
        
        print(f"✅ {len(rows)} cotes insérées/mises à jour")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur base de données : {e}")
        return False

def main():
    """Fonction principale"""
    print("="*60)
    print("  IMPORT DES COTES - MON_PS")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)
    
    # Vérifier la connexion DB
    if not DB_CONFIG["password"]:
        print("❌ Variable DB_PASSWORD non définie")
        sys.exit(1)
    
    # Récupérer les cotes
    matches = fetch_odds("soccer_epl")
    if not matches:
        print("⚠️  Aucune donnée à importer")
        sys.exit(0)
    
    # Parser les données
    rows = parse_odds_data(matches)
    
    # Insérer en base
    success = insert_odds(rows)
    
    print("="*60)
    print("  TERMINÉ")
    print("="*60)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
