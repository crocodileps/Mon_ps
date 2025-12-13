# TACHE EN COURS - MON_PS

**Derniere MAJ:** 2025-12-13 Session #08
**Statut:** DataOrchestrator COMPLET - Architecture Hedge Fund Grade

## Contexte General
Projet Mon_PS: Systeme de betting football avec donnees multi-sources (FBRef, Understat, SofaScore).
Paradigme Chess Engine: ADN unique par equipe + Friction entre 2 ADN = marches exploitables.

## Session #08 - DataOrchestrator Facade Pattern

### Accomplissement Majeur
**Refactoring architectural: DataOrchestrator qui REUTILISE les composants existants**

Principe: ZERO duplication, 100% reutilisation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DataOrchestrator (695L)                            │
│                      Point d'entree UNIQUE                              │
│                              │                                          │
│              ┌───────────────┼───────────────┐                         │
│              ▼               ▼               ▼                          │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐               │
│  │ UnifiedLoader │  │  PostgreSQL   │  │  dna_vectors  │               │
│  │   (915L)      │  │quantum.*(3403)│  │   (1106L)     │               │
│  │  96 equipes   │  │ team_profiles │  │  11 DNA types │               │
│  └───────────────┘  └───────────────┘  └───────────────┘               │
│     REUTILISE          REUTILISE          REUTILISE                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Commits Session #08
```
95cf31c feat(quantum_core): DataOrchestrator - Facade Pattern Hedge Fund Grade
12ef1ca feat(quantum_core): DataManager V2.6 - Coach/GK/Attackers integration
```

### Resultats Tests
| Test | Resultat |
|------|----------|
| Team DNA (Liverpool) | ELITE, 61.5% WR |
| Friction (LIV vs MCI) | 3.77 goals, 63% BTTS, 73% O2.5 |
| Match Context | 100% data quality |
| UnifiedLoader | 96 equipes CONNECTED |
| Players | Salah found |
| Referees | Michael Oliver found |

---

## Fichiers Session #08

### Crees
- `quantum_core/data/orchestrator.py` (695 lignes) - Facade principale
- `quantum_core/data/archive/manager_v26_archived.py` - DataManager V2.6 archive

### Modifies
- `quantum_core/data/__init__.py` - Export DataOrchestrator
- `docs/CURRENT_TASK.md`
- `docs/sessions/2025-12-13_08.md`

---

## Composants Reutilises

| Composant | Lignes | Contenu |
|-----------|--------|---------|
| unified_loader.py | 915 | Teams, Players, Referees JSON |
| dna_vectors.py | 1106 | 11 DNA dataclasses |
| quantum.matchup_friction | 3403 rows | Frictions pre-calculees |
| quantum.team_profiles | 99 rows | Equipes PostgreSQL |

---

## Usage DataOrchestrator

```python
from quantum_core.data import get_orchestrator

orchestrator = get_orchestrator()

# Team DNA (PostgreSQL + JSON fusion)
liverpool = orchestrator.get_team_dna("Liverpool")

# Friction pre-calculee
friction = orchestrator.get_friction("Liverpool", "Man City")
print(f"Predicted goals: {friction.predicted_goals}")
print(f"BTTS prob: {friction.btts_prob:.1%}")

# Contexte match complet
context = orchestrator.get_match_context("Arsenal", "Chelsea")
print(f"Expected goals: {context.expected_goals}")

# Players et Referees
salah = orchestrator.get_player("Mohamed Salah", "Liverpool")
ref = orchestrator.get_referee("Michael Oliver")
```

---

## Prochaines Etapes

### Priorite Haute
1. [ ] Connecter DataOrchestrator au QuantumEngine (probability/edge)
2. [ ] Ajouter predicteur Scorers (buteurs)
3. [ ] Ajouter predicteur Cards (cartons)
4. [ ] Creer API FastAPI pour exposer le systeme

### Priorite Moyenne
5. [ ] Backtest sur donnees historiques
6. [ ] Implementer conversion complete Dict -> TeamDNA dataclass
7. [ ] Ajouter cache Redis pour production

---

## Connexion PostgreSQL
```bash
docker exec monps_postgres psql -U monps_user -d monps_db
```

---

## Dernier Commit
```
95cf31c feat(quantum_core): DataOrchestrator - Facade Pattern Hedge Fund Grade
```
