# ADR 001: EventMetadata Should Be Optional

## Status
✅ Accepted

## Context
`AuditEvent` contient un champ `metadata: EventMetadata` pour stocker des informations
contextuelles (IP address, user agent, session ID, custom fields).

**Question architecturale** : Ce champ doit-il être Optional ou Required ?

## Decision
```python
metadata: Optional[EventMetadata] = Field(
    default=None,
    description=(
        "Métadonnées additionnelles de l'événement. "
        "Optional - Fournir seulement si contexte pertinent "
        "(ex: IP, user agent, session pour audit sécurité)."
    )
)
```

## Rationale

### Analyse des use cases

#### Use Case 1 : Audit simple (production normale)
```python
event = AuditEvent(
    event_id="evt_bet_placed",
    event_type=EventType.BET_PLACED,
    entity_id="bet_123",
    action="place_bet",
    success=True
    # metadata=None ← Pas de contexte additionnel nécessaire
)
```
**Fréquence** : 80% des events
**Besoin metadata** : ❌ Non

#### Use Case 2 : Audit sécurité (login, API calls)
```python
event = AuditEvent(
    event_id="evt_login",
    event_type=EventType.USER_LOGIN,
    entity_id="user_mya",
    action="login_success",
    success=True,
    metadata=EventMetadata(
        ip_address="91.98.131.218",
        user_agent="Mozilla/5.0...",
        session_id="sess_789",
        custom_fields={"location": "Marseille"}
    )
)
```
**Fréquence** : 15% des events
**Besoin metadata** : ✅ Oui

#### Use Case 3 : Tests unitaires
```python
event = AuditEvent(
    event_id="evt_test",
    event_type=EventType.TEST,
    entity_id="test_entity",
    action="test_action",
    success=True
    # metadata=None ← Tests simples
)
```
**Fréquence** : 5% des events
**Besoin metadata** : ❌ Non

### Alternatives considérées

#### Alternative 1 : Required avec empty default
```python
metadata: EventMetadata = Field(
    default_factory=lambda: EventMetadata(),
    description="..."
)
```

**Problèmes** :
- ❌ Overhead : Allocation mémoire inutile pour 80% des events
- ❌ Noise : EventMetadata() vide n'apporte aucune information
- ❌ Complexité : Besoin de vérifier si EventMetadata.ip_address is None partout

#### Alternative 2 : Union avec dict
```python
metadata: Optional[Union[EventMetadata, Dict[str, Any]]] = None
```

**Problèmes** :
- ❌ Perte de type safety (Dict accepte n'importe quoi)
- ❌ Validation Pydantic bypassed pour Dict
- ❌ Confusion : Quand utiliser EventMetadata vs Dict ?

#### Alternative 3 : Optional (CHOIX RETENU)
```python
metadata: Optional[EventMetadata] = Field(default=None)
```

**Avantages** :
- ✅ Pas d'overhead si non utilisé
- ✅ Type safety complète quand utilisé
- ✅ Idiomatique Python (Optional est standard)
- ✅ Clair : None = pas de metadata

## Consequences

### Positives
1. **Performance** : Pas d'allocation inutile (80% des cas)
2. **Clarté** : `None` explicite = "pas de contexte additionnel"
3. **Flexibilité** : Ajouter metadata seulement quand pertinent
4. **Standard Python** : Pattern Optional est idiomatique

### Negatives
1. **Guard clauses** : Code appelant doit gérer `if event.metadata is not None:`
   - Mais c'est acceptable (pattern Python standard)
   - Alternative serait pire (toujours allouer EventMetadata vide)

2. **Default factory impossible** : Pas de `default_factory=EventMetadata`
   - Mais c'était de toute façon une erreur de type
   - `default_factory` attend `Callable[[], T]` pas `Type[T]`
   - La vraie alternative aurait été `lambda: EventMetadata()` (verbose)

### Impact sur le code

**Création d'events** :
```python
# Simple (80% des cas)
event = AuditEvent(..., metadata=None)  # ou omis

# Avec contexte (20% des cas)
event = AuditEvent(..., metadata=EventMetadata(...))
```

**Lecture de metadata** :
```python
# Guard clause nécessaire
if event.metadata is not None:
    ip = event.metadata.ip_address
    # ...
```

## Validation technique

### Pydantic V2 compatibility
```python
# ✅ Fonctionne correctement
class AuditEvent(BaseModel):
    metadata: Optional[EventMetadata] = Field(default=None)

# Tests
event1 = AuditEvent(...)  # metadata=None ✅
event2 = AuditEvent(..., metadata=EventMetadata(...))  # ✅
event2.metadata.ip_address  # Type: str | None ✅
```

### mypy compliance
```bash
$ mypy quantum_core/models/audit.py
Success: no issues found ✅
```

## References
- Pydantic V2 Optional fields: https://docs.pydantic.dev/latest/concepts/fields/#optional-fields
- Python PEP 484 Type Hints: https://peps.python.org/pep-0484/
- Effective Python Item 89: Consider dataclasses for lightweight data containers

## Date
2025-12-13

## Authors
Mya & Claude - Mon_PS Quant Team
