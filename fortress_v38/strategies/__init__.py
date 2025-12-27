"""
FORTRESS V38 - STRATEGIES
=========================

Stratégies d'analyse et de décision.

Modules:
- alpha_hunter: Scanner de marchés avec lissage Bayésien
- convergence_engine: Triangulation de signaux (Historical + Friction + Claude)
- seasonality_adjuster: Ajustements saisonniers et motivationnels

Version: 1.0.0
"""

# ═══════════════════════════════════════════════════════════════
# ALPHA HUNTER
# ═══════════════════════════════════════════════════════════════

from .alpha_hunter import (
    # Enums
    MarketRegime,
    FilterLevel,
    # Dataclasses
    MarketCandidate,
    AlphaHunterResult,
    # Classe principale
    AlphaHunter,
)

# ═══════════════════════════════════════════════════════════════
# CONVERGENCE ENGINE
# ═══════════════════════════════════════════════════════════════

from .convergence_engine import (
    # Enums
    SignalSourceType,
    # Dataclasses
    SignalSource,
    ConvergenceResult,
    # Classe principale
    ConvergenceEngine,
    # Config
    CONVERGENCE_CONFIG,
)

# Note: MarketRegime aussi dans convergence_engine, on utilise celui d'alpha_hunter

# ═══════════════════════════════════════════════════════════════
# SEASONALITY ADJUSTER
# ═══════════════════════════════════════════════════════════════

from .seasonality_adjuster import (
    # Enums
    MotivationZone,
    # Dataclasses
    RestZoneInfo,
    TeamSeasonalityFactors,
    SeasonalityResult,
    # Classe principale
    SeasonalityAdjuster,
    # Config
    SEASONALITY_CONFIG,
    MOTIVATION_MATRIX,
)

# ═══════════════════════════════════════════════════════════════
# EXPORTS PUBLICS
# ═══════════════════════════════════════════════════════════════

__all__ = [
    # Alpha Hunter
    "MarketRegime",
    "FilterLevel",
    "MarketCandidate",
    "AlphaHunterResult",
    "AlphaHunter",
    # Convergence Engine
    "SignalSourceType",
    "SignalSource",
    "ConvergenceResult",
    "ConvergenceEngine",
    "CONVERGENCE_CONFIG",
    # Seasonality Adjuster
    "MotivationZone",
    "RestZoneInfo",
    "TeamSeasonalityFactors",
    "SeasonalityResult",
    "SeasonalityAdjuster",
    "SEASONALITY_CONFIG",
    "MOTIVATION_MATRIX",
]

__version__ = "1.0.0"
