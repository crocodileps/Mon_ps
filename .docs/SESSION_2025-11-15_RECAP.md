# Mon_PS - Session 15 Novembre 2025 - Récapitulatif Complet

## 🎯 État Actuel du Projet

### Infrastructure Production
- **Serveur** : Hetzner CCX23 (4 vCPU, 16GB RAM)
- **IP** : 91.98.131.218 (publique), 10.10.0.1 (VPN - non configuré sur ce serveur)
- **Sécurité** : UFW firewall + WireGuard VPN configuré localement
- **OS** : Ubuntu 24

### Services Docker Actifs
```bash
monps_postgres    → 0.0.0.0:5432 (TimescaleDB)
monps_backend     → 0.0.0.0:8001 (FastAPI)
monps_frontend    → 0.0.0.0:3001 (Next.js 14)
monps_grafana     → 0.0.0.0:3000
monps_prometheus  → 0.0.0.0:9090
monps_alertmanager → 0.0.0.0:9093
monps_uptime      → 0.0.0.0:3002
```

### Base de Données
- **150,813+ cotes** totales collectées
- **5,728 nouvelles cotes** cette session
- **411 matchs uniques** sur 38 ligues
- **460 opportunités** détectées actuellement
- **Tables principales** : odds_history, bets, bankroll_history
- **Vue** : v_current_opportunities

### Configuration Collecteur (v2.0)
- **Fichier** : `/home/Mon_ps/monitoring/collector/odds_collector.py`
- **Cache intelligent** : Skip si collecté < 4h
- **API Key** : `ODDS_API_KEY=0ded7830ebf698618017c92e51cfcffc`
- **Quota** : 377/500 requêtes restantes
- **DB Connection** : localhost:5432 (depuis serveur, pas Docker)

### 41 Ligues Soccer Configurées
```
soccer_argentina_primera_division, soccer_australia_aleague,
soccer_austria_bundesliga, soccer_belgium_first_div,
soccer_brazil_campeonato, soccer_brazil_serie_b,
soccer_chile_campeonato, soccer_china_superleague,
soccer_conmebol_copa_libertadores, soccer_conmebol_copa_sudamericana,
soccer_denmark_superliga, soccer_efl_champ,
soccer_england_league1, soccer_england_league2,
soccer_epl, soccer_fifa_world_cup_qualifiers_europe,
soccer_france_ligue_one, soccer_france_ligue_two,
soccer_germany_bundesliga, soccer_germany_bundesliga2,
soccer_germany_liga3, soccer_greece_super_league,
soccer_italy_serie_a, soccer_italy_serie_b,
soccer_japan_j_league, soccer_korea_kleague1,
soccer_mexico_ligamx, soccer_netherlands_eredivisie,
soccer_norway_eliteserien, soccer_poland_ekstraklasa,
soccer_portugal_primeira_liga, soccer_spain_la_liga,
soccer_spain_segunda_division, soccer_spl,
soccer_sweden_allsvenskan, soccer_switzerland_superleague,
soccer_turkey_super_league, soccer_uefa_champs_league,
soccer_uefa_europa_conference_league, soccer_uefa_europa_league,
soccer_usa_mls
```

---

## 🤖 Système ML - 4 Agents Opérationnels

### Backend API Endpoints
- `GET /agents/health` → Status 4 agents (0.3s)
- `GET /agents/signals` → 30 signaux combinés (5.7s)
- `GET /agents/performance` → Métriques comparatives (5.6s)
- `GET /agents/summary` → Vue d'ensemble

### Agent A - Anomaly Detector
- **Fichier** : `/home/Mon_ps/backend/agents/agent_anomaly.py`
- **Algorithme** : Isolation Forest
- **Output** : 20 signaux, 7.26% avg confidence
- **Direction** : REVIEW

### Agent B - Spread Optimizer (Kelly Criterion)
- **Fichier** : `/home/Mon_ps/backend/agents/agent_spread.py`
- **Algorithme** : Kelly Criterion + EV
- **Output** : 20 signaux, 100% confidence, EV=5.5, Kelly=23.42%
- **Direction** : BACK_AWAY, BACK_HOME, BACK_DRAW
- **Top Spreads** : 1551%, 1251%, 952%, 917%, 771%

### Agent C - Pattern Matcher
- **Fichier** : `/home/Mon_ps/backend/agents/agent_pattern.py`
- **Output** : 20 signaux, 71% avg confidence

### Agent D - Backtest Engine
- **Fichier** : `/home/Mon_ps/backend/agents/agent_backtest.py`
- **ROI Backtesting** : 202% (simulation)

### Routes Backend
- **Fichier** : `/home/Mon_ps/backend/api/routes/agents_routes.py` (312 lignes)
- **Imports** : psycopg2, agents modules
- **DB_CONFIG** : host='monps_postgres' (depuis container Docker)

---

## 🎨 Frontend - État Actuel

### Configuration API
- **Fichier** : `/home/Mon_ps/frontend/lib/api.ts`
- **URL** : `http://91.98.131.218:8001`
- **Timeout** : 10000ms (axios)
- **Exports** : api (axios instance), getBankrollStats, getGlobalStats, getOpportunities, getBets

### Hooks Agents
- **Fichier** : `/home/Mon_ps/frontend/hooks/use-agents.ts`
- **Hooks** : useAgentSignals, useAgentPerformance, useAgentHealth
- **Refresh** : 5 minutes (signals), 1 minute (stale)

### Types TypeScript
```typescript
AgentSignal {
  agent, match, sport, direction, confidence,
  odds?, spread_pct?, kelly_fraction?, expected_value?,
  recommended_stake_pct?, bookmaker_count?, reason
}

AgentPerformance {
  agent_id, agent_name, total_signals,
  avg_confidence, avg_ev, avg_kelly,
  status?, top_signal?
}

AgentHealth {
  status, agents[], db_connected, total_opportunities?
}
```

### Page Compare Agents
- **Fichier** : `/home/Mon_ps/frontend/app/compare-agents/page.tsx` (220 lignes)
- **État** : Affiche 30 signaux ML
- **Problème** : Header affiche "0 opportunités • 0 agents actifs"
- **Cause** : useAgentHealth() ne récupère pas les données correctement OU le header n'est pas connecté

---

## 🐛 Problèmes Connus à Corriger

### 1. Header Compare Agents
- Affiche : "0 opportunités • 0 agents actifs"
- Devrait : "460 opportunités • 4 agents actifs"
- Le backend retourne bien les données (testé avec curl)

### 2. Cartes Agents Manquantes
- La page n'affiche pas les 4 cartes avec couleurs
- Code existe mais n'est pas rendu (performance?.map)
- Probable : données undefined ou erreur silencieuse

### 3. Top Signal
- Affiche : Standard Liege vs SV Zulte-Waregem (Agent A)
- Devrait : PSG vs Le Havre avec 1551% spread (Agent B)
- Logique de sélection à revoir

---

## 📁 Structure Fichiers Clés
```
/home/Mon_ps/
├── backend/
│   ├── agents/
│   │   ├── agent_anomaly.py
│   │   ├── agent_spread.py
│   │   ├── agent_pattern.py
│   │   └── agent_backtest.py
│   └── api/routes/
│       └── agents_routes.py (312 lignes)
├── frontend/
│   ├── lib/api.ts (axios, http://91.98.131.218:8001)
│   ├── hooks/use-agents.ts (types + hooks)
│   └── app/compare-agents/page.tsx (220 lignes)
├── monitoring/
│   └── collector/
│       ├── odds_collector.py (v2.0)
│       └── cache/*.json (41 fichiers)
└── .docs/
    └── SESSION_2025-11-15_RECAP.md (ce fichier)
```

---

## 🔧 Commandes Utiles

### Lancer Collecte 41 Ligues
```bash
cd /home/Mon_ps/monitoring/collector
ODDS_API_KEY="0ded7830ebf698618017c92e51cfcffc" \
SPORTS="soccer_argentina_primera_division,..." \
DB_HOST=localhost DB_PORT=5432 \
DB_NAME=monps_db DB_USER=monps_user \
DB_PASSWORD=monps_secure_password_2024 \
python3 odds_collector.py
```

### Rebuild Backend
```bash
cd /home/Mon_ps/monitoring
docker cp backend/api/routes/agents_routes.py monps_backend:/app/api/routes/
docker compose build backend --no-cache
docker compose up -d backend
```

### Rebuild Frontend
```bash
cd /home/Mon_ps/monitoring
docker compose build frontend --no-cache
docker compose up -d frontend
```

### Test API Agents
```bash
curl -s http://91.98.131.218:8001/agents/health | python3 -m json.tool
curl -s http://91.98.131.218:8001/agents/performance | head -100
curl -s http://91.98.131.218:8001/agents/signals | head -100
```

### Vérifier DB
```bash
docker exec -it monps_postgres psql -U monps_user -d monps_db -c "
SELECT COUNT(*) as total_cotes FROM odds_history;
SELECT COUNT(*) as opportunites FROM v_current_opportunities;"
```

---

## 🎯 Prochaines Tâches (Branche feature/agents-ui-improvements)

### 1. Corriger Header (Priorité Haute)
- Débugger useAgentHealth() dans page.tsx
- S'assurer que health?.total_opportunities est défini
- Afficher 460 opportunités + 4 agents actifs

### 2. Ajouter 4 Cartes Agents (Priorité Haute)
- Vérifier que performance?.map() s'exécute
- Ajouter gestion d'erreur/loading
- Couleurs : Rouge (Anomaly), Vert (Spread), Bleu (Pattern), Violet (Backtest)

### 3. Améliorer Top Signal
- Prioriser Agent B (Spread Optimizer) avec EV > 0
- Afficher PSG vs Le Havre 1551% spread

### 4. Autres Améliorations
- Filtrage par agent
- Export CSV des signaux
- Graphiques de performance

---

## 📊 Métriques Clés

- **Version Git** : 2189527 (main)
- **Tag** : v1.9-complete-ml-system
- **GitHub** : github.com/crocodileps/Mon_ps
- **Date** : 15 Novembre 2025
- **Status** : Production-ready, ML opérationnel

---

## 💡 Notes Importantes

1. **CORS est OK** - Backend permet Origin depuis 91.98.131.218:3001
2. **Timeout 10s** - Agents prennent 5-6s, c'est OK
3. **Docker rebuild** - Toujours utiliser --no-cache pour le frontend
4. **DB depuis serveur** - Utiliser localhost:5432, pas monps_postgres
5. **DB depuis Docker** - Utiliser monps_postgres (container name)
6. **TypeScript strict** - Tous les types doivent être définis dans interfaces

