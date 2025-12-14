"""Base Repository - Abstract interface.

ADR #008: Repository pattern for data access abstraction.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Any

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository.

    Generic repository interface for CRUD operations.
    Concrete implementations: PostgreSQL, Redis, etc.

    Type parameter T: Domain model type (e.g., MarketPrediction)
    """

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create entity in storage.

        Args:
            entity: Domain model instance

        Returns:
            Created entity with generated ID
        """
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID.

        Args:
            entity_id: Unique identifier

        Returns:
            Entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def list(
        self, filters: Optional[Dict[str, Any]] = None, limit: int = 100
    ) -> List[T]:
        """List entities with optional filters.

        Args:
            filters: Filter conditions (e.g., {"match_id": "xyz"})
            limit: Maximum results

        Returns:
            List of entities
        """
        pass

    @abstractmethod
    async def update(self, entity_id: str, data: Dict[str, Any]) -> T:
        """Update entity.

        Args:
            entity_id: Entity to update
            data: Updated fields

        Returns:
            Updated entity
        """
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete entity.

        Args:
            entity_id: Entity to delete

        Returns:
            True if deleted, False if not found
        """
        pass
