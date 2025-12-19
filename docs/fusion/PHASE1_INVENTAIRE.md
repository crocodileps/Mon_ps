# PHASE 1: INVENTAIRE COMPLET

**Date:** 2025-12-19
**Status:** ✅ TERMINÉ

---

## OBJECTIF
Lister et mapper tous les marchés des deux fichiers sources.

---

## RÉSULTATS

| Métrique | Valeur |
|----------|--------|
| models.py marchés | 99 |
| market_registry.py marchés | 106 |
| Doublons (noms différents) | 16 |
| Identiques (même nom, même valeur) | 39 |
| **Conflits valeurs (même nom, valeur différente)** | **21** |
| Uniques models.py | 23 |
| Uniques registry | 30 |
| **TOTAL fichier unifié** | **129** |

---

## ERREUR IDENTIFIÉE - 21 CONFLITS DE VALEURS

### Cause racine
Session #91: market_registry.py créé avec format `over_25` (sans point)
ALORS QUE models.py utilisait déjà `over_0.5` (avec point)

### Pattern de l'erreur
| Nom Enum | models.py (correct) | registry.py (erreur) |
|----------|---------------------|---------------------|
| OVER_05 | over_0.5 | over_05 |
| OVER_15 | over_1.5 | over_15 |
| UNDER_25 | under_2.5 | under_25 |
| CORNERS_OVER_85 | corners_over_8.5 | corners_over_85 |
| CARDS_OVER_25 | cards_over_2.5 | cards_over_25 |

### Leçon
**TOUJOURS vérifier le format existant AVANT de créer de nouveaux éléments!**

### Décision
Format retenu: **AVEC point décimal** (over_0.5)
- Standard industrie bookmakers
- Format déjà en production
- Plus lisible

---

## DOUBLONS - NOMS DIFFÉRENTS (16)

| models.py (GARDER) | registry.py (SUPPRIMER) |
|--------------------|------------------------|
| HOME_WIN | HOME |
| AWAY_WIN | AWAY |
| HT_HOME_WIN | HT_HOME |
| HT_AWAY_WIN | HT_AWAY |
| HT_BTTS | HT_BTTS_YES |
| DR_1_1 à DR_2_2 | HT_FT_1_1 à HT_FT_2_2 |
| HOME_CLEAN_SHEET_YES | HOME_CLEAN_SHEET |
| AWAY_CLEAN_SHEET_YES | AWAY_CLEAN_SHEET |

Décision: Garder noms models.py pour compatibilité système existant.

---

## MARCHÉS UNIQUES À AJOUTER

### 23 de models.py (manquent dans registry)
- OVER_55, UNDER_55
- GOALS_0_1, GOALS_2_3, GOALS_4_5, GOALS_5_PLUS, GOALS_6_PLUS
- ODD_GOALS, EVEN_GOALS
- EXACTLY_0/1/2/3/4_GOALS
- HOME_WIN_TO_NIL_NO, AWAY_WIN_TO_NIL_NO
- SCORE_BOTH_HALVES_YES/NO
- HOME/AWAY_TO_SCORE_1H/2H
- CARDS_UNDER_25

### 30 de registry (à garder)
- Player props: ANYTIME_SCORER, FIRST_GOALSCORER, etc.
- Timing: GOAL_0_15, GOAL_16_30, etc.
- Specials: CORNER_GOAL, HEADER_GOAL, etc.

---

## PROCHAINE ÉTAPE

**Phase 2: Design fichier unifié**
- Enum unique avec 129 marchés
- Aliases pour compatibilité
- Corrélations bidirectionnelles
- Valeurs normalisées (format avec point)

