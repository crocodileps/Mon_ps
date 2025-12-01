# 🏗️ ARCHITECTURE SMART 2.0 - Mon_PS
## Vision: Exploiter 100% du potentiel existant

---

## 📊 INVENTAIRE ACTUEL

### Base de Données: 85 Tables
| Catégorie | Tables | Rows | Status |
|-----------|--------|------|--------|
| **ODDS** | odds_history, odds_totals, odds_spreads | 255K+ | ✅ Actif |
| **AGENTS ML** | agent_analyses, agent_predictions, agent_feedback | 25K+ | ✅ Actif |
| **INTELLIGENCE** | team_intelligence, scorer_intelligence, coach_intelligence | 1.2K+ | ⚠️ Sous-exploité |
| **TRACKING** | tracking_clv_picks, fg_combo_tracking | 3.4K+ | ✅ Actif |
| **PATTERNS** | market_patterns, patterns_correlations | 145 | ⚠️ Sous-exploité |
| **FERRARI** | market_traps, scorer_market_picks | 0 | ❌ VIDE |

### Tables Ultra-Riches (colonnes)
| Table | Colonnes | Données Clés |
|-------|----------|--------------|
| scorer_intelligence | 153 | probs, form, penalties, periods, streaks |
| coach_intelligence | 151 | styles, xG, matchups, strengths |
| market_traps | 90 | alerts, historical_roi, compound_traps |
| scorer_market_picks | 85 | value_rating, bookmaker_bias |
| team_intelligence | 83 | market_alerts JSON, home/away splits |

### API Routes: 53 Fichiers
| Route | Taille | Fonction |
|-------|--------|----------|
| agents_routes.py | 98 KB | 4 agents ML + conseil-ultim |
| pro_command_center.py | 96 KB | Dashboard pro |
| patron_diamond_routes.py | 42 KB | PATRON + Diamond |
| combos_routes.py | 34 KB | Combinés betting |
| ferrari_routes.py | 17 KB | Ferrari intelligence |
| tracking_clv_routes.py | 23 KB | CLV tracking |

---

## 🎯 ARCHITECTURE CIBLE

### Niveau 1: DATA LAYER
```
┌─────────────────────────────────────────────────────────┐
│                    PostgreSQL + TimescaleDB              │
├─────────────┬─────────────┬─────────────┬──────────────┤
│ ODDS DATA   │ INTELLIGENCE│ TRACKING    │ PATTERNS     │
│ - history   │ - teams     │ - clv_picks │ - market     │
│ - totals    │ - scorers   │ - combos    │ - traps      │
│ - spreads   │ - coaches   │ - feedback  │ - correlations│
└─────────────┴─────────────┴─────────────┴──────────────┘
```

### Niveau 2: INTELLIGENCE LAYER
```
┌─────────────────────────────────────────────────────────┐
│                   AGENTS ML ORCHESTRATION                │
├─────────────┬─────────────┬─────────────┬──────────────┤
│ Agent A     │ Agent B     │ Agent C     │ Agent D      │
│ Anomaly     │ Spread/Kelly│ Pattern     │ Backtest     │
├─────────────┴─────────────┴─────────────┴──────────────┤
│                    PATRON DIAMOND V3                     │
│         (Synthèse + Scoring + Recommandations)          │
├─────────────────────────────────────────────────────────┤
│                  FERRARI INTELLIGENCE                    │
│    (Team + Scorer + Coach + Market Traps + H2H)        │
└─────────────────────────────────────────────────────────┘
```

### Niveau 3: DECISION LAYER
```
┌─────────────────────────────────────────────────────────┐
│                  CONSEIL ULTIM ENGINE                    │
├─────────────────────────────────────────────────────────┤
│ Inputs:                                                  │
│ - 4 Agents ML scores                                    │
│ - PATRON Diamond synthesis                              │
│ - Ferrari traps detection                               │
│ - Coach matchup analysis                                │
│ - Scorer probabilities                                  │
│ - Market patterns                                       │
├─────────────────────────────────────────────────────────┤
│ Output: PICK avec confidence + CLV tracking             │
└─────────────────────────────────────────────────────────┘
```

### Niveau 4: UI LAYER
```
┌─────────────────────────────────────────────────────────┐
│                   DASHBOARD UNIFIÉ                       │
├──────────────────┬──────────────────┬──────────────────┤
│ 📊 Command Center│ 🎯 Picks du Jour │ 📈 Performance   │
│ - Live odds      │ - Top picks      │ - ROI tracking   │
│ - Alerts         │ - Traps warnings │ - CLV analysis   │
│ - Market moves   │ - Scorer specials│ - Agent compare  │
├──────────────────┼──────────────────┼──────────────────┤
│ 🔍 Deep Analysis │ ⚙️ Ferrari Intel │ 📋 Historique    │
│ - Match preview  │ - Team profiles  │ - Bets history   │
│ - H2H stats      │ - Scorer cards   │ - Patterns       │
│ - Coach matchup  │ - Trap detector  │ - Learning log   │
└──────────────────┴──────────────────┴──────────────────┘
```

---

## 🔧 PLAN D'IMPLÉMENTATION (12 semaines)

### Phase 1: ACTIVATION (Semaines 1-2)
- [ ] Activer market_traps (peupler avec données)
- [ ] Activer scorer_market_picks
- [ ] Connecter scorer_intelligence aux picks
- [ ] API /ferrari/traps fonctionnel

### Phase 2: INTÉGRATION (Semaines 3-4)
- [ ] Connecter coach_intelligence à PATRON
- [ ] Connecter team_intelligence.market_alerts
- [ ] Ajouter scorer probabilities au flow
- [ ] Créer API /unified/match-preview

### Phase 3: DASHBOARD (Semaines 5-8)
- [ ] Page unifiée "Picks du Jour"
- [ ] Cartes Scorer avec probs
- [ ] Trap Detector visuel
- [ ] Coach Matchup preview

### Phase 4: AUTOMATION (Semaines 9-12)
- [ ] Crons auto-populate intelligence
- [ ] Alertes Telegram smart
- [ ] Auto-tracking CLV
- [ ] Learning feedback loop

---

## 📋 ENDPOINTS À CRÉER

### /api/unified/
| Endpoint | Description |
|----------|-------------|
| GET /match-preview/{home}/{away} | Analyse complète unifiée |
| GET /picks-today | Top picks avec tous les facteurs |
| GET /traps-active | Pièges actifs à éviter |
| GET /scorers/{team} | Buteurs avec probs |
| GET /value-bets | Opportunités value détectées |

### /api/ferrari/ (à compléter)
| Endpoint | Status |
|----------|--------|
| /health | ✅ Existe |
| /team/{name} | ✅ Existe |
| /match/{home}/{away} | ✅ Existe |
| /traps/{home}/{away} | ⚠️ À activer |
| /scorers/{team} | ❌ À créer |

---

## 🎯 KPIs CIBLES

| Métrique | Actuel | Cible |
|----------|--------|-------|
| Tables actives | 30/85 | 60/85 |
| CLV moyen | ? | > 2% |
| ROI mensuel | ? | > 5% |
| Picks/jour | ~10 | 20-30 |
| Traps détectés | 0 | 5-10/jour |
