"""
SQLAlchemy Base Model - Mon_PS Hedge Fund Grade

Provides:
- Declarative base with common functionality
- Timestamp mixins
- Schema support (public, quantum)
- Repr helpers
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import MetaData, Column, DateTime, String, Text, func
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column


# Naming convention for constraints (important for Alembic)
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Features:
    - Automatic __repr__ based on primary keys
    - Naming convention for database constraints
    - Type annotations support
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def __repr__(self) -> str:
        """Generate a useful repr string."""
        class_name = self.__class__.__name__
        pk_cols = [col.name for col in self.__table__.primary_key.columns]
        pk_values = [getattr(self, col, None) for col in pk_cols]
        pk_str = ", ".join(f"{col}={val}" for col, val in zip(pk_cols, pk_values))
        return f"<{class_name}({pk_str})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}


class TimestampMixin:
    """
    Mixin for created_at and updated_at timestamps.

    Usage:
        class MyModel(Base, TimestampMixin):
            __tablename__ = "my_table"
            ...
    """

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )


class AuditMixin:
    """
    Mixin for audit trail - tracks who created/updated records and why.

    Provides:
    - created_by: User/system that created the record
    - updated_by: User/system that last updated the record
    - change_reason: Optional reason for the change

    Usage:
        class MyModel(Base, TimestampMixin, AuditMixin):
            __tablename__ = "my_table"
            ...

    Note: This is passive tracking. Application code must set these fields.
    Consider integrating with authentication system to auto-populate.
    """

    @declared_attr
    def created_by(cls) -> Mapped[Optional[str]]:
        """User or system that created this record."""
        return mapped_column(
            String(100),
            nullable=True,
            comment="User or system that created this record",
        )

    @declared_attr
    def updated_by(cls) -> Mapped[Optional[str]]:
        """User or system that last updated this record."""
        return mapped_column(
            String(100),
            nullable=True,
            comment="User or system that last updated this record",
        )

    @declared_attr
    def change_reason(cls) -> Mapped[Optional[str]]:
        """Optional reason for the last change."""
        return mapped_column(
            Text,
            nullable=True,
            comment="Reason for the last change to this record",
        )


# Schema definitions
SCHEMA_PUBLIC = None  # Default public schema
SCHEMA_QUANTUM = "quantum"
