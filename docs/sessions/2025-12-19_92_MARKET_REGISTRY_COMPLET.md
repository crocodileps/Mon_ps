# Session 2025-12-19 #92 - Market Registry 106/106 COMPLET

## Contexte

Configuration complete des 85 marches manquants dans market_registry.py:
- Objectif: Passer de 21 a 106 marches configures
- Chaque marche a: aliases, correlations, closing_config, liquidity

## Realise

### PHASE 1: Goals Over/Under (8 marches)
- OVER_05, OVER_15, OVER_35, OVER_45
- UNDER_05, UNDER_15, UNDER_35, UNDER_45

### PHASE 2: Team Goals (6 marches)
- HOME_OVER_05, HOME_OVER_15, HOME_OVER_25
- AWAY_OVER_05, AWAY_OVER_15, AWAY_OVER_25

### PHASE 3: BTTS Specials (2 marches)
- BTTS_BOTH_HALVES_YES, BTTS_BOTH_HALVES_NO

### PHASE 4: Corners (7 marches)
- CORNERS_OVER_85, 95, 105, 115
- CORNERS_UNDER_85, 95, 105

### PHASE 5: Cards (6 marches)
- CARDS_OVER_25, 35, 45, 55
- CARDS_UNDER_35, 45

### PHASE 6: Half-Time (8 marches)
- HT_HOME, HT_DRAW, HT_AWAY
- HT_OVER_05, HT_UNDER_05, HT_OVER_15
- HT_BTTS_YES, HT_BTTS_NO

### PHASE 7: HT/FT Double Result (9 marches)
- HT_FT_1_1, 1_X, 1_2
- HT_FT_X_1, X_X, X_2
- HT_FT_2_1, 2_X, 2_2

### PHASE 8: Asian Handicap (8 marches)
- AH_HOME_M05, M10, M15, M20
- AH_AWAY_P05, P10, P15, P20

### PHASE 9: Correct Score (13 marches)
- CS_0_0, 1_0, 0_1, 1_1, 2_0, 0_2, 2_1, 1_2, 2_2, 3_0, 0_3, 3_1, 1_3

### PHASE 10: Timing (9 marches)
- GOAL_16_30, 31_45, 46_60, 61_75
- NO_GOAL_FIRST_HALF
- FIRST_HALF_OVER_05, FIRST_HALF_OVER_15
- SECOND_HALF_OVER_05, SECOND_HALF_OVER_15

### PHASE 11: Player Props (3 marches)
- LAST_GOALSCORER, SCORER_2PLUS, SCORER_HATTRICK

### PHASE 12: Specials (4 marches)
- SET_PIECE_GOAL, OWN_GOAL, OUTSIDE_BOX_GOAL, SHOTS_ON_TARGET_OVER

### PHASE 13: Win To Nil (2 marches)
- HOME_WIN_TO_NIL, AWAY_WIN_TO_NIL

## Fichiers touches

### Modifies
- `/home/Mon_ps/quantum/models/market_registry.py` - 85 MarketMetadata ajoutes

## Ameliorations techniques

### 1. Normalisation coherente des aliases
```python
def _build_alias_registry() -> Dict[str, MarketType]:
    def _normalize_alias(alias: str) -> str:
        normalized = alias.lower().strip()
        normalized = re.sub(r'_(\d)_(\d)', r'_\1\2', normalized)
        normalized = re.sub(r'\.', '', normalized)
        return normalized
    # ...
```

### 2. Correlations mathematiques
- Marches opposes: correlation = -1.0 (ex: over_25 <-> under_25)
- Meme direction proche: +0.85 a +0.95 (ex: over_15 <-> over_25)
- Meme direction lointain: +0.60 a +0.75 (ex: over_15 <-> over_45)
- Implication: +0.90 a +0.99 (ex: over_35 -> over_25)

### 3. Liquidite par categorie
| Categorie | LiquidityTier | liquidity_tax | min_edge |
|-----------|---------------|---------------|----------|
| Goals O/U | ELITE/HIGH | 0.01-0.015 | 0.02 |
| BTTS | HIGH | 0.015 | 0.025 |
| Corners/Cards | LOW | 0.025 | 0.03 |
| Asian Handicap | HIGH | 0.015 | 0.02 |
| Correct Score | LOW/EXOTIC | 0.05 | 0.05-0.06 |

## Tests de validation

```
Configures: 106 / 106

=== TESTS NORMALIZE_MARKET ===
over_0.5 -> over_05 ✓
corners_over_8.5 -> corners_over_85 ✓
cards_over_3.5 -> cards_over_35 ✓
ah_-0.5_home -> ah_home_m05 ✓
1-1 -> cs_1_1 ✓
btts -> btts_yes ✓

Resultat: 31/31 tests passes
Validation: 0 erreurs
```

## Resume par categorie

| Categorie | Marches |
|-----------|---------|
| special | 31 |
| goals | 22 |
| timing | 19 |
| result | 8 |
| handicap | 8 |
| corners | 7 |
| cards | 6 |
| player | 5 |

## En cours / A faire

- [x] Configurer 85 marches manquants
- [x] Normalisation coherente des aliases
- [x] Tests de validation complets
- [ ] Integration avec le systeme de trading
- [ ] Implementation synthese DNA par categorie

## Notes techniques

### Structure MarketMetadata
```python
MarketMetadata(
    canonical_name="over_05",
    aliases=["over_0_5", "over05", "o05", "over_0.5"],
    category=MarketCategory.GOALS,
    payoff_type=PayoffType.BINARY,
    closing_config=ClosingConfig(
        primary_source=ClosingSource.SYNTHESIZED_DNA,
        fallback_sources=[ClosingSource.ESTIMATED],
        quality_by_source={...}
    ),
    liquidity_tier=LiquidityTier.HIGH,
    liquidity_tax=0.015,
    min_edge=0.02,
    correlations={"over_15": 0.95, "over_25": 0.85, "under_05": -1.0},
)
```

## Resume

**Session #92** - Configuration complete du Market Registry.

- 85 marches ajoutes (21 -> 106)
- Normalisation coherente des aliases
- Correlations mathematiquement valides
- 31/31 tests passes, 0 erreurs validation

**Status:** COMPLETE
