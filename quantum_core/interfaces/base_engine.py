"""
BaseEngine - Interface pour tous les engines d'analyse
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class EngineResult:
    """Résultat standardisé d'un engine."""
    engine_name: str
    success: bool
    data: Dict[str, Any]
    confidence: float = 1.0
    degraded: bool = False
    error_message: Optional[str] = None


class BaseEngine(ABC):
    """Interface commune pour tous les engines d'analyse."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nom de l'engine."""
        pass

    @abstractmethod
    def analyze(self, **kwargs) -> EngineResult:
        """Exécute l'analyse."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si l'engine est opérationnel."""
        pass

    def get_fallback_result(self) -> EngineResult:
        """Résultat par défaut si l'analyse échoue."""
        return EngineResult(
            engine_name=self.name,
            success=False,
            data={},
            confidence=0.0,
            degraded=True,
            error_message="Engine unavailable"
        )
