"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  BASE LOADER - Utilitaires de chargement JSON                                        ║
║  Version: 2.0                                                                        ║
║  Architecture Mon_PS - Chess Engine V2.0                                             ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Installation: /home/Mon_ps/quantum/loaders/base_loader.py
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, TypeVar, Type
from datetime import datetime
from functools import lru_cache

from pydantic import BaseModel

# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

# Chemins de base
DATA_ROOT = Path("/home/Mon_ps/data")
QUANTUM_DATA = DATA_ROOT / "quantum_v2"
DEFENSE_DATA = DATA_ROOT / "defense_dna"
GOALKEEPER_DATA = DATA_ROOT / "goalkeeper_dna"
COACH_DATA = DATA_ROOT / "coach_dna"
VARIANCE_DATA = DATA_ROOT / "variance"

# Logger
logger = logging.getLogger("quantum.loaders")

# Type générique pour les modèles Pydantic
T = TypeVar("T", bound=BaseModel)


# ═══════════════════════════════════════════════════════════════════════════════════════
# UTILITAIRES DE CHARGEMENT
# ═══════════════════════════════════════════════════════════════════════════════════════

def load_json(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Charge un fichier JSON de manière sécurisée.
    
    Args:
        filepath: Chemin vers le fichier JSON
        
    Returns:
        Dictionnaire ou None si erreur
    """
    try:
        if not filepath.exists():
            logger.warning(f"Fichier non trouvé: {filepath}")
            return None
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.debug(f"Chargé: {filepath} ({len(str(data))} chars)")
            return data
            
    except json.JSONDecodeError as e:
        logger.error(f"Erreur JSON dans {filepath}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur chargement {filepath}: {e}")
        return None


def save_json(data: Dict[str, Any], filepath: Path) -> bool:
    """
    Sauvegarde un dictionnaire en JSON.
    
    Args:
        data: Données à sauvegarder
        filepath: Chemin de destination
        
    Returns:
        True si succès
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
        logger.debug(f"Sauvegardé: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur sauvegarde {filepath}: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════════════
# NORMALISATION DES NOMS
# ═══════════════════════════════════════════════════════════════════════════════════════

# Mapping des noms d'équipes (variantes → nom canonique)
TEAM_ALIASES: Dict[str, str] = {
    # Premier League
    "man united": "Manchester United",
    "man utd": "Manchester United",
    "manchester utd": "Manchester United",
    "man city": "Manchester City",
    "manchester city": "Manchester City",
    "spurs": "Tottenham",
    "tottenham hotspur": "Tottenham",
    "wolves": "Wolverhampton",
    "wolverhampton wanderers": "Wolverhampton",
    "brighton & hove albion": "Brighton",
    "brighton and hove albion": "Brighton",
    "newcastle united": "Newcastle",
    "west ham united": "West Ham",
    "nottingham forest": "Nott'ham Forest",
    "nottm forest": "Nott'ham Forest",
    "leicester city": "Leicester",
    "ipswich town": "Ipswich",
    
    # La Liga
    "atletico madrid": "Atlético Madrid",
    "atletico": "Atlético Madrid",
    "athletic bilbao": "Athletic Club",
    "athletic": "Athletic Club",
    "real sociedad": "Real Sociedad",
    "celta vigo": "Celta Vigo",
    "celta": "Celta Vigo",
    "real betis": "Betis",
    "rayo vallecano": "Rayo Vallecano",
    "rayo": "Rayo Vallecano",
    
    # Serie A
    "inter milan": "Inter",
    "internazionale": "Inter",
    "ac milan": "Milan",
    "as roma": "Roma",
    "napoli": "Napoli",
    "atalanta bc": "Atalanta",
    "hellas verona": "Verona",
    
    # Bundesliga
    "bayern munich": "Bayern München",
    "bayern munchen": "Bayern München",
    "bayern": "Bayern München",
    "borussia dortmund": "Dortmund",
    "bvb": "Dortmund",
    "rb leipzig": "RB Leipzig",
    "leipzig": "RB Leipzig",
    "bayer leverkusen": "Leverkusen",
    "bayer 04 leverkusen": "Leverkusen",
    "borussia monchengladbach": "M'gladbach",
    "borussia mönchengladbach": "M'gladbach",
    "gladbach": "M'gladbach",
    "eintracht frankfurt": "Eintracht Frankfurt",
    "frankfurt": "Eintracht Frankfurt",
    "vfb stuttgart": "Stuttgart",
    "fc augsburg": "Augsburg",
    "1. fc union berlin": "Union Berlin",
    "union berlin": "Union Berlin",
    "1. fc heidenheim": "Heidenheim",
    "fc st. pauli": "St. Pauli",
    "st pauli": "St. Pauli",
    "tsg hoffenheim": "Hoffenheim",
    "1899 hoffenheim": "Hoffenheim",
    "vfl bochum": "Bochum",
    "vfl wolfsburg": "Wolfsburg",
    "sc freiburg": "Freiburg",
    "1. fsv mainz 05": "Mainz 05",
    "mainz": "Mainz 05",
    "sv werder bremen": "Werder Bremen",
    "werder": "Werder Bremen",
    "holstein kiel": "Holstein Kiel",
    "kiel": "Holstein Kiel",
    
    # Ligue 1
    "paris saint-germain": "PSG",
    "paris saint germain": "PSG",
    "paris sg": "PSG",
    "olympique marseille": "Marseille",
    "om": "Marseille",
    "olympique lyonnais": "Lyon",
    "olympique lyon": "Lyon",
    "ol": "Lyon",
    "as monaco": "Monaco",
    "ogc nice": "Nice",
    "losc lille": "Lille",
    "losc": "Lille",
    "rc lens": "Lens",
    "stade rennais": "Rennes",
    "stade de reims": "Reims",
    "fc nantes": "Nantes",
    "racing club de strasbourg": "Strasbourg",
    "rc strasbourg": "Strasbourg",
    "toulouse fc": "Toulouse",
    "montpellier hsc": "Montpellier",
    "angers sco": "Angers",
    "stade brestois": "Brest",
    "stade brestois 29": "Brest",
    "le havre ac": "Le Havre",
    "aj auxerre": "Auxerre",
    "as saint-etienne": "Saint-Étienne",
    "as saint etienne": "Saint-Étienne",
    "asse": "Saint-Étienne",
}


def normalize_team_name(name: str) -> str:
    """
    Normalise un nom d'équipe vers sa forme canonique.
    
    Args:
        name: Nom brut de l'équipe
        
    Returns:
        Nom canonique
    """
    if not name:
        return ""
    
    # Nettoyer
    cleaned = name.strip().lower()
    
    # Chercher dans les aliases
    if cleaned in TEAM_ALIASES:
        return TEAM_ALIASES[cleaned]
    
    # Sinon retourner le nom original avec capitalisation
    return name.strip()


def get_team_key(name: str) -> str:
    """
    Génère une clé normalisée pour lookup.
    
    Args:
        name: Nom de l'équipe
        
    Returns:
        Clé lowercase sans espaces
    """
    normalized = normalize_team_name(name)
    return normalized.lower().replace(" ", "_").replace("-", "_").replace("'", "")


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONVERSION DE VALEURS
# ═══════════════════════════════════════════════════════════════════════════════════════

def safe_float(value: Any, default: float = 0.0) -> float:
    """Convertit en float de manière sécurisée."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Convertit en int de manière sécurisée."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    """Convertit en bool de manière sécurisée."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "oui")
    try:
        return bool(value)
    except:
        return default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Limite une valeur entre min et max."""
    return max(min_val, min(max_val, value))


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse une datetime depuis différents formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
        ]:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


# ═══════════════════════════════════════════════════════════════════════════════════════
# CACHE & INDEX
# ═══════════════════════════════════════════════════════════════════════════════════════

class DataIndex:
    """
    Index centralisé pour lookup rapide des équipes.
    """
    
    def __init__(self):
        self._teams: Dict[str, Any] = {}
        self._aliases: Dict[str, str] = {}
        self._loaded_files: set = set()
    
    def register_team(self, canonical_name: str, data: Any, aliases: List[str] = None):
        """Enregistre une équipe dans l'index."""
        key = get_team_key(canonical_name)
        self._teams[key] = data
        
        # Enregistrer les aliases
        if aliases:
            for alias in aliases:
                alias_key = get_team_key(alias)
                self._aliases[alias_key] = key
    
    def get_team(self, name: str) -> Optional[Any]:
        """Récupère une équipe par nom ou alias."""
        key = get_team_key(name)
        
        # Direct lookup
        if key in self._teams:
            return self._teams[key]
        
        # Alias lookup
        if key in self._aliases:
            canonical_key = self._aliases[key]
            return self._teams.get(canonical_key)
        
        return None
    
    def list_teams(self) -> List[str]:
        """Liste toutes les équipes enregistrées."""
        return list(self._teams.keys())
    
    def clear(self):
        """Vide l'index."""
        self._teams.clear()
        self._aliases.clear()
        self._loaded_files.clear()


# Index global
_global_index = DataIndex()


def get_global_index() -> DataIndex:
    """Retourne l'index global."""
    return _global_index


# ═══════════════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════════════

def validate_required_fields(data: Dict[str, Any], required: List[str]) -> List[str]:
    """
    Vérifie que tous les champs requis sont présents.
    
    Returns:
        Liste des champs manquants
    """
    missing = []
    for field in required:
        if field not in data or data[field] is None:
            missing.append(field)
    return missing


def calculate_data_quality(data: Dict[str, Any], expected_fields: List[str]) -> str:
    """
    Calcule la qualité des données basée sur la complétude.
    
    Returns:
        HIGH, MODERATE, LOW, ou INSUFFICIENT
    """
    if not data:
        return "INSUFFICIENT"
    
    present = sum(1 for f in expected_fields if f in data and data[f] is not None)
    ratio = present / len(expected_fields) if expected_fields else 0
    
    if ratio >= 0.9:
        return "HIGH"
    elif ratio >= 0.7:
        return "MODERATE"
    elif ratio >= 0.5:
        return "LOW"
    else:
        return "INSUFFICIENT"
