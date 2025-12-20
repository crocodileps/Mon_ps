# Session 2025-12-20 #93 - Renommage Enums MarketType + Audit + Corrections

## Contexte
Mission d'enrichissement market_registry.py - Etape 1/5: Renommer les enums MarketType
pour compatibilite avec le systeme existant.

## Realise

### PHASE 1: Renommage 15 enums dans class MarketType
- HOME → HOME_WIN
- AWAY → AWAY_WIN
- HT_HOME → HT_HOME_WIN
- HT_AWAY → HT_AWAY_WIN
- HOME_CLEAN_SHEET → HOME_CLEAN_SHEET_YES
- AWAY_CLEAN_SHEET → AWAY_CLEAN_SHEET_YES
- HT_FT_1_1 → DR_1_1
- HT_FT_1_X → DR_1_X
- HT_FT_1_2 → DR_1_2
- HT_FT_X_1 → DR_X_1
- HT_FT_X_X → DR_X_X
- HT_FT_X_2 → DR_X_2
- HT_FT_2_1 → DR_2_1
- HT_FT_2_X → DR_2_X
- HT_FT_2_2 → DR_2_2

### PHASE 2: Renommage 15 cles dans MARKET_REGISTRY dict
Memes renommages appliques aux cles du dictionnaire.

### PHASE 3: Mise a jour 5 references dependencies
- DNB_HOME, DNB_AWAY, DC_1X, DC_X2, DC_12

### PHASE 4: Audit complet post-etape 1
Problemes detectes:
- closing_cascade.py: 2 refs (HOME, AWAY)
- scenarios_definitions.py: 10 refs (HOME_CLEAN_SHEET, AWAY_CLEAN_SHEET)
- ALIAS_REGISTRY: 4 aliases manquants (ht_ft_1_1, ht_ft_1_2, ht_ft_2_1, ht_ft_2_2)
- Correlations: HOME_WIN, DRAW, AWAY_WIN sans correlations

### PHASE 5: Corrections post-audit
- closing_cascade.py: HOME → HOME_WIN, AWAY → AWAY_WIN
- scenarios_definitions.py: 10 remplacements CLEAN_SHEET
- market_registry.py: 4 aliases ajoutes pour DR_*
- market_registry.py: 3 correlations ajoutees (5 valeurs chacune)

## Fichiers touches

### Modifies
- `/home/Mon_ps/quantum/models/market_registry.py` - 15 enums renommes, 15 cles dict, 5 dependencies, 4 aliases, 3 correlations
- `/home/Mon_ps/quantum/models/closing_cascade.py` - 2 refs corrigees
- `/home/Mon_ps/quantum/models/scenarios_definitions.py` - 10 refs corrigees

## Problemes resolus
- MarketType.HOME/AWAY cassaient closing_cascade → Renommes en HOME_WIN/AWAY_WIN
- MarketType.HOME_CLEAN_SHEET/AWAY_CLEAN_SHEET cassaient scenarios_definitions → Renommes avec _YES
- normalize_market("ht_ft_1_1") retournait None → Alias ajoute
- HOME_WIN/DRAW/AWAY_WIN sans correlations → 5 correlations ajoutees chacun

## Probleme preexistant detecte (NON RESOLU - hors scope)
- scenarios_definitions.py:343 utilise MarketType.HOME_2H_OVER_05
- Ce MarketType n'existe pas dans market_registry.py
- Suggestion: utiliser HOME_OVER_05 ou ajouter HOME_2H_OVER_05

## Tests valides
- TEST 1 (closing_cascade import): OK
- TEST 3 (aliases HT_FT): OK
- TEST 4 (correlations 1X2): OK
- TEST 5 (anciens noms): OK - Aucune reference

## En cours / A faire
- [ ] Resoudre HOME_2H_OVER_05 dans scenarios_definitions.py
- [ ] Etape 2/5 de l'enrichissement market_registry.py

## Notes techniques

### Valeurs string preservees
Les valeurs string des enums sont INCHANGEES:
- HOME_WIN.value = "home" (pas "home_win")
- DR_1_1.value = "ht_ft_1_1" (pas "dr_1_1")

### Correlations ajoutees
```python
HOME_WIN: {"draw": -0.40, "away": -0.60, "dc_1x": 0.70, "dc_12": 0.65, "dnb_home": 0.85}
DRAW: {"home": -0.40, "away": -0.40, "dc_1x": 0.65, "dc_x2": 0.65, "under_25": 0.35}
AWAY_WIN: {"home": -0.60, "draw": -0.40, "dc_x2": 0.70, "dc_12": 0.65, "dnb_away": 0.85}
```

### Commandes de verification
```bash
python3 -c "from quantum.models.market_registry import MarketType; print(MarketType.HOME_WIN.value)"
python3 -c "from quantum.models.market_registry import normalize_market; print(normalize_market('ht_ft_1_1'))"
```

## Resume
**Session #93** - Etape 1/5 de l'enrichissement market_registry completee.
- 15 enums renommes pour compatibilite
- 14 corrections post-audit effectuees
- 1 probleme preexistant detecte (HOME_2H_OVER_05)

**Status:** ETAPE 1 COMPLETE - Pret pour Etape 2
