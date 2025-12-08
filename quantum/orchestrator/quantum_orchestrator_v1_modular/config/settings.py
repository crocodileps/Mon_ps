"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM ORCHESTRATOR V1.0 - CONFIGURATION                          ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  Configuration centralisée pour:                                                      ║
║  • Connexion PostgreSQL                                                              ║
║  • Seuils de validation                                                              ║
║  • Poids des modèles                                                                 ║
║  • Paramètres Monte Carlo                                                            ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass
from typing import Dict, List
import os


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATABASE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class DatabaseConfig:
    """Configuration PostgreSQL"""
    host: str = "localhost"
    port: int = 5432
    user: str = "monps_user"
    password: str = "monps_secure_password_2024"
    database: str = "monps_db"
    min_pool_size: int = 2
    max_pool_size: int = 10
    
    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def asyncpg_params(self) -> Dict:
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "min_size": self.min_pool_size,
            "max_size": self.max_pool_size
        }


# Instance par défaut
DB_CONFIG = DatabaseConfig()


# ═══════════════════════════════════════════════════════════════════════════════════════
# TABLE NAMES - Mapping des tables PostgreSQL
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class TableNames:
    """Noms des tables PostgreSQL"""
    
    # Schema quantum
    TEAM_PROFILES: str = "quantum.team_profiles"
    TEAM_STRATEGIES: str = "quantum.team_strategies"
    MATCHUP_FRICTION: str = "quantum.matchup_friction"
    MARKET_PERFORMANCE: str = "quantum.market_performance"
    TEMPORAL_PATTERNS: str = "quantum.temporal_patterns"
    BET_SNAPSHOTS: str = "quantum.bet_snapshots"
    MODEL_VOTES: str = "quantum.model_votes"
    AUDIT_SNAPSHOTS: str = "quantum.audit_snapshots"
    
    # Schema public - Odds
    ODDS_HISTORY: str = "public.odds_history"
    ODDS_BTTS: str = "public.odds_btts"
    ODDS_TOTALS: str = "public.odds_totals"
    ODDS_LATEST: str = "public.odds_latest"
    
    # Schema public - Stats
    TEAM_CLASS: str = "public.team_class"
    TEAM_STATISTICS_LIVE: str = "public.team_statistics_live"
    TEAM_NAME_MAPPING: str = "public.team_name_mapping"
    
    # Schema public - Results
    MATCH_RESULTS: str = "public.fg_match_results"
    BETS: str = "public.bets"


TABLES = TableNames()


# ═══════════════════════════════════════════════════════════════════════════════════════
# MODEL WEIGHTS - Poids des 6 modèles (basés sur performance historique)
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ModelWeights:
    """
    Poids des modèles basés sur leur performance historique.
    
    Source: Audit des 99 équipes
    - team_strategy: +1,434.6u validé
    - quantum_scorer: r=+0.53
    - matchup_scorer: Momentum L5
    - dixon_coles: Probabilités calibrées
    - scenarios: 20 scénarios validés
    - dna_features: 11 vecteurs
    """
    
    TEAM_STRATEGY: float = 1.25    # +1,434.6u → surpondéré
    QUANTUM_SCORER: float = 1.15   # r=+0.53 → bon prédicteur
    MATCHUP_SCORER: float = 1.10   # Momentum validé
    DIXON_COLES: float = 1.00      # Baseline
    SCENARIOS: float = 0.85        # À valider sur plus de données
    DNA_FEATURES: float = 1.05     # 11 vecteurs validés
    
    @property
    def total(self) -> float:
        return (self.TEAM_STRATEGY + self.QUANTUM_SCORER + 
                self.MATCHUP_SCORER + self.DIXON_COLES + 
                self.SCENARIOS + self.DNA_FEATURES)
    
    def as_dict(self) -> Dict[str, float]:
        return {
            "team_strategy": self.TEAM_STRATEGY,
            "quantum_scorer": self.QUANTUM_SCORER,
            "matchup_scorer": self.MATCHUP_SCORER,
            "dixon_coles": self.DIXON_COLES,
            "scenarios": self.SCENARIOS,
            "dna_features": self.DNA_FEATURES
        }


MODEL_WEIGHTS = ModelWeights()


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONSENSUS THRESHOLDS - Seuils de validation
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ConsensusConfig:
    """Configuration du consensus engine"""
    
    # Seuils de votes
    MIN_POSITIVE_VOTES: int = 3           # Minimum 3/6 modèles
    WEIGHTED_THRESHOLD: float = 0.50      # 50% du poids total
    
    # Niveaux de conviction
    CONVICTION_MAXIMUM: int = 6           # 6/6 votes
    CONVICTION_STRONG: int = 5            # 5/6 votes
    CONVICTION_MODERATE: int = 4          # 4/6 votes
    
    # Multiplicateurs par conviction
    STAKE_MULTIPLIER_MAXIMUM: float = 1.30
    STAKE_MULTIPLIER_STRONG: float = 1.15
    STAKE_MULTIPLIER_MODERATE: float = 1.00


CONSENSUS_CONFIG = ConsensusConfig()


# ═══════════════════════════════════════════════════════════════════════════════════════
# MONTE CARLO CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class MonteCarloConfig:
    """Configuration du validateur Monte Carlo"""
    
    # Simulations
    N_SIMULATIONS: int = 5000
    NOISE_RANGE: tuple = (-0.15, 0.15)
    
    # Seuils de robustesse
    ROCK_SOLID_SUCCESS_RATE: float = 0.70
    ROCK_SOLID_MAX_STD: float = 15.0
    ROBUST_SUCCESS_RATE: float = 0.55
    ROBUST_MAX_STD: float = 20.0
    UNRELIABLE_SUCCESS_RATE: float = 0.40
    
    # Seuils de validation
    MIN_SCORE_THRESHOLD: float = 45.0
    MIN_EDGE_THRESHOLD: float = 0.02      # 2% minimum edge
    
    # Robustesses acceptées
    VALID_ROBUSTNESS: List[str] = None
    
    def __post_init__(self):
        if self.VALID_ROBUSTNESS is None:
            self.VALID_ROBUSTNESS = ["ROCK_SOLID", "ROBUST", "UNRELIABLE"]


MONTE_CARLO_CONFIG = MonteCarloConfig()


# ═══════════════════════════════════════════════════════════════════════════════════════
# CLV CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class CLVConfig:
    """Configuration du validateur CLV (Closing Line Value)"""
    
    # Sweet spot: 5-10% CLV = +5.21u historique
    SWEET_SPOT_MIN: float = 5.0
    SWEET_SPOT_MAX: float = 10.0
    
    # Danger zone: >10% = souvent trap
    DANGER_THRESHOLD: float = 10.0
    
    # Minimum CLV acceptable
    MIN_CLV: float = 2.0
    
    # Bonus/Malus
    SWEET_SPOT_MULTIPLIER: float = 1.20
    GOOD_CLV_MULTIPLIER: float = 1.10
    DANGER_CLV_MULTIPLIER: float = 0.80


CLV_CONFIG = CLVConfig()


# ═══════════════════════════════════════════════════════════════════════════════════════
# KELLY CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class KellyConfig:
    """Configuration du Bayesian Kelly Calculator"""
    
    # Fraction de Kelly (conservateur)
    KELLY_FRACTION: float = 0.25          # 25% du Kelly optimal
    
    # Limites de stake
    MIN_STAKE: float = 0.5                # 0.5 unité minimum
    MAX_STAKE: float = 5.0                # 5 unités maximum
    STAKE_ROUNDING: float = 0.5           # Arrondi à 0.5u
    
    # Ajustements par DNA
    VARIANCE_PENALTY_THRESHOLD: float = 0.7
    VARIANCE_PENALTY_FACTOR: float = 0.85


KELLY_CONFIG = KellyConfig()


# ═══════════════════════════════════════════════════════════════════════════════════════
# DNA CONFIGURATION - Seuils pour les 11 vecteurs
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class DNAConfig:
    """Configuration des seuils DNA"""
    
    # Psyche DNA
    KILLER_INSTINCT_LOW_THRESHOLD: float = 0.8    # LOW = value
    COMEBACK_MENTALITY_HIGH: float = 2.0
    
    # Luck DNA
    XPOINTS_DELTA_UNLUCKY: float = -2.0           # Très malchanceux
    
    # Temporal DNA
    DIESEL_FACTOR_HIGH: float = 0.65              # Late game killer
    
    # ROI thresholds
    HIGH_ROI_THRESHOLD: float = 30.0
    GOOD_ROI_THRESHOLD: float = 15.0
    
    # Win rate thresholds
    HIGH_WINRATE_THRESHOLD: float = 65.0
    
    # Friction thresholds
    HIGH_FRICTION_THRESHOLD: float = 60.0
    HIGH_CHAOS_THRESHOLD: float = 60.0


DNA_CONFIG = DNAConfig()


# ═══════════════════════════════════════════════════════════════════════════════════════
# BOOKMAKER PREFERENCES
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class BookmakerConfig:
    """Configuration des bookmakers préférés"""
    
    # Bookmakers sharp (référence)
    SHARP_BOOKMAKERS: List[str] = None
    
    # Bookmakers soft (meilleurs odds)
    SOFT_BOOKMAKERS: List[str] = None
    
    # Priorité pour le consensus de cotes
    PRIORITY_ORDER: List[str] = None
    
    def __post_init__(self):
        if self.SHARP_BOOKMAKERS is None:
            self.SHARP_BOOKMAKERS = ["Pinnacle", "Betfair Exchange", "Matchbook"]
        if self.SOFT_BOOKMAKERS is None:
            self.SOFT_BOOKMAKERS = ["1xBet", "Bet365", "Unibet", "888sport"]
        if self.PRIORITY_ORDER is None:
            self.PRIORITY_ORDER = [
                "Pinnacle", "Betfair Exchange", "1xBet", 
                "Bet365", "Unibet", "888sport", "William Hill"
            ]


BOOKMAKER_CONFIG = BookmakerConfig()


# ═══════════════════════════════════════════════════════════════════════════════════════
# LOGGING CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class LoggingConfig:
    """Configuration du logging"""
    
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    
    # Fichiers de log
    LOG_DIR: str = "/home/Mon_ps/quantum/orchestrator/logs"
    LOG_FILE_PICKS: str = "quantum_picks.log"
    LOG_FILE_ERRORS: str = "quantum_errors.log"
    LOG_FILE_DEBUG: str = "quantum_debug.log"


LOGGING_CONFIG = LoggingConfig()


# ═══════════════════════════════════════════════════════════════════════════════════════
# MARKET CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketConfig:
    """Configuration des marchés disponibles"""
    
    # Marchés 1X2
    MARKET_HOME: str = "home_win"
    MARKET_DRAW: str = "draw"
    MARKET_AWAY: str = "away_win"
    
    # Marchés Over/Under
    MARKET_OVER_15: str = "over_15"
    MARKET_OVER_25: str = "over_25"
    MARKET_OVER_35: str = "over_35"
    MARKET_UNDER_15: str = "under_15"
    MARKET_UNDER_25: str = "under_25"
    MARKET_UNDER_35: str = "under_35"
    
    # Marchés BTTS
    MARKET_BTTS_YES: str = "btts_yes"
    MARKET_BTTS_NO: str = "btts_no"
    
    # Marchés prioritaires pour l'analyse
    PRIMARY_MARKETS: List[str] = None
    
    def __post_init__(self):
        if self.PRIMARY_MARKETS is None:
            self.PRIMARY_MARKETS = [
                "over_25", "btts_yes", "home_win", 
                "away_win", "over_35", "btts_no"
            ]


MARKET_CONFIG = MarketConfig()


# ═══════════════════════════════════════════════════════════════════════════════════════
# EXPORT ALL CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════════════════════════════

__all__ = [
    'DB_CONFIG',
    'TABLES',
    'MODEL_WEIGHTS',
    'CONSENSUS_CONFIG',
    'MONTE_CARLO_CONFIG',
    'CLV_CONFIG',
    'KELLY_CONFIG',
    'DNA_CONFIG',
    'BOOKMAKER_CONFIG',
    'LOGGING_CONFIG',
    'MARKET_CONFIG',
    'DatabaseConfig',
    'TableNames',
    'ModelWeights',
    'ConsensusConfig',
    'MonteCarloConfig',
    'CLVConfig',
    'KellyConfig',
    'DNAConfig',
    'BookmakerConfig',
    'LoggingConfig',
    'MarketConfig'
]
