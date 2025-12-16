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

from sqlalchemy import MetaData, DateTime, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
    Mixin for automatic timestamp tracking.

    Provides:
    - created_at: Set automatically on insert
    - updated_at: Updated automatically on every update

    Usage:
        class MyModel(Base, TimestampMixin):
            __tablename__ = "my_table"
            ...

    Note: Uses mapped_column directly to avoid SAWarning about
    "Unmanaged access of declarative attribute from non-mapped class"
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
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
    """

    created_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="User or system that created this record",
    )

    updated_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="User or system that last updated this record",
    )

    change_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for the last change to this record",
    )


# Schema definitions
SCHEMA_PUBLIC = None  # Default public schema
SCHEMA_QUANTUM = "quantum"
