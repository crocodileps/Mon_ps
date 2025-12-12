#!/usr/bin/env python3
"""
Scraping FBRef COMPLET - Saison 2025/2026
METHODE: curl_cffi avec rotation de fingerprints
Hedge Fund Grade - Toutes positions (MF, FW, DF)
"""

from curl_cffi import requests
from bs4 import BeautifulSoup, Comment
import pandas as pd
import json
import time
import random
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import re

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION CURL_CFFI - ANTI-BOT BYPASS
# ============================================================================

BROWSERS = ["chrome110", "chrome116", "safari15_3", "edge99"]  # chrome110 works best
DELAY_MIN = 3
DELAY_MAX = 6
MAX_RETRIES = 5
TIMEOUT = 30

def get_random_headers():
    """Genere des headers realistes avec variation"""
    chrome_version = random.randint(118, 124)
    return {
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://www.google.com/',
        'Cache-Control': 'no-cache',
    }

def fetch_with_curl_cffi(url: str, max_retries: int = MAX_RETRIES) -> Optional[str]:
    """Fetch une page avec curl_cffi et rotation de fingerprints"""
    for attempt in range(max_retries):
        browser = random.choice(BROWSERS)
        delay = random.uniform(DELAY_MIN, DELAY_MAX)

        logger.info(f"Tentative {attempt+1}/{max_retries} avec {browser} (delay: {delay:.1f}s)")
        time.sleep(delay)

        try:
            response = requests.get(
                url,
                impersonate=browser,
                headers=get_random_headers(),
                timeout=TIMEOUT
            )

            if response.status_code == 200:
                logger.info(f"Succes: {url}")
                return response.text
            else:
                logger.warning(f"Status {response.status_code}")

        except Exception as e:
            logger.error(f"Erreur: {e}")

        # Backoff exponentiel
        time.sleep(delay * (attempt + 1))

    return None

# ============================================================================
# URLS FBREF 2025-26 (SAISON ACTUELLE)
# ============================================================================

LEAGUES = {
    "EPL": {
        "id": 9,
        "name": "Premier-League",
        "display": "Premier League"
    },
    "La_Liga": {
        "id": 12,
        "name": "La-Liga",
        "display": "La Liga"
    },
    "Bundesliga": {
        "id": 20,
        "name": "Bundesliga",
        "display": "Bundesliga"
    },
    "Serie_A": {
        "id": 11,
        "name": "Serie-A",
        "display": "Serie A"
    },
    "Ligue_1": {
        "id": 13,
        "name": "Ligue-1",
        "display": "Ligue 1"
    }
}

# Tables a scraper - STATS JOUEURS (pas equipes)
PLAYER_STATS_TABLES = {
    "standard": {
        "url_suffix": "stats",
        "table_id": "stats_standard",
        "description": "Stats standard par joueur"
    },
    "shooting": {
        "url_suffix": "shooting",
        "table_id": "stats_shooting",
        "description": "Stats de tir par joueur"
    },
    "passing": {
        "url_suffix": "passing",
        "table_id": "stats_passing",
        "description": "Stats de passes par joueur"
    },
    "pass_types": {
        "url_suffix": "passing_types",
        "table_id": "stats_passing_types",
        "description": "Types de passes par joueur"
    },
    "gca": {
        "url_suffix": "gca",
        "table_id": "stats_gca",
        "description": "Goal/Shot Creating Actions par joueur"
    },
    "defense": {
        "url_suffix": "defense",
        "table_id": "stats_defense",
        "description": "Stats defensives par joueur"
    },
    "possession": {
        "url_suffix": "possession",
        "table_id": "stats_possession",
        "description": "Stats de possession par joueur"
    },
    "misc": {
        "url_suffix": "misc",
        "table_id": "stats_misc",
        "description": "Stats diverses (cards, fouls, aerials)"
    }
}

def build_url(league_key: str, stat_type: str) -> str:
    """Construit l'URL FBRef pour une ligue et un type de stat"""
    league = LEAGUES[league_key]
    # Format saison actuelle (2025-26)
    # https://fbref.com/en/comps/9/stats/Premier-League-Stats
    return f"https://fbref.com/en/comps/{league['id']}/{stat_type}/{league['name']}-Stats"

def parse_table_from_html(html: str, table_id: str) -> Optional[pd.DataFrame]:
    """Parse une table FBRef (visible ou cachee dans commentaires)"""
    soup = BeautifulSoup(html, 'html.parser')

    # 1. Chercher table visible
    table = soup.find('table', {'id': table_id})

    # 2. Si pas trouvee, chercher dans les commentaires HTML
    if table is None:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            if table_id in comment:
                comment_soup = BeautifulSoup(comment, 'html.parser')
                table = comment_soup.find('table', {'id': table_id})
                if table:
                    break

    if table is None:
        return None

    try:
        df = pd.read_html(str(table))[0]

        # Gerer multi-index columns
        if isinstance(df.columns, pd.MultiIndex):
            # Prendre le niveau le plus bas
            df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col
                         for col in df.columns.values]

        # Nettoyer les noms de colonnes
        df.columns = [str(col).strip() for col in df.columns]

        return df

    except Exception as e:
        logger.error(f"Erreur parsing table {table_id}: {e}")
        return None

def clean_player_name(name: str) -> str:
    """Nettoie le nom du joueur (enleve drapeaux, etc.)"""
    if pd.isna(name):
        return ""
    # Enlever tout apres le backslash (drapeaux FBRef)
    name = str(name).split("\\")[0].strip()
    # Enlever caracteres speciaux
    name = re.sub(r'[^\w\s\-\'\.\u00C0-\u017F]', '', name)
    return name.strip()

def scrape_player_stats(league_key: str, stat_type: str, config: Dict) -> Optional[pd.DataFrame]:
    """Scrape une table de stats joueurs pour une ligue"""
    url = build_url(league_key, config["url_suffix"])
    logger.info(f"\nScraping {stat_type} pour {LEAGUES[league_key]['display']}")
    logger.info(f"   URL: {url}")

    html = fetch_with_curl_cffi(url)
    if html is None:
        logger.error(f"Echec fetch {url}")
        return None

    df = parse_table_from_html(html, config["table_id"])
    if df is None:
        logger.error(f"Table {config['table_id']} non trouvee")
        return None

    logger.info(f"{len(df)} lignes recuperees")
    return df

def scrape_all_player_stats():
    """Scrape TOUTES les stats joueurs pour TOUTES les ligues"""

    all_data = {
        "metadata": {
            "scraped_date": datetime.now().isoformat(),
            "season": "2025-26",
            "source": "FBRef",
            "method": "curl_cffi",
            "tables": list(PLAYER_STATS_TABLES.keys()),
            "leagues": list(LEAGUES.keys())
        },
        "players": {}
    }

    for league_key in LEAGUES.keys():
        league_display = LEAGUES[league_key]['display']
        logger.info(f"\n{'='*60}")
        logger.info(f"LIGUE: {league_display}")
        logger.info(f"{'='*60}")

        league_players = {}

        for stat_type, config in PLAYER_STATS_TABLES.items():
            df = scrape_player_stats(league_key, stat_type, config)

            if df is None:
                continue

            # Identifier la colonne Player
            player_col = None
            for col in df.columns:
                if 'Player' in col or 'player' in col.lower():
                    player_col = col
                    break

            if player_col is None:
                logger.warning(f"Colonne Player non trouvee dans {stat_type}")
                continue

            # Traiter chaque joueur
            for _, row in df.iterrows():
                player_name = clean_player_name(row.get(player_col, ""))

                # Skip headers repetes et lignes vides
                if not player_name or player_name == "Player" or player_name == "":
                    continue

                # Creer entree joueur si nouvelle
                if player_name not in league_players:
                    # Chercher colonnes team/position
                    team = ""
                    position = ""
                    for col in df.columns:
                        if 'Squad' in col:
                            team = str(row.get(col, "")).strip()
                        if col == 'Pos' or 'Position' in col:
                            position = str(row.get(col, "")).strip()

                    league_players[player_name] = {
                        "team": team,
                        "position": position,
                        "league": league_key
                    }

                # Ajouter donnees de cette table
                table_data = {}
                for col in df.columns:
                    if col != player_col and 'Squad' not in col and col != 'Pos':
                        val = row.get(col)
                        if pd.notna(val):
                            # Convertir en numerique si possible
                            try:
                                if isinstance(val, str):
                                    val = val.replace(',', '').replace('%', '')
                                    if val:
                                        val = float(val)
                            except (ValueError, TypeError):
                                pass
                            table_data[col] = val

                league_players[player_name][stat_type] = table_data

        # Ajouter au global
        for player, data in league_players.items():
            if player not in all_data["players"]:
                all_data["players"][player] = data
            else:
                # Merger (cas rare de transfert)
                for key, val in data.items():
                    if key not in all_data["players"][player]:
                        all_data["players"][player][key] = val

        logger.info(f"\n{league_display}: {len(league_players)} joueurs")

    return all_data

def main():
    """Point d'entree principal"""
    logger.info("="*70)
    logger.info("SCRAPING FBREF COMPLET - SAISON 2025/26")
    logger.info("   Methode: curl_cffi avec rotation fingerprints")
    logger.info("="*70)

    # Scrape
    all_data = scrape_all_player_stats()

    # Stats
    total_players = len(all_data["players"])
    positions = {"MF": 0, "FW": 0, "DF": 0, "GK": 0, "Other": 0}

    for player, data in all_data["players"].items():
        pos = data.get("position", "")
        if "MF" in pos:
            positions["MF"] += 1
        elif "FW" in pos:
            positions["FW"] += 1
        elif "DF" in pos:
            positions["DF"] += 1
        elif "GK" in pos:
            positions["GK"] += 1
        else:
            positions["Other"] += 1

    # Sauvegarder
    output_path = "/home/Mon_ps/data/fbref/fbref_players_complete_2025_26.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    # Resume
    logger.info("\n" + "="*70)
    logger.info("SCRAPING TERMINE")
    logger.info("="*70)
    logger.info(f"Fichier: {output_path}")
    logger.info(f"Total joueurs: {total_players}")
    logger.info(f"   - Milieux (MF): {positions['MF']}")
    logger.info(f"   - Attaquants (FW): {positions['FW']}")
    logger.info(f"   - Defenseurs (DF): {positions['DF']}")
    logger.info(f"   - Gardiens (GK): {positions['GK']}")

    # Taille fichier
    file_size = os.path.getsize(output_path) / (1024*1024)
    logger.info(f"Taille: {file_size:.1f} MB")


if __name__ == "__main__":
    main()
