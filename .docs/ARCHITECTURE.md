# 🏗️ MON_PS - Architecture Technique

## 📐 Vue d'Ensemble
```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT (Navigateur)                   │
│              http://91.98.131.218:3001                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FRONTEND (Next.js 14)                       │
│  - React Components (Dashboard, Business, UI)           │
│  - React Query (State Management)                       │
│  - Hooks (useBets, useOpportunities, useStats)         │
│  - Port: 3001                                           │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/REST
                     ▼
┌─────────────────────────────────────────────────────────┐
│               BACKEND (FastAPI)                          │
│  - API Routes (18 endpoints)                            │
│  - Pydantic Schemas                                     │
│  - SQLAlchemy ORM                                       │
│  - Port: 8001                                           │
└────────────────────┬────────────────────────────────────┘
                     │ SQL
                     ▼
┌─────────────────────────────────────────────────────────┐
│          DATABASE (PostgreSQL + TimescaleDB)            │
│  - odds_history (400k+ entrées)                         │
│  - bets, opportunities, metrics                         │
│  - Port: 5432                                           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              MONITORING (Grafana + Prometheus)          │
│  - Dashboards métriques système                         │
│  - Alerts email via Gmail                               │
│  - Ports: 3005 (Grafana), 9090 (Prometheus)           │
└─────────────────────────────────────────────────────────┘
```

## 📂 Structure des Dossiers
```
Mon_ps/
├── backend/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── odds.py          ✅ Matchs avec meilleures cotes
│   │   │   ├── bets.py          ✅ Gestion paris
│   │   │   ├── opportunities.py ✅ Détection opportunités
│   │   │   ├── stats.py         ✅ Statistiques globales
│   │   │   └── metrics*.py      ✅ Collecte métriques
│   │   ├── models/
│   │   │   └── schemas.py       ✅ Pydantic schemas
│   │   └── database.py          ✅ SQLAlchemy config
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── dashboard/page.tsx   ✅ Page dashboard principale
│   │   ├── opportunities/       ⚠️  Page opportunités
│   │   ├── bets/               ⚠️  Page gestion paris
│   │   └── page.tsx            ✅ Home page
│   │
│   ├── components/
│   │   ├── dashboard/           ✅ Composants dashboard
│   │   │   ├── ActiveBetsPreview.tsx
│   │   │   ├── DashboardStats.tsx
│   │   │   ├── RecentOpportunities.tsx
│   │   │   ├── stat-card.tsx
│   │   │   └── top-opportunities.tsx
│   │   │
│   │   ├── business/            ✅ Composants métier
│   │   │   ├── BetCard.tsx
│   │   │   ├── BetForm.tsx
│   │   │   ├── BetsTable.tsx
│   │   │   ├── OpportunityCard.tsx
│   │   │   ├── OpportunityFilters.tsx
│   │   │   └── StatsWidget.tsx
│   │   │
│   │   ├── ui/                  ✅ Composants UI réutilisables
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── animated-number.tsx
│   │   │   └── custom-tooltip.tsx
│   │   │
│   │   └── modals/              ⚠️  Modals (non utilisés actuellement)
│   │
│   ├── hooks/                   ✅ React Query hooks
│   │   ├── use-bets.ts
│   │   ├── use-opportunities.ts
│   │   └── use-dashboard-stats.ts
│   │
│   ├── lib/
│   │   ├── format.ts            ✅ Helpers formatage (NEW)
│   │   ├── utils.ts             ✅ Utilitaires généraux
│   │   └── mock/                ✅ Données de test
│   │
│   └── package.json
│
├── monitoring/
│   └── docker-compose.yml       ✅ Orchestration services
│
└── .docs/                       ✅ Documentation (NEW)
    ├── STATUS.md
    ├── METHODOLOGY.md
    ├── ARCHITECTURE.md          ← Vous êtes ici
    ├── TROUBLESHOOTING.md
    └── TODO.md
```

## 🔧 Technologies Stack

### Backend
- **Framework** : FastAPI 0.104+
- **ORM** : SQLAlchemy 2.0
- **Validation** : Pydantic v2
- **Database** : PostgreSQL 15 + TimescaleDB
- **Cache** : Redis
- **API Data** : The Odds API

### Frontend
- **Framework** : Next.js 14.2.0
- **Language** : TypeScript
- **UI Library** : React 18
- **Styling** : Tailwind CSS + shadcn/ui
- **State** : React Query (TanStack Query)
- **Forms** : react-hook-form + zod
- **Charts** : Recharts
- **Animations** : Framer Motion

### DevOps
- **Containerization** : Docker + Docker Compose
- **Monitoring** : Grafana + Prometheus
- **Reverse Proxy** : (WireGuard VPN direct)
- **CI/CD** : Git push manuel
- **Hosting** : Hetzner CCX23

## 🔌 API Endpoints (Backend)

### Odds & Matches
```
GET  /odds/odds/matches           ✅ Liste matchs avec meilleures cotes
GET  /odds/odds/history/{match_id} ✅ Historique cotes d'un match
```

### Bets
```
GET  /bets/                       ✅ Liste tous les paris
POST /bets/                       ✅ Créer un pari
GET  /bets/{bet_id}              ✅ Détails d'un pari
PUT  /bets/{bet_id}              ✅ Modifier un pari
```

### Opportunities
```
GET  /opportunities/              ✅ Liste opportunités
GET  /opportunities/top           ✅ Top opportunités par edge
```

### Stats
```
GET  /stats/global                ✅ Stats globales
GET  /stats/bankroll              ✅ État bankroll
GET  /stats/performance           ✅ Performance historique
```

### Metrics
```
GET  /metrics/refresh             ✅ Déclencher collecte manuelle
GET  /metrics/status              ✅ État collecteur
```

## 🔐 Sécurité

### Accès
- ✅ **Backend** : Accessible uniquement via VPN WireGuard
- ✅ **Frontend** : Accessible via IP publique Hetzner
- ✅ **Database** : Localhost uniquement (Docker network)
- ✅ **Monitoring** : Localhost uniquement

### Authentification
- ⚠️  **Pas d'auth actuellement** : Système personnel mono-utilisateur
- 🔒 **Sécurité réseau** : VPN obligatoire pour backend

## 📊 Base de Données

### Tables Principales

#### odds_history
```sql
- id (PK)
- match_id (index)
- sport (index)
- home_team
- away_team
- commence_time
- bookmaker (index)
- home_odds, away_odds, draw_odds
- last_update
- created_at
```

#### bets
```sql
- id (PK)
- match_id (FK)
- strategy_type
- bookmaker
- outcome
- odds_value
- stake
- bet_type
- result (won/lost/pending)
- actual_profit
- clv
- created_at
```

#### opportunities
```sql
- id (PK)
- match_id (FK)
- edge_pct (index)
- best_odds
- bookmaker_best
- calculated_at
```

## 🔄 Flux de Données

### 1. Collecte Odds (Backend)
```
The Odds API 
    ↓ (toutes les 4h + cache intelligent)
Collector Service
    ↓ (parsing + déduplication)
PostgreSQL odds_history
    ↓
Opportunités détectées
```

### 2. Affichage Dashboard (Frontend)
```
User ouvre /dashboard
    ↓
React Query: useOpportunities()
    ↓ HTTP GET
Backend: /opportunities/top
    ↓ SQL
PostgreSQL
    ↓ JSON
Frontend: Affichage OpportunityCard
```

## 🎨 Frontend - Composants Clés

### Dashboard Stats (DashboardStats.tsx)
```typescript
// Utilise StatsWidget pour afficher 4 métriques
- Bankroll actuel
- ROI global
- CLV moyen
- Paris actifs
```

### Active Bets Preview (ActiveBetsPreview.tsx)
```typescript
// Tableau des 5 derniers paris actifs
- Utilise formatNumber() pour affichage sûr
- Lien vers page /bets complète
```

### Recent Opportunities (RecentOpportunities.tsx)
```typescript
// Top 3 opportunités par edge %
- Utilise OpportunityCard
- Lien vers page /opportunities
```

## 🚀 Déploiement

### Build Frontend
```bash
cd /home/Mon_ps/monitoring
docker compose build frontend
docker compose up -d frontend
```

### Restart Backend
```bash
docker compose restart backend
```

### Logs
```bash
# Frontend
docker logs monps_frontend -f

# Backend
docker logs monps_backend -f

# Database
docker logs monps_postgres -f
```

## 📈 Performance

### Métriques Actuelles
- **API Response Time** : ~50-200ms
- **Odds Collection** : Toutes les 4h (cache 3h50)
- **Database Size** : ~2GB (400k+ odds)
- **Frontend Build** : ~45-50s
- **Page Load** : ~1-2s (first paint)

### Optimisations Appliquées
- ✅ Cache intelligent collector (98.3% réduction API calls)
- ✅ React Query caching (staleTime: 30s)
- ✅ TimescaleDB pour données time-series
- ✅ Indexes sur colonnes fréquentes (match_id, sport, edge_pct)

## �� Architecture Future

### Phase Suivante
- 📱 **Mobile-first** : Optimisation responsive
- 🤖 **Agents ML** : Interface de gestion agents
- 📊 **Analytics** : Page analytics avancées
- ⚙️  **Settings** : Configuration utilisateur
- 🔔 **Notifications** : Système d'alertes temps réel
