# SESSION 2025-12-21 - BTTS DNA SYNTHESIS FIX

## CONTEXTE
- **Problème initial:** 507 picks BTTS n'avaient pas de closing_odds
- **Diagnostic:** La synthèse ADN était skippée car over_25 manquait dans liquid_odds
- **Root cause:** synthesize_btts_closing() requiert 4 inputs: home, draw, away, over_25

## SOLUTION IMPLÉMENTÉE
1. **Modifié:** scripts/enrich_btts_closing_dna.py
2. **Ajouté:** Second CTE liquid_odds_totals pour joindre odds_totals (Over 2.5)
3. **Ajouté:** Clé over_25 dans le dict liquid_odds

## RÉSULTATS ENRICHISSEMENT
- **507/507 picks enrichis** (100% succès)
- **Source:** SYNTHESIZED_DNA (pas ESTIMATED)
- **Facteurs ADN:** defense_factor, attack_factor, lambda utilisés

## DÉCOUVERTES MAJEURES

### BTTS YES - Edge NÉGATIF
| Métrique | Valeur |
|----------|--------|
| Picks valides | 239 |
| CLV moyen | **-13.80%** |
| % CLV positif | 15% (36/239) |
| Gain moyen si positif | +9.75% |
| Perte moyenne si négatif | -17.98% |

**Interprétation:** Asymétrie défavorable. Le marché se resserre avant nos bets.

### BTTS NO - Edge POSITIF MASSIF
| Métrique | Valeur |
|----------|--------|
| Picks valides | 255 |
| CLV moyen | **+38.64%** |
| % CLV positif | 84% (213/255) |
| Gain moyen si positif | +47.98% |
| Perte moyenne si négatif | -8.75% |

**Interprétation:** Asymétrie favorable. Edge significatif détecté.

## ANOMALIE DONNÉES
- **16 picks** avaient odds_taken = 0 (données corrompues)
- **Impact:** Faussaient le CLV avec des -100% artificiels
- **Solution:** Filtrer WHERE odds_taken > 0 dans les analyses

## RECOMMANDATIONS STRATÉGIQUES
1. **RÉDUIRE** exposition BTTS YES (CLV négatif structurel)
2. **AUGMENTER** exposition BTTS NO (alpha confirmé +38%)
3. **INVESTIGUER** pourquoi BTTS YES sous-performe

## GIT COMMIT
- **Hash:** 101d4d1
- **Date:** 2025-12-21

## PROCHAINES ÉTAPES
1. Analyser pattern temporel BTTS YES (timing picks)
2. Comparer performance par league
3. Implémenter filtre CLV dans stratégie live
