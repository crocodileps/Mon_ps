# Session 2025-12-20 #95 - Etapes 2-3-4 Market Registry

## Contexte
Suite de l'enrichissement market_registry.py apres etape 1 (renommage enums).
3 etapes completees dans cette session.

## Realise

### ETAPE 2/5: CORRECTION FORMAT VALEURS (over_05 -> over_0.5)
Ajout des points decimaux dans les valeurs string des enums.

**Patterns corriges:**
| Categorie | Nombre | Exemple |
|-----------|--------|---------|
| OVER goals | 5 | over_05 -> over_0.5 |
| UNDER goals | 5 | under_25 -> under_2.5 |
| HOME OVER | 3 | home_over_05 -> home_over_0.5 |
| AWAY OVER | 3 | away_over_05 -> away_over_0.5 |
| HALF-TIME | 3 | ht_over_05 -> ht_over_0.5 |
| FIRST/SECOND HALF | 4 | first_half_over_05 -> first_half_over_0.5 |
| ASIAN HANDICAP | 8 | ah_home_m05 -> ah_home_-0.5 |
| CORNERS | 7 | corners_over_85 -> corners_over_8.5 |
| CARDS | 6 | cards_over_25 -> cards_over_2.5 |

**Total:** ~44 patterns corriges (enums + canonical_names + correlations)

### ETAPE 3/5: ENRICHISSEMENT ALIASES BOOKMAKERS
Ajout de 4 nouveaux aliases par marche OVER/UNDER pour formats bookmakers.

**Nouveaux prefixes:**
- total_over_X.X / total_under_X.X
- match_goals_over_X.X / match_goals_under_X.X
- totals_over_X.X / totals_under_X.X
- goals_over_X.X / goals_under_X.X

**Marches enrichis:** 10 (5 OVER + 5 UNDER)
**Aliases par marche:** 4 -> 8 (+4 chacun)
**Total nouveaux aliases:** +40

### ETAPE 4/5: AMELIORATION normalize_market()
Ajout gestion tirets et espaces dans la fonction de normalisation.

**Ligne ajoutee (ligne 2728):**
```python
normalized = re.sub(r'[-\s]+', '_', normalized)  # tirets/espaces -> underscores
```

**Nouveaux formats supportes:**
- "total-over-2.5" -> OVER_25
- "total over 2.5" -> OVER_25
- "match-goals-over-2.5" -> OVER_25
- "btts-yes" -> BTTS_YES
- "btts yes" -> BTTS_YES

## Fichiers touches

### Modifies
- `/home/Mon_ps/quantum/models/market_registry.py`
  - Etape 2: ~44 sed substitutions (valeurs decimales)
  - Etape 3: 10 listes aliases enrichies (+40 aliases)
  - Etape 4: +1 ligne regex dans normalize_market()

## Tests valides

### Etape 2
- Import OK - 109 MarketTypes
- Valeurs avec point decimal OK
- Aucune valeur sans point
- normalize_market retrocompat OK

### Etape 3
- Import OK - 109 MarketTypes
- 16/16 nouveaux aliases reconnus
- 5/5 retrocompatibilite
- 10/10 marches avec 8 aliases

### Etape 4
- Import OK
- 10/10 nouveaux formats (tirets/espaces)
- 8/8 retrocompatibilite

## En cours / A faire
- [x] Etape 1/5: Renommage enums (session #93)
- [x] Correction: 8 MarketTypes manquants (session #94)
- [x] Etape 2/5: Format valeurs decimales
- [x] Etape 3/5: Enrichissement aliases bookmakers
- [x] Etape 4/5: Amelioration normalize_market()
- [ ] Etape 5/5: [A definir par Mya]

## Notes techniques

### Structure normalize_market() finale
```python
def normalize_market(market_name: str) -> Optional[MarketType]:
    import re
    normalized = market_name.lower().strip()
    normalized = re.sub(r'[-\s]+', '_', normalized)  # tirets/espaces -> underscores
    normalized = re.sub(r'_(\d)_(\d)', r'_\1\2', normalized)  # over_2_5 -> over_25
    normalized = re.sub(r'\.', '', normalized)  # over_2.5 -> over_25
    return ALIAS_REGISTRY.get(normalized)
```

### Exemple alias liste enrichie
```python
aliases=["over_2_5", "over25", "o25", "over_2.5",
         "total_over_2.5", "match_goals_over_2.5",
         "totals_over_2.5", "goals_over_2.5"]
```

## Resume
**Session #95** - 3 etapes completees:
- Etape 2: Format decimales (44 patterns)
- Etape 3: Aliases bookmakers (+40)
- Etape 4: normalize_market() tirets/espaces

**Status:** ETAPES 2-3-4 COMPLETES
