# ADR 004: Pattern for Auto-Calculated Fields

## Status
✅ Accepted

## Context

Plusieurs de nos modèles Pydantic ont des champs "dérivés" qui se calculent automatiquement à partir d'autres champs :

**Exemples** :
- `implied_probability` = 1.0 / `fair_odds` (MarketPrediction)
- `confidence_level` = fonction de `confidence_score` (MarketPrediction)
- `stake_pct` = `recommended_stake` / `bankroll` × 100 (PositionSize)
- `risk_level` = fonction de `stake_pct` (PositionSize)
- `changes` = diff entre `before_state` et `after_state` (AuditEvent)

**Question architecturale** : Quel pattern utiliser pour ces auto-calculs ?

## Decision

Utiliser le **Pattern Hybrid** :
1. Champs dérivés définis comme **fields Pydantic normaux** (avec default)
2. **model_validator(mode='after')** pour calculer les valeurs si non fournies
3. **Permission de override** : Si utilisateur fournit une valeur explicite, elle est respectée

```python
class MarketPrediction(BaseModel):
    # Champs sources
    fair_odds: float = Field(..., gt=1.0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)

    # Champs dérivés (avec default qui sera overridden)
    implied_probability: float = Field(
        default=0.0,  # Sera calculé si omis
        ge=0.0, le=1.0,
        description="Probabilité implicite (auto-calculée si omise)"
    )
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.LOW,  # Sera calculé si omis
        description="Niveau de confiance (auto-calculé si omis)"
    )

    # Auto-calcul (ADR #004)
    @model_validator(mode='after')
    def calculate_derived_fields(self) -> Self:
        """Calcule les champs dérivés si non fournis explicitement.

        ADR #004: Pattern Hybrid - Permet override mais calcule par défaut.
        ADR #002: model_validator garantit accès à tous les champs.

        Returns:
            Instance avec champs calculés
        """
        # Calculer implied_probability si valeur par défaut
        if self.implied_probability == 0.0 and self.fair_odds > 1.0:
            self.implied_probability = 1.0 / self.fair_odds

        # Calculer confidence_level si valeur par défaut
        if self.confidence_level == ConfidenceLevel.LOW:
            score = self.confidence_score
            if score > 0.85:
                self.confidence_level = ConfidenceLevel.VERY_HIGH
            elif score > 0.70:
                self.confidence_level = ConfidenceLevel.HIGH
            elif score > 0.50:
                self.confidence_level = ConfidenceLevel.MEDIUM
            # Sinon reste LOW

        return self
```

## Rationale

### Alternatives considérées

#### Alternative 1 : @property (REJETÉE)
```python
class MarketPrediction(BaseModel):
    fair_odds: float

    @property
    def implied_probability(self) -> float:
        return 1.0 / self.fair_odds
```

**Problèmes** :
- ❌ **Pas serialisé par Pydantic** : `@property` n'est pas un Field
- ❌ **Calculé à chaque accès** : Pas de caching (inefficient)
- ❌ **Pas de type safety Pydantic** : Validation bypassed
- ❌ **Pas de override possible** : Utilisateur ne peut pas fournir valeur custom

**Verdict** : ❌ Inapproprié pour nos use cases

#### Alternative 2 : Computed Field (REJETÉE)
```python
from pydantic import computed_field

class MarketPrediction(BaseModel):
    fair_odds: float

    @computed_field
    @property
    def implied_probability(self) -> float:
        return 1.0 / self.fair_odds
```

**Problèmes** :
- ⚠️ **Pas de override possible** : Valeur toujours calculée
- ⚠️ **Calculé à chaque serialization** : Overhead
- ✅ Serialisé correctement (avantage vs @property pur)

**Verdict** : ⚠️ Acceptable si on ne veut JAMAIS permettre override (rare)

#### Alternative 3 : Field sans default + validator required (REJETÉE)
```python
class MarketPrediction(BaseModel):
    fair_odds: float
    implied_probability: float  # Obligatoire, pas de default

    @model_validator(mode='after')
    def validate_implied_probability(self) -> Self:
        expected = 1.0 / self.fair_odds
        if abs(self.implied_probability - expected) > 0.001:
            raise ValueError("implied_probability incorrect")
        return self
```

**Problèmes** :
- ❌ **Utilisateur DOIT calculer manuellement** : Mauvaise UX
- ❌ **Code boilerplate partout** : MarketPrediction(..., implied_probability=1.0/odds)
- ❌ **Risque d'erreurs** : Utilisateur peut se tromper dans le calcul

**Verdict** : ❌ Mauvaise UX, antipattern

#### Alternative 4 : Pattern Hybrid (RETENUE) ✅
```python
class MarketPrediction(BaseModel):
    fair_odds: float
    implied_probability: float = Field(default=0.0)

    @model_validator(mode='after')
    def calculate_derived_fields(self) -> Self:
        if self.implied_probability == 0.0:
            self.implied_probability = 1.0 / self.fair_odds
        return self
```

**Avantages** :
- ✅ **Auto-calcul par défaut** : UX excellente
- ✅ **Override possible** : Utilisateur peut fournir valeur custom si besoin
- ✅ **Serialisé correctement** : C'est un Field Pydantic normal
- ✅ **Type safety complète** : Pydantic valide le type
- ✅ **Performance** : Calculé 1 fois à l'instanciation

**Verdict** : ✅ Meilleur compromis flexibilité/performance/UX

### Cas d'usage du override

**Pourquoi permettre override ?**

#### Use Case 1 : Tests unitaires
```python
def test_edge_case_implied_probability():
    """Test avec implied_probability custom pour edge case."""
    pred = MarketPrediction(
        fair_odds=1.50,
        implied_probability=0.65  # Override pour tester comportement spécifique
    )
    # Test logique avec cette valeur custom
```

#### Use Case 2 : Migration de données
```python
# Migration anciennes données avec formule différente
old_data = load_old_predictions()
for old_pred in old_data:
    new_pred = MarketPrediction(
        fair_odds=old_pred.odds,
        implied_probability=old_pred.custom_formula()  # Override
    )
```

#### Use Case 3 : Correction manuelle
```python
# Correction manuelle par Mya dans des cas exceptionnels
pred = MarketPrediction(
    fair_odds=1.50,
    implied_probability=0.68  # Mya override la valeur calculée
)
```

**Conclusion** : Override rare mais utile → Pattern Hybrid gagne

### Pattern de détection override

**Comment détecter si c'est une valeur calculée ou override ?**
```python
# Option 1 : Valeur sentinelle (NOTRE CHOIX)
if self.implied_probability == 0.0:  # Sentinelle
    # Calculer
    self.implied_probability = 1.0 / self.fair_odds

# Option 2 : None pour Optional (si applicable)
if self.implied_probability is None:
    self.implied_probability = 1.0 / self.fair_odds

# Option 3 : Metadata field (overkill)
if self._implied_probability_computed is False:
    self.implied_probability = 1.0 / self.fair_odds
```

**Notre choix : Option 1 (sentinelle)**
- Pour float : `0.0` est une sentinelle valide (probabilité ne peut pas être 0.0)
- Pour Enum : Utiliser valeur spécifique (ex: ConfidenceLevel.LOW)
- Pour Optional : Utiliser `None`

## Consequences

### Positives
1. **UX excellente** : Auto-calcul par défaut, pas de boilerplate
2. **Flexibilité** : Override possible si nécessaire
3. **Type safety** : Pydantic valide tout
4. **Performance** : Calculé 1 fois (pas à chaque accès)
5. **Testable** : Peut tester avec valeurs custom
6. **Serialization** : Fonctionne automatiquement

### Negatives
1. **Sentinelle peut être ambiguë** : 0.0 vs valeur réelle 0.0
   - Mitigation : Utiliser validation (ge=0.001) si 0.0 invalide
   - Ou utiliser Optional[float] avec None comme sentinelle

2. **Mutation de self** : model_validator modifie l'instance
   - Acceptable : Pattern standard Pydantic V2

## Implementation Guidelines

### Guideline 1 : Choisir la bonne sentinelle

| Type | Sentinelle | Exemple |
|------|-----------|---------|
| float (probability) | `0.0` | implied_probability: float = 0.0 |
| float (money) | `0.0` | recommended_stake: float = 0.0 |
| Optional[float] | `None` | edge_vs_market: Optional[float] = None |
| Enum | Valeur par défaut | confidence_level = ConfidenceLevel.LOW |
| List | `[]` | changes: List[Dict] = Field(default_factory=list) |

### Guideline 2 : Documenter l'auto-calcul
```python
implied_probability: float = Field(
    default=0.0,
    ge=0.0, le=1.0,
    description=(
        "Probabilité implicite (1 / fair_odds). "
        "Auto-calculée si omise (default=0.0). "
        "Peut être overridden si nécessaire."
    )
)
```

### Guideline 3 : Validator bien structuré
```python
@model_validator(mode='after')
def calculate_derived_fields(self) -> Self:
    """Calcule TOUS les champs dérivés.

    ADR #004: Pattern Hybrid pour auto-calculs.
    ADR #002: model_validator pour logique inter-champs.

    Champs calculés:
    - implied_probability: 1.0 / fair_odds (si 0.0)
    - confidence_level: basé sur confidence_score (si LOW)

    Returns:
        Instance avec champs calculés
    """
    # Groupe 1 : Calculs probabilités
    if self.implied_probability == 0.0 and self.fair_odds > 1.0:
        self.implied_probability = 1.0 / self.fair_odds

    # Groupe 2 : Calculs confiance
    if self.confidence_level == ConfidenceLevel.LOW:
        self.confidence_level = self._calculate_confidence_level()

    return self

def _calculate_confidence_level(self) -> ConfidenceLevel:
    """Helper pour calculer confidence_level.

    Séparé pour testabilité et lisibilité.
    """
    score = self.confidence_score
    if score > 0.85:
        return ConfidenceLevel.VERY_HIGH
    elif score > 0.70:
        return ConfidenceLevel.HIGH
    elif score > 0.50:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW
```

### Guideline 4 : Tests exhaustifs
```python
def test_auto_calculation_default():
    """Test auto-calcul avec valeurs par défaut."""
    pred = MarketPrediction(
        fair_odds=1.50,
        confidence_score=0.82
        # implied_probability omis → sera calculé
        # confidence_level omis → sera calculé
    )

    assert pred.implied_probability == pytest.approx(1.0 / 1.50)
    assert pred.confidence_level == ConfidenceLevel.HIGH

def test_auto_calculation_override():
    """Test override des valeurs calculées."""
    pred = MarketPrediction(
        fair_odds=1.50,
        confidence_score=0.82,
        implied_probability=0.65,  # Override
        confidence_level=ConfidenceLevel.VERY_HIGH  # Override
    )

    # Valeurs overridden préservées
    assert pred.implied_probability == 0.65
    assert pred.confidence_level == ConfidenceLevel.VERY_HIGH
```

## Special Cases

### Special Case 1 : Calcul conditionnel
```python
# changes : calculé seulement si before_state ET after_state fournis
@model_validator(mode='after')
def calculate_changes(self) -> Self:
    if (len(self.changes) == 0 and
        self.before_state is not None and
        self.after_state is not None):
        self.changes = self._compute_changes()
    return self
```

### Special Case 2 : Calcul en chaîne
```python
# stake_pct dépend de recommended_stake
# risk_level dépend de stake_pct
@model_validator(mode='after')
def calculate_risk_metrics(self) -> Self:
    # Étape 1 : Calculer stake_pct
    if self.stake_pct == 0.0:
        self.stake_pct = (self.recommended_stake / self.bankroll) * 100

    # Étape 2 : Calculer risk_level (dépend de stake_pct)
    if self.risk_level == RiskLevel.LOW:
        self.risk_level = self._calculate_risk_level()

    return self
```

## References
- Pydantic Computed Fields: https://docs.pydantic.dev/latest/concepts/computed_fields/
- ADR #002: model_validator for cross-field logic
- Effective Python Item 26: Define Function Decorators with functools.wraps

## Date
2025-12-13

## Authors
Mya & Claude - Mon_PS Quant Team
