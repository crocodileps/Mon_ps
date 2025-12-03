# Tactical Matrix - Styles Guide

## 12 Styles Tactiques Disponibles

| Style | Description | Équipes Typiques |
|-------|-------------|------------------|
| **possession** | Contrôle du ballon, passes courtes | Man City, Barcelone |
| **pressing** | Pressing haut, récupération active | Liverpool (Klopp) |
| **balanced** | Approche équilibrée | Arsenal, Real Madrid |
| **defensive** | Bloc bas, solidité défensive | Atlético Madrid |
| **attacking** | Jeu offensif, risques assumés | Tottenham |
| **low_block_counter** | Bloc bas + contre-attaque | Inter Milan |
| **counter_attack** | Transitions rapides | Leicester 2016 |
| **gegenpressing** | Contre-pressing immédiat | Liverpool, Dortmund |
| **high_press** | Pressing ultra-haut | Man City, Bayern |
| **tiki_taka** | Passes courtes ultra-précises | Barcelone Pep |
| **park_the_bus** | Bloc ultra-défensif | Chelsea Mourinho |
| **direct_play** | Jeu direct, longs ballons | Burnley, Stoke |

## Matrice Complète

- **144 combinaisons** (12 × 12)
- Chaque matchup inclut:
  - win_rate_a, draw_rate, win_rate_b
  - btts_probability, over_25_probability
  - sample_size, confidence_level
  - notes explicatives

## Utilisation
```python
# Récupérer les stats d'un matchup
matchup = get_tactical_matchup("gegenpressing", "park_the_bus")
# → btts: 42%, over_25: 48%, gegenpressing win: 50%
```
