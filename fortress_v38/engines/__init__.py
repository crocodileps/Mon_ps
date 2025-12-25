"""
FORTRESS V3.8 - Engines Module
==============================

Moteurs de calcul Senior Quant Institutional Grade.

FRICTION SYSTEM V3 (Session 25 Déc 2025):
- friction_config: Configuration et constantes
- friction_loader: Chargement DB (V1+V3 fusion)
- friction_tensor: Calculs Alpha 15/10 (5 dimensions)
- friction_matrix_unified: Matrices de style/tempo/mental
- friction_integration: Pont vers orchestrator
- friction_enrichment_v3: Script d'enrichissement 3,321 paires

AUTRES ENGINES:
- friction_engine: Wrapper legacy (backup)
- quant_engine: Z-Score et calculs statistiques
- runtime_calculators: Coach, Absences, Fatigue
"""

# ═══════════════════════════════════════════════════════════════
# FRICTION SYSTEM V3 (NOUVEAU)
# ═══════════════════════════════════════════════════════════════

# Config (fonctions de configuration)
from .friction_config import (
    get_kinetic_config,
    get_physical_config,
    get_disciplinary_config,
    get_velocity_config,
    get_frustration_config,
    get_spatial_config,
    get_aerial_config,
    normalize_to_100,
    denormalize_from_100,
    FRICTION_CONFIG_VERSION,
)

# Matrices Senior Quant (depuis friction_enrichment_v3.py)
from .friction_enrichment_v3 import (
    STYLE_CLASH_MATRIX,
    PSYCHE_CLASH_MATRIX,
)

# Loader DB (V1+V3 fusion)
from .friction_loader import (
    FrictionLoader,
    FrictionData,
    FrictionVector,
)

# Tensor Alpha 15/10 (5 dimensions)
from .friction_tensor import (
    FrictionTensor,
    FrictionTensorCalculator,
    GameScript,
    TradingSignal,
    VelocityMismatch,
    FrustrationIndex,
    SpatialFriction,
    AerialMismatch,
)

# Matrix Unified
from .friction_matrix_unified import (
    FrictionMatrix,
    PhysicalBreakdown,
)

# Integration (pont vers orchestrator)
from .friction_integration import (
    FrictionIntegration,
    friction_data_to_matrix,
    create_friction_integration,
)

# ═══════════════════════════════════════════════════════════════
# LEGACY (backup)
# ═══════════════════════════════════════════════════════════════
from .friction_engine import FrictionEngine, FrictionOutput

# ═══════════════════════════════════════════════════════════════
# AUTRES ENGINES
# ═══════════════════════════════════════════════════════════════
from .quant_engine import QuantEngine
from .runtime_calculators import (
    CoachImpact,
    AbsenceImpact,
    FatigueImpact,
)

# ═══════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════
__all__ = [
    # Config
    "get_kinetic_config",
    "get_physical_config",
    "get_disciplinary_config",
    "get_velocity_config",
    "FRICTION_CONFIG_VERSION",
    "normalize_to_100",
    "denormalize_from_100",
    # Matrices Senior Quant
    "STYLE_CLASH_MATRIX",
    "PSYCHE_CLASH_MATRIX",
    # Loader
    "FrictionLoader",
    "FrictionData",
    "FrictionVector",
    # Tensor
    "FrictionTensor",
    "FrictionTensorCalculator",
    "GameScript",
    "TradingSignal",
    # Matrix
    "FrictionMatrix",
    "PhysicalBreakdown",
    # Integration
    "FrictionIntegration",
    "friction_data_to_matrix",
    "create_friction_integration",
    # Legacy
    "FrictionEngine",
    "FrictionOutput",
    # Autres
    "QuantEngine",
    "CoachImpact",
    "AbsenceImpact",
    "FatigueImpact",
]
