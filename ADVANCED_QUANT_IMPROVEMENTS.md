# 🎯 AMÉLIORATIONS QUANT AVANCÉES

## 📊 PARTIE 1: AMÉLIORER LA PRÉCISION DES STEAM MOVES (66.7% → 75%+)

### 1.1 Steam Velocity (Vitesse du mouvement)

**Concept:** Un mouvement de 5% en 1 heure est plus significatif qu'un mouvement de 5% sur 3 jours.
```python
def calculate_steam_velocity(snapshots):
    """
    Steam Velocity = Δ_prob / Δ_time (en heures)
    
    Seuils:
    - Velocity > 2%/heure = SHARP MONEY (très fiable, ~80% précision)
    - Velocity 0.5-2%/heure = NORMAL STEAM (~65% précision)
    - Velocity < 0.5%/heure = GRADUAL DRIFT (bruit, ~55% précision)
    """
    if len(snapshots) < 2:
        return 0
    
    first, last = snapshots[0], snapshots[-1]
    prob_change = abs((1/last['odds']) - (1/first['odds'])) * 100
    hours_elapsed = (last['timestamp'] - first['timestamp']).total_seconds() / 3600
    
    if hours_elapsed == 0:
        return float('inf')  # Mouvement instantané = très sharp
    
    return prob_change / hours_elapsed
```

### 1.2 Reverse Line Movement (RLM)

**Concept:** Quand le public mise massivement sur une équipe mais la ligne bouge CONTRE eux, c'est du sharp money.
```python
def detect_reverse_line_movement(public_pct, line_movement):
    """
    RLM = Public mise Home (>65%) MAIS odds Home montent
    
    Très puissant: ~75% précision quand détecté
    
    Nécessite: données de % de mises publiques (pas toujours dispo)
    Alternative: utiliser le volume relatif des bookmakers soft vs sharp
    """
    # Si >65% public sur Home mais Home odds augmentent
    if public_pct['home'] > 65 and line_movement['home'] > 0:
        return {'signal': 'AWAY', 'confidence': 'HIGH', 'type': 'RLM'}
    
    # Inverse pour Away
    if public_pct['away'] > 65 and line_movement['away'] > 0:
        return {'signal': 'HOME', 'confidence': 'HIGH', 'type': 'RLM'}
    
    return None
```

### 1.3 Multi-Book Convergence

**Concept:** Si TOUS les sharps (Pinnacle, Betfair, Asian books) bougent dans la même direction, c'est plus fiable.
```python
def check_multi_book_convergence(odds_data):
    """
    Convergence Score = nombre de books qui bougent dans la même direction
    
    - 5+ books convergent = HIGH CONFIDENCE (~80%)
    - 3-4 books convergent = MEDIUM CONFIDENCE (~70%)
    - <3 books = LOW CONFIDENCE (~55%)
    """
    sharp_books = ['pinnacle', 'betfair', 'sbobet', 'matchbook']
    
    directions = []
    for book in sharp_books:
        if book in odds_data:
            move = odds_data[book]['close'] - odds_data[book]['open']
            directions.append(1 if move > 0 else -1 if move < 0 else 0)
    
    # Tous dans la même direction?
    if len(set(directions)) == 1 and directions[0] != 0:
        return {'convergence': 'STRONG', 'direction': 'HOME' if directions[0] < 0 else 'AWAY'}
    
    return {'convergence': 'WEAK', 'direction': None}
```

### 1.4 Timing Analysis (Quand le steam arrive)

**Concept:** Steam moves à différents moments ont différentes significations.
```
┌──────────────────────────────────────────────────────────────────────────────┐
│  TIMING              │ SIGNIFICATION                    │ PRÉCISION         │
├──────────────────────┼──────────────────────────────────┼───────────────────┤
│  J-7 à J-3          │ Early sharp money (pros)         │ ~70%              │
│  J-3 à J-1          │ Informed bettors                 │ ~65%              │
│  J-1 à H-6          │ Late sharp + syndicate           │ ~75%              │
│  H-6 à H-1          │ CRITICAL ZONE (news, lineups)    │ ~80%              │
│  H-1 à kickoff      │ Steam + possible inside info     │ ~70% (volatile)   │
└──────────────────────┴──────────────────────────────────┴───────────────────┘
```
```python
def get_timing_weight(hours_before_match, prob_shift):
    """
    Pondère le steam selon le timing
    """
    if hours_before_match <= 6:
        return prob_shift * 1.3  # Boost les mouvements tardifs
    elif hours_before_match <= 24:
        return prob_shift * 1.1
    else:
        return prob_shift * 0.9  # Moins fiable si trop tôt
```

---

## 📊 PARTIE 2: AMÉLIORER LA SÉLECTION DES BETS

### 2.1 Poisson-xG Hybrid Model

**Concept:** Combiner la distribution de Poisson avec les xG pour prédire les scores.
```python
import numpy as np
from scipy.stats import poisson

def poisson_xg_probability(home_xg, away_xg, market='over_25'):
    """
    Utilise xG comme λ (lambda) de Poisson
    
    P(Over 2.5) = 1 - P(0-0) - P(1-0) - P(0-1) - P(1-1) - P(2-0) - P(0-2)
    """
    prob_matrix = np.zeros((8, 8))
    
    for h in range(8):
        for a in range(8):
            prob_matrix[h, a] = poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)
    
    if market == 'over_25':
        # P(total > 2.5)
        over_prob = 0
        for h in range(8):
            for a in range(8):
                if h + a >= 3:
                    over_prob += prob_matrix[h, a]
        return over_prob
    
    elif market == 'btts_yes':
        # P(home > 0 AND away > 0)
        btts_prob = 0
        for h in range(1, 8):
            for a in range(1, 8):
                btts_prob += prob_matrix[h, a]
        return btts_prob
    
    return 0.5
```

### 2.2 Kelly Criterion avec Incertitude

**Concept:** Ajuster Kelly pour l'incertitude du modèle.
```python
def fractional_kelly(prob, odds, uncertainty=0.1, fraction=0.25):
    """
    Kelly ajusté pour l'incertitude
    
    Kelly = (p * (odds-1) - (1-p)) / (odds-1)
    Mais avec incertitude: on réduit p de l'incertitude
    
    fraction = 0.25 (Quarter Kelly) pour protection
    """
    # Ajuster la probabilité pour l'incertitude
    adjusted_prob = prob * (1 - uncertainty)
    
    # Calcul Kelly
    edge = adjusted_prob * (odds - 1) - (1 - adjusted_prob)
    kelly = edge / (odds - 1) if odds > 1 else 0
    
    # Fractional Kelly
    final_kelly = max(0, kelly * fraction)
    
    return {
        'kelly_pct': final_kelly * 100,
        'edge': edge * 100,
        'recommended_stake': min(final_kelly, 0.05)  # Cap à 5%
    }
```

### 2.3 Expected Value avec Confidence Intervals

**Concept:** Ne pas juste calculer l'EV, mais aussi l'incertitude.
```python
import numpy as np

def calculate_ev_with_ci(prob, odds, n_simulations=10000, prob_std=0.05):
    """
    Monte Carlo pour EV avec intervalles de confiance
    
    prob_std = incertitude sur notre estimation de probabilité
    """
    # Simuler des probabilités avec incertitude
    simulated_probs = np.random.normal(prob, prob_std, n_simulations)
    simulated_probs = np.clip(simulated_probs, 0.01, 0.99)  # Borner
    
    # Calculer EV pour chaque simulation
    evs = simulated_probs * (odds - 1) - (1 - simulated_probs)
    
    return {
        'ev_mean': np.mean(evs) * 100,
        'ev_std': np.std(evs) * 100,
        'ev_p5': np.percentile(evs, 5) * 100,   # 5ème percentile
        'ev_p95': np.percentile(evs, 95) * 100,  # 95ème percentile
        'prob_positive_ev': (evs > 0).mean() * 100  # % de simulations avec EV+
    }
```

---

## 📊 PARTIE 3: MÉTRIQUES AVANCÉES

### 3.1 Bayesian Updating pour les équipes

**Concept:** Mettre à jour nos croyances sur une équipe après chaque match.
```python
def bayesian_update_team_strength(prior_mean, prior_std, observed_xg, n_matches):
    """
    Met à jour notre estimation de la force d'une équipe
    
    prior_mean = estimation actuelle de xG moyen
    prior_std = incertitude actuelle
    observed_xg = xG du dernier match
    
    Utilise la formule bayésienne pour combiner prior et likelihood
    """
    # Poids de l'observation vs prior (plus de matchs = plus de poids au prior)
    weight_prior = n_matches / (n_matches + 1)
    weight_obs = 1 / (n_matches + 1)
    
    # Posterior mean
    posterior_mean = weight_prior * prior_mean + weight_obs * observed_xg
    
    # Posterior std (diminue avec plus de données)
    posterior_std = prior_std * np.sqrt(weight_prior)
    
    return posterior_mean, posterior_std
```

### 3.2 Market Implied Probability vs Model Probability

**Concept:** Comparer notre estimation à celle du marché pour trouver de la value.
```python
def find_value(model_prob, market_odds, min_edge=0.03):
    """
    Trouve de la value en comparant modèle vs marché
    
    Value = Model_prob - Implied_prob
    
    Edge minimum = 3% pour compenser le vig et l'incertitude
    """
    # Probabilité implicite du marché
    implied_prob = 1 / market_odds
    
    # Edge
    edge = model_prob - implied_prob
    
    # Ratio model/market (>1 = value)
    value_ratio = model_prob / implied_prob
    
    return {
        'model_prob': model_prob,
        'implied_prob': implied_prob,
        'edge': edge,
        'value_ratio': value_ratio,
        'has_value': edge >= min_edge,
        'confidence': 'HIGH' if edge >= 0.08 else ('MEDIUM' if edge >= 0.05 else 'LOW')
    }
```

### 3.3 Correlation Matrix pour Multi-Bets

**Concept:** Comprendre les corrélations entre marchés pour optimiser les combos.
```
┌──────────────────────────────────────────────────────────────────────────────┐
│  CORRÉLATIONS TYPIQUES                                                       │
├──────────────────┬───────────┬──────────┬───────────┬───────────────────────┤
│                  │ Over 2.5  │ BTTS Yes │ Home Win  │ Interprétation        │
├──────────────────┼───────────┼──────────┼───────────┼───────────────────────┤
│ Over 2.5         │   1.00    │   0.72   │   0.15    │ O25 ↔ BTTS très liés  │
│ BTTS Yes         │   0.72    │   1.00   │   0.05    │ BTTS neutre vs 1X2    │
│ Home Win         │   0.15    │   0.05   │   1.00    │ 1X2 indépendant       │
│ Over 3.5         │   0.85    │   0.65   │   0.20    │ O35 ↔ O25 très liés   │
└──────────────────┴───────────┴──────────┴───────────┴───────────────────────┘

RÈGLE: Ne jamais combiner des marchés avec corrélation > 0.7
       (ex: Over 2.5 + BTTS = mauvais combo car très corrélés)
       
BON COMBO: Over 2.5 + Home Win (corr = 0.15)
MAUVAIS COMBO: Over 2.5 + BTTS Yes (corr = 0.72)
```

---

## 📊 PARTIE 4: ADVANCED FILTERS

### 4.1 Wisdom of Crowds Filter

**Concept:** Si tous les modèles (le nôtre, le marché, les tipsters) convergent, c'est plus fiable.
```python
def wisdom_of_crowds(our_prob, market_prob, consensus_prob):
    """
    Combine plusieurs sources avec pondération
    
    - Notre modèle: 40% (on lui fait confiance mais pas aveuglément)
    - Marché (Pinnacle): 40% (efficace mais pas parfait)
    - Consensus: 20% (agrégation d'autres sources)
    """
    weights = {'our': 0.4, 'market': 0.4, 'consensus': 0.2}
    
    combined_prob = (
        weights['our'] * our_prob +
        weights['market'] * market_prob +
        weights['consensus'] * consensus_prob
    )
    
    # Vérifier la convergence
    probs = [our_prob, market_prob, consensus_prob]
    std_dev = np.std(probs)
    
    return {
        'combined_prob': combined_prob,
        'convergence': 'HIGH' if std_dev < 0.05 else ('MEDIUM' if std_dev < 0.10 else 'LOW'),
        'std_dev': std_dev
    }
```

### 4.2 Régression to the Mean Filter

**Concept:** Les équipes en forme extrême (très bonne ou très mauvaise) vont régresser vers leur moyenne.
```python
def regression_to_mean_adjustment(recent_form, historical_mean, n_recent=5):
    """
    Ajuste les prédictions pour la régression vers la moyenne
    
    Si une équipe surperforme récemment, elle va probablement moins bien jouer
    Si une équipe sous-performe récemment, elle va probablement mieux jouer
    
    Formule: Adjusted = α * Recent + (1-α) * Historical
    où α diminue quand l'écart est grand (plus de régression attendue)
    """
    deviation = abs(recent_form - historical_mean)
    
    # Plus l'écart est grand, plus on régresse
    if deviation > 0.5:
        alpha = 0.4  # Fort régression
    elif deviation > 0.25:
        alpha = 0.6  # Régression modérée
    else:
        alpha = 0.8  # Faible régression
    
    adjusted = alpha * recent_form + (1 - alpha) * historical_mean
    
    return {
        'original': recent_form,
        'adjusted': adjusted,
        'regression_factor': 1 - alpha,
        'expected_direction': 'DOWN' if recent_form > historical_mean else 'UP'
    }
```

---

## 🎯 RÉSUMÉ: PRIORITÉS D'IMPLÉMENTATION

| Priorité | Amélioration | Impact Attendu | Complexité |
|----------|--------------|----------------|------------|
| 1 | Steam Velocity | +5% précision | Faible |
| 2 | Multi-Book Convergence | +3% précision | Moyenne |
| 3 | Poisson-xG Hybrid | +4% edge | Moyenne |
| 4 | Kelly avec Incertitude | -15% drawdown | Faible |
| 5 | Timing Analysis | +3% précision | Faible |
| 6 | Bayesian Team Strength | +2% edge | Élevée |

