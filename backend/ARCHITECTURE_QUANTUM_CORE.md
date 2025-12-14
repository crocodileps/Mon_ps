# Architecture Quantum Core - Mon_PS

## Problème Initial (Avant refactoring)

Chaos architectural : 2 quantum_core différents
```
/home/Mon_ps/quantum_core/        [A] MASTER (brain, chess, goalscorer)
/home/Mon_ps/backend/quantum_core/ [B] API Utils (observability, api)
```

**Impact** : ModuleNotFoundError au runtime Docker

## Solution Hedge Fund Grade

**Principe** : Single Source of Truth
```
/home/Mon_ps/quantum_core/        ← MASTER (Read-Only mount)
/home/Mon_ps/backend/infrastructure/ ← API Utils (renommé)
```

## Structure Docker
```yaml
# monitoring/docker-compose.yml
backend:
  volumes:
    - /home/Mon_ps/quantum_core:/quantum_core_master:ro
```

## Imports Python
```python
# AVANT (cassé)
from brain.unified_brain import UnifiedBrain  # ❌ brain not found

# APRÈS (robuste)
sys.path.insert(0, '/quantum_core_master')
from brain.unified_brain import UnifiedBrain  # ✅ explicit path
```

## Validation

- ✅ Un seul quantum_core MASTER
- ✅ Volume Docker read-only (immutabilité)
- ✅ Paths explicites (pas de confusion)
- ✅ Tests integration validés

Date: 2025-12-14
Version: 1.0
