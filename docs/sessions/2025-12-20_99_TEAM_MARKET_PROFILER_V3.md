# Session 2025-12-20 #99 - Team Market Profiler V3 Unified

## Contexte
Suite à l'audit session #98 qui a identifié V1 vs V2 incompatibles, mission d'implémenter une V3 unifiée "Hedge Fund Grade" fusionnant les deux sources de données:
- V1: match_xg_stats (817 matchs réels, 489 jours)
- V2: tracking_clv_picks (2477 picks système)

## Réalisé

### ÉTAPE 1: TABLE V3 CRÉÉE
- 43 colonnes couvrant réalité + système + métriques combinées
- 9 index (dont GIN pour JSONB)
- 3 contraintes CHECK (location, confidence_level, recommended_action)
- 1 contrainte UNIQUE (team_name, league, season, location)

### ÉTAPE 2: SCRIPT PYTHON V3
- 517 lignes, architecture modulaire
- Chemin: `/home/Mon_ps/backend/ml/profilers/team_market_profiler_v3.py`
- Fonctions: extract_reality_data, extract_system_data, build_unified_profiles, save_profiles
- Pondération dynamique: 60/40 (high data), 80/20 (medium), 100/0 (low)

### ÉTAPE 3: TEST RÉUSSI
- 297 profils créés en 0.8s
- 99 équipes uniques
- 219 avec données système (74%)
- Composite score moyen: 69.96

### ÉTAPE 4: CRON CONFIGURÉ
- Wrapper script: `/home/Mon_ps/scripts/run_team_market_profiler_v3.sh`
- Horaire: 0 5 * * * (05h00 quotidien)
- Log: `/home/Mon_ps/logs/team_market_profiler_v3.log`

### ÉTAPE 5: VALIDATION
- Table V1 préservée (1188 rows)
- Backward compatibility maintenue

## Fichiers touchés
- `/home/Mon_ps/backend/ml/profilers/team_market_profiler_v3.py` - CRÉÉ (517 lignes)
- `/home/Mon_ps/scripts/run_team_market_profiler_v3.sh` - CRÉÉ (wrapper CRON)
- `/home/Mon_ps/logs/team_market_profiler_v3.log` - CRÉÉ
- `team_market_profiles_v3` (table PostgreSQL) - CRÉÉE (43 colonnes)
- crontab - MODIFIÉ (ajout job 05h00)

## Problèmes résolus
- **tracking_clv_picks n'a pas de colonne team_name** -> Solution: Utilisation UNION ALL sur home_team + away_team
- **odds column n'existe pas** -> Solution: Utilisation de odds_taken
- **Script non visible dans container** -> Solution: Wrapper script avec docker cp avant exécution

## En cours / À faire
- [x] Créer table V3
- [x] Créer script Python V3
- [x] Tester le script
- [x] Ajouter au CRON
- [x] Validation finale
- [ ] **OPTIONNEL**: Ajouter V3 check à Guardian
- [ ] **OPTIONNEL**: Créer consumer pour quantum/chess_engine

## Notes techniques

### Architecture V3
```
match_xg_stats (RÉALITÉ) ──┐
                           ├──► team_market_profiler_v3.py ──► team_market_profiles_v3
tracking_clv_picks (SYSTÈME)┘
```

### Schéma colonnes principales
- reality_*: Métriques des matchs réels (matches_played, wins, win_rate, best_market, markets_detail JSONB)
- system_*: Métriques des picks système (picks_count, wins, avg_clv, total_profit, markets_detail JSONB)
- composite_score: Score 0-100 combiné
- confidence_level: high/medium/low/insufficient
- recommended_action: strong_bet/bet/wait/avoid/strong_avoid

### Pondération composite score
- High (>50 picks): 60% réalité + 40% système
- Medium (10-50 picks): 80% réalité + 20% système
- Low (<10 picks): 100% réalité + 0% système

### Métriques finales
| Métrique | Valeur |
|----------|--------|
| Total profils | 297 |
| Équipes | 99 |
| Avec système | 219 (74%) |
| Avg composite | 69.96 |
| Strong bet | 26 |
| Bet | 226 |
| Wait | 45 |
| Avoid | 0 |

## Résumé
Session #99 - Implémentation complète de Team Market Profiler V3 "Unified Hedge Fund Grade". Fusion réussie des données réalité (match_xg_stats) et système (tracking_clv_picks) en une seule table unifiée avec scoring composite. Prochaine exécution automatique: demain 05h00.

**Status:** MISSION ACCOMPLIE
