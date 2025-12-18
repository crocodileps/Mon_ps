# Session 2025-12-18 #74 (suite) - Guardian + Audit ADN

## Contexte
Continuation de la session #74. Deux missions:
1. Ajout success_max_age_hours par cron job
2. Audit ADN scientifique Phase B.1 (lecture seule)

## Realise

### Mission 1: SUCCESS_MAX_AGE_HOURS par cron

**Probleme**: Guardian montrait DEGRADED car le max_age global de 120min etait trop restrictif pour les crons quotidiens (fbref).

**Solution**: Configurer un max_age specifique par cron job.

| Cron Job | success_max_age_hours | Justification |
|----------|----------------------|---------------|
| fbref_scraper | 26h | 24h interval + 2h marge |
| fbref_pipeline | 26h | 24h interval + 2h marge |
| understat_main | 14h | 12h interval + 2h marge |
| football_data | 8h | 6h interval + 2h marge |

**Resultat**: Guardian passe de DEGRADED a HEALTHY.

### Mission 2: Audit ADN Scientifique - Phase B.1

Audit exhaustif en lecture seule pour comprendre l'etat actuel du systeme ADN.

#### Fichiers ADN
- Fichier principal: `/home/Mon_ps/data/quantum_v2/team_dna_unified_v2.json` (5.7 MB)
- 50+ fichiers DNA dans le projet (actifs + archives)
- Note: Le chemin documente `/home/Mon_ps/data/team_dna_unified_v2.json` est INCORRECT

#### Structure JSON
```
metadata
teams (96 equipes)
  └── [equipe]
      ├── meta
      ├── context (xG, formations, timing, Understat)
      ├── tactical (PPDA, style)
      ├── exploit
      ├── fbref
      ├── defense
      ├── defensive_line
      └── betting
```
**8 dimensions** (pas 18 comme attendu)

#### Unicite Fingerprints
- 96 equipes / 96 fingerprints uniques = **100%**
- Variance confirmee (metriques differentes par equipe)

#### Base de Donnees
- Table: `quantum.team_quantum_dna_v3`
- 96 equipes, **60 colonnes**
- Mise a jour: 2025-12-17
- Toutes les colonnes DNA remplies (context_dna, tactical_dna, etc.)

#### Integration Understat
- **233+ metriques Understat** trouvees dans le JSON
- xG, xGA, PPDA, deep, npxG integres
- Table `understat_team_match_history`: 1482 rows, 96 teams

#### Coherence JSON vs DB
- JSON: 96 equipes (13 dec)
- DB: 96 equipes (17 dec)
- Match: **89.6%**
- 10 noms divergents (AS Roma vs Roma, etc.)

## Fichiers modifies

### Cette session
- `/home/Mon_ps/monitoring/guardian/config/settings.py` - Ajout success_max_age_hours
- `/home/Mon_ps/monitoring/guardian/checks/cron_check.py` - Validation temporelle par job

### Session precedente (non pushes)
- `guardian.py` - Logique WARNING + self-healing
- `checks/logs_check.py` - Tolerance selective
- `backend/scripts/fetch_results_football_data_v2.py` - host localhost
- `.env` - Credentials Telegram

## Problemes resolus

1. **Guardian DEGRADED** → HEALTHY via success_max_age_hours par job
2. **Chemin fichier ADN** → Identifie comme `/data/quantum_v2/` (pas `/data/`)

## En cours / A faire

- [ ] Mya envoie /start au bot Telegram
- [ ] Test --test-telegram
- [ ] Push modifications Guardian
- [ ] Decision sur suite audit ADN (mapping noms, sync JSON/DB)

## Notes techniques

### Configuration success_max_age_hours
```python
# settings.py - CRON_JOBS
"fbref_scraper": {
    ...
    "success_max_age_hours": 26,  # 24h interval + 2h margin
}
```

### Validation temporelle par job
```python
# cron_check.py - check_all_crons()
job_success_max_age = job_config.get("success_max_age_hours")
if job_success_max_age:
    success_max_age_minutes = job_success_max_age * 60
else:
    success_max_age_minutes = self.success_max_age_minutes
```

### Questions ouvertes ADN
1. JSON (13 dec) vs DB (17 dec) - Source de verite?
2. 10 noms divergents - Comment mapper?
3. 60 colonnes DB vs 8 dimensions JSON - Extras?
4. Script de synchronisation JSON <-> DB?

### Commandes utiles
```bash
# Guardian status
cd /home/Mon_ps/monitoring/guardian
python3 guardian.py --dry-run --verbose

# Audit ADN rapide
python3 -c "import json; d=json.load(open('/home/Mon_ps/data/quantum_v2/team_dna_unified_v2.json')); print(len(d['teams']), 'teams')"

# Verifier coherence
docker exec monps_postgres psql -U monps_user -d monps_db -c "SELECT COUNT(*) FROM quantum.team_quantum_dna_v3"
```
