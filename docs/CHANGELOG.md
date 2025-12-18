# CHANGELOG - Mon_PS Quantum Trading System

All notable changes to this project will be documented in this file.

## [2025-12-18] Session #79-80: Extension DataOrchestrator

### Added
- `_get_team_from_v3()`: Charge depuis `quantum.team_quantum_dna_v3` (59 colonnes)
- `_get_tse_name()`: Mapping equipes speciales (AC Milan->Milan, etc.)
- `_get_tse_data()`: Charge depuis `quantum.team_stats_extended` (corner/card/goalscorer DNA)
- Fallback ILIKE intelligent (single-match safe)
- Alias mapping (PSG, Barca, Bayern, BVB, Juve, Atleti)
- DB alignment mapping (Paris Saint-Germain, Borussia Monchengladbach)

### Changed
- `get_team_dna()`: Cascade TSE -> V3 -> JSON -> profiles(fallback)
- `orchestrator.py`: 695 -> 875 lignes (+180)

### Removed
- `quantum/services/dna_loader_db.py`: Obsolete (0 utilisateurs), fonctionnalite integree dans DataOrchestrator
- Imports dna_loader_db dans `quantum/services/__init__.py`

### Verified
- 96/96 equipes V3 accessibles avec TSE + V3
- 89/96 avec JSON supplementaire
- Mapping PSG et Borussia M.Gladbach corrige

---

## [2025-12-17] Session #74: Guardian Hedge Fund Grade

### Added
- `scripts/guardian.py`: Health check system institutionnel
- Tolerance selective par type de service
- Validation temporelle intelligente
- Crontab integration toutes les 5 minutes

### Changed
- Monitoring proactif des services critiques
