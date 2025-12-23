"""
THE QUANTUM SOVEREIGN V3.8 - CONFIGURATION
Paramètres centralisés du système.
Créé le: 23 Décembre 2025
"""

from dataclasses import dataclass, field
from typing import Dict, List


# ═══════════════════════════════════════════════════════════
# VERSIONING
# ═══════════════════════════════════════════════════════════

MODEL_VERSION = "v3.8.0"
ALPHA_WEIGHTS_VERSION = "2024-12-23"


# ═══════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════

POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

CONTAINER_NAME = "monps_postgres"


# ═══════════════════════════════════════════════════════════
# SYSTEM CONFIGURATION
# ═══════════════════════════════════════════════════════════

@dataclass
class SystemConfig:
    """Configuration centralisée du système Quantum Sovereign V3.8"""

    # ═══════════════════════════════════════════════════════════
    # BUDGET & LIMITES
    # ═══════════════════════════════════════════════════════════
    CLAUDE_DAILY_BUDGET_USD: float = 5.0
    MAX_STAKE_PERCENT: float = 0.02          # 2% bankroll max par bet
    MAX_DAILY_EXPOSURE: float = 0.10         # 10% bankroll total/jour

    # ═══════════════════════════════════════════════════════════
    # CIRCUIT BREAKERS
    # ═══════════════════════════════════════════════════════════
    DRAWDOWN_PAUSE_THRESHOLD: float = 0.05   # Pause si -5%
    CONSECUTIVE_LOSSES_PAUSE: int = 3        # Pause après 3 pertes
    MIN_CONVERGENCE_SCORE: float = 50.0      # Skip si convergence < 50

    # ═══════════════════════════════════════════════════════════
    # RETRY & TIMEOUTS
    # ═══════════════════════════════════════════════════════════
    CLAUDE_TIMEOUT_SEC: int = 30
    CLAUDE_MAX_RETRIES: int = 3
    RSS_TIMEOUT_SEC: int = 5
    DB_TIMEOUT_SEC: int = 10

    # ═══════════════════════════════════════════════════════════
    # DATA FRESHNESS
    # ═══════════════════════════════════════════════════════════
    FRESH_THRESHOLD_DAYS: int = 3
    AGING_THRESHOLD_DAYS: int = 7
    STALE_CONFIDENCE_PENALTY: float = 0.30   # -30% confiance si données vieilles

    # ═══════════════════════════════════════════════════════════
    # ALPHA HUNTER - Poids de scoring
    # ═══════════════════════════════════════════════════════════
    ALPHA_WEIGHTS: Dict = field(default_factory=lambda: {
        "dna": 0.4,
        "friction": 0.4,
        "luck": 0.2,
        "version": ALPHA_WEIGHTS_VERSION
    })

    # ═══════════════════════════════════════════════════════════
    # ALPHA HUNTER - Niveaux de filtrage progressif
    # ═══════════════════════════════════════════════════════════
    FILTER_LEVELS: List[Dict] = field(default_factory=lambda: [
        {"name": "STRICT",  "odds_range": (1.50, 2.50), "min_edge": 0.03, "min_sample": 15},
        {"name": "RELAXED", "odds_range": (1.40, 2.80), "min_edge": 0.025, "min_sample": 10},
        {"name": "WIDE",    "odds_range": (1.30, 3.00), "min_edge": 0.02, "min_sample": 5},
    ])

    # ═══════════════════════════════════════════════════════════
    # SEASONALITY - Ajustements saisonniers
    # ═══════════════════════════════════════════════════════════
    SEASON_PROFILES: Dict = field(default_factory=lambda: {
        "early_season": {
            "months": [8, 9],
            "confidence_penalty": 0.15,
            "description": "Début de saison - équipes pas encore rodées"
        },
        "congestion": {
            "months": [12],
            "confidence_penalty": 0.10,
            "description": "Décembre - matchs tous les 3 jours"
        },
        "end_season": {
            "months": [5],
            "confidence_penalty": 0.05,
            "description": "Fin de saison - motivations variables"
        }
    })

    # ═══════════════════════════════════════════════════════════
    # EXECUTION MODE
    # ═══════════════════════════════════════════════════════════
    DEFAULT_EXECUTION_MODE: str = "SHADOW"

    # ═══════════════════════════════════════════════════════════
    # MONTE CARLO
    # ═══════════════════════════════════════════════════════════
    MC_SIMULATIONS: int = 5000
    MC_BASE_SIGMA: float = 1.2

    # ═══════════════════════════════════════════════════════════
    # DRIFT DETECTION
    # ═══════════════════════════════════════════════════════════
    DRIFT_WINDOW_SIZE: int = 50              # Fenêtre glissante 50 picks
    DRIFT_CRITICAL_THRESHOLD: float = -0.02  # CLV moyen < -2% = critique
    DRIFT_MODERATE_THRESHOLD: float = 0.0    # CLV moyen < 0% = modéré


# ═══════════════════════════════════════════════════════════
# INSTANCE GLOBALE
# ═══════════════════════════════════════════════════════════

CONFIG = SystemConfig()


# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════

def get_db_connection_string() -> str:
    """Retourne la connection string PostgreSQL"""
    return (
        f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}"
        f"@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"
    )


def get_docker_psql_command(sql: str) -> str:
    """Retourne la commande docker pour exécuter du SQL"""
    return (
        f"docker exec {CONTAINER_NAME} psql -U {POSTGRES_CONFIG['user']} "
        f"-d {POSTGRES_CONFIG['database']} -c \"{sql}\""
    )
