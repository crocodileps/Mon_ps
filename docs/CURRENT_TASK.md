# TACHE EN COURS - MON_PS

**Derniere MAJ:** 2025-12-13 Session #07
**Statut:** ✅ BUG CORRIGE - Classification Tactique V25.1

## Contexte General
Projet Mon_PS: Systeme de betting football avec donnees multi-sources (FBRef, Understat, SofaScore).
Paradigme Chess Engine: ADN unique par equipe + Friction entre 2 ADN = marches exploitables.

## ✅ BUG CORRIGE - Session #07

### Corrections Appliquées (12 équipes EPL)

**GEGENPRESS (4):**
- Liverpool: TRANSITION → GEGENPRESS (PPDA=9.04)
- Chelsea: ADAPTIVE → GEGENPRESS (PPDA=9.41)
- Brighton: BALANCED → GEGENPRESS (PPDA=9.50)
- Tottenham: BALANCED → GEGENPRESS (PPDA=10.32)

**POSSESSION (2):**
- Arsenal: WIDE_ATTACK → POSSESSION (PPDA=10.40)
- Manchester City: WIDE_ATTACK → POSSESSION (PPDA=13.69)

**LOW_BLOCK (3):**
- West Ham: MID_BLOCK → LOW_BLOCK (PPDA=16.70)
- Crystal Palace: TRANSITION → LOW_BLOCK (PPDA=16.94)
- Everton: TRANSITION → LOW_BLOCK (PPDA=15.32)

**TRANSITION (3):**
- Aston Villa: BALANCED → TRANSITION (PPDA=12.47)
- Newcastle United: MID_BLOCK → TRANSITION (PPDA=11.18)
- Fulham: BALANCED → TRANSITION (PPDA=13.24)

### Validation Friction
- Liverpool vs Man City: PRESSING_BATTLE ✅
- Arsenal vs Chelsea: PRESSING_BATTLE ✅
- Liverpool vs West Ham: ABSORB_COUNTER ✅
- Man City vs Everton: SIEGE_WARFARE ✅

### Fichiers Créés
- `understat_ppda_by_team.json` - PPDA pour 96 équipes
- `tactical_classification_dataset.csv` - Dataset avec features
- `team_dna_unified_v2_backup_*.json` - Backup avant correction

---

## BUG INITIAL (Historique)

### Symptome
Liverpool classe comme **TRANSITION** au lieu de **GEGENPRESS/POSSESSION**

### Cause Racine
```
fbref_tactical_profiles.json
  └── defensive_style = "DEEP_BLOCK" ← FAUX!
        (calcule UNIQUEMENT sur tackle_def_pct > 45%)
        │
        ▼
transform_fbref_to_features() [test_96_teams.py:108]
  └── counter_attack_goals_pct = 35 ← HARDCODE!
        │
        ▼
RuleBasedClassifier → TRANSITION (67%) gagne
```

### Donnees Liverpool (preuve du bug)
| Metrique | Valeur | Interpretation |
|----------|--------|----------------|
| possession_pct | 61.1% | **PLUS ELEVE du Top 6** |
| pressing_intensity | HIGH | Pressing agressif |
| progressive_passes | 786 | **PLUS ELEVE du Top 6** |
| tackle_def_pct | 46% | Cause du bug (> 45% = DEEP_BLOCK) |

### Impact
- Liverpool classe TRANSITION au lieu de POSSESSION/GEGENPRESS
- Man City classe WIDE_ATTACK au lieu de POSSESSION
- GEGENPRESS = 0 equipes sur 96!
- Friction incorrecte: SPACE_EXPLOITATION au lieu de PRESSING_BATTLE

## Corrections A Faire

### Option 1: Correction Manuelle (5 min)
```json
// fbref_tactical_profiles.json
"Liverpool": {
  "defensive_style": "HIGH_LINE_PRESSING"  // pas DEEP_BLOCK
}

// team_dna_unified_v2.json
"Liverpool.tactical.defensive_style": "HIGH_LINE_PRESSING"
"Liverpool.fbref.defensive_style": "HIGH_LINE_PRESSING"
```

### Option 2: Correction Script (30 min)
Modifier `transform_fbref_to_features()` pour recalculer:
```python
if possession_pct >= 55 and pressing_intensity == "HIGH":
    defensive_style = "HIGH_LINE_PRESSING"
elif possession_pct >= 55:
    defensive_style = "HIGH_LINE"
elif tackle_def_pct >= 50 and possession_pct < 45:
    defensive_style = "DEEP_BLOCK"
else:
    defensive_style = "MID_BLOCK"
```

### Option 3: Ajuster PROFILE_RULES (15 min)
```python
TacticalProfile.POSSESSION: {
    'possession': ('>', 55),       # 58 → 55
    'pass_accuracy': ('>', 80),    # 85 → 80
}
```

## Architecture Systeme (Reference)

```
FLUX DE DONNEES:
┌─────────────────────────────────────────────────────────────────────────────┐
│  fbref_tactical_profiles.json → transform_fbref_to_features()              │
│       ↓                                  ↓                                  │
│  classification_results_v25.json → team_dna_unified_v2.json                │
│       ↓                                  ↓                                  │
│  match_analyzer_v2.py → friction_matrix_12x12.py                           │
└─────────────────────────────────────────────────────────────────────────────┘

COMPOSANTS:
├── rule_engine.py (quantum/services/)     # Betting orchestrator
├── rule_based.py (backend/chess_engine/)  # Tactical classifier
├── match_analyzer_v2.py (quantum/)        # Match analysis
└── friction_matrix_12x12.py (quantum/)    # 78 friction combinations
```

## Fichiers Cles

### Sources de Donnees (BUG)
- `/home/Mon_ps/data/quantum_v2/fbref_tactical_profiles.json` - SOURCE DU BUG
- `/home/Mon_ps/data/quantum_v2/team_dna_unified_v2.json` - PROPAGATION
- `/home/Mon_ps/data/quantum_v2/classification_results_v25.json` - RESULTAT

### Code (A MODIFIER)
- `/home/Mon_ps/backend/quantum/chess_engine_v25/test_96_teams.py` - transform_fbref_to_features()
- `/home/Mon_ps/backend/quantum/chess_engine_v25/learning/classifiers/rule_based.py` - PROFILE_RULES

### Code (OK)
- `/home/Mon_ps/quantum/analyzers/match_analyzer_v2.py` - Test OK
- `/home/Mon_ps/quantum/models/friction_matrix_12x12.py` - 78 combinaisons OK

## Commandes de Test

```bash
# Tester classification Liverpool
python3 -c "
from quantum.analyzers.match_analyzer_v2 import MatchAnalyzerV2
analyzer = MatchAnalyzerV2()
result = analyzer.analyze('Liverpool', 'Manchester City')
print(f'Liverpool: {result[\"profiles\"][\"home\"]}')
print(f'Man City: {result[\"profiles\"][\"away\"]}')
print(f'Friction: {result[\"friction\"][\"clash_type\"]}')
"

# Verifier donnees source
python3 -c "
import json
with open('/home/Mon_ps/data/quantum_v2/fbref_tactical_profiles.json') as f:
    fbref = json.load(f)
liv = [t for t in fbref if t.get('team') == 'Liverpool'][0]
print(f'defensive_style: {liv[\"defensive_style\"]}')
print(f'possession_pct: {liv[\"possession_pct\"]}')
print(f'pressing_intensity: {liv[\"pressing_intensity\"]}')
"
```

## Sessions Precedentes
- Session #05: Architecture DNA Profiler V2 (en attente)
- **Session #06**: Audit Classification Tactique V25 (BUG IDENTIFIE)

## Prochaines Etapes
1. [x] ~~Corriger defensive_style pour Liverpool/Man City~~ FAIT Session #07
2. [x] ~~Re-executer classification 96 equipes~~ FAIT (ML XGBoost V2.0)
3. [x] ~~Valider friction Liverpool vs Man City = PRESSING_BATTLE~~ FAIT
4. [ ] Corriger nom "Paris Saint Germain" (erreur de match)
5. [ ] Etendre ground truth ML (actuellement 39 equipes)
6. [ ] Integrer PPDA dans pipeline scraping automatique
7. [ ] Revenir a DNA Profiler V2 (Session #05)

## Session #07 - Fichiers Crees
- `understat_ppda_by_team.json` - PPDA 96 equipes
- `tactical_ml_dataset_v2.csv` - Dataset ML
- `tactical_classifier_v2_model.pkl` - Modele XGBoost
- `tactical_classification_ml_v2.json` - Resultats ML
