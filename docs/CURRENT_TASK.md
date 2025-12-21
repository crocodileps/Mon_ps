# CURRENT TASK - SESSION #100 - TEAM MARKET PROFILER V3 BUGFIX

**Status**: MISSION ACCOMPLIE
**Date**: 2025-12-20
**Dernière session**: #100 (Bugfix V3)

===============================================================================

## CONTEXTE

Suite à l'audit Hedge Fund de la session #99, 3 bugs critiques corrigés:
- Bug 1: Double comptage système (UNION ALL)
- Bug 2: Composite score biaisé (ROI au lieu de win_rate)
- Bug 3: Seuils trop laxistes (85% en "bet")

===============================================================================

## CORRECTIONS APPLIQUÉES

### Bug 1 - Double comptage système
```python
def extract_system_data():
    # DÉSACTIVÉ - retourne {}
    # Données insuffisantes + risque double comptage
```

### Bug 2 - Composite score
```python
# Basé sur team_win market win_rate
# 60%+ → 75-100, 40-60% → 50-75, etc.
```

### Bug 3 - Seuils recommandation
```python
# win_rate < 20% → strong_avoid
# win_rate < 30% → avoid
# composite >= 75 ET win_rate >= 55% → strong_bet
# composite >= 60 ET win_rate >= 45% → bet
```

===============================================================================

## RÉSULTATS

### Distribution Recommandations
| Action | Count | % |
|--------|-------|---|
| strong_avoid | 64 | 21.5% |
| avoid | 73 | 24.6% |
| wait | 59 | 19.9% |
| bet | 44 | 14.8% |
| strong_bet | 57 | 19.2% |

### Distribution Scores
| Range | Count | % |
|-------|-------|---|
| 80-100 | 34 | 11.4% |
| 60-79 | 67 | 22.6% |
| 40-59 | 65 | 21.9% |
| 20-39 | 73 | 24.6% |
| 0-19 | 58 | 19.5% |

===============================================================================

## FICHIERS MODIFIÉS

| Fichier | Action |
|---------|--------|
| `backend/ml/profilers/team_market_profiler_v3.py` | MODIFIÉ |
| `backend/ml/profilers/team_market_profiler_v3.py.backup_20251220_1755` | CRÉÉ |

===============================================================================

## NEXT STEPS (OPTIONNEL)

1. [ ] Ajouter colonne target_team à tracking_clv_picks
2. [ ] Réactiver données système quand 3+ mois disponibles
3. [ ] Ajouter check V3 à Guardian (fraîcheur <48h)

===============================================================================

**Last Update**: 2025-12-20 17:58
**Status**: V3 CORRIGÉE - Prochaine exécution 05h00
