"""
Configuration FBRef Ingestion Service
═══════════════════════════════════════════════════════════════════════════
Seuils de validation Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════
"""
from dataclasses import dataclass
from typing import List
from pathlib import Path


@dataclass
class FBRefConfig:
    """Configuration pour FBRef Ingestion Service."""

    # === SEUILS DE VALIDATION ===
    # Minimum absolu pour accepter les données
    MIN_PLAYERS_REQUIRED: int = 500

    # Minimum par ligue (si < seuil, warning mais pas rejet)
    MIN_PLAYERS_PER_LEAGUE: int = 80

    # Ligues attendues
    EXPECTED_LEAGUES: List[str] = None

    # === CHEMINS FICHIERS ===
    RAW_JSON_PATH: Path = None
    CLEAN_JSON_PATH: Path = None
    BACKUP_DIR: Path = None

    # === DATABASE ===
    DB_TABLE: str = "fbref_player_stats_full"
    DB_SCHEMA: str = "public"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "monps_db"
    DB_USER: str = "monps_user"
    DB_PASSWORD: str = "monps_secure_password_2024"

    # === VALIDATION MÉTRIQUES ===
    # Colonnes obligatoires (si absentes = rejet)
    REQUIRED_COLUMNS: List[str] = None

    # Seuils soft (warning si hors range)
    XG_90_SOFT_MIN: float = 0.0
    XG_90_SOFT_MAX: float = 1.5
    SHOTS_90_SOFT_MIN: float = 0.0
    SHOTS_90_SOFT_MAX: float = 8.0

    # Seuils hard (rejet si hors range - données corrompues)
    XG_90_HARD_MAX: float = 5.0
    SHOTS_90_HARD_MAX: float = 20.0

    def __post_init__(self):
        if self.EXPECTED_LEAGUES is None:
            self.EXPECTED_LEAGUES = [
                "EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"
            ]

        if self.RAW_JSON_PATH is None:
            self.RAW_JSON_PATH = Path("/home/Mon_ps/data/fbref/fbref_players_complete_2025_26.json")

        if self.CLEAN_JSON_PATH is None:
            self.CLEAN_JSON_PATH = Path("/home/Mon_ps/data/fbref/fbref_players_clean_2025_26.json")

        if self.BACKUP_DIR is None:
            self.BACKUP_DIR = Path("/home/Mon_ps/data/fbref/backups")

        if self.REQUIRED_COLUMNS is None:
            self.REQUIRED_COLUMNS = [
                "player_name", "team", "league", "minutes_90",
                "xg", "xg_90", "shots", "shots_90"
            ]


# Instance par défaut
DEFAULT_CONFIG = FBRefConfig()
