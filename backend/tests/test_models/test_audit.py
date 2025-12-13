"""Tests for audit models.

Test Strategy:
- Tests unitaires documentant les Architecture Decision Records
- Coverage de tous les edge cases identifiés
- Validation comportement Pydantic V2

Created: 2025-12-13
Authors: Mya & Claude - Mon_PS Quant Team
"""

import pytest
from datetime import datetime
from quantum_core.models.audit import (
    AuditEvent,
    EventMetadata,
    EventSeverity,
    EventType,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS ADR #001: EventMetadata Optional
# ═══════════════════════════════════════════════════════════════════════════════


class TestADR001EventMetadataOptional:
    """Tests validant ADR #001: EventMetadata should be Optional."""

    def test_audit_event_without_metadata_is_valid(self):
        """ADR #001: AuditEvent sans metadata doit être valide (80% des cas)."""
        event = AuditEvent(
            event_id="evt_no_metadata",
            event_type=EventType.BET_PLACED,
            entity_id="bet_123",
            action="place_bet",
            success=True,
            # metadata=None (implicite)
        )

        assert event.metadata is None
        assert event.event_id == "evt_no_metadata"

    def test_audit_event_with_metadata_is_valid(self):
        """ADR #001: AuditEvent avec metadata doit être valide (20% des cas)."""
        metadata = EventMetadata(
            ip_address="91.98.131.218", user_agent="Mon_PS/1.0", session_id="sess_789"
        )

        event = AuditEvent(
            event_id="evt_with_metadata",
            event_type=EventType.USER_LOGIN,
            entity_id="user_mya",
            action="login_success",
            success=True,
            metadata=metadata,
        )

        assert event.metadata is not None
        assert event.metadata.ip_address == "91.98.131.218"

    def test_metadata_none_vs_empty_metadata(self):
        """ADR #001: None plus efficace que EventMetadata() vide."""
        # Avec None (recommandé)
        event1 = AuditEvent(
            event_id="evt_1",
            event_type=EventType.TEST,
            entity_id="test",
            action="test",
            success=True,
            metadata=None,
        )

        # Avec EventMetadata vide (non recommandé mais valide)
        event2 = AuditEvent(
            event_id="evt_2",
            event_type=EventType.TEST,
            entity_id="test",
            action="test",
            success=True,
            metadata=EventMetadata(),
        )

        # Les deux sont valides mais event1 plus efficient
        assert event1.metadata is None
        assert event2.metadata is not None
        assert event2.metadata.ip_address is None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS ADR #002: model_validator for Cross-Field Logic
# ═══════════════════════════════════════════════════════════════════════════════


class TestADR002ModelValidatorCrossField:
    """Tests validant ADR #002: model_validator accède aux defaults."""

    def test_auto_severity_with_default_success(self):
        """ADR #002: model_validator accède à success même si default."""
        event = AuditEvent(
            event_id="evt_defaults",
            event_type=EventType.READ,
            entity_id="entity_123",
            action="read",
            success=False,  # Fourni explicitement
            # severity omis → utilisera default INFO puis sera escaladé
        )

        # ADR #002: model_validator a escaladé severity à ERROR
        assert event.severity == EventSeverity.ERROR

    def test_auto_severity_respects_explicit_value(self):
        """ADR #002: Si severity fourni explicitement, ne pas override."""
        event = AuditEvent(
            event_id="evt_explicit",
            event_type=EventType.WRITE,
            entity_id="entity_456",
            action="write",
            success=False,
            severity=EventSeverity.CRITICAL,  # Explicite
        )

        # Valeur explicite préservée
        assert event.severity == EventSeverity.CRITICAL

    def test_auto_severity_only_if_success_false(self):
        """ADR #002: Auto-escalade seulement si success=False."""
        event = AuditEvent(
            event_id="evt_success",
            event_type=EventType.READ,
            entity_id="entity_789",
            action="read",
            success=True,  # Success
            # severity=INFO (default)
        )

        # Pas d'escalade si success=True
        assert event.severity == EventSeverity.INFO


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS ADR #003: field_serializer Explicit
# ═══════════════════════════════════════════════════════════════════════════════


class TestADR003FieldSerializerExplicit:
    """Tests validant ADR #003: Serialization JSON."""

    def test_datetime_serializes_to_iso8601_json(self):
        """ADR #003: .model_dump_json() serialise datetime en ISO 8601."""
        event = AuditEvent(
            event_id="evt_serialize",
            event_type=EventType.TEST,
            entity_id="test",
            action="test",
            success=True,
            computed_at=datetime(2025, 12, 13, 20, 30, 0),
        )

        json_str = event.model_dump_json()

        # Datetime serialisé en ISO 8601
        assert '"computed_at":"2025-12-13T20:30:00"' in json_str

    def test_datetime_preserved_in_model_dump(self):
        """ADR #003: .model_dump() préserve datetime object (when_used='json')."""
        event = AuditEvent(
            event_id="evt_dump",
            event_type=EventType.TEST,
            entity_id="test",
            action="test",
            success=True,
            computed_at=datetime(2025, 12, 13, 20, 30, 0),
        )

        data = event.model_dump()

        # Datetime object préservé (pas string)
        assert isinstance(data["computed_at"], datetime)
        assert data["computed_at"].year == 2025


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS ADR #004: Auto-Calculated Fields (Pattern Hybrid)
# ═══════════════════════════════════════════════════════════════════════════════


class TestADR004AutoCalculatedFields:
    """Tests validant ADR #004: Pattern Hybrid pour auto-calculs."""

    def test_changes_auto_calculated_from_states(self):
        """ADR #004: changes auto-calculé si before_state et after_state fournis."""
        event = AuditEvent(
            event_id="evt_changes",
            event_type=EventType.DATA_UPDATE,
            entity_id="entity_update",
            action="update",
            success=True,
            before_state={"status": "pending", "amount": 100},
            after_state={"status": "completed", "amount": 100},
            # changes omis → sera calculé
        )

        # ADR #004: changes auto-calculé
        assert len(event.changes) == 1
        assert event.changes[0]["field"] == "status"
        assert event.changes[0]["before"] == "pending"
        assert event.changes[0]["after"] == "completed"

    def test_changes_respects_explicit_value(self):
        """ADR #004: Si changes fourni explicitement, ne pas override."""
        explicit_changes = [{"field": "custom", "before": "a", "after": "b"}]

        event = AuditEvent(
            event_id="evt_explicit_changes",
            event_type=EventType.DATA_UPDATE,
            entity_id="entity_explicit",
            action="update",
            success=True,
            before_state={"status": "pending"},
            after_state={"status": "completed"},
            changes=explicit_changes,  # Explicite
        )

        # Valeur explicite préservée
        assert event.changes == explicit_changes

    def test_changes_empty_if_no_states(self):
        """ADR #004: changes reste vide si before_state/after_state non fournis."""
        event = AuditEvent(
            event_id="evt_no_states",
            event_type=EventType.TEST,
            entity_id="test",
            action="test",
            success=True,
            # before_state=None, after_state=None
        )

        # changes vide (pas de calcul possible)
        assert event.changes == []


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS FONCTIONNELS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditEventFunctional:
    """Tests fonctionnels des cas d'usage réels."""

    def test_simple_bet_placed_event(self):
        """Use case simple : Pari placé (80% des events)."""
        event = AuditEvent(
            event_id="evt_bet_123",
            event_type=EventType.BET_PLACED,
            entity_id="bet_123",
            action="place_bet",
            success=True,
            message="Pari placé sur Lyon vs Marseille",
            duration_ms=45.3,
        )

        assert event.event_id == "evt_bet_123"
        assert event.success is True
        assert event.severity == EventSeverity.INFO
        assert event.metadata is None

    def test_user_login_with_metadata(self):
        """Use case avec metadata : Login utilisateur (20% des events)."""
        event = AuditEvent(
            event_id="evt_login_mya",
            event_type=EventType.USER_LOGIN,
            entity_id="user_mya",
            action="login_success",
            success=True,
            metadata=EventMetadata(
                ip_address="91.98.131.218",
                user_agent="Mozilla/5.0",
                session_id="sess_abc123",
            ),
        )

        assert event.success is True
        assert event.metadata.ip_address == "91.98.131.218"

    def test_failed_api_call_with_error(self):
        """Use case erreur : API call failed."""
        event = AuditEvent(
            event_id="evt_api_error",
            event_type=EventType.API_ERROR,
            entity_id="api_odds_provider",
            action="fetch_odds",
            success=False,
            error="Connection timeout after 30s",
            duration_ms=30000.0,
        )

        assert event.success is False
        assert event.severity == EventSeverity.ERROR  # Auto-escaladé
        assert "timeout" in event.error


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
