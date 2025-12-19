# PHASE 1: INVENTAIRE COMPLET

**Date:** 2025-12-19
**Status:** ✅ TERMINÉ
**Commit:** (à venir)

---

## OBJECTIF
Lister et mapper tous les marchés des deux fichiers sources.

---

## RÉSULTATS

### Comptage
| Fichier | Marchés | Autres enums |
|---------|---------|--------------|
| models.py | 99 | 10 |
| market_registry.py | 106 | 4 catégories |

### Analyse croisée
| Catégorie | Nombre | Action |
|-----------|--------|--------|
| Doublons (noms différents) | 16 | Renommer registry → models.py |
| Identiques valeurs | 39 | Aucune |
| Identiques noms, valeurs différentes | 21 | Unifier valeurs |
| Uniques models.py | 23 | Ajouter à registry |
| Uniques registry | 30 | Garder |

### Total fichier unifié
- 99 (models) + 30 (uniques registry) = **129 marchés**

---

## DOUBLONS DÉTAILLÉS (16)

| models.py | registry.py | Valeur models | Valeur registry |
|-----------|-------------|---------------|-----------------|
| HOME_WIN | HOME | home_win | home |
| AWAY_WIN | AWAY | away_win | away |
| HT_HOME_WIN | HT_HOME | ht_home_win | ht_home |
| HT_AWAY_WIN | HT_AWAY | ht_away_win | ht_away |
| HT_BTTS | HT_BTTS_YES | ht_btts | ht_btts_yes |
| DR_1_1 | HT_FT_1_1 | dr_1_1 | ht_ft_1_1 |
| DR_1_X | HT_FT_1_X | dr_1_x | ht_ft_1_x |
| DR_1_2 | HT_FT_1_2 | dr_1_2 | ht_ft_1_2 |
| DR_X_1 | HT_FT_X_1 | dr_x_1 | ht_ft_x_1 |
| DR_X_X | HT_FT_X_X | dr_x_x | ht_ft_x_x |
| DR_X_2 | HT_FT_X_2 | dr_x_2 | ht_ft_x_2 |
| DR_2_1 | HT_FT_2_1 | dr_2_1 | ht_ft_2_1 |
| DR_2_X | HT_FT_2_X | dr_2_x | ht_ft_2_x |
| DR_2_2 | HT_FT_2_2 | dr_2_2 | ht_ft_2_2 |
| HOME_CLEAN_SHEET_YES | HOME_CLEAN_SHEET | home_clean_sheet_yes | home_clean_sheet |
| AWAY_CLEAN_SHEET_YES | AWAY_CLEAN_SHEET | away_clean_sheet_yes | away_clean_sheet |

**DÉCISION:** Garder noms et valeurs de models.py

---

## CONFLITS DE VALEURS (21)

| Nom | models.py | registry.py | DÉCISION |
|-----|-----------|-------------|----------|
| OVER_05 | over_0.5 | over_05 | over_0.5 |
| OVER_15 | over_1.5 | over_15 | over_1.5 |
| OVER_25 | over_2.5 | over_25 | over_2.5 |
| OVER_35 | over_3.5 | over_35 | over_3.5 |
| OVER_45 | over_4.5 | over_45 | over_4.5 |
| UNDER_05 | under_0.5 | under_05 | under_0.5 |
| UNDER_15 | under_1.5 | under_15 | under_1.5 |
| UNDER_25 | under_2.5 | under_25 | under_2.5 |
| UNDER_35 | under_3.5 | under_35 | under_3.5 |
| UNDER_45 | under_4.5 | under_45 | under_4.5 |
| CORNERS_OVER_85 | corners_over_8.5 | corners_over_85 | corners_over_8.5 |
| CORNERS_OVER_95 | corners_over_9.5 | corners_over_95 | corners_over_9.5 |
| CORNERS_OVER_105 | corners_over_10.5 | corners_over_105 | corners_over_10.5 |
| CORNERS_UNDER_85 | corners_under_8.5 | corners_under_85 | corners_under_8.5 |
| CORNERS_UNDER_95 | corners_under_9.5 | corners_under_95 | corners_under_9.5 |
| CORNERS_UNDER_105 | corners_under_10.5 | corners_under_105 | corners_under_10.5 |
| CARDS_OVER_25 | cards_over_2.5 | cards_over_25 | cards_over_2.5 |
| CARDS_OVER_35 | cards_over_3.5 | cards_over_35 | cards_over_3.5 |
| CARDS_OVER_45 | cards_over_4.5 | cards_over_45 | cards_over_4.5 |
| CARDS_UNDER_35 | cards_under_3.5 | cards_under_35 | cards_under_3.5 |
| CARDS_UNDER_45 | cards_under_4.5 | cards_under_45 | cards_under_4.5 |

**DÉCISION:** Garder format avec point (over_0.5) - standard industrie

---

## MARCHÉS UNIQUES À MODELS.PY (23)

À intégrer dans le fichier unifié avec métadonnées:
- OVER_55, UNDER_55
- CARDS_UNDER_25
- GOALS_0_1, GOALS_2_3, GOALS_4_5, GOALS_5_PLUS, GOALS_6_PLUS
- HOME_WIN_TO_NIL_NO, AWAY_WIN_TO_NIL_NO
- ODD_GOALS, EVEN_GOALS
- EXACTLY_0_GOALS, EXACTLY_1_GOAL, EXACTLY_2_GOALS, EXACTLY_3_GOALS, EXACTLY_4_GOALS
- SCORE_BOTH_HALVES_YES, SCORE_BOTH_HALVES_NO
- HOME_TO_SCORE_1H, HOME_TO_SCORE_2H, AWAY_TO_SCORE_1H, AWAY_TO_SCORE_2H

---

## MARCHÉS UNIQUES À REGISTRY (30)

À garder dans le fichier unifié:
- CORNERS_OVER_115, CARDS_OVER_55
- CS_0_3, CS_1_3, CS_3_0
- GOAL_0_15, GOAL_16_30, GOAL_31_45, GOAL_46_60, GOAL_61_75, GOAL_76_90
- HT_BTTS_NO, HT_OVER_15
- SCORER_2PLUS, SCORER_HATTRICK
- ANYTIME_SCORER, FIRST_GOALSCORER, LAST_GOALSCORER
- FIRST_HALF_OVER_05, FIRST_HALF_OVER_15
- NO_GOAL_FIRST_HALF
- CORNER_GOAL, HEADER_GOAL, OUTSIDE_BOX_GOAL, OWN_GOAL
- SET_PIECE_GOAL, PENALTY_SCORED, SHOTS_ON_TARGET_OVER

---

## PROCHAINE ÉTAPE

Phase 2: Design du fichier unifié
- Structure enum unique
- Système d'aliases pour compatibilité
- Métadonnées complètes (corrélations bidirectionnelles)

