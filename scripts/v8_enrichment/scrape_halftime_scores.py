#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 V8 PHASE 1: SCRAPER SCORES MI-TEMPS                                      ║
║                                                                              ║
║  Source: API-Football /fixtures                                              ║
║  Cible: Enrichir match_results avec ht_home_score, ht_away_score            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import time

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

API_KEY = os.getenv("API_FOOTBALL_KEY", "122c7380779a7a5b381c4d0896e33c3d")
API_BASE = "https://v3.football.api-sports.io"

# Leagues cibles (ID API-Football)
TARGET_LEAGUES = {
    39: "Premier League",
    140: "La Liga", 
    135: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1"
}

SEASON = 2024  # Saison 2024-2025

# ═══════════════════════════════════════════════════════════════════════════════
# API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class APIFootballClient:
    def __init__(self):
        self.headers = {"x-apisports-key": API_KEY}
        self.calls = 0
        self.daily_limit = 100
    
    def request(self, endpoint: str, params: dict) -> dict:
        if self.calls >= self.daily_limit:
            print(f"⚠️ Quota atteint ({self.daily_limit})")
            return None
        
        url = f"{API_BASE}/{endpoint}"
        time.sleep(1.1)  # Rate limit
        
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=30)
            self.calls += 1
            
            if resp.status_code == 200:
                data = resp.json()
                remaining = resp.headers.get('x-ratelimit-requests-remaining', '?')
                print(f"   📡 API call #{self.calls} - Remaining: {remaining}")
                return data
            else:
                print(f"❌ HTTP {resp.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def get_fixtures_by_league(self, league_id: int, season: int) -> list:
        """Récupère tous les matchs d'une league avec scores HT"""
        data = self.request("fixtures", {
            "league": league_id,
            "season": season,
            "status": "FT"  # Matchs terminés uniquement
        })
        
        if data and data.get("response"):
            return data["response"]
        return []

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_columns_exist():
    """Ajoute les colonnes HT si elles n'existent pas"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Ajouter colonnes à match_results
    columns_to_add = [
        ("match_results", "ht_home_score", "INTEGER"),
        ("match_results", "ht_away_score", "INTEGER"),
        ("match_results", "fixture_id", "INTEGER"),
        ("match_results", "corners_home", "INTEGER"),
        ("match_results", "corners_away", "INTEGER"),
        ("match_results", "cards_home", "INTEGER"),
        ("match_results", "cards_away", "INTEGER"),
    ]
    
    for table, col, dtype in columns_to_add:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {dtype};")
            print(f"   ✅ Colonne {col} ajoutée à {table}")
        except Exception as e:
            print(f"   ⚠️ {col}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()

def save_fixture_data(fixtures: list, league_name: str):
    """Sauvegarde les données de fixtures avec scores HT"""
    conn = get_connection()
    cur = conn.cursor()
    
    saved = 0
    updated = 0
    
    for fix in fixtures:
        try:
            fixture_id = fix["fixture"]["id"]
            match_date = fix["fixture"]["date"][:10]
            home_team = fix["teams"]["home"]["name"]
            away_team = fix["teams"]["away"]["name"]
            
            # Scores
            ft_home = fix["goals"]["home"]
            ft_away = fix["goals"]["away"]
            ht_home = fix["score"]["halftime"]["home"]
            ht_away = fix["score"]["halftime"]["away"]
            
            if ft_home is None or ft_away is None:
                continue
            
            # Vérifier si le match existe déjà
            cur.execute("""
                SELECT id FROM match_results 
                WHERE home_team = %s AND away_team = %s 
                AND DATE(commence_time) = %s
            """, (home_team, away_team, match_date))
            
            existing = cur.fetchone()
            
            if existing:
                # Update avec scores HT
                cur.execute("""
                    UPDATE match_results SET
                        ht_home_score = %s,
                        ht_away_score = %s,
                        fixture_id = %s
                    WHERE id = %s
                """, (ht_home, ht_away, fixture_id, existing[0]))
                updated += 1
            else:
                # Insert nouveau match
                cur.execute("""
                    INSERT INTO match_results 
                    (home_team, away_team, sport, league, commence_time, 
                     score_home, score_away, ht_home_score, ht_away_score,
                     fixture_id, is_finished, outcome)
                    VALUES (%s, %s, 'soccer', %s, %s, %s, %s, %s, %s, %s, true, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    home_team, away_team, league_name, match_date,
                    ft_home, ft_away, ht_home, ht_away, fixture_id,
                    '1' if ft_home > ft_away else ('2' if ft_away > ft_home else 'X')
                ))
                saved += 1
                
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    return saved, updated

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 V8 PHASE 1: SCRAPING SCORES MI-TEMPS                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # 1. Préparer la DB
    print("📊 Préparation de la base de données...")
    ensure_columns_exist()
    
    # 2. Init API client
    client = APIFootballClient()
    
    total_saved = 0
    total_updated = 0
    
    # 3. Scraper chaque league
    for league_id, league_name in TARGET_LEAGUES.items():
        print(f"\n🏆 {league_name} (ID: {league_id})...")
        
        fixtures = client.get_fixtures_by_league(league_id, SEASON)
        print(f"   📥 {len(fixtures)} matchs récupérés")
        
        if fixtures:
            saved, updated = save_fixture_data(fixtures, league_name)
            total_saved += saved
            total_updated += updated
            print(f"   ✅ {saved} nouveaux, {updated} mis à jour")
        
        # Check quota
        if client.calls >= client.daily_limit - 5:
            print(f"\n⚠️ Quota presque atteint, arrêt préventif")
            break
    
    # 4. Résumé
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  📊 RÉSUMÉ SCRAPING                                                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Appels API:     {client.calls:4d}                                                       ║
║  Nouveaux:       {total_saved:4d}                                                       ║
║  Mis à jour:     {total_updated:4d}                                                       ║
║  Total:          {total_saved + total_updated:4d}                                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # 5. Vérification
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as total,
               COUNT(ht_home_score) as with_ht
        FROM match_results
    """)
    row = cur.fetchone()
    print(f"\n📊 État match_results: {row[0]} matchs, {row[1]} avec scores HT")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
