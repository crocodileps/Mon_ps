#!/usr/bin/env python3
"""
🏎️ FERRARI 2.0 - Collecteur de Buteurs HYBRIDE
================================================
Combine API-Football (historique) + FBref (actuel)

Sources:
- API-Football: Données 2023 (profil, historique, penalties)
- FBref: Données 2024 (goals actuels, xG, forme)

Output: scorer_intelligence table peuplée
"""

import os
import sys
import json
import time
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
import re
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/Mon_ps/logs/ferrari_scorers.log')
    ]
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "monps_db"),
    "user": os.getenv("DB_USER", "monps_user"),
    "password": os.getenv("DB_PASSWORD", "monps_secure_password_2024"),
    "port": 5432
}

API_FOOTBALL_KEYS = [
    os.getenv("API_FOOTBALL_KEY_MAIN", "8fbe542554070a5f04ae8aec40f9afba"),
    os.getenv("API_FOOTBALL_KEY_BACKUP", "e7a4315f951b5bfd671d01ade29638f2"),
    os.getenv("API_FOOTBALL_KEY", "122c7380779a7a5b381c4d0896e33c3d"),
]

# Ligues à collecter
LEAGUES = {
    39: {"name": "Premier League", "country": "England"},
    140: {"name": "La Liga", "country": "Spain"},
    135: {"name": "Serie A", "country": "Italy"},
    78: {"name": "Bundesliga", "country": "Germany"},
    61: {"name": "Ligue 1", "country": "France"},
}

# FBref URLs pour top scorers 2024-25
FBREF_URLS = {
    "Premier League": "https://fbref.com/en/comps/9/shooting/Premier-League-Stats",
    "La Liga": "https://fbref.com/en/comps/12/shooting/La-Liga-Stats",
    "Serie A": "https://fbref.com/en/comps/11/shooting/Serie-A-Stats",
    "Bundesliga": "https://fbref.com/en/comps/20/shooting/Bundesliga-Stats",
    "Ligue 1": "https://fbref.com/en/comps/13/shooting/Ligue-1-Stats",
}


class ScorerCollectorHybrid:
    """Collecteur hybride de données buteurs"""
    
    def __init__(self):
        self.api_key_index = 0
        self.request_count = 0
        self.collected_scorers = {}
        
    def _get_api_key(self) -> str:
        """Rotation des clés API"""
        key = API_FOOTBALL_KEYS[self.api_key_index % len(API_FOOTBALL_KEYS)]
        return key
    
    def _rotate_key(self):
        """Passer à la clé suivante"""
        self.api_key_index += 1
        logger.info(f"🔄 Rotation clé API -> {self.api_key_index % len(API_FOOTBALL_KEYS)}")
    
    def _get_conn(self):
        return psycopg2.connect(**DB_CONFIG)
    
    # ════════════════════════════════════════════════════════════
    # API-FOOTBALL (DONNÉES 2023)
    # ════════════════════════════════════════════════════════════
    
    def fetch_api_football_scorers(self, league_id: int, season: int = 2023) -> List[Dict]:
        """Récupère les top scorers depuis API-Football"""
        
        url = f"https://v3.football.api-sports.io/players/topscorers"
        params = {"league": league_id, "season": season}
        headers = {"x-apisports-key": self._get_api_key()}
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            self.request_count += 1
            
            if response.status_code == 429:  # Rate limit
                logger.warning("⚠️ Rate limit - rotation clé")
                self._rotate_key()
                time.sleep(2)
                return self.fetch_api_football_scorers(league_id, season)
            
            data = response.json()
            
            if data.get("errors"):
                if "plan" in str(data["errors"]):
                    logger.warning(f"⚠️ Plan Free - saison {season} non disponible")
                    return []
                logger.error(f"❌ Erreur API: {data['errors']}")
                return []
            
            return data.get("response", [])
            
        except Exception as e:
            logger.error(f"❌ Erreur fetch API-Football: {e}")
            return []
    
    def parse_api_football_player(self, player_data: Dict) -> Dict:
        """Parse les données d'un joueur API-Football"""
        
        player = player_data.get("player", {})
        stats = player_data.get("statistics", [{}])[0]
        
        goals_data = stats.get("goals", {})
        games_data = stats.get("games", {})
        penalty_data = stats.get("penalty", {})
        
        return {
            "player_name": player.get("name"),
            "api_football_id": player.get("id"),
            "photo_url": player.get("photo"),
            "nationality": player.get("nationality"),
            "age": player.get("age"),
            "height_cm": self._parse_height(player.get("height")),
            
            # Équipe
            "current_team": stats.get("team", {}).get("name"),
            "current_team_id": stats.get("team", {}).get("id"),
            "league": stats.get("league", {}).get("name"),
            
            # Position
            "position_primary": games_data.get("position"),
            
            # Stats 2023
            "season_2023_matches": games_data.get("appearences", 0),
            "season_2023_starts": games_data.get("lineups", 0),
            "season_2023_minutes": games_data.get("minutes", 0),
            "season_2023_goals": goals_data.get("total", 0),
            "season_2023_assists": goals_data.get("assists", 0),
            
            # Penalties
            "penalties_taken": penalty_data.get("taken", 0) or 0,
            "penalties_scored": penalty_data.get("scored", 0) or 0,
            "penalties_missed": penalty_data.get("missed", 0) or 0,
            "is_penalty_taker": (penalty_data.get("taken", 0) or 0) >= 3,
            
            # Source
            "source_api_football": True,
            "api_football_updated": datetime.now().isoformat()
        }
    
    def _parse_height(self, height_str: str) -> Optional[int]:
        """Parse la taille '185 cm' -> 185"""
        if not height_str:
            return None
        match = re.search(r'(\d+)', str(height_str))
        return int(match.group(1)) if match else None
    
    # ════════════════════════════════════════════════════════════
    # FBREF SCRAPING (DONNÉES 2024)
    # ════════════════════════════════════════════════════════════
    
    def fetch_fbref_scorers(self, league_name: str) -> List[Dict]:
        """Scrape les stats de FBref pour la saison actuelle"""
        
        url = FBREF_URLS.get(league_name)
        if not url:
            logger.warning(f"⚠️ URL FBref non trouvée pour {league_name}")
            return []
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"❌ FBref status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Trouver la table des stats de tir
            table = soup.find('table', {'id': 'stats_shooting'})
            if not table:
                # Essayer autre ID
                table = soup.find('table', class_='stats_table')
            
            if not table:
                logger.warning(f"⚠️ Table non trouvée pour {league_name}")
                return []
            
            players = []
            tbody = table.find('tbody')
            
            if tbody:
                for row in tbody.find_all('tr')[:30]:  # Top 30
                    player = self._parse_fbref_row(row, league_name)
                    if player and player.get('player_name'):
                        players.append(player)
            
            logger.info(f"✅ FBref {league_name}: {len(players)} joueurs")
            return players
            
        except Exception as e:
            logger.error(f"❌ Erreur scraping FBref {league_name}: {e}")
            return []
    
    def _parse_fbref_row(self, row, league_name: str) -> Optional[Dict]:
        """Parse une ligne de la table FBref"""
        try:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 10:
                return None
            
            # Extraire le nom du joueur
            player_cell = row.find('th', {'data-stat': 'player'})
            if not player_cell:
                return None
            
            player_name = player_cell.get_text(strip=True)
            
            # Équipe
            team_cell = row.find('td', {'data-stat': 'team'})
            team = team_cell.get_text(strip=True) if team_cell else None
            
            # Stats
            def get_stat(stat_name: str, default=0):
                cell = row.find('td', {'data-stat': stat_name})
                if cell:
                    text = cell.get_text(strip=True)
                    try:
                        return float(text) if '.' in text else int(text)
                    except:
                        return default
                return default
            
            return {
                "player_name": player_name,
                "current_team": team,
                "league": league_name,
                
                # Stats 2024 (FBref)
                "season_2024_matches": get_stat('games'),
                "season_2024_minutes": get_stat('minutes'),
                "season_2024_goals": get_stat('goals'),
                "season_2024_shots": get_stat('shots'),
                "season_2024_shots_on_target": get_stat('shots_on_target'),
                "season_2024_xg": get_stat('xg', 0.0),
                "season_2024_npxg": get_stat('npxg', 0.0),  # Non-penalty xG
                
                # Source
                "source_fbref": True,
                "fbref_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.debug(f"Erreur parsing row: {e}")
            return None
    
    # ════════════════════════════════════════════════════════════
    # FUSION SMART
    # ════════════════════════════════════════════════════════════
    
    def normalize_player_name(self, name: str) -> str:
        """Normalise le nom pour matching"""
        if not name:
            return ""
        # Enlever accents, lowercase
        import unicodedata
        name = unicodedata.normalize('NFKD', name)
        name = name.encode('ASCII', 'ignore').decode('ASCII')
        name = name.lower().strip()
        # Enlever suffixes courants
        name = re.sub(r'\s+(jr|sr|ii|iii)\.?$', '', name)
        return name
    
    def merge_player_data(self, api_data: Dict, fbref_data: Dict) -> Dict:
        """Fusionne les données API-Football et FBref"""
        
        merged = {**api_data}  # Base = API-Football
        
        if fbref_data:
            # Ajouter stats 2024 de FBref
            merged.update({
                "season_2024_matches": fbref_data.get("season_2024_matches"),
                "season_2024_minutes": fbref_data.get("season_2024_minutes"),
                "season_2024_goals": fbref_data.get("season_2024_goals"),
                "season_2024_xg": fbref_data.get("season_2024_xg"),
                "season_2024_npxg": fbref_data.get("season_2024_npxg"),
                "source_fbref": True,
                "fbref_updated": fbref_data.get("fbref_updated")
            })
            
            # Calculer stats combinées
            g_2023 = merged.get("season_2023_goals", 0) or 0
            g_2024 = merged.get("season_2024_goals", 0) or 0
            m_2023 = merged.get("season_2023_matches", 0) or 0
            m_2024 = merged.get("season_2024_matches", 0) or 0
            
            # Moyennes pondérées (2024 pèse 60%, 2023 pèse 40%)
            if m_2023 + m_2024 > 0:
                total_matches = m_2023 + m_2024
                total_goals = g_2023 + g_2024
                
                merged["career_goals_per_match"] = round(total_goals / total_matches, 3)
                
                # Goals per 90 (si on a les minutes)
                min_2023 = merged.get("season_2023_minutes", 0) or 0
                min_2024 = merged.get("season_2024_minutes", 0) or 0
                total_minutes = min_2023 + min_2024
                
                if total_minutes > 0:
                    merged["career_goals_per_90"] = round((total_goals / total_minutes) * 90, 3)
        
        return merged
    
    # ════════════════════════════════════════════════════════════
    # INSERTION DATABASE
    # ════════════════════════════════════════════════════════════
    
    def upsert_scorer(self, conn, scorer_data: Dict) -> bool:
        """Insert ou update un buteur dans scorer_intelligence"""
        
        cur = conn.cursor()
        
        try:
            # Normaliser le nom
            player_name = scorer_data.get("player_name")
            if not player_name:
                return False
            
            normalized = self.normalize_player_name(player_name)
            
            # Calculer goals_per_90 si possible
            goals_per_90 = None
            minutes = scorer_data.get("season_2024_minutes") or scorer_data.get("season_2023_minutes")
            goals = scorer_data.get("season_2024_goals") or scorer_data.get("season_2023_goals")
            if minutes and goals and minutes > 0:
                goals_per_90 = round((goals / minutes) * 90, 3)
            
            # Calculer penalty rate
            pen_taken = scorer_data.get("penalties_taken", 0) or 0
            pen_scored = scorer_data.get("penalties_scored", 0) or 0
            pen_rate = round(pen_scored / pen_taken * 100, 1) if pen_taken > 0 else None
            
            cur.execute("""
                INSERT INTO scorer_intelligence (
                    player_name, player_name_normalized, 
                    api_football_id, photo_url, nationality, age, height_cm,
                    current_team, position_primary,
                    season, season_matches, season_goals, season_assists,
                    season_minutes, goals_per_90,
                    is_penalty_taker, penalties_taken, penalties_scored,
                    penalty_conversion_rate,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    NOW(), NOW()
                )
                ON CONFLICT (player_name_normalized) 
                DO UPDATE SET
                    current_team = EXCLUDED.current_team,
                    season_matches = EXCLUDED.season_matches,
                    season_goals = EXCLUDED.season_goals,
                    season_assists = EXCLUDED.season_assists,
                    season_minutes = EXCLUDED.season_minutes,
                    goals_per_90 = EXCLUDED.goals_per_90,
                    updated_at = NOW()
            """, (
                player_name,
                normalized,
                scorer_data.get("api_football_id"),
                scorer_data.get("photo_url"),
                scorer_data.get("nationality"),
                scorer_data.get("age"),
                scorer_data.get("height_cm"),
                scorer_data.get("current_team"),
                scorer_data.get("position_primary"),
                "2024-25",  # Saison actuelle
                scorer_data.get("season_2024_matches") or scorer_data.get("season_2023_matches"),
                scorer_data.get("season_2024_goals") or scorer_data.get("season_2023_goals"),
                scorer_data.get("season_2023_assists"),
                scorer_data.get("season_2024_minutes") or scorer_data.get("season_2023_minutes"),
                goals_per_90,
                scorer_data.get("is_penalty_taker", False),
                pen_taken,
                pen_scored,
                pen_rate
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur upsert {scorer_data.get('player_name')}: {e}")
            return False
        finally:
            cur.close()
    
    # ════════════════════════════════════════════════════════════
    # EXÉCUTION PRINCIPALE
    # ════════════════════════════════════════════════════════════
    
    def collect_all(self, use_api_football: bool = True, use_fbref: bool = True):
        """Collecte hybride complète"""
        
        logger.info("��️ FERRARI SCORER COLLECTOR - Mode Hybride")
        logger.info("=" * 60)
        
        conn = self._get_conn()
        stats = {"api_football": 0, "fbref": 0, "merged": 0, "inserted": 0}
        
        # Index FBref par nom normalisé
        fbref_index = {}
        
        # ═══ ÉTAPE 1: Collecter FBref 2024 ═══
        if use_fbref:
            logger.info("\n📊 ÉTAPE 1: Collecte FBref (2024)")
            logger.info("-" * 40)
            
            for league_name in FBREF_URLS.keys():
                players = self.fetch_fbref_scorers(league_name)
                for p in players:
                    norm_name = self.normalize_player_name(p.get("player_name"))
                    fbref_index[norm_name] = p
                    stats["fbref"] += 1
                
                time.sleep(3)  # Respecter les serveurs
            
            logger.info(f"✅ FBref: {stats['fbref']} joueurs collectés")
        
        # ═══ ÉTAPE 2: Collecter API-Football 2023 ═══
        if use_api_football:
            logger.info("\n�� ÉTAPE 2: Collecte API-Football (2023)")
            logger.info("-" * 40)
            
            for league_id, league_info in LEAGUES.items():
                logger.info(f"  📍 {league_info['name']}...")
                
                players = self.fetch_api_football_scorers(league_id, season=2023)
                
                for p in players:
                    parsed = self.parse_api_football_player(p)
                    stats["api_football"] += 1
                    
                    # Chercher match FBref
                    norm_name = self.normalize_player_name(parsed.get("player_name"))
                    fbref_data = fbref_index.get(norm_name)
                    
                    if fbref_data:
                        stats["merged"] += 1
                        parsed = self.merge_player_data(parsed, fbref_data)
                    
                    # Insérer
                    if self.upsert_scorer(conn, parsed):
                        stats["inserted"] += 1
                
                time.sleep(1)  # Rate limit
        
        # ═══ ÉTAPE 3: Insérer joueurs FBref non matchés ═══
        logger.info("\n📊 ÉTAPE 3: Insertion FBref uniquement")
        for norm_name, fbref_data in fbref_index.items():
            # Vérifier si déjà inséré
            cur = conn.cursor()
            cur.execute("""
                SELECT id FROM scorer_intelligence 
                WHERE player_name_normalized = %s
            """, (norm_name,))
            
            if not cur.fetchone():
                if self.upsert_scorer(conn, fbref_data):
                    stats["inserted"] += 1
            cur.close()
        
        conn.close()
        
        # ═══ RÉSUMÉ ═══
        logger.info("\n" + "=" * 60)
        logger.info("🏆 COLLECTE TERMINÉE!")
        logger.info(f"  📊 API-Football: {stats['api_football']} joueurs")
        logger.info(f"  📊 FBref: {stats['fbref']} joueurs")
        logger.info(f"  🔄 Fusionnés: {stats['merged']}")
        logger.info(f"  ✅ Insérés: {stats['inserted']}")
        logger.info("=" * 60)
        
        return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Collecteur de buteurs hybride")
    parser.add_argument("--api-only", action="store_true", help="API-Football uniquement")
    parser.add_argument("--fbref-only", action="store_true", help="FBref uniquement")
    
    args = parser.parse_args()
    
    collector = ScorerCollectorHybrid()
    
    if args.api_only:
        collector.collect_all(use_api_football=True, use_fbref=False)
    elif args.fbref_only:
        collector.collect_all(use_api_football=False, use_fbref=True)
    else:
        collector.collect_all()
