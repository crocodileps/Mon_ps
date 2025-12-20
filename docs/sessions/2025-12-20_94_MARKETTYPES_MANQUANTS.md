# Session 2025-12-20 #94 - Correction 8 MarketTypes Manquants

## Contexte
Apres l'etape 1 (renommage enums), scenarios_definitions.py utilisait 8 MarketTypes
qui n'existaient pas dans market_registry.py. Mission: corriger avec approche hybride.

## Realise

### PARTIE 1: Remplacements par equivalents existants (5)
Via sed dans scenarios_definitions.py:
- AWAY_PLUS_15 → AH_AWAY_P15
- HOME_MINUS_15 → AH_HOME_M15
- HOME_OR_DRAW → DC_1X
- GOAL_0_15_YES → GOAL_0_15
- GOAL_75_90_YES → GOAL_76_90

### PARTIE 2: Creation nouveaux MarketTypes (3)
Dans market_registry.py:
- HOME_2H_OVER_05 = "home_2h_over_05"
- FIRST_HALF_HIGHEST = "first_half_highest"
- SECOND_HALF_HIGHEST = "second_half_highest"

Avec MarketMetadata complets (aliases, category, closing_config, correlations).

### PARTIE 3: Correction erreur
ClosingSource.PINNACLE n'existait pas → remplace par SYNTHESIZED_DNA

## Fichiers touches

### Modifies
- `/home/Mon_ps/quantum/models/scenarios_definitions.py` - 5 remplacements sed
- `/home/Mon_ps/quantum/models/market_registry.py` - 3 enums + 3 MarketMetadata ajoutes

## Problemes resolus
- 8 MarketTypes manquants cassaient scenarios_definitions → 5 remplacements + 3 creations
- ClosingSource.PINNACLE n'existe pas → utilise SYNTHESIZED_DNA

## Tests valides
```
TEST 1 (import market_registry): OK - 109 MarketTypes
TEST 2 (nouveaux existent): OK
TEST 3 (import scenarios): OK - 20 scenarios
TEST 4 (aucun manquant): OK - Tous les MarketTypes existent
```

## En cours / A faire
- [x] Etape 1: Renommage enums (session #93)
- [x] Correction: 8 MarketTypes manquants (cette session)
- [ ] Etape 2/5: [A definir par Mya]

## Notes techniques

### Nouveaux MarketMetadata
```python
MarketType.HOME_2H_OVER_05: MarketMetadata(
    canonical_name="home_2h_over_05",
    aliases=["home_to_score_2h", "home_2nd_half_goal", "home_score_2h"],
    category=MarketCategory.TIMING,
    closing_config=ClosingConfig(primary_source=ClosingSource.SYNTHESIZED_DNA, ...),
    liquidity_tier=LiquidityTier.LOW,
    correlations={"home_over_05": 0.60, "over_25": 0.40, "second_half_over_05": 0.50},
)
```

### Bilan MarketTypes
- Avant: 106
- Apres: 109 (+3)

## Resume
**Session #94** - Correction des 8 MarketTypes manquants.
- 5 remplacements par equivalents existants
- 3 nouveaux MarketTypes crees
- scenarios_definitions.py fonctionne maintenant

**Status:** COMPLETE
