# Session 2025-12-18 #74 - Guardian Hedge Fund Perfection

## Contexte
Continuation des sessions #73-74. Installation et perfectionnement du système Institutional Guardian v1.0 - un système de monitoring, health check et self-healing de niveau Hedge Fund pour Mon_PS.

## Réalisé

### Phase 1: Corrections Crontab
- Correction chemin football_data: retiré `/data_enrichment/` du path
- Correction understat_main: ajouté `cd /home/Mon_ps &&` manquant
- Backup créé: `crontab_backup_phase2_20251218_154919.txt`

### Phase 2: Corrections Guardian Post-Validation
- settings.py: chemin script football_data corrigé
- fetch_results_football_data_v2.py: host DB `monps_postgres` → `localhost`
- Tests validés: script fonctionne, Guardian montre script_ready: OK

### Phase 3: Commit Git
- Commit `4f3b5af`: fix: Correct football_data paths and DB hostname

### Phase 4: Configuration Telegram
- Fichier `.env` créé avec credentials
- Ajout `load_dotenv()` dans settings.py
- Issue: "chat not found" - bot doit recevoir /start de l'utilisateur

### Phase 5: Corrections Guardian Logique Hedge Fund (3 corrections)
1. **determine_overall_status()**: Détecte WARNING pour non_critical_down et cron_warnings
2. **attempt_self_healing()**: Traite critical_down ET non_critical_down
3. **send_notifications()**: Message WARNING avec détails
4. **BONUS**: Ajout WARNING dans exit_codes

### Phase 6: Tolérance Sélective + Validation Positive
- **logs_check.py**:
  - Patterns IGNORE_WARNING_PATTERNS et IGNORE_ERROR_PATTERNS
  - Promotion CRITICAL_IN_WARNINGS vers erreurs
- **cron_check.py**:
  - SUCCESS_PATTERNS pour validation positive
  - check_success_confirmation() ajouté

### Phase 7: Guardian Perfection Hedge Fund (5 points)
1. **Point 1 - Faux Négatifs**: ZERO_RESULTS_PATTERNS avec word boundary matching
2. **Point 2 - Fenêtre**: 50→150 lignes (configurable)
3. **Point 3 - Contamination**: Validation temporelle (max 120min)
4. **Point 4 - Patterns externalisés**: Tout dans settings.py
5. **Point 5 - Métriques filtrage**: filtered_warnings, filtered_errors, promoted_to_error, zero_results_detected

## Fichiers créés
- `/home/Mon_ps/monitoring/guardian/.env` - Credentials Telegram
- `/home/Mon_ps/crontab_backup_phase2_20251218_154919.txt` - Backup crontab

## Fichiers modifiés
- `/home/Mon_ps/monitoring/guardian/config/settings.py` - Patterns centralisés + load_dotenv
- `/home/Mon_ps/monitoring/guardian/checks/logs_check.py` - Tolérance sélective + métriques
- `/home/Mon_ps/monitoring/guardian/checks/cron_check.py` - Validation positive temporelle
- `/home/Mon_ps/monitoring/guardian/guardian.py` - Logique WARNING + self-healing amélioré
- `/home/Mon_ps/backend/scripts/fetch_results_football_data_v2.py` - host localhost
- Crontab - 2 corrections chemins

## Problèmes résolus
- "chat not found" Telegram → User doit /start le bot (action manuelle)
- "non-critical" matchait "CRITICAL" → IGNORE_ERROR_PATTERNS ajouté
- "380 matchs" matchait "0 matchs" → Word boundary regex
- Logs Guardian propres matchaient WARNING → Patterns d'exclusion
- Succès ancien comptait → Validation temporelle max 2h

## En cours / À faire
- [ ] User doit /start le bot Telegram
- [ ] Test --test-telegram après /start
- [ ] Push des modifications (attente validation Mya)
- [ ] Vérifier cron Guardian demain 7h00 UTC

## Notes techniques

### Configuration Telegram
```bash
# Après /start au bot, tester:
cd /home/Mon_ps/monitoring/guardian
python3 guardian.py --test-telegram
```

### Patterns externalisés (settings.py)
- IGNORE_WARNING_PATTERNS: 10 patterns (FutureWarning, Status 403, etc.)
- IGNORE_ERROR_PATTERNS: 3 patterns (non-critical, Overall status, Complete)
- CRITICAL_IN_WARNINGS: 10 patterns (Status 429, Connection refused, etc.)
- ZERO_RESULTS_PATTERNS: 14 patterns spécifiques
- SUCCESS_PATTERNS: 18 patterns (✅, rows saved, SCRAPING TERMINE, etc.)
- LOG_SCAN_CONFIG: {"lines_to_scan": 150, "success_max_age_minutes": 120}

### Validation temporelle
La méthode `check_success_confirmation()` extrait le timestamp des logs et vérifie que le succès date de moins de 120 minutes. Évite la contamination par des succès anciens.

### Métriques de filtrage (Point 5)
```json
{
  "filtering_metrics": {
    "filtered_warnings": 25,
    "filtered_errors": 1,
    "promoted_to_error": 0,
    "zero_results_detected": 0
  }
}
```

### Git
- Commit local: `4f3b5af` (pas encore pushé)
- Modifications guardian non commitées (attente validation)

### Cron Guardian
```
0 7 * * * cd /home/Mon_ps/monitoring/guardian && python3 guardian.py >> /home/Mon_ps/logs/guardian_cron.log 2>&1
```
