# Session 2025-12-20 #100 - Team Market Profiler V3 Bugfix

## Contexte
Suite à l'audit Hedge Fund de la session #99, 3 bugs critiques ont été identifiés dans team_market_profiler_v3.py:
1. **BUG 1 - Double comptage système**: UNION ALL sur home_team + away_team doublait les picks
2. **BUG 2 - Composite score biaisé**: Calcul basé sur ROI positif, pas sur win_rate global
3. **BUG 3 - Seuils trop laxistes**: 85% des équipes en "bet", 0% en "avoid"

## Réalisé

### CORRECTION BUG 1: Double comptage système
- Fonction `extract_system_data()` désactivée temporairement
- Retourne `{}` car données insuffisantes (6 jours) + risque double comptage
- TODO: Réactiver quand colonne target_team ajoutée

### CORRECTION BUG 2: Composite score
- Nouvelle logique basée sur `team_win` market win_rate
- Échelle 0-100 mappée sur win_rate:
  - 60%+ → 75-100
  - 40-60% → 50-75
  - 20-40% → 25-50
  - 0-20% → 0-25

### CORRECTION BUG 3: Seuils recommandation
- Nouvelle signature: `determine_recommendation(composite, team_win_rate, system_profit, system_picks)`
- Règle absolue: win_rate < 20% → strong_avoid
- win_rate < 30% → avoid
- strong_bet: composite >= 75 ET win_rate >= 55%
- bet: composite >= 60 ET win_rate >= 45%
- avoid: composite < 40 OU win_rate < 35%
- wait: tout le reste

### CORRECTION save_profiles()
- `reality_win_rate` calculé depuis le marché team_win directement

## Fichiers touchés
- `/home/Mon_ps/backend/ml/profilers/team_market_profiler_v3.py` - MODIFIÉ (corrections bugs)
- `/home/Mon_ps/backend/ml/profilers/team_market_profiler_v3.py.backup_20251220_1755` - CRÉÉ (backup)
- `/home/Mon_ps/logs/team_market_profiler_v3_corrected.log` - CRÉÉ

## Problèmes résolus
- **Double comptage 2477→4954 picks** → Désactivation temporaire système
- **Composite biaisé sur ROI** → Basé sur team_win win_rate
- **0% win rate = "bet"** → Maintenant "strong_avoid"
- **85% en "bet"** → Distribution équilibrée (46% avoid, 20% wait, 34% bet)

## En cours / À faire
- [x] Backup fichier original
- [x] Corriger Bug 1 (désactiver extract_system_data)
- [x] Corriger Bug 2 (composite basé sur team_win_rate)
- [x] Corriger Bug 3 (seuils recalibrés)
- [x] Valider syntaxe
- [x] Exécuter et valider résultats
- [ ] **OPTIONNEL**: Ajouter colonne target_team à tracking_clv_picks
- [ ] **OPTIONNEL**: Réactiver système quand 3+ mois de données

## Notes techniques

### Distribution AVANT correction
| Recommandation | % |
|----------------|---|
| strong_bet | ~8% |
| bet | ~77% |
| wait | ~15% |
| avoid | 0% |
| strong_avoid | 0% |

### Distribution APRÈS correction
| Recommandation | Count | % |
|----------------|-------|---|
| strong_avoid | 64 | 21.5% |
| avoid | 73 | 24.6% |
| wait | 59 | 19.9% |
| bet | 44 | 14.8% |
| strong_bet | 57 | 19.2% |

### Scores APRÈS correction
| Range | Count | % |
|-------|-------|---|
| 80-100 | 34 | 11.4% |
| 60-79 | 67 | 22.6% |
| 40-59 | 65 | 21.9% |
| 20-39 | 73 | 24.6% |
| 0-19 | 58 | 19.5% |

### Validation équipes 0% win rate
Toutes correctement en `strong_avoid`:
- Auxerre (away), Valencia (away), Fiorentina (all), etc.

### Top équipes strong_bet
- Barcelona (home): 100% win rate
- RB Leipzig (home): 100% win rate
- Man City (home): 90% win rate
- Arsenal (home): 90% win rate

## Résumé
Session #100 - Correction de 3 bugs critiques dans Team Market Profiler V3. Distribution des recommandations passée de 85% "bet" à une répartition équilibrée (46% avoid, 20% wait, 34% bet). Les équipes à 0% win rate sont maintenant correctement classées "strong_avoid".

**Status:** MISSION ACCOMPLIE
