# Session 2025-12-20 #96 - Enrichissement Aliases Massif

## Contexte
Suite de l'enrichissement market_registry.py - Etape 5/5 definie par Mya.
4 missions completees pour enrichir les aliases et ajouter de nouveaux MarketTypes.

## Realise

### MISSION 1: ENRICHIR ALIASES BTTS/DC/DNB/1X2
10 marches enrichis avec +47 nouveaux aliases:
- BTTS_YES: +5 aliases (bts, both_to_score, goals_both_teams, gol_gol, btts_yes)
- BTTS_NO: +4 aliases (btts_no, no_btts, both_to_score_no, no_gol_gol)
- DC_1X/DC_12/DC_X2: +5 aliases chacun (1x, dc1x, dc_home_draw, etc.)
- DNB_HOME/DNB_AWAY: +4 aliases chacun (dnb_home, money_line_home, ml_home, etc.)
- HOME_WIN/DRAW/AWAY_WIN: +5 aliases chacun (home, match_result_1, ft_1, etc.)

### MISSION 2: CORRIGER 2 COLLISIONS
- "home_to_nil": HOME_CLEAN_SHEET_YES le perd → HOME_WIN_TO_NIL le garde
  - Nouveaux: home_shutout, home_no_goals_against, clean_sheet_home
- "no_goal_first_half": HT_UNDER_05 le perd → NO_GOAL_FIRST_HALF le garde
  - Nouveau: first_half_0_goals

### MISSION 3: SYMETRISER AWAY_CLEAN_SHEET_YES
- Ajout +3 aliases pour symetrie avec HOME_CLEAN_SHEET_YES
- away_shutout, away_no_goals_against, clean_sheet_away

### MISSION 4: AJOUTER 14 NOUVEAUX MARKETTYPES
**Exact Goals (5):**
- EXACTLY_0, EXACTLY_1, EXACTLY_2, EXACTLY_3, EXACTLY_4

**Goal Ranges (5):**
- GOALS_0_1, GOALS_2_3, GOALS_4_5, GOALS_5_PLUS, GOALS_6_PLUS

**Odd/Even (2):**
- ODD_GOALS, EVEN_GOALS

**Win To Nil No (2):**
- HOME_WIN_TO_NIL_NO, AWAY_WIN_TO_NIL_NO

Correction collision: "2_goals"→"total_2_goals", "3_goals"→"total_3_goals"

### MISSION 5: ENRICHIR ALIASES CORNERS/CARDS/AH (+56 aliases)
**CORNERS (7 marches, +14 aliases):**
- Ajout total_corners_* et match_corners_* pour chaque marche

**CARDS (6 marches, +18 aliases):**
- Ajout total_cards_*, match_cards_*, bookings_* pour chaque marche

**AH (8 marches, +24 aliases):**
- Ajout asian_handicap_*, spread_*, handicap_* pour chaque marche

### CORRECTION REGEX normalize_market()
Probleme: regex `[-\s]+` remplacait aussi le signe moins des handicaps
Solution: regex `(?<!_)-|\s+` preserve le signe moins apres underscore

## Fichiers touches

### Modifies
- `/home/Mon_ps/quantum/models/market_registry.py`
  - +14 membres enum MarketType
  - +14 MarketMetadata complets
  - ~100 aliases ajoutes/modifies
  - Regex normalize_market() ameliore

## Problemes resolus
- Collision "2_goals" avec SCORER_2PLUS → renomme en "total_2_goals"
- Collision "3_goals" avec SCORER_HATTRICK → renomme en "total_3_goals"
- Regex ne preservait pas signe moins → nouveau regex `(?<!_)-|\s+`

## Tests valides
- Import OK: 109 → 123 MarketTypes
- Zero collision detectee
- ALIAS_REGISTRY: 610 entrees
- Tous formats supportes: tirets, espaces, signe moins

## En cours / A faire
- [x] Mission 1: Aliases BTTS/DC/DNB/1X2
- [x] Mission 2: Corriger collisions
- [x] Mission 3: Symetriser AWAY_CLEAN_SHEET_YES
- [x] Mission 4: 14 nouveaux MarketTypes
- [x] Mission 5: Aliases CORNERS/CARDS/AH
- [ ] Prochaine etape: A definir par Mya

## Notes techniques

### Structure normalize_market() finale
```python
def normalize_market(market_name: str) -> Optional[MarketType]:
    import re
    normalized = market_name.lower().strip()
    normalized = re.sub(r'(?<!_)-|\s+', '_', normalized)  # tirets (sauf apres _) + espaces
    normalized = re.sub(r'_(\d)_(\d)', r'_\1\2', normalized)  # over_2_5 -> over_25
    normalized = re.sub(r'\.', '', normalized)  # over_2.5 -> over_25
    return ALIAS_REGISTRY.get(normalized)
```

### Bilan MarketTypes
- Avant session: 109
- Apres session: 123 (+14)

### Bilan Aliases
- ALIAS_REGISTRY: 610 entrees
- Total aliases dans MARKET_REGISTRY: 520

## Resume
**Session #96** - Enrichissement massif:
- 4 missions completees
- +14 MarketTypes
- ~100 aliases ajoutes
- 2 collisions resolues
- Regex ameliore

**Status:** SESSION COMPLETE
