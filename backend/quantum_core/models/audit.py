"""Audit models for Mon_PS system events tracking.

Architecture Decision Records:
- ADR #001: EventMetadata is Optional (80% events don't need it)
- ADR #002: model_validator for cross-field logic (auto_severity, changes)
- ADR #003: field_serializer for datetime (type-safe, FastAPI compatible)
- ADR #004: Pattern Hybrid for auto-calculated fields (changes)

Created: 2025-12-13
Authors: Mya & Claude - Mon_PS Quant Team
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Self
from pydantic import BaseModel, Field, field_serializer, model_validator, ConfigDict


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class EventType(str, Enum):
    """Types d'événements audit."""

    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    HEALTH_CHECK = "health_check"

    # Data events
    DATA_FETCH = "data_fetch"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"

    # Model events
    MODEL_TRAIN = "model_train"
    MODEL_PREDICT = "model_predict"
    MODEL_UPDATE = "model_update"

    # Betting events
    BET_PLACED = "bet_placed"
    BET_UPDATED = "bet_updated"
    BET_SETTLED = "bet_settled"

    # User events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_ACTION = "user_action"

    # API events
    API_CALL = "api_call"
    API_ERROR = "api_error"

    # Test events
    TEST = "test"
    READ = "read"
    WRITE = "write"
    DELETE = "delete"


class EventSeverity(str, Enum):
    """Niveaux de sévérité des événements."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ═══════════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class EventMetadata(BaseModel):
    """Métadonnées additionnelles pour AuditEvent.

    ADR #001: Ce modèle est utilisé comme Optional dans AuditEvent.
    Seulement 20% des events ont besoin de metadata contextuelle.
    """

    ip_address: Optional[str] = Field(
        None, description="Adresse IP de l'origine de l'événement"
    )
    user_agent: Optional[str] = Field(
        None, description="User agent (pour requêtes HTTP)"
    )
    session_id: Optional[str] = Field(None, description="ID de session utilisateur")
    request_id: Optional[str] = Field(
        None, description="ID de requête pour traçabilité"
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, description="Champs custom additionnels"
    )

    # Configuration Pydantic V2 (ADR #003)
    model_config = ConfigDict(use_enum_values=True)


class AuditEvent(BaseModel):
    """Événement d'audit système.

    Architecture Decision Records appliqués:
    - ADR #001: metadata est Optional[EventMetadata]
    - ADR #002: model_validator pour auto_severity et calculate_changes
    - ADR #003: field_serializer pour computed_at avec when_used='json'
    - ADR #004: changes auto-calculé (Pattern Hybrid)

    Examples:
        Simple event (80% des cas):
        >>> event = AuditEvent(
        ...     event_id="evt_123",
        ...     event_type=EventType.BET_PLACED,
        ...     entity_id="bet_123",
        ...     action="place_bet",
        ...     success=True
        ... )

        Event avec metadata (20% des cas):
        >>> event = AuditEvent(
        ...     event_id="evt_login",
        ...     event_type=EventType.USER_LOGIN,
        ...     entity_id="user_mya",
        ...     action="login_success",
        ...     success=True,
        ...     metadata=EventMetadata(
        ...         ip_address="91.98.131.218",
        ...         user_agent="Mozilla/5.0..."
        ...     )
        ... )
    """

    # ───────────────────────────────────────────────────────────────────────────
    # CHAMPS OBLIGATOIRES
    # ───────────────────────────────────────────────────────────────────────────

    event_id: str = Field(
        ...,
        description="ID unique de l'événement (format: evt_xxxxx)",
        min_length=1,
        max_length=100,
    )
    event_type: EventType = Field(..., description="Type d'événement")
    entity_id: str = Field(
        ...,
        description="ID de l'entité concernée (bet_id, user_id, model_id, etc.)",
        min_length=1,
        max_length=100,
    )
    action: str = Field(
        ...,
        description="Action effectuée (verbe: create, update, delete, predict, etc.)",
        min_length=1,
        max_length=100,
    )
    success: bool = Field(..., description="Succès de l'action")

    # ───────────────────────────────────────────────────────────────────────────
    # CHAMPS OPTIONNELS
    # ───────────────────────────────────────────────────────────────────────────

    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp de l'événement (UTC)"
    )

    severity: EventSeverity = Field(
        default=EventSeverity.INFO,
        description=(
            "Sévérité de l'événement. "
            "Auto-escaladé à ERROR si success=False (ADR #002)."
        ),
    )

    message: Optional[str] = Field(
        None, description="Message descriptif de l'événement", max_length=500
    )

    error: Optional[str] = Field(
        None, description="Message d'erreur si success=False", max_length=1000
    )

    duration_ms: Optional[float] = Field(
        None, ge=0.0, description="Durée de l'action en millisecondes"
    )

    # ADR #001: EventMetadata Optional (80% events sans metadata)
    metadata: Optional[EventMetadata] = Field(
        None,
        description=(
            "Métadonnées additionnelles (IP, user agent, session, etc.). "
            "Optional - Fournir seulement si contexte pertinent. "
            "ADR #001: 80% des events n'ont pas besoin de metadata."
        ),
    )

    before_state: Optional[Dict[str, Any]] = Field(
        None, description="État avant l'action (pour events UPDATE/DELETE)"
    )

    after_state: Optional[Dict[str, Any]] = Field(
        None, description="État après l'action (pour events CREATE/UPDATE)"
    )

    # ADR #004: changes auto-calculé (Pattern Hybrid)
    changes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Liste des changements (diff before_state/after_state). "
            "Auto-calculé si before_state et after_state fournis (ADR #004). "
            "Format: [{'field': str, 'before': Any, 'after': Any}]"
        ),
    )

    # ───────────────────────────────────────────────────────────────────────────
    # CONFIGURATION PYDANTIC V2
    # ───────────────────────────────────────────────────────────────────────────

    model_config = ConfigDict(use_enum_values=True)

    # ───────────────────────────────────────────────────────────────────────────
    # SERIALIZATION (ADR #003)
    # ───────────────────────────────────────────────────────────────────────────

    @field_serializer("computed_at", when_used="json")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO 8601 format.

        ADR #003: field_serializer explicite avec when_used='json'.
        - Compatible FastAPI (.model_dump_json())
        - Type-safe (mypy vérifie)
        - Testable unitairement

        Args:
            dt: Datetime to serialize

        Returns:
            ISO 8601 string (e.g. '2025-12-13T20:30:00Z')

        Example:
            >>> event = AuditEvent(...)
            >>> event.model_dump_json()
            '{"computed_at": "2025-12-13T20:30:00", ...}'
        """
        return dt.isoformat()

    # ───────────────────────────────────────────────────────────────────────────
    # VALIDATION & AUTO-CALCULS (ADR #002 & #004)
    # ───────────────────────────────────────────────────────────────────────────

    @model_validator(mode="after")
    def compute_changes_and_severity(self) -> Self:
        """Calcule changes et auto-escalade severity.

        ADR #002: model_validator garantit accès à tous les champs (y compris defaults).
        ADR #004: Pattern Hybrid pour auto-calcul de changes.

        Logique:
        1. Si changes vide ET before_state/after_state fournis → calculer diff
        2. Si success=False ET severity=INFO → escalader à ERROR

        Returns:
            Instance modifiée avec changes calculés et severity ajustée

        Example:
            >>> event = AuditEvent(
            ...     ...,
            ...     success=False,
            ...     before_state={"status": "pending"},
            ...     after_state={"status": "failed"}
            ... )
            >>> # changes auto-calculé: [{'field': 'status', 'before': 'pending', 'after': 'failed'}]
            >>> # severity auto-escaladé: ERROR
        """
        # ─────────────────────────────────────────────────────────────────────
        # AUTO-CALCUL : changes (ADR #004)
        # ─────────────────────────────────────────────────────────────────────

        if (
            len(self.changes) == 0
            and self.before_state is not None
            and self.after_state is not None
        ):

            # Calculer diff
            calculated_changes = []

            # Champs modifiés
            all_keys = set(self.before_state.keys()) | set(self.after_state.keys())
            for key in all_keys:
                before_val = self.before_state.get(key)
                after_val = self.after_state.get(key)

                if before_val != after_val:
                    calculated_changes.append(
                        {"field": key, "before": before_val, "after": after_val}
                    )

            self.changes = calculated_changes

        # ─────────────────────────────────────────────────────────────────────
        # AUTO-ESCALADE : severity (ADR #002)
        # ─────────────────────────────────────────────────────────────────────

        if not self.success and self.severity == EventSeverity.INFO:
            self.severity = EventSeverity.ERROR

        return self


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "EventType",
    "EventSeverity",
    "EventMetadata",
    "AuditEvent",
]
