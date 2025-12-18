# Session 2025-12-18 #78 - Cartographie Complete Mon_PS

## Contexte
Suite session #77 (Investigation Loaders + Suppression quantum_dna_legacy).
Investigation exhaustive de tout l'ecosysteme Mon_PS avant decisions sur les loaders.

## Realise

### Phase 1: Investigation Zones d'Ombre Initiales
- team_profiles: 99 rows dans schema quantum (pas public!)
- team_loader.py: 605 lignes (PAS 26K comme suppose)
- Deux matchup_engine: COMPLEMENTAIRES (pas duplication)
- dna_loader_db.py: 0 utilisateurs CONFIRME

### Phase 2: Cartographie Complete PostgreSQL
33 tables dans schema quantum:
- team_quantum_dna_v3: 96 rows, 1.9 MB (SOUS-UTILISEE)
- team_stats_extended: 198 rows, 384 KB (TSE - corner/card DNA)
- team_profiles: 99 rows, 3.9 MB (ANCIENNE)
- matchup_friction: 3403 rows, 2.9 MB
- quantum_friction_matrix_v3: 3321 rows, 2.4 MB

3 equipes dans profiles pas dans v3: Ipswich, Leicester, Southampton

### Phase 3: Identification des 3 Systemes
1. quantum/loaders/ (6,069 lignes) - JSON seul
2. quantum/chess_engine/ (25 fichiers) - JSON + TSE + team_profiles
3. quantum_core/ (12,272 lignes) - DataOrchestrator + UnifiedBrain

### Phase 4: PARADOXE MAJEUR DECOUVERT
- data_hub.py charge team_stats_extended (corner/card DNA)
- DataOrchestrator charge team_profiles (ANCIENNE) mais PAS TSE!
- DataHubAdapter expose interface DataHub mais utilise DataOrchestrator
- RESULTAT: UnifiedBrain n'a PAS acces aux corner/card DNA!

### Phase 5: Backend API
- FastAPI direct vers PostgreSQL
- N'utilise PAS quantum/loaders, chess_engine, ou quantum_core
- Endpoints: bets, odds, opportunities, stats, agents
- quantum_core.backup = API preparee, PAS en production

### Phase 6: Verification Complementarite matchup_engine
- quantum/engines/ (616 lignes): Oriente PARIS, edges, best_bets
- chess_engine/engines/ (130 lignes): Oriente ZONES, xG, tactique
- 0 fonction en commun, appelants differents
- VERDICT: COMPLEMENTAIRES, garder les deux

## Fichiers touches
Aucun - SESSION LECTURE SEULE (investigation)

## Decouvertes Majeures

### Architecture Reelle
```
PRODUCTION ACTUELLE:
Backend API → PostgreSQL direct (team_profiles, matchup_friction)
Cron Jobs → Scrapers (Understat, FBRef, Football-data)

SYSTEMES PREPARES (NON ACTIFS):
UnifiedBrain V2.8 → DataHubAdapter → DataOrchestrator
                         ↓
              UnifiedLoader (JSON) + team_profiles (ANCIENNE!)
              ❌ PAS team_quantum_dna_v3
              ❌ PAS team_stats_extended
```

### Donnees Sous-Utilisees
- team_quantum_dna_v3 (59 colonnes, 30 JSONB): Scripts batch seulement
- status_2025_2026, signature_v3, profile_2d: NON exploites
- roi, avg_clv, tier (v3): NON utilises par UnifiedBrain

### Tables Utilisees par Qui
| Table | Utilisateurs |
|-------|--------------|
| team_quantum_dna_v3 | Scripts batch, ORM, tests |
| team_stats_extended | data_hub.py seulement |
| team_profiles | data_hub + DataOrchestrator |
| matchup_friction | DataOrchestrator |

## Problemes resolus
1. Paradoxe DataHub vs DataOrchestrator: EXPLIQUE
2. Complementarite matchup_engine: CONFIRMEE
3. quantum_core en production: NON, c'est un backup/preparation

## En cours / A faire

### Decisions Requises (Mya)
- [ ] DECISION: Etendre DataOrchestrator avec v3 + TSE?
- [ ] DECISION: Supprimer dna_loader_db.py (0 utilisateurs)?
- [ ] DECISION: Supprimer/archiver quantum.team_profiles apres migration?
- [ ] DECISION: Ajouter Ipswich/Leicester/Southampton a v3?

### Actions Techniques
- [ ] Etendre DataOrchestrator (~100 lignes) pour charger v3 + TSE
- [ ] Supprimer dna_loader_db.py
- [ ] Documenter architecture 3 systemes
- [ ] Push Git modifications sessions #77-78

## Notes techniques

### Systeme 1: quantum/loaders/
- unified_loader.py: 915 lignes, JSON seul
- team_loader.py: 605 lignes, agregateur
- Utilise par: matchup_engine (standalone), DataOrchestrator

### Systeme 2: quantum/chess_engine/
- data_hub.py: ~500 lignes, JSON + PostgreSQL (TSE + team_profiles)
- 6 engines: coach, matchup, variance, pattern, referee, chain
- Utilise par: quantum_brain.py

### Systeme 3: quantum_core/
- unified_brain.py: 1,425 lignes, 99 marches
- orchestrator.py: 695 lignes, UnifiedLoader + team_profiles
- data_hub_adapter.py: 642 lignes, pont vers DataOrchestrator
- Status: PRET mais PAS en production

### Solution Proposee
Etendre DataOrchestrator pour charger:
1. team_quantum_dna_v3 (au lieu de/en plus de team_profiles)
2. team_stats_extended (comme data_hub.py le fait)
→ UnifiedBrain automatiquement enrichi via chaine existante

### Commandes utiles
```bash
# Verifier tables quantum
docker exec monps_postgres psql -U monps_user -d monps_db -c "
SELECT relname, n_live_tup FROM pg_stat_user_tables
WHERE schemaname = 'quantum' ORDER BY n_live_tup DESC;"

# Verifier qui utilise v3
grep -r "team_quantum_dna_v3" /home/Mon_ps --include="*.py" | grep -v __pycache__
```
