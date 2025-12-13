"""Pydantic models for Mon_PS Quant Trading System.

Architecture:
- Type-safe data validation (Pydantic V2)
- Auto-calculated derived fields
- FastAPI compatible serialization
- Comprehensive audit trail

Architecture Decision Records:
- docs/adr/001-eventmetadata-optional.md
- docs/adr/002-model-validator-cross-field.md
- docs/adr/003-explicit-field-serializers.md
- docs/adr/004-auto-calculation-pattern.md

Created: 2025-12-13
Authors: Mya & Claude - Mon_PS Quant Team
"""

from .audit import (
    AuditEvent,
    EventMetadata,
    EventSeverity,
    EventType,
)

__all__ = [
    # Audit models
    'AuditEvent',
    'EventMetadata',
    'EventSeverity',
    'EventType',
]
