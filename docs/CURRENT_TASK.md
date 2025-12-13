# TACHE EN COURS - MON_PS

**Derniere MAJ:** 2025-12-13 Session #15
**Statut:** Audit Donnees Complet - Goalscorer Data DISPONIBLE

## Contexte General
Projet Mon_PS: Systeme de betting football avec donnees multi-sources (FBRef, Understat, SofaScore).
Paradigme Chess Engine: ADN unique par equipe + Friction entre 2 ADN = marches exploitables.

## Session #14 - UnifiedBrain V2.7 (93 Marches)

### Accomplissement Majeur
**UnifiedBrain V2.7: Extension de 85 a 93 marches (+8 nouveaux)**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    UnifiedBrain V2.7 (16 composants)                    │
│                              │                                          │
│                     DataHubAdapter (651L)                               │
│                              │                                          │
│    ┌─────────────────────────┼─────────────────────────────┐           │
│    │              8 ENGINES INTEGRES:                      │           │
│    │  matchup │ corner │ card │ coach │ referee           │           │
│    │  variance │ pattern │ chain                          │           │
│    └─────────────────────────┼─────────────────────────────┘           │
│                              ▼                                          │
│    ┌────────────┬────────────┬────────────┬────────────┐              │
│    │ Poisson    │ Derived    │ CorrectSc  │ HalfTime   │              │
│    │ O/U Goals  │ DC/DNB     │ 10 scores  │ HT 1X2     │              │
│    └────────────┴────────────┴────────────┴────────────┘              │
│    ┌────────────┬────────────┬────────────┬────────────┐              │
│    │ AsianHC    │ GoalRange  │ DoubleRes  │ WinToNil   │              │
│    │ 8 lines    │ 0-1,2-3... │ HT/FT 9    │ 4 WTN      │              │
│    └────────────┴────────────┴────────────┴────────────┘              │
│    ┌────────────┬────────────┬────────────┬────────────┐              │
│    │ OddEven    │ ExactGoals │ BttsBothH  │ ScoreBothH │ <- V2.6/2.7 │
│    │ 2 marches  │ 6 marches  │ 2 marches  │ 2 marches  │              │
│    └────────────┴────────────┴────────────┴────────────┘              │
│    ┌────────────┬────────────┐                                        │
│    │ CleanSheet │ ToScoreHf  │ <- V2.7 NEW                            │
│    │ 2 marches  │ 4 marches  │                                        │
│    └────────────┴────────────┘                                        │
│                              │                                          │
│                    BayesianFusion                                       │
│                    EdgeCalculator + LIQUIDITY_TAX                       │
│                    KellySizer                                           │
│                              ▼                                          │
│                    MatchPrediction (93 marches)                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 93 Marches Supportes
| Categorie | Count | Marches |
|-----------|-------|---------|
| 1X2 | 3 | home_win, draw, away_win |
| Double Chance | 3 | dc_1x, dc_x2, dc_12 |
| DNB | 2 | dnb_home, dnb_away |
| BTTS | 2 | btts_yes, btts_no |
| Goals Over | 6 | 0.5, 1.5, 2.5, 3.5, 4.5, 5.5 |
| Goals Under | 6 | 0.5, 1.5, 2.5, 3.5, 4.5, 5.5 |
| Corners | 6 | over/under 8.5, 9.5, 10.5 |
| Cards | 6 | over/under 2.5, 3.5, 4.5 |
| Correct Score | 10 | top 10 scores dynamiques |
| Half-Time | 6 | ht_1x2, ht_over_05, ht_btts |
| Asian Handicap | 8 | -0.5, -1.0, -1.5, -2.0 (H&A) |
| Goal Range | 4 | 0-1, 2-3, 4-5, 6+ |
| Double Result | 9 | 9 combinaisons HT/FT |
| Win to Nil | 4 | home/away WTN yes/no |
| Odd/Even | 2 | odd_goals, even_goals |
| Exact Goals | 6 | 0, 1, 2, 3, 4, 5+ |
| BTTS Both Halves | 2 | yes/no |
| Score Both Halves | 2 | yes/no |
| Clean Sheet | 2 | home/away CS yes |
| To Score in Half | 4 | home/away 1H/2H |
| **TOTAL** | **93** | |

### Commits Session #14
```
c139168 feat(brain): ScoreBothHalves + CleanSheet + ToScoreHalf - +8 marches (93 total)
```

### Test Results (Liverpool vs Man City)
```
Version: 2.7.0
Markets: 93

1. ScoreInBothHalvesCalculator:
   xG=2.5: YES=50.5% | NO=49.5%

2. CleanSheetCalculator:
   Home xG=1.5, Away xG=1.2:
   Home CS: 30.1%
   Away CS: 22.3%

3. ToScoreInHalfCalculator:
   Home 1H: 49.1% | 2H: 56.2%
   Away 1H: 41.7% | 2H: 48.3%
```

---

## Fichiers Session #14

### Crees
- `quantum_core/brain/score_both_halves.py`
- `quantum_core/brain/clean_sheet.py`
- `quantum_core/brain/to_score_half.py`

### Modifies
- `quantum_core/brain/models.py` (+8 MarketTypes, +8 fields, V2.7)
- `quantum_core/brain/__init__.py` (version 2.7.0, +3 exports)
- `quantum_core/brain/unified_brain.py` (+3 calculateurs, 93 marches)

---

## Audit Donnees pour Prochains Marches

### Team Totals - PRET POUR V2.8
- expected_home_goals: disponible via UnifiedBrain
- expected_away_goals: disponible via UnifiedBrain
- PoissonCalculator: deja implemente
- Marches possibles: Home/Away Over/Under 0.5, 1.5, 2.5 (+6 marches)

### First/Anytime Goalscorer - DONNEES COMPLETES (Session #15)
**Audit revele que les donnees existent deja!**

| Source | Fichier | Taille | Donnees |
|--------|---------|--------|---------|
| Understat | `all_shots_against_2025.json` | 11 MB | 1,869 buts avec minute exacte |
| Understat | `players_impact_dna.json` | - | 2,324 joueurs (xG agrege) |
| FBRef | `fbref_players_complete_2025_26.json` | 17 MB | 2,290 joueurs, 8 tables |

**Cles disponibles par but:**
- `minute`: timing exact -> is_first_goal, is_last_goal
- `xG`: expected goals du tir
- `situation`: OpenPlay, Penalty, SetPiece
- `shotType`: RightFoot, LeftFoot, Head
- `player_id`: pour jointure

**Top First Goalscorers (calcules):**
```
Erling Haaland: 8 premiers buts
Kylian Mbappe: 7 premiers buts
Lautaro Martinez: 5 premiers buts
```

**Prochaine etape:** Transformer all_shots_against en goalscorer_profiles_2025.json

---

## Usage UnifiedBrain V2.7

```python
from quantum_core.brain import get_unified_brain

brain = get_unified_brain()
prediction = brain.analyze_match("Liverpool", "Manchester City")

# 93 marches disponibles
print(f"Markets: {prediction.markets_count}")

# V2.7 NEW
print(f"Score Both Halves YES: {prediction.score_both_halves_yes_prob:.1%}")
print(f"Home Clean Sheet: {prediction.home_clean_sheet_yes_prob:.1%}")
print(f"Away Clean Sheet: {prediction.away_clean_sheet_yes_prob:.1%}")
print(f"Home to Score 1H: {prediction.home_to_score_1h_prob:.1%}")
print(f"Away to Score 2H: {prediction.away_to_score_2h_prob:.1%}")
```

---

## Evolution UnifiedBrain

| Version | Marches | Nouveautes |
|---------|---------|------------|
| V2.0 | 34 | Base + Poisson + DC/DNB |
| V2.1 | 44 | + CorrectScore (10) |
| V2.2 | 50 | + HalfTime (6) |
| V2.3 | 58 | + AsianHandicap (8) |
| V2.4 | 71 | + GoalRange (4) + DoubleResult (9) |
| V2.5 | 75 | + WinToNil (4) |
| V2.6 | 85 | + OddEven (2) + ExactGoals (6) + BttsBothHalves (2) |
| V2.7 | 93 | + ScoreBothHalves (2) + CleanSheet (2) + ToScoreHalf (4) |

---

## Prochaines Etapes

### Priorite Haute
1. [x] UnifiedBrain V2.7 - 93 marches
2. [ ] TeamTotalsCalculator V2.8 (+6 marches) -> 99 marches
3. [ ] Creer API FastAPI pour exposer UnifiedBrain
4. [ ] Backtest sur donnees historiques

### Priorite Moyenne
5. [ ] First/Anytime Goalscorer - **DONNEES PRETES** (transformer all_shots_against)
6. [ ] Marches Booking (cartons par joueur)
7. [ ] Tests de performance/benchmark

---

## Git Status
- Dernier commit: c139168 (V2.7 - 93 marches)
- Branche: main
- Pousse: Oui
