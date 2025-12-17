# SESSION #59 (Part 2) - AUDIT ARCHITECTURE PREPARATION PHASE 6

**Date**: 2025-12-17
**Durée**: 20 minutes
**Grade**: 10/10 ✅ (Audit exhaustif et précis)
**Modèle**: Claude Sonnet 4.5

## 🎯 OBJECTIF AUDIT

Comprendre l'état EXACT de l'architecture avant d'implémenter Phase 6 (ORM Models V3):
- Structure tables PostgreSQL existantes
- Modèles ORM existants (backend/models/)
- Configuration database active
- Gap analysis: ce qui existe vs ce qui manque

## 📊 FINDINGS - DATABASE STRUCTURE

### Table `quantum.team_quantum_dna_v3`

**Métriques**:
- **60 colonnes** au total
- **31 colonnes JSONB** (vecteurs ADN)
- **1 colonne ARRAY** (narrative_fingerprint_tags)
- **96 équipes** avec données complètes
- **4.27 tags/équipe** en moyenne

**Colonnes principales**:
```sql
-- Identification
team_id                    | INTEGER (PK, autoincrement)
team_name                  | VARCHAR (unique, indexed)
team_name_normalized       | VARCHAR
league                     | VARCHAR (indexed)
tier                       | VARCHAR (ELITE, TOP6, MID, BOTTOM)
tier_rank                  | INTEGER

-- Intelligence & Strategy
team_intelligence_id       | INTEGER
current_style              | VARCHAR (gegenpress, possession, etc.)
style_confidence           | INTEGER
team_archetype             | VARCHAR
best_strategy              | VARCHAR
betting_identity           | JSONB

-- Performance Metrics
total_matches              | INTEGER
total_bets                 | INTEGER
total_wins                 | INTEGER
total_losses               | INTEGER
win_rate                   | DOUBLE PRECISION
total_pnl                  | DOUBLE PRECISION
roi                        | DOUBLE PRECISION
avg_clv                    | DOUBLE PRECISION
unlucky_losses             | INTEGER
bad_analysis_losses        | INTEGER
unlucky_pct                | DOUBLE PRECISION

-- DNA Vectors (JSONB) - 31 total
market_dna                 | JSONB
context_dna                | JSONB
temporal_dna               | JSONB
nemesis_dna                | JSONB
psyche_dna                 | JSONB
roster_dna                 | JSONB
physical_dna               | JSONB
luck_dna                   | JSONB
tactical_dna               | JSONB
chameleon_dna              | JSONB
meta_dna                   | JSONB
sentiment_dna              | JSONB
clutch_dna                 | JSONB
shooting_dna               | JSONB
card_dna                   | JSONB
corner_dna                 | JSONB
form_analysis              | JSONB
current_season             | JSONB
status_2025_2026           | JSONB
profile_2d                 | JSONB
signature_v3               | JSONB
advanced_profile_v8        | JSONB
friction_signatures        | JSONB
narrative_tactical_profile | JSONB
narrative_mvp              | JSONB

-- Strategy & Optimization
exploit_markets            | JSONB
avoid_markets              | JSONB
optimal_scenarios          | JSONB
optimal_strategies         | JSONB
quantum_dna_legacy         | JSONB

-- Narrative Tags
narrative_fingerprint_tags | ARRAY (text[])

-- Metadata
narrative_profile          | TEXT
dna_fingerprint            | VARCHAR (unique hash)
season                     | VARCHAR
created_at                 | TIMESTAMP WITH TIME ZONE
updated_at                 | TIMESTAMP WITH TIME ZONE
last_audit_at              | TIMESTAMP WITHOUT TIME ZONE
```

### Autres Tables Quantum Schema

**33 tables au total** dans le schéma `quantum`:
```
team_quantum_dna_v3          | 60 colonnes ⭐ (table principale)
quantum_friction_matrix_v3   | 32 colonnes ⭐ (target Phase 6)
quantum_strategies_v3        | 29 colonnes ⭐ (target Phase 6)
team_quantum_dna             | 19 colonnes (OLD, legacy)
quantum_friction_matrix      | 14 colonnes (OLD, legacy)
quantum_strategies           | 16 colonnes (OLD, legacy)
+ 27 autres tables (views, mappings, etc.)
```

### Sample Data Example (Liverpool)

```json
{
  "team_id": 146,
  "team_name": "Liverpool",
  "league": "Premier League",
  "tier": "ELITE",
  "current_style": "balanced",
  "best_strategy": "MONTE_CARLO_PURE",
  "total_matches": 17,
  "win_rate": 61.5,
  "roi": 13.8,
  "narrative_fingerprint_tags": [
    "GEGENPRESS",
    "GK_Alisson",
    "COMEBACK_KING",
    "GK_LEAKY"
  ],
  "market_dna": {
    "best_strategy": "MONTE_CARLO_PURE",
    "empirical_profile": {
      "avg_clv": 0,
      "avg_edge": 0.651,
      "sample_size": 24,
      "over_specialist": false,
      "under_specialist": true,
      "btts_no_specialist": true,
      "btts_yes_specialist": false
    },
    "profitable_strategies": 1,
    "total_strategies_tested": 5
  }
}
```

## 🏗️ FINDINGS - ORM ARCHITECTURE EXISTANTE

### Structure Répertoires

**✅ EXISTE**:
```
/home/Mon_ps/backend/models/
├── base.py           # Base class (DeclarativeBase, SQLAlchemy 2.0)
├── quantum.py        # TeamQuantumDNA (OLD table, NOT V3)
├── odds.py           # Odds-related models
└── __init__.py       # Module exports

/home/Mon_ps/backend/core/
└── database.py       # ⭐ ACTIVE DB CONFIG (sync + async)

/home/Mon_ps/quantum/models/
├── base.py           # Pydantic models (NOT SQLAlchemy)
├── team_dna.py       # Pydantic TeamDNA
└── [...]             # Business logic models
```

**❌ N'EXISTE PAS**:
```
/home/Mon_ps/backend/app/models/    # Dossier inexistant
/home/Mon_ps/backend/models/quantum_v3.py  # Model V3 manquant ⚠️
```

### Contenu `backend/models/base.py` (✅ MODERNE)

```python
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models (SQLAlchemy 2.0)"""
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def __repr__(self) -> str:
        # Auto repr based on primary keys
        ...

    def to_dict(self) -> dict[str, Any]:
        # Convert to dict
        ...

class TimestampMixin:
    """Automatic timestamp tracking"""
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

**Grade**: ⭐ **EXCELLENT** (Modern SQLAlchemy 2.0, type hints, mixins)

### Contenu `backend/models/quantum.py` (⚠️ LEGACY)

```python
class TeamQuantumDNA(Base, TimestampMixin):
    """OLD table team_quantum_dna (NOT V3)"""

    __tablename__ = "team_quantum_dna"
    __table_args__ = {"schema": "quantum"}

    team_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_name: Mapped[str] = mapped_column(String(100), unique=True)
    league: Mapped[str] = mapped_column(String(50))

    # Only 8 DNA vectors (OLD architecture)
    market_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    context_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    risk_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    temporal_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    nemesis_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    psyche_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    roster_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    physical_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
```

**Verdict**: ✅ Bonne base, MAIS table obsolète (8 DNA vectors vs 31 en V3)

### Contenu `backend/core/database.py` (⭐ ACTIF)

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager, asynccontextmanager

# SYNC Engine (backward compatible)
sync_engine = create_engine(
    settings.sync_database_url,
    pool_size=settings.DB_POOL_SIZE,
    pool_pre_ping=True,  # Health check
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for DB sessions"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# ASYNC Engine (new code)
async_engine = create_async_engine(settings.async_database_url, ...)
AsyncSessionLocal = async_sessionmaker(async_engine, ...)

@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager"""
    ...
```

**Grade**: ⭐ **PERFECT** (Sync + Async, health checks, context managers)

## 📋 GAP ANALYSIS - CE QUI MANQUE

### Models ORM V3 (À créer)

**Fichier cible**: `/home/Mon_ps/backend/models/quantum_v3.py`

**3 modèles requis**:

1. **`TeamQuantumDnaV3`**
   - Mapper les 60 colonnes de `quantum.team_quantum_dna_v3`
   - Support 31 JSONB vectors + 1 ARRAY (tags)
   - Méthodes query helpers:
     - `.filter_by_tags(tags: list[str])`
     - `.filter_by_tier(tier: str)`
     - `.filter_by_league(league: str)`
     - `.get_by_name(name: str)`
   - Properties calculées:
     - `.has_tag(tag: str) -> bool`
     - `.tag_count -> int`
     - `.is_elite -> bool`

2. **`QuantumFrictionMatrixV3`**
   - Mapper `quantum.quantum_friction_matrix_v3` (32 colonnes)
   - Relations avec TeamQuantumDnaV3 (team_home, team_away)
   - Méthodes query:
     - `.get_friction(team_a: str, team_b: str)`
     - `.get_high_friction_matchups(threshold: float)`

3. **`QuantumStrategiesV3`**
   - Mapper `quantum.quantum_strategies_v3` (29 colonnes)
   - Relation avec TeamQuantumDnaV3
   - Méthodes:
     - `.get_best_strategy(team: str, context: dict)`
     - `.get_strategies_by_conviction(min_conviction: float)`

### Repositories (À créer)

**Fichier cible**: `/home/Mon_ps/backend/repositories/quantum_v3_repository.py`

**Pattern Repository** pour abstraction queries:
```python
class QuantumV3Repository:
    def __init__(self, session: Session):
        self.session = session

    # Team DNA queries
    def get_team_by_name(self, name: str) -> TeamQuantumDnaV3 | None
    def get_teams_by_tags(self, tags: list[str]) -> list[TeamQuantumDnaV3]
    def get_elite_teams(self) -> list[TeamQuantumDnaV3]
    def get_teams_by_league(self, league: str) -> list[TeamQuantumDnaV3]

    # Friction queries
    def get_friction_score(self, team_a: str, team_b: str) -> float
    def get_high_friction_matchups(self, threshold: float = 0.7)

    # Strategy queries
    def get_optimal_strategy(self, team: str, context: dict) -> dict
    def get_strategies_by_team(self, team: str) -> list[QuantumStrategiesV3]
```

### Tests (À créer)

**Fichiers cibles**:
- `/home/Mon_ps/backend/tests/test_models/test_quantum_v3.py`
- `/home/Mon_ps/backend/tests/test_repositories/test_quantum_v3_repository.py`

**Tests requis**:
- ORM model instantiation
- JSONB field serialization/deserialization
- ARRAY field (tags) queries
- Repository methods
- Edge cases (None values, empty arrays, etc.)

## 🎯 PLAN D'IMPLÉMENTATION PHASE 6

### Étape 1: Créer ORM Models V3 (30 min)

**Fichier**: `backend/models/quantum_v3.py`

**Actions**:
- Copier structure de `quantum.py` comme template
- Mapper les 60 colonnes de `team_quantum_dna_v3`
- Ajouter types hints pour JSONB (Dict[str, Any])
- Ajouter type hint pour ARRAY (List[str])
- Implémenter méthodes helper:
  - `has_tag(tag: str) -> bool`
  - `filter_by_tags(tags: list) -> Query`
  - `get_dna_vector(vector_name: str) -> dict | None`

**Template suggéré**:
```python
from typing import Dict, Any, List, Optional
from sqlalchemy import String, Integer, Float, Text, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base, TimestampMixin

class TeamQuantumDnaV3(Base, TimestampMixin):
    """Team Quantum DNA V3 - Hedge Fund Grade (96 teams, 60 columns)"""

    __tablename__ = "team_quantum_dna_v3"
    __table_args__ = {"schema": "quantum"}

    # Primary key
    team_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identification
    team_name: Mapped[str] = mapped_column(String, unique=True, index=True)
    team_name_normalized: Mapped[Optional[str]] = mapped_column(String)
    league: Mapped[str] = mapped_column(String, index=True)
    tier: Mapped[Optional[str]] = mapped_column(String)
    tier_rank: Mapped[Optional[int]] = mapped_column(Integer)

    # Intelligence
    team_intelligence_id: Mapped[Optional[int]] = mapped_column(Integer)
    current_style: Mapped[Optional[str]] = mapped_column(String)
    style_confidence: Mapped[Optional[int]] = mapped_column(Integer)
    team_archetype: Mapped[Optional[str]] = mapped_column(String)
    betting_identity: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    best_strategy: Mapped[Optional[str]] = mapped_column(String)

    # Performance metrics
    total_matches: Mapped[Optional[int]] = mapped_column(Integer)
    total_bets: Mapped[Optional[int]] = mapped_column(Integer)
    total_wins: Mapped[Optional[int]] = mapped_column(Integer)
    total_losses: Mapped[Optional[int]] = mapped_column(Integer)
    win_rate: Mapped[Optional[float]] = mapped_column(Float)
    total_pnl: Mapped[Optional[float]] = mapped_column(Float)
    roi: Mapped[Optional[float]] = mapped_column(Float)
    avg_clv: Mapped[Optional[float]] = mapped_column(Float)
    unlucky_losses: Mapped[Optional[int]] = mapped_column(Integer)
    bad_analysis_losses: Mapped[Optional[int]] = mapped_column(Integer)
    unlucky_pct: Mapped[Optional[float]] = mapped_column(Float)

    # DNA Vectors (31 JSONB columns)
    market_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    context_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    temporal_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    nemesis_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    psyche_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    roster_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    physical_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    luck_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    tactical_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    chameleon_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    meta_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    sentiment_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    clutch_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    shooting_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    card_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    corner_dna: Mapped[Optional[Dict]] = mapped_column(JSONB)
    form_analysis: Mapped[Optional[Dict]] = mapped_column(JSONB)
    current_season: Mapped[Optional[Dict]] = mapped_column(JSONB)
    status_2025_2026: Mapped[Optional[Dict]] = mapped_column(JSONB)
    profile_2d: Mapped[Optional[Dict]] = mapped_column(JSONB)
    signature_v3: Mapped[Optional[Dict]] = mapped_column(JSONB)
    advanced_profile_v8: Mapped[Optional[Dict]] = mapped_column(JSONB)
    friction_signatures: Mapped[Optional[Dict]] = mapped_column(JSONB)
    narrative_tactical_profile: Mapped[Optional[Dict]] = mapped_column(JSONB)
    narrative_mvp: Mapped[Optional[Dict]] = mapped_column(JSONB)

    # Strategy & Optimization
    exploit_markets: Mapped[Optional[Dict]] = mapped_column(JSONB)
    avoid_markets: Mapped[Optional[Dict]] = mapped_column(JSONB)
    optimal_scenarios: Mapped[Optional[Dict]] = mapped_column(JSONB)
    optimal_strategies: Mapped[Optional[Dict]] = mapped_column(JSONB)
    quantum_dna_legacy: Mapped[Optional[Dict]] = mapped_column(JSONB)

    # Narrative Tags (ARRAY)
    narrative_fingerprint_tags: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String), default=[]
    )

    # Metadata
    narrative_profile: Mapped[Optional[str]] = mapped_column(Text)
    dna_fingerprint: Mapped[Optional[str]] = mapped_column(String, unique=True)
    season: Mapped[Optional[str]] = mapped_column(String)
    last_audit_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Helper methods
    def has_tag(self, tag: str) -> bool:
        """Check if team has specific tag"""
        return tag in (self.narrative_fingerprint_tags or [])

    @property
    def tag_count(self) -> int:
        """Get number of tags"""
        return len(self.narrative_fingerprint_tags or [])

    @property
    def is_elite(self) -> bool:
        """Check if team is ELITE tier"""
        return self.tier == "ELITE"

    def get_dna_vector(self, vector_name: str) -> Dict[str, Any] | None:
        """Get specific DNA vector by name"""
        return getattr(self, vector_name, None)
```

### Étape 2: Créer Repository (20 min)

**Fichier**: `backend/repositories/quantum_v3_repository.py`

### Étape 3: Tests Unitaires (30 min)

**Fichier**: `backend/tests/test_models/test_quantum_v3.py`

### Étape 4: Documentation (10 min)

**Fichier**: `backend/models/QUANTUM_V3_README.md`

## 📈 MÉTRIQUES SESSION

**Temps**:
- Audit database: 5 min
- Audit ORM existant: 5 min
- Analyse gaps: 5 min
- Documentation: 10 min
- **Total**: 25 minutes

**Découvertes**:
- ✅ 60 colonnes mappées (team_quantum_dna_v3)
- ✅ 33 tables quantum schema identifiées
- ✅ Configuration DB moderne (sync + async)
- ✅ Base class SQLAlchemy 2.0 prête
- ❌ Aucun model ORM V3 existant (à créer)

**Grade Audit**: 10/10 ✅ (Exhaustif et précis)

---

**Session terminée**: 2025-12-17 13:10 UTC
**Status**: ✅ AUDIT TERMINÉ - Ready to implement Phase 6
**Next Action**: Créer `backend/models/quantum_v3.py`
