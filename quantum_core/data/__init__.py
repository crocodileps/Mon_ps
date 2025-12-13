"""
Quantum Core Data Layer
═══════════════════════════════════════════════════════════════════════════

Point d'entree: DataOrchestrator

L'orchestrateur reutilise les composants existants de quantum/:
- unified_loader.py (JSON)
- dna_vectors.py (structures)
- PostgreSQL quantum.* (donnees temps reel)
"""

from .orchestrator import DataOrchestrator, get_orchestrator
from .orchestrator import FrictionResult, MatchContext

__all__ = [
    "DataOrchestrator",
    "get_orchestrator",
    "FrictionResult",
    "MatchContext"
]
