"""
BaseLoader - Interface pour tous les loaders
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from datetime import datetime


class BaseLoader(ABC):
    """Interface commune pour tous les loaders de données."""

    @abstractmethod
    def get(self, identifier: str, as_of_date: Optional[datetime] = None) -> Optional[Any]:
        """Récupère une entité par son identifiant."""
        pass

    @abstractmethod
    def get_all(self, as_of_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Récupère toutes les entités."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si le loader est disponible."""
        pass

    def get_fallback(self, identifier: str) -> Optional[Any]:
        """Retourne une valeur par défaut si get() échoue."""
        return None
