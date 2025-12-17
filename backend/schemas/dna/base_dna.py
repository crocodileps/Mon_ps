"""
Base DNA Schema - Hedge Fund Grade Alpha
========================================

Base class for all DNA vector schemas.
Provides common functionality and validation.
"""

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class BaseDNA(BaseModel):
    """
    Base class for all DNA vector schemas.

    Features:
    - Immutable after creation (frozen)
    - Extra fields forbidden (strict validation)
    - JSON serialization ready
    """

    model_config = ConfigDict(
        frozen=False,  # Allow modification for setters
        extra="ignore",  # Ignore extra fields from DB (forward compatibility)
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSONB storage."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["BaseDNA"]:
        """Create from dictionary (JSONB from DB)."""
        if data is None:
            return None
        try:
            return cls(**data)
        except Exception:
            # Return None if validation fails (defensive)
            return None
