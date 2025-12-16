"""
Base Repository - Mon_PS Hedge Fund Grade

Generic repository pattern for CRUD operations.
Provides type-safe data access layer.
"""

from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import Base

# Type variable for model classes
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic repository for synchronous database operations.

    Usage:
        class OddsRepository(BaseRepository[Odds]):
            pass

        repo = OddsRepository(Odds, session)
        odds = repo.get_by_id(1)
    """

    def __init__(self, model: Type[ModelType], session: Session):
        self.model = model
        self.session = session

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get single record by primary key."""
        return self.session.get(self.model, id)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_by_field(self, field: str, value: Any) -> List[ModelType]:
        """Get records by field value."""
        column = getattr(self.model, field)
        stmt = select(self.model).where(column == value)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_first_by_field(self, field: str, value: Any) -> Optional[ModelType]:
        """Get first record matching field value."""
        column = getattr(self.model, field)
        stmt = select(self.model).where(column == value).limit(1)
        result = self.session.execute(stmt)
        return result.scalars().first()

    def count(self) -> int:
        """Count all records."""
        stmt = select(func.count()).select_from(self.model)
        result = self.session.execute(stmt)
        return result.scalar() or 0

    def create(self, obj: ModelType) -> ModelType:
        """Create new record."""
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)
        return obj

    def update(self, obj: ModelType) -> ModelType:
        """Update existing record."""
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> bool:
        """Delete record."""
        self.session.delete(obj)
        self.session.flush()
        return True


class AsyncBaseRepository(Generic[ModelType]):
    """Generic repository for asynchronous operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        return await self.session.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
