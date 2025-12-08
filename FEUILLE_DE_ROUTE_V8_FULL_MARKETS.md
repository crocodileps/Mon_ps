# 🎯 FEUILLE DE ROUTE V8 - FULL MARKETS DATA

## 📊 ÉTAT ACTUEL (Audit 8 Décembre 2025)

### Données Disponibles
| Donnée | Table | Volume | Marchés Possibles |
|--------|-------|--------|-------------------|
| Score final | match_results | 901 | 1X2, Over/Under, BTTS |
| Tirs/SOT | match_advanced_stats | 763 | Shots over/under |
| xG | match_xg_stats | ? | xG-based markets |
| Big chances | match_advanced_stats | 763 | Conversion markets |

### Données MANQUANTES (Priorité Haute)
| Donnée | Impact | Source |
|--------|--------|--------|
| ❌ Score mi-temps | 12 marchés (HT 1X2, HT Over, 2H markets) | API-Football |
| ❌ Corners par match | 10 marchés (Corners over/under) | API-Football |
| ❌ Cartons par match | 8 marchés (Cards over/under) | API-Football |
| ❌ Events/Buteurs | Marchés buteurs | API-Football (VIDE!) |

---

## 🚀 PHASE 1: ENRICHISSEMENT SCORES MI-TEMPS

### Objectif
Ajouter `score_home_ht`, `score_away_ht` à tous les matchs

### Marchés Débloqués (12)
- `ht_home`, `ht_draw`, `ht_away` (1ère mi-temps 1X2)
- `ht_over_05`, `ht_over_15` (1ère mi-temps over)
- `2h_home`, `2h_draw`, `2h_away` (2ème mi-temps 1X2)
- `2h_over_05`, `2h_over_15` (2ème mi-temps over)
- `ht_ft_xx` (combos mi-temps/final)

### Action
```sql
ALTER TABLE match_results ADD COLUMN IF NOT EXISTS score_home_ht INTEGER;
ALTER TABLE match_results ADD COLUMN IF NOT EXISTS score_away_ht INTEGER;
```

---

## 🚀 PHASE 2: ENRICHISSEMENT STATS MATCH

### Objectif
Créer table `quantum.match_full_stats` avec TOUTES les stats

### Colonnes Requises
- `fixture_id`, `match_date`, `home_team`, `away_team`
- `home_corners`, `away_corners`, `total_corners`
- `home_yellow`, `away_yellow`, `home_red`, `away_red`
- `home_fouls`, `away_fouls`
- `home_possession`, `away_possession`
- `home_offsides`, `away_offsides`

### Marchés Débloqués (18)
- Corners: `corners_over_8`, `corners_over_10`, `corners_over_12`
- Cartons: `cards_over_3`, `cards_over_4`, `cards_over_5`
- Par équipe: `home_corners_over_4`, `away_corners_over_4`

---

## 🚀 PHASE 3: BUTEURS (match_events)

### Objectif
Remplir table `match_events` avec tous les buts

### Données Requises
- `fixture_id`, `player_id`, `player_name`, `team`
- `minute`, `event_type` (Goal, Card, Subst)
- `is_first_goal`, `is_penalty`

### Marchés Débloqués
- Anytime goalscorer par joueur
- First goalscorer
- Player to score 2+

---

## 🚀 PHASE 4: HANDICAPS (Calculés)

### Objectif
Calculer résultats handicaps depuis scores existants

### Marchés Débloqués (16)
- `ah_home_-2`, `ah_home_-1.5`, `ah_home_-1`, `ah_home_-0.5`
- `ah_home_+0.5`, `ah_home_+1`, `ah_home_+1.5`, `ah_home_+2`
- Idem pour away

---

## 📅 PLANNING

| Phase | Durée | Priorité |
|-------|-------|----------|
| Phase 1: Mi-temps | 2 jours | 🔴 CRITIQUE |
| Phase 2: Corners/Cards | 3 jours | 🔴 CRITIQUE |
| Phase 3: Buteurs | 2 jours | 🟡 HAUTE |
| Phase 4: Handicaps | 1 jour | 🟢 MOYENNE |

---

## 🎯 RÉSULTAT ATTENDU

| Avant V8 | Après V8 |
|----------|----------|
| 16 marchés | ~90 marchés |
| Pépites limitées | Pépites sur tous marchés |
| Smart Menu basique | Smart Menu 3 options |

