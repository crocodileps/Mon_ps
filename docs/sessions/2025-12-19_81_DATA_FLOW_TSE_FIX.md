# Session 2025-12-19 #81 - Correction Data Flow TSE vers UnifiedBrain

## Contexte
Suite session #80 (Nettoyage Post-Extension). Mission: Valider et corriger le flux de donnees TSE vers UnifiedBrain.

## Realise

### Phase 3: Validation UnifiedBrain avec donnees TSE + V3 (COMPLETE)
- Verification donnees reelles Arsenal: corner_dna, card_dna, signature_v3 PRESENTS
- Trace du flux: UnifiedBrain -> DataHubAdapter -> DataOrchestrator -> TSE + V3
- Test match Arsenal vs Liverpool: corners_expected = 10.0 (default!)
- Diagnostic: DataHubAdapter cherchait mauvaises cles

### Correction DataHubAdapter (COMPLETE)
- Bug 1: `dna["corners"]` -> `dna["corner_dna"]`
- Bug 2: `dna["cards"]` -> `dna["card_dna"]`
- Bug 3: `corners.get("corners_for")` -> `corner_dna.get("corners_for_avg")`
- Bug 4: `cards.get("yellow_cards")` -> `card_dna.get("yellows_for_avg")`
- Bug 5: Ajout alias `home_team`/`away_team` pour UnifiedBrain

### Correction UnifiedBrain (COMPLETE)
- Bug 6: `expected_total` -> `expected_total_corners`
- Bug 7: `expected_cards` -> `expected_total_cards`

### Validation finale (COMPLETE)
- Arsenal vs Liverpool: corners=10.00 (calcul reel confirme)
- Crystal Palace vs Brighton: corners=9.30 (pas default!)
- Bournemouth vs Newcastle: corners=10.80 (pas default!)
- cards_expected varie aussi: 3.00, 3.10, 3.30, 3.60

### Audit Philosophie ADN (COMPLETE)
- 96 equipes avec ADN unique: OUI
- 23 vecteurs DNA dans V3: OUI
- Profils diversifies: 5 corners, 5 cards, 13 signatures
- Donnees utilisees par UnifiedBrain: OUI (apres corrections)

### Audit Exhaustif Systemes (COMPLETE)
- Inventaire complet de tous les orchestrators, engines, loaders
- Identification systemes potentiellement legacy
- Documentation flux de donnees actuel

## Fichiers touches

### Modifies
- `/home/Mon_ps/quantum_core/adapters/data_hub_adapter.py` - Correction cles corner_dna/card_dna + alias
- `/home/Mon_ps/quantum_core/brain/unified_brain.py` - Correction cles expected_total_corners/cards

### Crees
- `/home/Mon_ps/quantum_core/adapters/data_hub_adapter.py.backup_20251219` - Backup avant modif

## Problemes resolus

1. **DataHubAdapter cherchait "corners" au lieu de "corner_dna"**
   - Cause: Nomenclature differente entre DataOrchestrator et attentes DataHubAdapter
   - Solution: Remplacer `if "corners" in dna` par `if "corner_dna" in dna`

2. **DataHubAdapter cherchait "corners_for" au lieu de "corners_for_avg"**
   - Cause: Noms de sous-cles differents dans TSE
   - Solution: Utiliser `corner_dna.get("corners_for_avg")`

3. **UnifiedBrain cherchait "expected_total" au lieu de "expected_total_corners"**
   - Cause: CornerEngine retourne une cle differente
   - Solution: Modifier la cle dans _fuse_probabilities()

4. **matchup_data n'avait pas "home_team"/"away_team"**
   - Cause: prepare_matchup_data() utilisait "home"/"away" seulement
   - Solution: Ajouter alias home_team/away_team

5. **corners_expected toujours 10.0 pour Arsenal-Liverpool**
   - Diagnostic: Calcul manuel confirme que 10.0 est CORRECT (coincidence)
   - Arsenal for=6.14, against=3.43; Liverpool for=5.29, against=5.14
   - (6.14+5.14)/2 + (5.29+3.43)/2 = 5.64 + 4.36 = 10.0

## En cours / A faire

- [x] Phase 3: Validation UnifiedBrain - COMPLETE
- [x] Correction DataHubAdapter - COMPLETE
- [x] Correction UnifiedBrain - COMPLETE
- [x] Audit philosophie ADN - COMPLETE
- [x] Audit exhaustif systemes - COMPLETE
- [ ] (Optionnel) Exploiter temporal_dna, psyche_dna, signature_v3 dans UnifiedBrain
- [ ] (Optionnel) Verifier utilisation systemes legacy

## Notes techniques

### Commit de la session
```
a4603bb fix(data-flow): Connect TSE corner/card data to UnifiedBrain
```

### Flux de donnees corrige
```
DB (TSE/V3) -> DataOrchestrator -> DataHubAdapter -> UnifiedBrain
     |              |                    |                |
 corner_dna    corner_dna         corners_for_avg   corners_expected
 (6.14)        (6.14)             (6.14)            (calcule=9.3-10.8)
```

### Donnees ADN disponibles mais non exploitees
```
V3 contient 23 vecteurs DNA, seuls 2 sont utilises:
- corner_dna -> corners_expected
- card_dna -> cards_expected

Non utilises:
- temporal_dna (early/late scorer)
- psyche_dna (mental state)
- signature_v3 (profil tactique)
- clutch_dna, luck_dna, etc.
```

### Systemes potentiellement legacy
```
- quantum/orchestrator/quantum_orchestrator_v1.py (84K)
- agents/defense_v2/, attack_v1/
- quantum/services/scenario_detector.py
- quantum/services/rule_engine.py
```

### Validations finales
```
Arsenal (DataHubAdapter):
  corners_for_avg: 6.14 (pas 5.0 default)
  yellow_cards_avg: 1.29 (pas 1.8 default)

UnifiedBrain:
  Arsenal-Liverpool: corners=10.00, cards=3.10
  Crystal Palace-Brighton: corners=9.30, cards=3.60
  Bournemouth-Newcastle: corners=10.80, cards=3.30
```
