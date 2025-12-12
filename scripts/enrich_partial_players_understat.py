#!/usr/bin/env python3
"""
ENRICHISSEMENT JOUEURS PARTIELS VIA UNDERSTAT
Cible: joueurs avec data_completeness='partial' ou needs_enrichment=True
"""

from curl_cffi import requests
import json
import re
import time
import random
import unicodedata
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fichiers
UNIFIED_FILE = '/home/Mon_ps/data/quantum_v2/player_dna_unified.json'
OUTPUT_FILE = '/home/Mon_ps/data/quantum_v2/player_dna_unified.json'
UNDERSTAT_CACHE = '/home/Mon_ps/data/understat/understat_players_cache.json'
UNDERSTAT_EXISTING = '/home/Mon_ps/data/quantum_v2/players_impact_dna.json'  # Donnees existantes!

# Configuration scraping
BROWSERS = ["chrome110", "chrome116", "safari15_3", "edge99"]
DELAY_MIN = 2
DELAY_MAX = 4

# Mapping ligues
LEAGUES = {
    'EPL': 'EPL',
    'La_Liga': 'La_liga',
    'Bundesliga': 'Bundesliga',
    'Serie_A': 'Serie_A',
    'Ligue_1': 'Ligue_1'
}

# ============================================================================
# SCRAPING UNDERSTAT
# ============================================================================

def fetch_understat_page(url: str) -> Optional[str]:
    """Fetch une page Understat avec curl_cffi"""
    browser = random.choice(BROWSERS)
    delay = random.uniform(DELAY_MIN, DELAY_MAX)

    time.sleep(delay)

    try:
        response = requests.get(
            url,
            impersonate=browser,
            timeout=30
        )

        if response.status_code == 200:
            return response.text
        else:
            logger.warning(f"Status {response.status_code} pour {url}")
            return None

    except Exception as e:
        logger.error(f"Erreur fetch {url}: {e}")
        return None


def extract_players_data(html: str) -> List[Dict]:
    """Extrait les donnees joueurs depuis HTML Understat"""
    # Format: playersData = JSON.parse('...')
    match = re.search(r"playersData\s*=\s*JSON\.parse\('(.+?)'\)", html)

    if not match:
        return []

    try:
        # Decoder les caracteres echappes
        json_str = match.group(1)
        json_str = json_str.encode().decode('unicode_escape')
        players = json.loads(json_str)
        return players
    except Exception as e:
        logger.error(f"Erreur parsing JSON: {e}")
        return []


def scrape_all_understat_players() -> Dict[str, Dict]:
    """Scrape tous les joueurs de toutes les ligues Understat"""
    all_players = {}

    for league_key, understat_league in LEAGUES.items():
        url = f"https://understat.com/league/{understat_league}"
        logger.info(f"Scraping {league_key} ({url})...")

        html = fetch_understat_page(url)
        if not html:
            continue

        players = extract_players_data(html)
        logger.info(f"  {len(players)} joueurs trouves")

        for player in players:
            name = player.get('player_name', '')
            if name:
                player['league'] = league_key
                all_players[normalize_name(name)] = player

    return all_players


# ============================================================================
# NORMALISATION
# ============================================================================

def normalize_name(name: str) -> str:
    """Normalise un nom pour le matching"""
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    return name.lower().strip()


def create_name_variants(name: str) -> List[str]:
    """Cree des variantes d'un nom"""
    variants = []

    # Nettoyer le nom
    clean_name = name.split('_')[0] if '_' in name else name

    variants.append(normalize_name(clean_name))

    parts = clean_name.split()
    if len(parts) >= 2:
        variants.append(normalize_name(" ".join(parts)))
        variants.append(normalize_name(parts[0] + " " + parts[-1]))
        variants.append(normalize_name(parts[-1]))

    return list(set(v for v in variants if v))


# ============================================================================
# ENRICHISSEMENT
# ============================================================================

def extract_understat_stats(player_data: Dict) -> Dict:
    """Extrait les stats Understat pertinentes"""
    return {
        "source": "understat",
        "updated_at": datetime.now().isoformat(),
        "player_id": player_data.get('id'),
        "player_name": player_data.get('player_name'),
        "team": player_data.get('team_title', ''),
        "position": player_data.get('position', ''),

        # Stats offensives
        "games": int(player_data.get('games', 0)),
        "time": int(player_data.get('time', 0)),
        "goals": int(player_data.get('goals', 0)),
        "assists": int(player_data.get('assists', 0)),
        "shots": int(player_data.get('shots', 0)),
        "key_passes": int(player_data.get('key_passes', 0)),

        # xG metrics
        "xG": float(player_data.get('xG', 0)),
        "xA": float(player_data.get('xA', 0)),
        "npxG": float(player_data.get('npxG', 0)),
        "xGChain": float(player_data.get('xGChain', 0)),
        "xGBuildup": float(player_data.get('xGBuildup', 0)),

        # Derived
        "xG_diff": round(int(player_data.get('goals', 0)) - float(player_data.get('xG', 0)), 2),
        "npg": int(player_data.get('npg', player_data.get('goals', 0))),
    }


def load_existing_understat() -> Dict[str, Dict]:
    """Charge les donnees Understat existantes depuis players_impact_dna.json"""
    try:
        with open(UNDERSTAT_EXISTING, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Indexer par nom normalise
        index = {}
        for player in data:
            name = player.get('player_name', '')
            if name:
                index[normalize_name(name)] = player

        return index
    except Exception as e:
        logger.error(f"Erreur chargement Understat existant: {e}")
        return {}


def main():
    logger.info("=" * 70)
    logger.info("ENRICHISSEMENT JOUEURS PARTIELS VIA UNDERSTAT")
    logger.info("=" * 70)

    # 1. Charger unified
    logger.info("\n1. Chargement player_dna_unified...")
    with open(UNIFIED_FILE, 'r', encoding='utf-8') as f:
        unified_data = json.load(f)
    logger.info(f"   Total joueurs: {len(unified_data['players'])}")

    # 2. Identifier joueurs partiels
    partial_players = []
    for name, player in unified_data['players'].items():
        if player.get('needs_enrichment') or player.get('data_completeness') == 'partial':
            partial_players.append(name)

    logger.info(f"   Joueurs partiels: {len(partial_players)}")

    if not partial_players:
        logger.info("Aucun joueur partiel a enrichir!")
        return

    # 3. Charger donnees Understat EXISTANTES (pas de scraping!)
    logger.info("\n2. Chargement donnees Understat existantes...")

    understat_players = load_existing_understat()
    logger.info(f"   Total joueurs Understat: {len(understat_players)}")

    # 4. Enrichir joueurs partiels
    logger.info("\n3. Enrichissement...")

    stats = {
        'enriched': 0,
        'not_found': 0,
        'already_full': 0
    }

    for player_name in partial_players:
        player_data = unified_data['players'][player_name]

        # Chercher dans Understat
        variants = create_name_variants(player_name)
        match = None

        for variant in variants:
            if variant in understat_players:
                match = understat_players[variant]
                break

        if match:
            # Enrichir avec Understat
            understat_stats = extract_understat_stats(match)
            player_data['understat'] = understat_stats

            # Mettre a jour completeness
            player_data['data_completeness'] = 'full'
            player_data['needs_enrichment'] = False

            if 'missing_sources' in player_data:
                missing = player_data['missing_sources']
                if 'understat' in missing:
                    missing.remove('understat')
                player_data['missing_sources'] = missing

            stats['enriched'] += 1
        else:
            stats['not_found'] += 1

    # 5. Mettre a jour metadata
    unified_data['metadata']['understat_enrichment'] = {
        'enriched_at': datetime.now().isoformat(),
        'stats': stats
    }

    # 6. Sauvegarder
    logger.info("\n4. Sauvegarde...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, indent=2, ensure_ascii=False)

    # Resume
    logger.info("\n" + "=" * 70)
    logger.info("ENRICHISSEMENT TERMINE")
    logger.info("=" * 70)

    logger.info(f"\nResultats:")
    logger.info(f"   Enrichis: {stats['enriched']}")
    logger.info(f"   Non trouves: {stats['not_found']}")

    # Verifier combien restent partiels
    remaining_partial = sum(1 for p in unified_data['players'].values()
                          if p.get('needs_enrichment') or p.get('data_completeness') == 'partial')
    logger.info(f"   Restent partiels: {remaining_partial}")


if __name__ == "__main__":
    main()
