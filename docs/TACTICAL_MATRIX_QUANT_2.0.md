# Tactical Matrix - QUANT 2.0

## 🎯 Évolution Statisticien Amateur → Quant Professionnel

### Amélioration des Erreurs (MAE)

| Métrique | v4.7.0 (Amateur) | v4.8.0 (Quant 2.0) | Amélioration |
|----------|------------------|---------------------|--------------|
| Goals | 0.563 | **0.220** | **-61%** |
| Home Win | 24.21% | **9.74%** | **-60%** |
| Over 2.5 | 17.53% | **6.70%** | **-62%** |
| BTTS | 18.39% | **7.37%** | **-60%** |

## 📊 Méthodologie Bayesian Blend

### Pondération par Sample Size

| Sample Size | Données Réelles | Prior Théorique | Confidence |
|-------------|-----------------|-----------------|------------|
| n ≥ 30 | 100% | 0% | high |
| n ≥ 10 | 70% | 30% | medium |
| n ≥ 5 | 50% | 50% | low |
| n < 5 | 30% | 70% | very_low |

## 📈 Intervalles de Confiance Wilson (95%)

Formule: `p ± 1.96 * sqrt(p * (1-p) / n)`

### Exemple Lecture
```
pressing vs pressing (n=93, quality=1.00)
├── Home Win: 48.39% [38.23% - 58.55%]
├── Draw: 22.58%
├── Away Win: 29.03%
├── Goals: 2.73
├── Over 2.5: 59.14% [49.15% - 69.13%]
└── BTTS: 52.69% [42.54% - 62.84%]
```

## 🔄 Recalibration Automatique

- **Fréquence**: Quotidienne à 06:00 UTC
- **Script**: `scripts/cron/recalibrate_tactical_matrix.sh`
- **Process**:
  1. Recalcul stats depuis match_results
  2. Application blend Bayesian
  3. Mise à jour intervalles de confiance
  4. Logging résultats

## 📋 Structure Table (26 colonnes)

### Colonnes Core
- `style_a`, `style_b`: Styles tactiques
- `win_rate_a`, `draw_rate`, `win_rate_b`: Probabilités 1X2
- `avg_goals_total`: Moyenne buts
- `btts_probability`, `over_25_probability`: Marchés

### Colonnes Quant 2.0
- `win_rate_a_ci_lower/upper`: IC 95% Home Win
- `over25_ci_lower/upper`: IC 95% Over 2.5
- `btts_ci_lower/upper`: IC 95% BTTS
- `data_quality_score`: Score qualité (0-1)
- `sample_size`: Nombre matchs observés
- `confidence_level`: high/medium/low/very_low
- `last_calibration`: Dernière mise à jour
- `calibration_method`: bayesian_blend

## 🎯 Utilisation API
```python
# Récupérer prédiction avec IC
def get_tactical_prediction(home_style, away_style):
    query = """
    SELECT 
        win_rate_a, win_rate_a_ci_lower, win_rate_a_ci_upper,
        over_25_probability, over25_ci_lower, over25_ci_upper,
        data_quality_score, confidence_level
    FROM tactical_matrix
    WHERE style_a = %s AND style_b = %s
    """
    return db.execute(query, (home_style, away_style))
```
