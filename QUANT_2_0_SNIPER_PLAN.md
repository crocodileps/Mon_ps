# 🎯 QUANT 2.0 SNIPER - PLAN D'INTÉGRATION

## SYNTHÈSE DE L'AUDIT SCIENTIFIQUE

### Données Totales: 2,817,115 points
### Données Exploitées par V10: ~5% (team_intel partiel, team_class partiel, odds_history)
### Données Ignorées: ~95%

---

## 🔴 PROBLÈMES IDENTIFIÉS

### 1. Incohérence Style Liverpool
```
team_intelligence.current_style = "balanced"
team_class.playing_style = "high_press"
```
→ Lequel utiliser? **Priorité team_intelligence** (plus récent, 2025-12-02)

### 2. Données xG Manquantes
```
xg_for_avg: 0% rempli
xg_against_avg: 0% rempli
```
→ Fallback sur home_goals_scored_avg (déjà implémenté)

### 3. H2H Faible Sample
```
706 paires: 1 match seulement
65 paires: 2 matchs
1 paire: 3 matchs
```
→ Pondérer par total_matches (ignorer si < 2)

---

## ✅ DONNÉES 100% EXPLOITABLES (Quick Wins)

### PRIORITÉ 1A: team_intelligence (100% rempli)
| Colonne | Utilisation |
|---------|-------------|
| current_style | Matcher avec tactical_matrix |
| current_pressing | Ajuster xG (high_press = +0.15) |
| current_form | Ajuster confiance |
| vs_top_teams (jsonb) | Si adversaire = top tier |
| vs_bottom_teams (jsonb) | Si adversaire = bottom tier |
| after_europe (jsonb) | Si match après Europe |

### PRIORITÉ 1B: team_class (100% rempli)
| Colonne | Utilisation |
|---------|-------------|
| home_fortress_factor | Multiplier home_xg |
| away_weakness_factor | Multiplier away_xg |
| psychological_edge | Ajuster confiance |
| playing_style | Backup pour tactical_matrix |
| calculated_power_index | Comparer équipes |
| star_players (jsonb) | Vérifier absences |

### PRIORITÉ 1C: tactical_matrix (100% rempli)
| Matchup | BTTS | Over25 | Goals |
|---------|------|--------|-------|
| gegenpressing vs attacking | 95.0% | 96.2% | 3.53 |
| attacking vs gegenpressing | 90.2% | 70.6% | 3.50 |
| high_press vs attacking | 81.4% | 82.8% | 4.22 |
| park_the_bus vs high_press | 28.0% | - | 1.91 |

**IMPACT**: +15-20 pts Score

---

## ⚠️ DONNÉES PARTIELLEMENT EXPLOITABLES

### PRIORITÉ 2A: head_to_head
- **Condition**: Utiliser SEULEMENT si total_matches >= 2
- **Colonnes**: dominance_factor, over_25_percentage, btts_percentage

### PRIORITÉ 2B: scorer_intelligence
- **Disponible**: goals_per_90 (100%), is_hot_streak (100%), is_injured (100%)
- **Manquant**: anytime_scorer_prob (0%)
- **Utilisation**: Vérifier top buteurs présents/absents

### PRIORITÉ 2C: coach_intelligence
- **Disponible**: career_win_rate (100%), tactical_style (100%), over25_rate (93%)
- **Manquant**: formation_primary (0%)

### PRIORITÉ 2D: referee_intelligence
- **Range Goals/Match**: 2.35 → 3.35 (différence de 1 but!)
- **Condition**: Si arbitre connu dans match_data
- **Impact**: Ajuster Over/Under probas

---

## 🏗️ ARCHITECTURE QUANT 2.0 SNIPER
```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR V11 QUANT 2.0                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ DATA LAYER   │  │ ANALYSIS     │  │ DECISION     │          │
│  │              │  │ LAYER        │  │ LAYER        │          │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤          │
│  │ team_intel   │→ │ Monte Carlo  │→ │ Score Multi  │          │
│  │ team_class   │→ │ xG Engine    │→ │ Layer        │          │
│  │ tactical_mx  │→ │ Style Match  │→ │ Kelly Calc   │          │
│  │ h2h          │→ │ H2H Analysis │→ │ Steam Valid  │          │
│  │ scorers      │→ │ Scorer Check │→ │ Trap Filter  │          │
│  │ coaches      │→ │ Coach Style  │→ │ Final Pick   │          │
│  │ referees     │→ │ Referee Adj  │→ │              │          │
│  │ odds_history │→ │ Steam Detect │→ │              │          │
│  │ market_traps │→ │ Trap Detect  │→ │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 LAYERS À IMPLÉMENTER

### LAYER 1: TACTICAL_STYLE_LAYER (+15 pts)
```python
def analyze_tactical_matchup(home_style, away_style):
    """
    Requête: tactical_matrix WHERE style_a = home_style AND style_b = away_style
    Retourne: btts_probability, over_25_probability, avg_goals_total
    """
```

### LAYER 2: TEAM_CLASS_EXTENDED_LAYER (+8 pts)
```python
def apply_class_factors(home_class, away_class):
    """
    Utilise: home_fortress_factor, away_weakness_factor, psychological_edge
    Multiplie xG par ces facteurs
    """
```

### LAYER 3: H2H_LAYER (+5-10 pts)
```python
def analyze_h2h(team_a, team_b):
    """
    Requête: head_to_head WHERE (team_a, team_b) OR (team_b, team_a)
    Condition: total_matches >= 2
    Retourne: dominance_factor, over_25_percentage, btts_percentage
    """
```

### LAYER 4: SCORER_LAYER (+5 pts)
```python
def check_scorers(team):
    """
    Requête: scorer_intelligence WHERE current_team = team
    Vérifie: is_injured, is_hot_streak, goals_per_90
    """
```

### LAYER 5: COACH_LAYER (+3-5 pts)
```python
def analyze_coach(team):
    """
    Requête: coach_intelligence WHERE current_team = team
    Retourne: tactical_style, over25_rate, btts_rate
    """
```

### LAYER 6: REFEREE_LAYER (+2-4 pts)
```python
def analyze_referee(referee_name):
    """
    Requête: referee_intelligence WHERE referee_name = name
    Retourne: avg_goals_per_game, home_bias_factor
    """
```

---

## 🎯 SCORE FINAL ESTIMÉ

| Composant | Score Actuel | Score V2.0 |
|-----------|--------------|------------|
| Monte Carlo | 10 pts | 10 pts |
| Tier Adjustment | 5 pts | 8 pts |
| Momentum | 3 pts | 5 pts |
| Steam Detection | 3 pts | 5 pts |
| **Tactical Matrix** | 0 pts | **15 pts** |
| **Team Class Extended** | 0 pts | **8 pts** |
| **H2H** | 0 pts | **5 pts** |
| **Scorers** | 0 pts | **5 pts** |
| **Coach** | 0 pts | **3 pts** |
| **Referee** | 0 pts | **2 pts** |
| **TOTAL** | **21 pts** | **66 pts** |

---

## 🚀 ÉTAPES D'IMPLÉMENTATION

### Phase 1: Quick Wins (2h)
1. Intégrer team_class extended (home_fortress, psychological_edge)
2. Intégrer current_style depuis team_intelligence

### Phase 2: Tactical Matrix (3h)
1. Créer TacticalMatchupEngine
2. Matcher home_style vs away_style
3. Ajuster probas BTTS/Over25

### Phase 3: H2H (2h)
1. Créer H2HEngine
2. Requête avec pondération sample_size

### Phase 4: Scorers/Coach/Referee (3h)
1. Créer ScorerCheckEngine
2. Créer CoachStyleEngine
3. Créer RefereeAdjustmentEngine

### Phase 5: Intégration Finale (2h)
1. Combiner tous les layers
2. Pondérer les scores
3. Tests complets

**TEMPS TOTAL ESTIMÉ: 12h**
