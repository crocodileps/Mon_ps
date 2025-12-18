# Session 2025-12-18 #76 - Architecture Mapping 3 Colonnes

## Contexte
Suite session #75. Phase 2 du mapping: correction architecture apres decouverte
que historical_name servait au backtester (API-Football), pas a TSE (Understat).

## Realise

### Phase 1: Sync 5 equipes corner/card (19:25)
- AC Milan, Hamburger SV, Mainz 05, Real Oviedo, VfB Stuttgart
- UPDATE 5 reussi
- ERREUR: Modifie historical_name au lieu de creer nouvelle colonne

### Phase 2A: Audit complet mapping
- 99 mappings pour 96 equipes (3 orphelines: Ipswich, Leicester, Southampton)
- 46 mappings "invalides" = ne matchent pas TSE
- DECOUVERTE: historical_name = API-Football format (pour backtester)
- tse_name devrait = Understat format (pour TSE)

### Phase 2A-bis: Verification critique
- Les 46 "invalides" ne sont PAS invalides
- historical_name matche tracking_clv_picks (1423 picks)
- quantum_name matche TSE (94/96)
- CONFLIT: 2 usages incompatibles pour historical_name

### Investigation: Origine noms
- TSE (team_stats_extended) = Understat format
- tracking_clv_picks = API-Football format
- Le mapping servait a faire le pont entre les deux
- Phase 1 a CASSE le backtester pour 3 equipes!

### Correction architecture (20:15)
1. ROLLBACK Phase 1: 4 valeurs restaurees
2. DELETE 3 orphelines (Ipswich, Leicester, Southampton)
3. ADD COLUMN tse_name VARCHAR(100)
4. UPDATE tse_name = quantum_name (par defaut)
5. FIX 5 cas speciaux (AC Milan->Milan, etc.)

### Investigation: 198 equipes TSE
- TSE contient 10 divisions (5 top + 5 second)
- 102 orphelins = equipes de 2eme division
- Pas un probleme, c'est une richesse

## Fichiers touches

### Base de donnees
- `quantum.team_name_mapping` - Rollback + ADD COLUMN tse_name
- `quantum.team_quantum_dna_v3` - Corner/card sync (inchange)

### Modifications SQL executees
```sql
-- Rollback Phase 1
UPDATE quantum.team_name_mapping m
SET historical_name = b.historical_name
FROM quantum.team_name_mapping_backup_20251218 b
WHERE m.quantum_name = b.quantum_name
AND m.historical_name != b.historical_name;

-- Delete orphelines
DELETE FROM quantum.team_name_mapping
WHERE quantum_name IN ('Ipswich', 'Leicester', 'Southampton');

-- Nouvelle colonne
ALTER TABLE quantum.team_name_mapping
ADD COLUMN tse_name VARCHAR(100);

-- Peupler tse_name
UPDATE quantum.team_name_mapping SET tse_name = quantum_name;
UPDATE quantum.team_name_mapping SET tse_name = 'Milan' WHERE quantum_name = 'AC Milan';
UPDATE quantum.team_name_mapping SET tse_name = 'Hamburg' WHERE quantum_name = 'Hamburger SV';
UPDATE quantum.team_name_mapping SET tse_name = 'Mainz' WHERE quantum_name = 'Mainz 05';
UPDATE quantum.team_name_mapping SET tse_name = 'Oviedo' WHERE quantum_name = 'Real Oviedo';
UPDATE quantum.team_name_mapping SET tse_name = 'Stuttgart' WHERE quantum_name = 'VfB Stuttgart';
```

## Problemes resolus

1. **Phase 1 cassait backtester** -> Rollback + nouvelle colonne tse_name
2. **Confusion API-Football vs Understat** -> Architecture 3 colonnes claire
3. **3 equipes orphelines (99 vs 96)** -> Supprimees
4. **5 equipes sans match TSE** -> tse_name specifique

## En cours / A faire

- [ ] Test Telegram Guardian (/start puis --test-telegram)
- [ ] Push modifications Guardian
- [ ] Documenter architecture 3 colonnes pour equipe

## Notes techniques

### Architecture finale mapping (3 colonnes)
```
| Colonne         | Usage                | Format        | Exemple AC Milan |
|-----------------|----------------------|---------------|------------------|
| quantum_name    | v3, Brain, JSON      | Understat     | AC Milan         |
| historical_name | Backtester, tracking | API-Football  | Milan            |
| tse_name        | Sync corner/card     | TSE/Understat | Milan            |
```

### 5 cas speciaux (quantum_name != tse_name)
| quantum_name  | tse_name  |
|---------------|-----------|
| AC Milan      | Milan     |
| Hamburger SV  | Hamburg   |
| Mainz 05      | Mainz     |
| Real Oviedo   | Oviedo    |
| VfB Stuttgart | Stuttgart |

### Validation finale
- Mappings: 96 = 96 equipes v3
- tse_name -> TSE: 96/96 (100%)
- Corner filled: 96/96
- Card filled: 96/96

### TSE contient 198 equipes
- 96 equipes des 5 top divisions (mappees a v3)
- 102 equipes des 5 secondes divisions (orphelines, normal)

### Backups disponibles
- `quantum.team_name_mapping_backup_20251218` (99 rows, avant toute modif)
- `quantum.team_quantum_dna_v3_backup_phase1_20251218_192443` (5 rows)

### Commandes utiles
```bash
# Verifier architecture mapping
docker exec monps_postgres psql -U monps_user -d monps_db -c "
SELECT quantum_name, historical_name, tse_name
FROM quantum.team_name_mapping
WHERE quantum_name IN ('AC Milan', 'Hamburger SV', 'Mainz 05', 'Real Oviedo', 'VfB Stuttgart');"

# Verifier couverture corner/card
docker exec monps_postgres psql -U monps_user -d monps_db -c "
SELECT COUNT(*) as total,
       COUNT(*) FILTER (WHERE corner_dna IS NOT NULL) as corner,
       COUNT(*) FILTER (WHERE card_dna IS NOT NULL) as card
FROM quantum.team_quantum_dna_v3;"
```
