"""
FORTRESS V3.8 - Settings (Pydantic V2)
======================================

Configuration centralisée avec validation au runtime.
Standard industriel Hedge Fund Grade.

Hiérarchie de priorité:
1. Variables d'environnement système (plus haute)
2. Fichier .env à la racine du projet
3. Valeurs par défaut (plus basse)

Usage:
    from fortress_v38.settings import SETTINGS

    budget = SETTINGS.claude.daily_budget_usd
    mode = SETTINGS.mode
    db_uri = SETTINGS.postgres.uri

Version: 1.0.0
Date: 27 Décembre 2025
"""

from pathlib import Path
from typing import Literal, Optional
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ═══════════════════════════════════════════════════════════════
# CHEMINS
# ═══════════════════════════════════════════════════════════════

PROJECT_ROOT = Path("/home/Mon_ps")
ENV_FILE = PROJECT_ROOT / ".env"


# ═══════════════════════════════════════════════════════════════
# SOUS-MODÈLES (BaseModel - pas BaseSettings)
# ═══════════════════════════════════════════════════════════════

class ClaudeConfig(BaseModel):
    """Configuration de l'API Claude."""
    daily_budget_usd: float = Field(
        default=5.0,
        gt=0,
        le=100,
        description="Budget journalier max en USD"
    )
    input_cost_per_1m: float = Field(
        default=3.0,
        description="Coût input par million de tokens"
    )
    output_cost_per_1m: float = Field(
        default=15.0,
        description="Coût output par million de tokens"
    )
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=60, ge=10, le=300)


class RiskConfig(BaseModel):
    """Configuration de gestion des risques."""
    max_drawdown_pct: float = Field(
        default=5.0,
        gt=0,
        le=20,
        description="Drawdown max avant stop (%)"
    )
    max_losing_streak: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Pertes consécutives avant pause"
    )
    max_exposure_pct: float = Field(
        default=15.0,
        gt=0,
        le=50,
        description="Exposition max du capital (%)"
    )
    kelly_fraction: float = Field(
        default=0.25,
        ge=0.1,
        le=1.0,
        description="Fraction de Kelly (conservateur)"
    )


class TradingConfig(BaseModel):
    """Configuration des seuils de trading."""
    min_convergence_score: int = Field(
        default=60,
        ge=0,
        le=100,
        description="Score convergence minimum"
    )
    min_edge_pct: float = Field(
        default=2.0,
        ge=0,
        le=20,
        description="Edge minimum pour bet (%)"
    )
    min_liquidity_tier: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Tier liquidité minimum"
    )
    min_confidence: float = Field(
        default=0.55,
        ge=0.5,
        le=1.0,
        description="Confiance minimum"
    )


class MonteCarloConfig(BaseModel):
    """Configuration Monte Carlo."""
    n_simulations: int = Field(
        default=5000,
        ge=100,
        le=100000,
        description="Nombre de simulations"
    )
    noise_level: float = Field(
        default=0.15,
        ge=0,
        le=1.0,
        description="Niveau de bruit"
    )
    confidence_interval: float = Field(
        default=0.95,
        ge=0.8,
        le=0.99,
        description="Intervalle de confiance"
    )


class PostgresConfig(BaseModel):
    """Configuration PostgreSQL."""
    host: str = Field(default="localhost")
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = Field(default="monps_db")
    user: str = Field(default="monps_user")
    password: str = Field(
        default="changeme",
        description="Mot de passe DB (depuis .env)"
    )

    @computed_field
    @property
    def uri(self) -> str:
        """URI de connexion PostgreSQL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION PRINCIPALE
# ═══════════════════════════════════════════════════════════════

class FortressSettings(BaseSettings):
    """
    Configuration Centralisée et Validée - Fortress V3.8.

    Lit automatiquement les variables d'environnement.

    Exemples .env:
        MODE=LIVE
        POSTGRES__PASSWORD=secret
        CLAUDE__DAILY_BUDGET_USD=10.0
        RISK__KELLY_FRACTION=0.20
    """

    # Métadonnées
    version: str = Field(default="3.8.0")
    mode: Literal["SHADOW", "LIVE", "BACKTEST"] = Field(
        default="SHADOW",
        description="Mode d'exécution"
    )

    # Sous-configurations
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    monte_carlo: MonteCarloConfig = Field(default_factory=MonteCarloConfig)
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)

    # Configuration Pydantic Settings
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator('mode', mode='before')
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Normalise le mode en majuscules."""
        if isinstance(v, str):
            return v.upper()
        return v


# ═══════════════════════════════════════════════════════════════
# INSTANCE SINGLETON (Cached)
# ═══════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def get_settings() -> FortressSettings:
    """
    Retourne l'instance singleton des settings.

    Cached pour éviter de relire .env à chaque import.
    Fail-Fast: Crashe au démarrage si config invalide.
    """
    return FortressSettings()


# Pour import direct: from fortress_v38.settings import SETTINGS
# Note: Ne pas appeler get_settings() ici car .env doit être complet
# Les autres modules doivent utiliser get_settings() ou importer après avoir
# vérifié que .env est configuré
