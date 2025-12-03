# Niveau 1 Avancé - Nettoyage et Enrichissement des Données

## Corrections Effectuées

### 1. team_class.league

| Problème | Avant | Après |
|----------|-------|-------|
| Équipes en "Champions League" | 24 | 0 |
| Équipes sans ligue | 32 | 0 |
| Doublons incohérents | 7 paires | 0 |
| Ligues distinctes | 8 | 30 |

### 2. Harmonisation des Doublons

| Équipe | Style harmonisé | Source |
|--------|-----------------|--------|
| Liverpool / Liverpool FC | high_press | coach: Arne Slot |
| Real Madrid / Real Madrid CF | high_press | coach: Ancelotti |
| PSG / Paris Saint-Germain FC | high_press | coach: Luis Enrique |
| Napoli / SSC Napoli | low_block_counter | coach: Conte |
| Juventus / Juventus FC | low_block_counter | coach: Motta |
| Arsenal / Arsenal FC | high_press | coach: Arteta |
| Chelsea / Chelsea FC | attacking | coach: Maresca |

### 3. League Modifiers

Table `league_modifiers` avec coefficients multiplicatifs par ligue.

| Ligue | Goals Mod | HW Mod | O25 Mod | Home Adv |
|-------|-----------|--------|---------|----------|
| Bundesliga | 1.164 | 0.965 | 1.186 | +0.33 |
| Premier League | 1.020 | 1.138 | 1.077 | +0.48 |
| Ligue 1 | 1.032 | 1.066 | 1.002 | +0.60 |
| La Liga | 0.952 | 1.053 | 0.887 | +0.48 |
| Serie A | 0.846 | 0.864 | 0.823 | +0.16 |

**Usage:**
```sql
prediction_ajustée = prediction_base × league_modifier
```

## Résultat

- 231 équipes avec données propres
- 90 combinaisons tactiques observées
- 807 matchs pour calibration
- 6 ligues principales avec modifiers
