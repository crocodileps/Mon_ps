# 🏎️ Mon_PS - Trading Quantitatif Ferrari 2.0

> Système de trading professionnel pour paris sportifs avec Machine Learning et automatisation complète.

[![Version](https://img.shields.io/badge/version-2.1.0--ferrari--complete-blue.svg)](https://github.com/crocodileps/Mon_ps)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Private-red.svg)]()

---

## 📦 CONTENU VERSION 2.1.0

### 🏎️ Agent A Ferrari 2.0 Multi-Facteurs
Système d'analyse avancé avec 4 facteurs de scoring :

**Formule Ferrari :**
```python
Score Total = Spread (0-50) + Variance (0-20) + Bookmakers (0-15) + Extrême (0-15)
Maximum : 95/100 (cap automatique)
```

**Classification Intelligente :**
- 🔥 **80-95 : DIAMANT** - Opportunités exceptionnelles (spreads >500%)
- ⚡ **65-79 : PREMIUM** - Anomalies fortes exploitables
- 💎 **50-64 : BONNE** - Opportunités intéressantes
- 📊 **35-49 : STANDARD** - Légères anomalies
- ✓ **0-34 : NORMALE** - Marché équilibré

**Facteurs :**
1. **Spread Principal (0-50 pts)** : Échelle logarithmique pour spreads >10%
2. **Variance (0-20 pts)** : Dispersion entre Home/Draw/Away
3. **Bookmakers (0-15 pts)** : Nombre de sources (fiabilité)
4. **Bonus Extrême (0-15 pts)** : Spreads massifs (>500%)

### 🤖 Bot Telegram Diamond 2.0
- Alertes premium avec détails bookmakers
- 4 boutons interactifs : Portfolio | Agents | Stats | Today
- Routes HTML responsive avec glassmorphism
- Intégration Agent Patron

### ⏰ Workflows N8N Automatiques
- **Morning Briefing** : 08h00 (top 10 opportunités)
- **Evening Briefing** : 23h30 (résumé journalier)
- **Alertes Agent Patron** : Toutes les 4h

### 📊 Architecture
```
Mon_PS/
├── backend/          # FastAPI + Agents ML
│   ├── agents/       # 4 agents (A, B, C, D + Patron)
│   └── api/          # Routes REST
├── frontend/         # Next.js 14 + React Query
├── monitoring/       # Prometheus + Grafana
└── scripts/          # Automation
```

---

## 🚀 DÉMARRAGE RAPIDE

### Prérequis
- Docker & Docker Compose
- Hetzner CCX23 (ou équivalent)
- Accès VPN WireGuard configuré

### Installation
```bash
git clone https://github.com/crocodileps/Mon_ps.git
cd Mon_ps/monitoring
docker compose up -d
```

### Accès
- **Frontend** : http://localhost:3001
- **Backend API** : http://localhost:8001
- **Grafana** : http://localhost:3000
- **Prometheus** : http://localhost:9090

---

## 🎯 AGENTS ML

### Agent A - Anomaly Detector Ferrari 2.0
```python
# Score multi-facteurs avec recommandations
Score 95/100 = Spread(50) + Variance(20) + Books(15) + Extrême(15)
```

### Agent B - Spread Optimizer
- Critère de Kelly pour sizing
- Expected Value (EV) calculé
- ROI historique : 202%

### Agent C - Pattern Matcher
- Détection patterns historiques
- Analyse ligues spécifiques
- Corrélations équipes

### Agent D - Backtest Engine
- Win rate par agent
- ROI historique
- Sample size validation

### Agent Patron (Orchestrator)
- Consensus des 4 agents
- Score global /100
- Recommandation finale : BUY / STRONG BET / WAIT

---

## 📱 BOT TELEGRAM

### Commandes
```
/start       - Menu principal
/portfolio   - Voir portefeuille
/agents      - État des agents
/stats       - Statistiques
/today       - Opportunités du jour
```

### Configuration
```bash
# .env
TELEGRAM_BOT_TOKEN=votre_token
TELEGRAM_CHAT_ID=votre_chat_id
```

---

## 🔧 CONFIGURATION

### Environment Variables
```bash
# Database
DB_HOST=monps_postgres
DB_PORT=5432
DB_NAME=monps_db
DB_USER=monps_user
DB_PASSWORD=***

# APIs
ODDS_API_KEY=***
PINNACLE_API_KEY=***

# Telegram
TELEGRAM_BOT_TOKEN=***
TELEGRAM_CHAT_ID=***
```

### Docker Compose
```yaml
services:
  backend:
    build: ../backend
    ports:
      - "8001:8000"
    depends_on:
      - postgres
  
  frontend:
    build: ../frontend
    ports:
      - "3001:3000"
```

---

## 📊 MÉTRIQUES & MONITORING

### Prometheus Metrics
```
- monps_opportunities_total
- monps_agent_scores
- monps_clv_tracking
- monps_bet_performance
```

### Grafana Dashboards
- Vue d'ensemble système
- Performance agents
- Bankroll tracking
- CLV analysis

---

## 🧪 TESTS
```bash
# Backend
pytest backend/tests/

# API Health
curl http://localhost:8001/health

# Agent Ferrari 2.0
curl http://localhost:8001/agents/analyze/{match_id}
```

---

## 📈 RÉSULTATS

### Validation Ferrari 2.0
```
Match : PSG vs Le Havre
Spread : 1735%
Bookmakers : 45
Score : 95/100
Classification : 🔥 DIAMANT (Extrême)
Recommandation : "Opportunité RARE avec spread massif..."
```

### Performance Agents
- Agent A (Ferrari) : 95% confiance sur spreads >1000%
- Agent B : 202% ROI backtest
- Agent C : Patterns validés
- Agent D : Win rate 52%

---

## 🛠️ DÉVELOPPEMENT

### Branches
- `main` : Production stable
- `feature/n8n-workflows` : Workflows mergée ✅
- `feature/agent-ferrari-2.0` : Ferrari mergée ✅

### Tags
- `v2.0-telegram-bot-complete` : Bot Telegram
- `v2.1.0-ferrari-complete` : Ferrari 2.0 ⭐ ACTUEL

### Workflow Git
```bash
git checkout -b feature/nouvelle-feature
# Développement...
git commit -m "✨ feat: Description"
git push origin feature/nouvelle-feature
# Merge sur main après validation
```

---

## 📚 DOCUMENTATION

### API Endpoints
```
GET  /health                     - Santé système
GET  /opportunities              - Liste opportunités
GET  /agents/analyze/{match_id}  - Analyse complète
GET  /briefing/morning           - Briefing matin
GET  /briefing/evening           - Briefing soir
POST /agents/patron/batch        - Analyse batch
```

### Frontend Routes
```
/                    - Dashboard
/opportunities       - Liste opportunités
/agents              - État agents
/agents-comparison   - Comparaison agents
/manual-bets         - Paris manuels + CLV
/stats               - Statistiques
```

---

## 🔐 SÉCURITÉ

- ✅ VPN WireGuard obligatoire
- ✅ Pas d'exposition publique
- ✅ Tokens en variables d'environnement
- ✅ Données sensibles chiffrées
- ✅ Backup quotidien PostgreSQL

---

## 📞 SUPPORT

**Développeur** : Mya  
**GitHub** : https://github.com/crocodileps/Mon_ps  
**Version** : 2.1.0-ferrari-complete  
**Date** : 21 novembre 2025  

---

## 🎉 CHANGELOG

### v2.1.0-ferrari-complete (21/11/2025)
- ✨ Agent A Ferrari 2.0 multi-facteurs
- ✨ Workflows n8n automatiques
- 🔧 Scores frontend /100 cohérents
- 📝 Recommandations explicatives
- ✅ Tests production validés

### v2.0-telegram-bot-complete
- 🤖 Bot Telegram Diamond 2.0
- �� Boutons interactifs
- 👑 Agent Patron integration

---

## 📄 LICENSE

Propriétaire - Tous droits réservés  
© 2025 Mon_PS Trading System
