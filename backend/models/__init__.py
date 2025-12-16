"""
Models Package - Mon_PS Hedge Fund Grade

Exports all SQLAlchemy models for easy importing.
"""

from models.base import Base, TimestampMixin, AuditMixin, SCHEMA_PUBLIC, SCHEMA_QUANTUM

# Public schema models
from models.odds import Odds, TrackingCLVPicks

# Quantum schema models
from models.quantum import (
    TeamQuantumDNA,
    QuantumFrictionMatrix,
    QuantumStrategy,
    ChessClassification,
    GoalscorerProfile,
)

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
    # Quantum models
    "TeamQuantumDNA",
    "QuantumFrictionMatrix",
    "QuantumStrategy",
    "ChessClassification",
    "GoalscorerProfile",
]
