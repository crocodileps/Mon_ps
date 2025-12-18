# Session 2025-12-18 #77 - Investigation Loaders + Suppression quantum_dna_legacy

## Contexte
Suite session #76 (Architecture Mapping 3 colonnes). Deux missions:
1. Supprimer quantum_dna_legacy (prouve 100% redondant)
2. Investigation exhaustive des loaders avant creation UnifiedLoader V3

## Realise

### Phase 1: Suppression quantum_dna_legacy (COMPLETE)
- Verification: 443 KB, 0 scripts utilisant (sauf ORM)
- Backup cree: team_quantum_dna_v3_backup_before_legacy_drop
- Colonne supprimee: ALTER TABLE DROP COLUMN
- ORM modifie: quantum_v3.py (60 -> 59 colonnes, 31 -> 30 JSONB)

### Phase 2A: Investigation 3 silos (COMPLETE)
- JSON (team_dna_unified_v2.json): 8 dimensions, ~1,120 cles/equipe
- DB v3 (team_quantum_dna_v3): 59 colonnes (30 JSONB)
- TSE (team_stats_extended): 7 colonnes, 198 equipes

### Phase 2B: Verifications Hedge Fund (COMPLETE)
- TSE partiels: goal_timing_dna 46%, goalscorer_dna 100%
- Context JSON vs DB: COMPLEMENTAIRES (pas redondants)
- Stack DB: psycopg2 + SQLAlchemy (requirements)
- Memoire totale: ~8 MB (JSON 5.7 + v3 1.9 + TSE 0.4)

### Phase 2C: Investigation Loaders (COMPLETE)
DECOUVERTE MAJEURE: data_hub.py fait DEJA la fusion JSON + DB!

| Loader | Source | Utilise par | Status |
|--------|--------|-------------|--------|
| data_hub.py | JSON + TSE | Chess Engine (6 engines) | Actif |
| unified_loader.py | JSON seul | matchup_engine | Actif |
| dna_loader_db.py | DB ancienne | PERSONNE | OBSOLETE |

## Fichiers touches

### Base de donnees
- `quantum.team_quantum_dna_v3` - DROP COLUMN quantum_dna_legacy
- `quantum.team_quantum_dna_v3_backup_before_legacy_drop` - Backup cree

### Modifications code
- `/home/Mon_ps/backend/models/quantum_v3.py` - Supprime quantum_dna_legacy, MAJ commentaires

## Problemes resolus

1. **quantum_dna_legacy redondant** -> Supprime avec backup
2. **Confusion loaders** -> Investigation complete, data_hub.py identifie comme solution

## En cours / A faire

- [ ] DECISION: Etendre data_hub.py avec team_quantum_dna_v3?
- [ ] DECISION: Supprimer dna_loader_db.py (obsolete)?
- [ ] Push modifications Git (quantum_dna_legacy supprime)
- [ ] Test Telegram Guardian (/start + --test-telegram)

## Notes techniques

### Architecture Loaders Identifiee
```
SYSTEME 1: quantum/loaders/         SYSTEME 2: quantum/chess_engine/
--------------------------          ------------------------------
unified_loader.py (JSON)            data_hub.py (JSON + TSE)
      |                                   |
      v                                   v
matchup_engine.py             tous les engines chess_engine
(quantum/engines/)            (coach, variance, pattern, etc.)
```

### Recommandation
ETENDRE data_hub.py (pas creer nouveau loader) car:
- Pattern JSON + DB deja implemente
- Connexion psycopg2 existante
- ~50 lignes a ajouter vs ~300 pour nouveau loader

### dna_loader_db.py = OBSOLETE
- Utilise table team_profiles (ancienne, 99 rows)
- Pas team_quantum_dna_v3 (nouvelle, 96 rows)
- 0 consommateurs identifies
- A supprimer ou archiver

### Donnees TSE partiellement remplies
| Colonne | Remplie | Note |
|---------|---------|------|
| goalscorer_dna | 100% | OK |
| handicap_dna | 100% | OK |
| goal_timing_dna | 46% | Partiel |
| scorer_dna | 46% | Partiel |

### Commandes utiles
```bash
# Verifier backup existe
docker exec monps_postgres psql -U monps_user -d monps_db -c "
SELECT COUNT(*) FROM quantum.team_quantum_dna_v3_backup_before_legacy_drop;"

# Verifier colonnes v3
docker exec monps_postgres psql -U monps_user -d monps_db -c "
SELECT COUNT(*) FROM information_schema.columns
WHERE table_schema = 'quantum' AND table_name = 'team_quantum_dna_v3';"
```
