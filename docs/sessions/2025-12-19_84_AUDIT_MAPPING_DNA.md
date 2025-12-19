# Session 2025-12-19 #84 - Audit Mapping DNA et Chasse CLV

## Contexte

Mya a demande de:
1. Auditer le mapping DNA existant dans UnifiedBrain/DataOrchestrator
2. Comparer les 11 dataclasses de quantum_orchestrator_v1 avec les donnees reelles V3
3. Verifier le mapping PSG/Inter
4. Trouver les donnees CLV pour SentimentDNA

## Realise

### Phase 1: Audit Mapping Existant
- **DataOrchestrator** (`quantum_core/data/orchestrator.py`): 954 lignes
  - Methode `get_team_dna()` ligne 254
  - Charge depuis: TSE + V3 + JSON + team_profiles (fallback)
  - Mapping PSG existe ligne 804: `"PSG": "Paris Saint Germain"`
  - Mapping Inter: **MANQUANT** (JSON="Inter Milan", DB="Inter")

### Phase 2: Comparaison V1 Dataclasses vs V3 DB

| Dataclass V1 | Compatibilite avec V3 |
|--------------|----------------------|
| TemporalDNA | 33% (2/6 champs communs) |
| MarketDNA | 14% (1/7 champs communs) |
| NemesisDNA | 20% (1/5 champs communs) |
| PsycheDNA | 40% (2/5 champs communs) |
| LuckDNA | 33% (2/6 champs communs) |
| ChameleonDNA | 33% (2/6 champs communs) |
| RosterDNA | **0%** (0/4 champs communs) |
| PhysicalDNA | **0%** (0/4 champs communs) |
| ContextDNA | ~20% (home/away_strength) |
| SentimentDNA | **0%** (colonne vide) |

**Conclusion**: Les dataclasses V1 ont des champs DIFFERENTS de ce qui est stocke en V3.

### Phase 3: Chasse CLV pour SentimentDNA

**sentiment_dna**: VIDE pour 96/96 equipes

**CLV trouve dans:**
- `market_dna.empirical_profile.avg_clv` = 0 pour toutes equipes
- `quantum.team_quantum_dna_v3.avg_clv` = NULL pour toutes equipes
- `public.bet_tracker_clv` = 2 rows, CLV NULL

**Conclusion**: Structure CLV existe mais valeurs = 0 (pas de paris trackes)

### Phase 4: Mapping PSG/Inter

**PSG**:
- DB: `Paris Saint Germain`
- JSON: `Paris Saint-Germain`
- Mapping existe ligne 820: `"Paris Saint-Germain": "Paris Saint Germain"`

**Inter**:
- DB: `Inter`
- JSON: `Inter Milan`
- Mapping: **MANQUANT** - a ajouter ligne 822

## Fichiers touches

### Analyses (lecture seule)
- `/home/Mon_ps/quantum_core/data/orchestrator.py` (954 lignes)
- `/home/Mon_ps/quantum_core/adapters/data_hub_adapter.py` (645 lignes)
- `/home/Mon_ps/quantum_core/brain/unified_brain.py` (1,426 lignes)
- `/home/Mon_ps/quantum/orchestrator/quantum_orchestrator_v1.py` (2,243 lignes)
- `/home/Mon_ps/data/quantum_v2/team_dna_unified_v3.json`
- `quantum.team_quantum_dna_v3` (59 colonnes, 96 equipes)

### Aucun fichier modifie cette session

## Problemes resolus

### 1. HybridDNALoader redondant?
- **Probleme**: Session #83 a cree HybridDNALoader, est-il redondant avec DataOrchestrator?
- **Reponse**: PAS REDONDANT - DataOrchestrator charge les donnees mais les SCHEMAS sont INCOMPATIBLES
- **Realite**: Les dataclasses V1 ont des champs differents de V3 DB (0-40% compatibilite)

### 2. Ou est le CLV?
- **Probleme**: SentimentDNA vide, ou sont les donnees CLV?
- **Reponse**: Structure existe dans `market_dna.empirical_profile.avg_clv` mais valeur = 0
- **Cause**: Pas de paris trackes = pas de CLV calcule

### 3. Mapping Inter manquant
- **Probleme**: "Inter Milan" (JSON) ne matche pas "Inter" (DB)
- **Solution**: Ajouter `"Inter Milan": "Inter"` ligne 822 de orchestrator.py

## En cours / A faire

- [ ] **DECISION**: Adapter dataclasses V1 pour matcher V3, ou adapter V3 pour matcher V1?
- [ ] **ACTION**: Ajouter mapping `"Inter Milan": "Inter"` dans orchestrator.py:822
- [ ] **OPTIONNEL**: Creer convertisseur Dict→Dataclasses pour les champs compatibles
- [ ] **FUTUR**: Calculer CLV quand systeme de tracking paris sera actif

## Notes techniques

### Champs V1 vs V3 - Exemples concrets

**RosterDNA V1 attend:**
```python
mvp_dependency, bench_impact, keeper_status, squad_depth
```

**roster_dna V3 contient:**
```json
{"mvp": {"name": "...", "dependency_score": 11.4}, "top3_dependency": 32.0, "clinical_finishers": 5}
```
→ Champs COMPLETEMENT DIFFERENTS

**PhysicalDNA V1 attend:**
```python
pressing_decay, late_game_threat, intensity_60_plus, recovery_rate
```

**physical_dna V3 contient:**
```json
{"stamina_profile": "MEDIUM", "pressing_intensity": 6.6, "late_game_dominance": 47.0}
```
→ Champs avec noms differents mais concepts proches

### Sources donnees existantes

```
DataOrchestrator.get_team_dna() charge:
1. TSE (team_stats_extended) → corner_dna, card_dna
2. V3 (team_quantum_dna_v3) → 30+ JSONB DNA vectors
3. JSON (UnifiedLoader) → donnees granulaires
4. team_profiles (legacy fallback)
```

### Import fonctionnel
```python
from quantum_core.data.orchestrator import DataOrchestrator  # OK
orchestrator = DataOrchestrator()
dna = orchestrator.get_team_dna("Liverpool")  # Retourne Dict
```

## Resume

**Session #84** - Audit factuel du mapping DNA existant.

- Decouvert: Dataclasses V1 INCOMPATIBLES avec donnees V3 (0-40%)
- Decouvert: CLV existe dans structure mais valeur=0 (pas de tracking)
- Mapping PSG: OK, Mapping Inter: MANQUANT
- HybridDNALoader: PAS redondant car probleme = SCHEMA, pas chargement

**Status**: Audit termine, en attente decision Mya sur direction
**Grade**: Methodologie Hedge Fund (verifier AVANT d'affirmer)
