# AUDIT DONNÉES JOUEURS - 2025-12-12

## RÉSUMÉ EXÉCUTIF

**BONNE NOUVELLE:** La majorité des données "manquantes" EXISTENT DÉJÀ sur le serveur !

- **Timing par buteur:** `scorer_profiles_2025.json` (goals_1H, goals_2H, by_period)
- **Zones de tir:** `all_shots_against_2025.json` (X, Y coordinates, 11MB de données brutes)
- **Matchup friction:** `defender_dna_quant_v9.json` (vs_SPEED_DEMON, vs_AERIAL_THREAT, etc.)
- **Home/Away splits:** `defender_dna_quant_v9.json` → `quant_v9.stadium`

---

## FICHIERS TROUVÉS

| Fichier | Taille | Joueurs/Éléments | Dernière modif |
|---------|--------|------------------|----------------|
| `defender_dna_quant_v9.json` | 20M | 664 défenseurs | 10 Dec |
| `goalkeeper_dna_v4_4_final.json` | 718K | 96 gardiens | 10 Dec |
| `all_shots_against_2025.json` | 11M | ~50,000 tirs | 12 Dec |
| `scorer_profiles_2025.json` | 76K | 238 buteurs | 10 Dec |
| `attacker_dna_v2.json` | 524K | 1,199 attaquants | 11 Dec |
| `attacker_styles_v1.json` | 1.3M | 1,980 attaquants | 11 Dec |
| `players_impact_dna.json` | 775K | 2,324 joueurs | 12 Dec |
| `player_dna_unified.json` | 29M | 2,377 joueurs | 12 Dec |
| `fbref_raw_2025_26.json` | - | 5 ligues (équipes) | - |

---

## DÉFENSEURS (664 joueurs)

### Source: `defender_dna_quant_v9.json`

| Champ recherché | TROUVÉ | Fichier source | Nom du champ |
|-----------------|--------|----------------|--------------|
| strengths | ✅ OUI | defender_dna | `dna.strengths[]` |
| weaknesses | ✅ OUI | defender_dna | `dna.weaknesses[]` |
| home_performance | ✅ OUI | defender_dna | `quant_v9.stadium.home_performance` |
| away_performance | ✅ OUI | defender_dna | `quant_v9.stadium.away_performance` |
| vs_pace/speed | ✅ OUI | defender_dna | `quant_v8.matchup_friction.SPEED_DEMON` |
| vs_aerial | ✅ OUI | defender_dna | `quant_v8.matchup_friction.AERIAL_THREAT` |
| vs_technical | ✅ OUI | defender_dna | `quant_v8.matchup_friction.TECHNICAL_WIZARD` |
| vs_clinical | ✅ OUI | defender_dna | `quant_v8.matchup_friction.CLINICAL_FINISHER` |
| vs_pressing | ✅ OUI | defender_dna | `quant_v8.matchup_friction.PRESSING_MONSTER` |
| fouls/cards | ✅ OUI | defender_dna | `quant_v8.xCards`, `yellow_cards`, `red_cards`, `cards_90` |
| gamestate | ✅ OUI | defender_dna | `quant_v7.gamestate_analysis.states` |
| formation | ✅ OUI | defender_dna | `quant_v7.formation_analysis` |
| speed_vulnerability | ✅ OUI | defender_dna | `quant_v7.speed_vulnerability.speeds` |
| zone_vulnerability | ✅ OUI | defender_dna | `quant_v7.zone_vulnerability` |
| paire_synergy | ✅ OUI | defender_dna | `quant_v8.paire_synergy.pairs[]` |
| clutch | ✅ OUI | defender_dna | `quant_v8.clutch` |
| volatility | ✅ OUI | defender_dna | `quant_v8.volatility` |
| regression | ✅ OUI | defender_dna | `quant_v8.regression` |
| fatigue | ✅ OUI | defender_dna | `quant_v8.fatigue` |
| referee_interaction | ✅ OUI | defender_dna | `quant_v9.referee` |
| weather_impact | ✅ OUI | defender_dna | `quant_v9.weather_congestion` |
| age_curve | ✅ OUI | defender_dna | `quant_v9.age_curve` |
| intl_duty_impact | ✅ OUI | defender_dna | `quant_v9.intl_duty` |
| leadership | ✅ OUI | defender_dna | `quant_v9.leadership` |
| tilt_risk | ✅ OUI | defender_dna | `quant_v9.tilt` |
| alpha_beta | ✅ OUI | defender_dna | `quant_v9.alpha_beta` |
| sharpe_ratio | ✅ OUI | defender_dna | `quant_v9.sharpe` |
| kelly_stake | ✅ OUI | defender_dna | `quant_v9.kelly` |

**VERDICT DÉFENSEURS: 100% des données recherchées EXISTENT**

---

## ATTAQUANTS (1,199 - 1,980 joueurs)

### Sources multiples

| Champ recherché | TROUVÉ | Fichier source | Nom du champ |
|-----------------|--------|----------------|--------------|
| goals_by_period | ✅ OUI | scorer_profiles | `goals_1H`, `goals_2H`, `avg_minute` |
| first_scorer | ✅ OUI | scorer_profiles | `first_goals` |
| shot_zones | ✅ OUI | all_shots_against | `X`, `Y` coordinates |
| header_vs_foot | ✅ OUI | scorer_profiles | `by_shot_type.Head/RightFoot/LeftFoot` |
| by_situation | ✅ OUI | scorer_profiles | `by_situation.OpenPlay/FromCorner/Penalty` |
| xG/xA | ✅ OUI | attacker_dna | `xG`, `xA`, `xG_per_90`, `xA_per_90` |
| xG_diff | ✅ OUI | attacker_dna | `xG_diff` |
| threat_score | ✅ OUI | attacker_dna | `threat_score`, `tier` |
| style | ✅ OUI | attacker_styles | `primary_style`, `secondary_styles` |
| conversion | ✅ OUI | attacker_styles | `metrics.conversion` |
| shots_90 | ✅ OUI | attacker_styles | `metrics.shots_90` |
| home_goal_ratio | ✅ OUI | attacker_styles | `home_goal_ratio` |
| xGChain | ✅ OUI | players_impact | `xGChain`, `xGBuildup` |
| vs_top_teams | ❌ NON | - | À enrichir |
| vs_bottom_teams | ❌ NON | - | À enrichir |
| cards_attacker | ❌ NON | - | Pas dans attacker_dna |

**DONNÉES BRUTES DISPONIBLES:**
- `all_shots_against_2025.json` (11MB) contient TOUS les tirs avec:
  - `minute` exacte
  - `X`, `Y` position (zones)
  - `shotType` (RightFoot, LeftFoot, Head)
  - `situation` (OpenPlay, FromCorner, SetPiece)
  - `player`, `player_id`
  - `lastAction` (Cross, Pass, etc.)
  - `xG` par tir

**VERDICT ATTAQUANTS: 90% des données existent, 10% à enrichir/calculer**

---

## MILIEUX (2,324 joueurs)

### Source: `players_impact_dna.json`

| Champ recherché | TROUVÉ | Fichier source | Nom du champ |
|-----------------|--------|----------------|--------------|
| key_passes | ✅ OUI | players_impact | `key_passes` |
| xA | ✅ OUI | players_impact | `xA`, `xA/90` calculable |
| xGChain | ✅ OUI | players_impact | `xGChain` |
| xGBuildup | ✅ OUI | players_impact | `xGBuildup` |
| shots | ✅ OUI | players_impact | `shots` |
| goals | ✅ OUI | players_impact | `goals` |
| assists | ✅ OUI | players_impact | `assists` |
| through_balls | ❌ NON | - | Pas disponible |
| progressive_carries | ❌ NON | - | Pas disponible |
| tackles | ❌ NON | - | Pas disponible |
| interceptions | ❌ NON | - | Pas disponible |
| ball_recoveries | ❌ NON | - | Pas disponible |
| fouls_committed | ❌ NON | - | Pas disponible |
| cards_history | ❌ NON | - | Pas disponible |
| corner_taker | ❌ NON | - | Pas disponible |
| fk_taker | ❌ NON | - | Pas disponible |

**VERDICT MILIEUX: 50% des données existent, manque données défensives et discipline**

---

## GARDIENS (96 joueurs) - RÉFÉRENCE DE QUALITÉ

### Source: `goalkeeper_dna_v4_4_final.json`

| Champ | STRUCTURE |
|-------|-----------|
| `difficulty_analysis` | easy/medium/hard/very_hard avec sr, vs_expected, sample, confidence |
| `situation_analysis` | open_play, corners, set_pieces, penalties |
| `timing_analysis` | 0-15, 16-30, 31-45, 46-60, 61-75, 76-90, 90+ |
| `shot_type_analysis` | RightFoot, LeftFoot, Head |
| `strengths` | Liste de forces |
| `weaknesses` | Liste de faiblesses |
| `exploits` | Liste de marchés exploitables avec edge et confidence |
| `fingerprint` | Signature unique |
| `raw` | Données brutes (shots, saves, goals par catégorie) |

**VERDICT GARDIENS: 100% complet - Modèle à suivre**

---

## DONNÉES VRAIMENT MANQUANTES

### À SCRAPER (priorité)

| Donnée | Position | Source recommandée | Priorité |
|--------|----------|-------------------|----------|
| tackles, interceptions | MID | FBRef Player Stats | HIGH |
| progressive_carries | MID | FBRef Player Stats | HIGH |
| fouls_committed | MID/ATT | FBRef Misc Stats | HIGH |
| cards_attacker | ATT | FBRef Misc Stats | MEDIUM |
| corner_taker, fk_taker | MID/ATT | WhoScored | LOW |
| vs_top_teams | ATT | Understat filtré | MEDIUM |
| vs_bottom_teams | ATT | Understat filtré | MEDIUM |

### À CALCULER (depuis données existantes)

| Donnée | Source | Calcul |
|--------|--------|--------|
| timing_goals par attaquant | all_shots_against | Grouper par player + minute |
| shot_zones par attaquant | all_shots_against | Grouper par player + X,Y |
| header_ratio | all_shots_against | Filtrer shotType=Head |
| conversion_by_situation | all_shots_against | Filtrer par situation |

---

## RECOMMANDATIONS

### PRIORITÉ 1: EXPLOITER LES DONNÉES EXISTANTES

1. **Enrichir attaquants** depuis `all_shots_against_2025.json`:
   - Calculer timing_profile par joueur (comme gardiens)
   - Calculer zone_profile par joueur
   - Calculer shot_type_profile par joueur

2. **Enrichir milieux** depuis `defender_dna_quant_v9.json`:
   - Les milieux défensifs (M S, D M S) ont déjà des données !
   - Vérifier couverture dans defender_dna

### PRIORITÉ 2: SCRAPER LE MINIMUM

1. **FBRef Player Stats** (1 page par ligue, 5 ligues):
   - tackles, interceptions, ball_recoveries
   - fouls, cards
   - progressive_carries
   - Temps estimé: 30min

2. **Understat filtré** (optionnel):
   - vs_top_teams, vs_bottom_teams
   - Temps estimé: 1h

### NE PAS SCRAPER

- **Timing attaquants** → Calculable depuis all_shots_against
- **Shot zones** → Calculable depuis all_shots_against
- **Strengths/weaknesses défenseurs** → EXISTE DÉJÀ
- **Home/Away splits** → EXISTE DÉJÀ
- **Matchup friction** → EXISTE DÉJÀ

---

## COUVERTURE ACTUELLE

```
DÉFENSEURS:  ████████████████████ 100% complet
GARDIENS:    ████████████████████ 100% complet
ATTAQUANTS:  ██████████████████░░  90% (timing/zones calculables)
MILIEUX:     ██████████░░░░░░░░░░  50% (manque défensif/discipline)
```

---

## PROCHAINES ACTIONS

1. [ ] Script pour calculer timing_profile attaquants depuis all_shots_against
2. [ ] Script pour calculer zone_profile attaquants depuis all_shots_against
3. [ ] Scraper FBRef player stats (tackles, interceptions, cards) pour milieux
4. [ ] Intégrer données milieux dans player_dna_unified.json
5. [ ] Générer betting_profiles milieux avec données enrichies

**Temps total estimé: 2-3h** (dont 90% de calcul, 10% de scraping)
