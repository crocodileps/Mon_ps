# ADR 003: Explicit field_serializer Over json_encoders

## Status
✅ Accepted

## Context

Pydantic V1 utilisait `json_encoders` pour serializer des types custom en JSON :
```python
class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat()
    }
```

Pydantic V2 a **deprecated** `json_encoders` en faveur de `@field_serializer`.

**Question architecturale** : Quelle stratégie de serialization adopter pour datetime et autres types custom ?

## Decision

Utiliser `@field_serializer` explicite pour chaque champ datetime, avec `when_used='json'`.
```python
from pydantic import field_serializer

@field_serializer('computed_at', 'expires_at', when_used='json')
def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
    """Serialize datetime fields to ISO 8601 format.

    Args:
        dt: Datetime to serialize (or None)

    Returns:
        ISO 8601 string (e.g. '2025-12-13T20:30:00Z') or None

    Example:
        >>> pred = MarketPrediction(...)
        >>> pred.model_dump_json()
        '{"computed_at": "2025-12-13T20:30:00Z", ...}'
    """
    return dt.isoformat() if dt else None
```

## Rationale

### Problèmes de json_encoders (V1)

#### 1. Global et implicite
```python
class Config:
    json_encoders = {datetime: lambda v: v.isoformat()}

# Affecte TOUS les datetime du modèle
# computed_at, expires_at, created_at → tous serialisés pareil
# Pas de contrôle granulaire
```

**Problème** : Et si on veut formatter `created_at` différemment ?
- Impossible sans overrider globalement
- Perte de flexibilité

#### 2. Pas de type safety
```python
json_encoders = {
    datetime: lambda v: v.isoformat()  # Lambda non typée
}
# mypy ne vérifie pas : v est-il Optional[datetime] ou datetime ?
# Risque : AttributeError si v=None
```

#### 3. Difficile à tester
```python
# Comment tester la lambda json_encoders ?
# Impossible d'isoler la fonction
# Doit tester via .json() complet (test d'intégration)
```

#### 4. Pas de granularité when_used
```python
# json_encoders s'applique TOUJOURS
# Pas de différence entre .model_dump() et .model_dump_json()
```

### Avantages de field_serializer (V2)

#### 1. Explicite par champ
```python
@field_serializer('computed_at', 'expires_at', when_used='json')
def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None

@field_serializer('created_at', when_used='json')
def serialize_created_at(self, dt: datetime) -> str:
    # Logique différente si nécessaire
    return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
```

**Avantage** : Contrôle granulaire, logique différente par champ possible.

#### 2. Type safe
```python
@field_serializer('computed_at', when_used='json')
def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
    #                         ^^^^^^^^^^^^^^^^^^^    ^^^^^^^^^^^^^^
    #                         mypy vérifie input     mypy vérifie output
    return dt.isoformat() if dt else None
```

**Avantage** : mypy détecte les erreurs de type à la compilation.

#### 3. Testable isolément
```python
def test_serialize_datetime():
    """Test du serializer datetime."""
    pred = MarketPrediction(...)

    # Test avec datetime
    dt = datetime(2025, 12, 13, 20, 30, 0)
    result = pred.serialize_datetime(dt)
    assert result == "2025-12-13T20:30:00"

    # Test avec None
    result = pred.serialize_datetime(None)
    assert result is None
```

**Avantage** : Tests unitaires directs de la fonction.

#### 4. when_used granularité
```python
when_used='json'           # Seulement .model_dump_json()
when_used='always'         # .model_dump() ET .model_dump_json()
when_used='json-unless-none'  # Comme json mais skip si None
```

**Avantage** : Contrôle fin du comportement.

### Analyse when_used options

| Option | .model_dump() | .model_dump_json() | Use Case |
|--------|---------------|-------------------|----------|
| **'json'** | datetime object | ISO string | **RECOMMANDÉ** - Compatible FastAPI |
| 'always' | ISO string | ISO string | Si on veut toujours des strings |
| 'json-unless-none' | datetime object | ISO string (skip None) | Optimize payload size |

**Notre choix : `when_used='json'`**

**Justification** :
1. **FastAPI utilise .model_dump_json()** pour responses → serializer appelé ✅
2. **.model_dump() garde datetime objects** → utile pour manipulation Python ✅
3. **Flexibilité maximale** : Comportement différent selon contexte ✅

### Impact FastAPI
```python
# FastAPI endpoint
@app.get("/predictions/{id}")
async def get_prediction(id: str) -> MarketPrediction:
    pred = MarketPrediction(...)
    return pred  # FastAPI appelle .model_dump_json() automatiquement

# Response JSON
{
  "prediction_id": "pred_123",
  "computed_at": "2025-12-13T20:30:00Z",  ← Serialisé en ISO string ✅
  ...
}
```

**Conclusion** : `when_used='json'` est parfait pour FastAPI.

## Alternatives considérées

### Alternative 1 : Garder json_encoders (REJETÉE)
```python
class Config:
    json_encoders = {datetime: lambda v: v.isoformat()}
```

**Problèmes** :
- ❌ Deprecated (sera removed en Pydantic V3)
- ❌ Warnings à chaque utilisation
- ❌ Dette technique

### Alternative 2 : model_serializer (REJETÉE)
```python
@model_serializer
def serialize_model(self):
    data = self.model_dump()
    # Manually serialize datetime fields
    data['computed_at'] = data['computed_at'].isoformat() if data['computed_at'] else None
    return data
```

**Problèmes** :
- ❌ Overkill (trop complexe pour juste datetime)
- ❌ Moins type-safe
- ❌ Plus difficile à maintenir

### Alternative 3 : field_serializer sans when_used (REJETÉE)
```python
@field_serializer('computed_at')
def serialize_datetime(self, dt):
    return dt.isoformat() if dt else None
```

**Problèmes** :
- ⚠️ when_used par défaut = 'always'
- ⚠️ .model_dump() retourne strings au lieu de datetime
- ⚠️ Perte de flexibilité

### Alternative 4 : field_serializer avec when_used='json' (RETENUE) ✅

Voir Decision ci-dessus.

## Consequences

### Positives
1. **Type safety** : mypy vérifie input/output types
2. **Testable** : Tests unitaires directs possibles
3. **Explicite** : On voit exactement quels champs sont serialisés
4. **Flexible** : Logique différente par champ si besoin
5. **FastAPI compatible** : when_used='json' parfait pour API responses
6. **Future-proof** : Prêt pour Pydantic V3

### Negatives
1. **Plus verbeux** : Besoin de répéter pour chaque modèle
   - Mitigation : Pattern réutilisable (voir Implementation Pattern)
   - Trade-off acceptable : Verbosité > Implicite

2. **Duplication** : Même serializer dans plusieurs modèles
   - Mitigation : Créer un mixin si vraiment nécessaire (overkill pour nous)

## Implementation Pattern

### Pattern standard (RECOMMANDÉ)
```python
from pydantic import BaseModel, Field, field_serializer, ConfigDict
from typing import Optional
from datetime import datetime

class MarketPrediction(BaseModel):
    # Fields
    computed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp de calcul"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Timestamp d'expiration"
    )

    # Config
    model_config = ConfigDict(use_enum_values=True)

    # Serializer (ADR #003)
    @field_serializer('computed_at', 'expires_at', when_used='json')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO 8601 format.

        ADR #003: field_serializer explicite avec when_used='json'.
        Compatible FastAPI, type-safe, testable.

        Args:
            dt: Datetime to serialize (or None)

        Returns:
            ISO 8601 string (e.g. '2025-12-13T20:30:00Z') or None
        """
        return dt.isoformat() if dt else None
```

### Pattern pour date (pas datetime)
```python
from datetime import date

class BacktestRequest(BaseModel):
    start_date: date
    end_date: date

    @field_serializer('start_date', 'end_date', when_used='json')
    def serialize_date(self, dt: date) -> str:
        """Serialize date to ISO format (YYYY-MM-DD)."""
        return dt.isoformat()
```

### Pattern avec timezone awareness (si nécessaire futur)
```python
from datetime import datetime, timezone

@field_serializer('computed_at', when_used='json')
def serialize_datetime_utc(self, dt: datetime) -> str:
    """Serialize datetime to ISO 8601 with explicit UTC.

    Returns:
        ISO 8601 string with Z suffix (e.g. '2025-12-13T20:30:00Z')
    """
    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # isoformat() avec Z suffix
    return dt.isoformat().replace('+00:00', 'Z')
```

## Testing Strategy

### Test unitaire du serializer
```python
def test_serialize_datetime_with_value():
    """Test serialization datetime avec valeur."""
    pred = MarketPrediction(
        ...,
        computed_at=datetime(2025, 12, 13, 20, 30, 0)
    )

    # Test serializer directement
    result = pred.serialize_datetime(pred.computed_at)
    assert result == "2025-12-13T20:30:00"

def test_serialize_datetime_with_none():
    """Test serialization datetime avec None."""
    pred = MarketPrediction(...)
    result = pred.serialize_datetime(None)
    assert result is None
```

### Test d'intégration .model_dump_json()
```python
def test_model_dump_json_serializes_datetime():
    """Test que .model_dump_json() serialise correctement datetime."""
    pred = MarketPrediction(
        ...,
        computed_at=datetime(2025, 12, 13, 20, 30, 0)
    )

    json_str = pred.model_dump_json()
    assert '"computed_at":"2025-12-13T20:30:00"' in json_str
```

### Test .model_dump() preserve datetime
```python
def test_model_dump_preserves_datetime_object():
    """Test que .model_dump() garde datetime object."""
    pred = MarketPrediction(
        ...,
        computed_at=datetime(2025, 12, 13, 20, 30, 0)
    )

    data = pred.model_dump()
    assert isinstance(data['computed_at'], datetime)
    assert data['computed_at'].year == 2025
```

## References
- Pydantic V2 Serialization: https://docs.pydantic.dev/latest/concepts/serialization/
- FastAPI JSON encoding: https://fastapi.tiangolo.com/tutorial/encoder/
- ISO 8601 standard: https://en.wikipedia.org/wiki/ISO_8601

## Date
2025-12-13

## Authors
Mya & Claude - Mon_PS Quant Team
