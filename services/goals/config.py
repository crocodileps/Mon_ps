#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
GOALS SERVICE - CONFIGURATION
═══════════════════════════════════════════════════════════════════════════════
Configuration centralisée pour le service d'ingestion des buts.

Auteur: Mon_PS Team
Date: 2025-12-23
Branche: feature/goals-unified-ssot
═══════════════════════════════════════════════════════════════════════════════
"""

from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path("/home/Mon_ps")
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Sources
UNDERSTAT_RAW_FILE = DATA_DIR / "quantum_v2" / "understat_raw_api.json"

# Destinations legacy (pour compatibilité)
LEGACY_GOALS_FILE = DATA_DIR / "goal_analysis" / "all_goals_2025.json"
LEGACY_GOALS_BACKUP = DATA_DIR / "goal_analysis" / "all_goals_2025.json.bak"

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION - PROTECTIONS ANTI-BUG
# ═══════════════════════════════════════════════════════════════════════════════

# Minimum de buts requis pour valider une ingestion
# Si on reçoit moins, c'est que le scraping a échoué
MIN_GOALS_REQUIRED = 100

# Ligues supportées
SUPPORTED_LEAGUES = ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1"]

# Mapping des noms de ligues (Understat -> Display)
LEAGUE_NAMES = {
    "EPL": "Premier League",
    "La_liga": "La Liga",
    "Bundesliga": "Bundesliga",
    "Serie_A": "Serie A",
    "Ligue_1": "Ligue 1"
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAPPING STRUCTURE UNDERSTAT
# ═══════════════════════════════════════════════════════════════════════════════
# 
# ATTENTION - BUG HISTORIQUE DOCUMENTÉ:
# Le fichier understat_master_v2.py avait un bug de mapping:
#   - FAUX: match.get('h', {}).get('goals', 0)
#   - CORRECT: match.get('goals', {}).get('h', 0)
#
# Structure réelle d'un match Understat:
# {
#     'id': '28778',
#     'isResult': True,
#     'h': {'id': '87', 'title': 'Liverpool', 'short_title': 'LIV'},
#     'a': {'id': '73', 'title': 'Bournemouth', 'short_title': 'BOU'},
#     'goals': {'h': '4', 'a': '2'},  # SCORES ICI (strings!)
#     'xG': {'h': '2.45', 'a': '1.12'},
#     'datetime': '2025-08-15 19:00:00',
# }
#
# NE JAMAIS REPRODUIRE CE BUG !
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

LOG_FILE = LOGS_DIR / "goals_ingestion.log"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
