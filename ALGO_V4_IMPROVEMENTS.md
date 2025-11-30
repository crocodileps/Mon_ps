# 🧠 ALGO V4 - DATA-DRIVEN BETTING

## 📊 PROBLÈMES IDENTIFIÉS (29/11/2025)

### ❌ ERREURS CRITIQUES DE L'ALGO ACTUEL

| Problème | Impact | Preuve |
|----------|--------|--------|
| DC_12 surpondéré | -5.64 units | Historique 82 paris |
| DC_1X ignoré | +17.46 units perdus | Win rate 86.4% |
| BTTS_YES mal calibré | -10.11 units | Cotes trop basses prises |
| Données team_intelligence non utilisées | Picks sans contexte | 675 équipes ignorées |
| Buteurs non intégrés | BTTS imprécis | 499 buteurs ignorés |

### ✅ MARCHÉS RENTABLES (Historique)

| Marché | Paris | Win Rate | Profit |
|--------|-------|----------|--------|
| DC_1X | 88 | 86.4% | +17.46 |
| BTTS_NO | 79 | 49.4% | +20.15 |
| HOME | 89 | 58.4% | +10.78 |
| OVER_25 | 69 | 62.3% | +4.65 |

### ❌ MARCHÉS À ÉVITER

| Marché | Paris | Win Rate | Profit |
|--------|-------|----------|--------|
| DC_12 | 82 | 74.4% | -5.64 |
| BTTS_YES | 74 | 54.1% | -10.11 |
| OVER_35 | 31 | 29.0% | -8.59 |
| AWAY | 95 | 15.8% | -53.93 |

---

## 🎯 NOUVELLES RÈGLES ALGO V4

### RÈGLE 1: Remplacer DC_12 par DC_1X
```python
if market == "dc_12" and home_draw_rate > 20:
    market = "dc_1x"  # Plus safe, meilleur profit
```

### RÈGLE 2: BTTS basé sur team_intelligence
```python
btts_probability = (home_btts_rate + away_btts_rate) / 2
if btts_probability > 55 and odds >= 1.70:
    recommend = "STRONG_BET"
elif btts_probability > 50 and odds >= 1.90:
    recommend = "VALUE_BET"
```

### RÈGLE 3: Intégrer les buteurs
```python
home_scorers = get_scorers(home_team)
away_scorers = get_scorers(away_team)
if any(s.goals_per_match > 0.5 for s in home_scorers + away_scorers):
    btts_boost = 1.15  # +15% confiance BTTS
```

### RÈGLE 4: Validation historique obligatoire
```python
market_history = get_market_performance(market_type)
if market_history.profit_units < 0:
    recommendation = "AVOID"
    reason = f"Historique négatif: {market_history.profit_units} units"
```

### RÈGLE 5: Pattern matching
```python
patterns = get_profitable_patterns(league, day_of_week)
for pattern in patterns:
    if pattern.roi > 20 and pattern.recommendation == "STRONG_BET":
        boost_score(pattern.market_type, 1.2)
```

---

## 📁 FICHIERS À CRÉER/MODIFIER

1. `backend/api/services/algo_v4_service.py` - Nouveau service
2. `backend/api/routes/algo_v4_routes.py` - Nouveaux endpoints
3. Modifier `pro_score_v3_service.py` - Intégrer validations

