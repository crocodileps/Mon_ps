"""
Quantum Orchestrator - Point d'entrée Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════

Usage:
    from quantum_core.orchestrator import get_quantum_orchestrator

    orchestrator = get_quantum_orchestrator()
    analysis = orchestrator.analyze_match("Liverpool", "Manchester City")
"""

from .quantum_orchestrator_v2 import (
    QuantumOrchestratorV2,
    get_quantum_orchestrator,
    MatchAnalysis,
    TeamAnalysis,
    FrictionAnalysis,
    MLConfidence,
    TacticalProfile,
    ClashType,
    DataQuality
)

__all__ = [
    "QuantumOrchestratorV2",
    "get_quantum_orchestrator",
    "MatchAnalysis",
    "TeamAnalysis",
    "FrictionAnalysis",
    "MLConfidence",
    "TacticalProfile",
    "ClashType",
    "DataQuality"
]
