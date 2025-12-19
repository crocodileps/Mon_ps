# 🔬 FUSION MARKET REGISTRY - FEUILLE DE ROUTE

**Date début:** 2025-12-19
**Branche:** feature/market-registry-fusion
**Status global:** EN COURS

---

## CONTEXTE

### Problèmes identifiés (Session #93)
1. **DEUX enums MarketType en conflit** (noms différents pour même concept)
2. **142 asymétries de corrélations** (A→B mais pas B→A)
3. **DR_* vs HT_FT_*** = doublons (même concept, noms différents)
4. **21 marchés originaux sans corrélations** (0 pour HOME, DRAW, AWAY, etc.)
5. **normalize_market('dr_1_1') → None** (non reconnu!)

### Fichiers sources
| Fichier | Marchés | Rôle actuel |
|---------|---------|-------------|
| `quantum_core/brain/models.py` | ~24 | Système existant (utilisé partout) |
| `quantum/models/market_registry.py` | 106 | Nouveau avec métadonnées (partiellement utilisé) |

### Fichiers qui importent market_registry (5)
1. `quantum/models/closing_cascade.py`
2. `quantum/models/scenarios_strategy.py`
3. `quantum/models/enums.py`
4. `backend/api/services/patron_diamond_v3.py`
5. `backend/agents/clv_tracker/agent_clv_tracker_v3.py`

---

## OBJECTIF FINAL

**UN SEUL fichier source de vérité** avec:
- Tous les MarketTypes (noms compatibles avec existant)
- Toutes les métadonnées (corrélations bidirectionnelles, closing_config, etc.)
- Aliases complets pour compatibilité
- Zero duplication

---

## PHASES DE TRAVAIL

### PHASE 1: INVENTAIRE COMPLET
**Status:** ⏳ EN COURS
**Objectif:** Lister et mapper tous les marchés des deux fichiers

| Étape | Description | Status |
|-------|-------------|--------|
| 1.1 | Extraire MarketTypes de models.py | ⏳ |
| 1.2 | Extraire MarketTypes de market_registry.py | ⏳ |
| 1.3 | Créer table de mapping (doublons, différences) | ⏳ |
| 1.4 | Identifier marchés uniques dans chaque fichier | ⏳ |
| 1.5 | Documenter résultats | ⏳ |

---

### PHASE 2: DESIGN DU FICHIER UNIFIÉ
**Status:** ❌ NON COMMENCÉE
**Objectif:** Définir la structure finale

| Étape | Description | Status |
|-------|-------------|--------|
| 2.1 | Décider noms canoniques (compatibilité models.py) | ⏳ |
| 2.2 | Définir structure MarketMetadata complète | ⏳ |
| 2.3 | Planifier corrélations bidirectionnelles | ⏳ |
| 2.4 | Valider design avec Mya | ⏳ |

---

### PHASE 3: CRÉER FICHIER UNIFIÉ
**Status:** ❌ NON COMMENCÉE

---

### PHASE 4: CORRÉLATIONS COMPLÈTES
**Status:** ❌ NON COMMENCÉE

---

### PHASE 5: MIGRATION IMPORTS
**Status:** ❌ NON COMMENCÉE

---

### PHASE 6: NETTOYAGE
**Status:** ❌ NON COMMENCÉE

---

## ERREURS RENCONTRÉES & SOLUTIONS

| Date | Phase | Erreur | Solution | Leçon |
|------|-------|--------|----------|-------|
| 2025-12-19 | Pré-fusion | Claude Code a créé HT_FT_* au lieu d'utiliser DR_* existant | Fusion complète nécessaire | Toujours vérifier l'existant avant de créer |
| 2025-12-19 | Pré-fusion | 142 asymétries corrélations | Corrélations bidirectionnelles obligatoires | A→B implique B→A |
| 2025-12-19 | Pré-fusion | Fichiers modifiés non commités | Commit tout avant nouvelle branche | Toujours git status avant checkout |

---

## DÉCISIONS PRISES

| Date | Décision | Justification |
|------|----------|---------------|
| 2025-12-19 | Option C: Fusion complète | Solution la plus propre, ZERO duplication, source unique |
| 2025-12-19 | Garder noms models.py pour compatibilité | HOME_WIN plutôt que HOME (système existant) |

---

## COMMITS

| Date | Hash | Message | Phase |
|------|------|---------|-------|
| 2025-12-19 | (pending) | docs: init fusion documentation | 0 |

---

**Dernière mise à jour:** 2025-12-19

---

## MISE À JOUR 2025-12-20

### AUDIT ML COMPLET RÉALISÉ

**Découvertes:**
- team_intelligence: 675 équipes avec 70+ métriques
- market_alerts DÉJÀ REMPLI avec structure TRAP/CAUTION/alternative
- tracking_clv_picks: 3,361 picks (2,477 résolus = 74%)
- auto_learning_v7: facteurs globaux par marché existants

**Décision:** ÉTENDRE team_intelligence (pas créer nouvelle table)

### PHASE 2-3: IMPLÉMENTATION EN COURS
