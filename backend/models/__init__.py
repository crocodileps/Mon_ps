"""
Models Package - Mon_PS Hedge Fund Grade

Exports all SQLAlchemy models for easy importing.
"""

from models.base import Base, TimestampMixin, AuditMixin, SCHEMA_PUBLIC, SCHEMA_QUANTUM

# Public schema models
from models.odds import Odds, TrackingCLVPicks

# Quantum schema models (legacy)
from models.quantum import (
    TeamQuantumDNA,
    QuantumFrictionMatrix,
    QuantumStrategy,
    ChessClassification,
    GoalscorerProfile,
)

# Quantum V3 models (Phase 6 - Hedge Fund Grade)
from models.quantum_v3 import TeamQuantumDnaV3
from models.friction_matrix_v3 import QuantumFrictionMatrixV3
from models.strategies_v3 import QuantumStrategiesV3

# Export all
__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "AuditMixin",
    "SCHEMA_PUBLIC",
    "SCHEMA_QUANTUM",
    # Public models
    "Odds",
    "TrackingCLVPicks",
    # Quantum models (legacy)
    "TeamQuantumDNA",
    "QuantumFrictionMatrix",
    "QuantumStrategy",
    "ChessClassification",
    "GoalscorerProfile",
    # Quantum V3 models
    "TeamQuantumDnaV3",
    "QuantumFrictionMatrixV3",
    "QuantumStrategiesV3",
]
