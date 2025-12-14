"""Repository Layer - Data Access.

ADR #008: Layered Architecture.
- Abstract repository interfaces
- Concrete implementations (PostgreSQL, Redis)
- Repository pattern for testability
"""

from quantum_core.repositories.base import BaseRepository
from quantum_core.repositories.prediction_repository import (
    PredictionRepository,
    PostgresPredictionRepository,
)

__all__ = [
    "BaseRepository",
    "PredictionRepository",
    "PostgresPredictionRepository",
]
