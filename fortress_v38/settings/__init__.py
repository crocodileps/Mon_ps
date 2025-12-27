"""
FORTRESS V38 - SETTINGS
=======================

Configuration centralisée avec Pydantic Settings V2.

Usage:
    from fortress_v38.settings import SETTINGS, get_settings

    # Accès aux valeurs
    budget = SETTINGS.claude.daily_budget_usd
    mode = SETTINGS.mode
    db_uri = SETTINGS.postgres.uri

Version: 1.0.0
"""

from .models import (
    # Fonction factory (recommandé)
    get_settings,
    # Sous-modèles (pour type hints)
    ClaudeConfig,
    RiskConfig,
    TradingConfig,
    MonteCarloConfig,
    PostgresConfig,
    # Classe principale
    FortressSettings,
)

# Instance singleton - évaluation lazy via get_settings()
# Ceci permet de charger SETTINGS seulement quand .env est prêt
try:
    SETTINGS = get_settings()
except Exception as e:
    # En cas d'erreur de config, on log mais on ne crashe pas l'import
    import logging
    logging.warning(f"Settings not loaded: {e}. Call get_settings() after configuring .env")
    SETTINGS = None

__all__ = [
    "SETTINGS",
    "get_settings",
    "FortressSettings",
    "ClaudeConfig",
    "RiskConfig",
    "TradingConfig",
    "MonteCarloConfig",
    "PostgresConfig",
]

__version__ = "1.0.0"
