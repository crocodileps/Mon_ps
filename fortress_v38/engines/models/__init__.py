"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    FORTRESS V38 - PREDICTION MODELS                           ║
║                    7 Modèles Ensemble + Structures de base                    ║
║                    Version: 1.0 - Hedge Fund Grade                            ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Modèles de prédiction:
- Model A: TeamStrategy (+1,434.6u) ✅ Phase 2b
- Model B: QuantumScorer (r=+0.53) ✅ Phase 2c
- Model C: MatchupScorer (+10% ROI) ✅ Phase 2d
- Model D: DixonColes (Probabilités) ✅ Phase 2e
- Model E: Scenarios (20 scénarios)
- Model F: DNAFeatures (11 vecteurs)
- Model G: MicroStrategy (126 marchés)
"""

# ═══════════════════════════════════════════════════════════════════════════════
# BASE STRUCTURES (Phase 2a)
# ═══════════════════════════════════════════════════════════════════════════════

from .base import (
    # Enums
    ModelName,
    Signal,
    Conviction,
    MomentumTrend,
    ConflictResolution,
    Robustness,
    CLVSignal,
    # Dataclass
    ModelVote,
    # ABC
    BaseModel,
    # Constantes
    BASE_MODEL_WEIGHTS,
    BASE_VERSION,
)

# ═══════════════════════════════════════════════════════════════════════════════
# MODEL A: TEAM STRATEGY (Phase 2b)
# ═══════════════════════════════════════════════════════════════════════════════

from .team_strategy import ModelTeamStrategy

# ═══════════════════════════════════════════════════════════════════════════════
# MODEL B: QUANTUM SCORER (Phase 2c)
# ═══════════════════════════════════════════════════════════════════════════════

from .quantum_scorer import ModelQuantumScorer

# ═══════════════════════════════════════════════════════════════════════════════
# MODEL C: MATCHUP SCORER (Phase 2d)
# ═══════════════════════════════════════════════════════════════════════════════

from .matchup_scorer import ModelMatchupScorer

# ═══════════════════════════════════════════════════════════════════════════════
# MODEL D: DIXON-COLES (Phase 2e)
# ═══════════════════════════════════════════════════════════════════════════════

from .dixon_coles import ModelDixonColes

# ═══════════════════════════════════════════════════════════════════════════════
# MODÈLES À VENIR
# ═══════════════════════════════════════════════════════════════════════════════

# Phase 2f: from .scenarios import ModelScenarios
# Phase 2g: from .dna_features import ModelDNAFeatures
# Phase 2h: from .microstrategy import MicroStrategyModel

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "ModelName",
    "Signal",
    "Conviction",
    "MomentumTrend",
    "ConflictResolution",
    "Robustness",
    "CLVSignal",
    # Dataclass
    "ModelVote",
    # ABC
    "BaseModel",
    # Constantes
    "BASE_MODEL_WEIGHTS",
    "BASE_VERSION",
    # Models
    "ModelTeamStrategy",   # Phase 2b
    "ModelQuantumScorer",  # Phase 2c
    "ModelMatchupScorer",  # Phase 2d
    "ModelDixonColes",     # Phase 2e
]
