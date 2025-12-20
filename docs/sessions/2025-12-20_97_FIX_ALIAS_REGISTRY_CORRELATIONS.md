# Session 2025-12-20 #97 - Fix ALIAS_REGISTRY + Fonctions Correlations

## Contexte
Suite de l'enrichissement market_registry.py. 3 missions de correction et d'ajout de fonctionnalites.

## Realise

### MISSION 1: FIX NORMALISATION ALIAS_REGISTRY
**Probleme:** canonical_name stocke tel quel mais normalize_market() cherche version normalisee.
- Exemple: "second_half_over_0.5" stocke, mais "second_half_over_05" cherche → None

**Solution:** Modifier _build_alias_registry() pour stocker AUSSI le canonical_name normalise.

**Code modifie (lignes 2999-3015):**
```python
# AVANT:
registry[metadata.canonical_name] = market_type

# APRES:
# Ajouter le canonical_name ORIGINAL
registry[metadata.canonical_name] = market_type
# Ajouter le canonical_name NORMALISE (si different)
normalized_canonical = _normalize_alias(metadata.canonical_name)
if normalized_canonical != metadata.canonical_name:
    registry[normalized_canonical] = market_type
```

**Resultat:** ALIAS_REGISTRY: 610 → 631 (+21 entrees normalisees)

### MISSION 2: AJOUTER FONCTIONS CORRELATIONS
2 nouvelles fonctions utilitaires:

**get_all_correlations(market_type):**
- Retourne outgoing (ce que le marche implique) + incoming (ce qui implique le marche)
- Docstring detaillee sur l'asymetrie mathematique
- Lignes 3186-3235

**get_correlation_graph():**
- Retourne le graphe complet des correlations (109 marches, 317 edges)
- Lignes 3238-3256

### MISSION 3: CORRIGER FORMAT OUTGOING
**Probleme:** outgoing retournait alias bruts minuscules, incoming retournait enum names.

**Solution:** Normaliser outgoing vers enum names via normalize_market().

**Resultat:** Format unifie MAJUSCULES partout (DRAW, DC_1X, DNB_HOME...)

## Fichiers touches

### Modifies
- `/home/Mon_ps/quantum/models/market_registry.py`
  - _build_alias_registry(): +5 lignes pour canonical normalise
  - +2 fonctions: get_all_correlations(), get_correlation_graph()
  - __all__: +2 exports (get_all_correlations, get_correlation_graph)
  - get_all_correlations(): outgoing normalise vers enum names

## Problemes resolus
- Orphelines "second_half_over_0.5" etc → 7/7 resolues
- Format incohrent outgoing/incoming → unifie ENUM NAMES

## Tests valides
- Import OK: 123 MarketTypes
- ALIAS_REGISTRY: 631 entrees
- Orphelines: 7/7 resolues
- Retrocompatibilite: 5/5
- Collisions: 0
- Graphe correlations: 109 marches, 317 edges
- Format unifie: outgoing/incoming = ENUM NAMES
- Relations bidirectionnelles detectables

## En cours / A faire
- [x] Fix normalisation ALIAS_REGISTRY
- [x] Ajouter get_all_correlations()
- [x] Ajouter get_correlation_graph()
- [x] Corriger format outgoing vers enum names
- [ ] Prochaine etape: A definir par Mya

## Notes techniques

### Structure get_all_correlations()
```python
def get_all_correlations(market_type: MarketType) -> Dict[str, Dict[str, float]]:
    result = {'outgoing': {}, 'incoming': {}}

    # 1. Correlations SORTANTES (normalisees vers enum names)
    meta = MARKET_REGISTRY.get(market_type)
    if meta and meta.correlations:
        for target_alias, weight in meta.correlations.items():
            target_mt = normalize_market(target_alias)
            if target_mt:
                result['outgoing'][target_mt.name] = weight

    # 2. Correlations ENTRANTES (scan inverse)
    for mt, m in MARKET_REGISTRY.items():
        if mt == market_type:
            continue
        if m.correlations:
            for target_name, weight in m.correlations.items():
                target_mt = normalize_market(target_name)
                if target_mt == market_type:
                    result['incoming'][mt.name] = weight

    return result
```

### Bilan statistiques
- MarketTypes: 123
- ALIAS_REGISTRY: 631
- Correlations: 109 marches sources, 317 edges

## Resume
**Session #97** - 3 missions:
- Fix ALIAS_REGISTRY: +21 entrees normalisees
- 2 fonctions correlations ajoutees
- Format outgoing unifie

**Status:** SESSION COMPLETE
