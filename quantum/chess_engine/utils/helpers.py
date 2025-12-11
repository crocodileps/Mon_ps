"""
CHESS ENGINE V2.0 - HELPERS
"""

from typing import Any, Dict, Optional
from datetime import datetime
import json


def safe_get(d: dict, *keys, default=None) -> Any:
    """Recupere une valeur imbriquee de facon securisee"""
    result = d
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key, default)
        else:
            return default
    return result if result is not None else default


def normalize_team_name(name: str) -> str:
    """Normalise le nom d'equipe pour matching"""
    replacements = {
        "Man City": "Manchester City",
        "Man United": "Manchester United",
        "Man Utd": "Manchester United",
        "Spurs": "Tottenham",
        "Wolves": "Wolverhampton",
        "PSG": "Paris Saint Germain",
    }
    name = name.strip()
    return replacements.get(name, name)


def get_team_tier(team_name: str, tiers: dict) -> str:
    """Retourne le tier d'une equipe"""
    for tier, teams in tiers.items():
        if team_name in teams:
            return tier
    return "STANDARD"


def calculate_edge(our_prob: float, market_odds: float) -> float:
    """Calcule l'edge"""
    implied_prob = 1 / market_odds
    return our_prob - implied_prob


def get_market_category(market: str) -> str:
    """Retourne la categorie d'un marche"""
    from .constants import MARKET_CATEGORIES
    for category, markets in MARKET_CATEGORIES.items():
        if market in markets:
            return category
    return "OTHER"


def timestamp_now() -> str:
    """Retourne timestamp actuel ISO"""
    return datetime.now().isoformat()


def save_json(data: Any, filepath: str) -> None:
    """Sauvegarde en JSON"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def load_json(filepath: str) -> Any:
    """Charge un JSON"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)
