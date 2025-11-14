# Architecture Mon_PS

## Vue d'ensemble

Mon_PS est une plateforme de trading sportif quantitatif combinant stratégies automatisées (Ligne) et manuelles (Tabac).

## Stack Technique

### Backend
- **Framework** : FastAPI (Python 3.11)
- **Database** : PostgreSQL + TimescaleDB
- **Caching** : Redis
- **API** : RESTful avec 18+ endpoints

### Frontend
- **Framework** : Next.js 14 (React)
- **Styling** : Tailwind CSS + Glassmorphism
- **State** : React Query (TanStack Query)
- **Charts** : Recharts
- **UI** : shadcn/ui

### Infrastructure
- **Hosting** : Hetzner CCX23 (4 vCPU, 16GB RAM)
- **Deployment** : Docker Compose
- **Monitoring** : Prometheus + Grafana
- **Alerting** : Email via Gmail SMTP
- **Security** : WireGuard VPN (accès privé uniquement)

## Architecture Backend

### Routes API (18 endpoints)

#### Settings (`/settings/`)
- `GET /settings/` - Liste tous les paramètres
- `GET /settings/{key}` - Récupère un paramètre spécifique
- `PUT /settings/{key}` - Met à jour un paramètre
- `GET /settings/health` - Health check

#### Stats (`/stats/stats/`)
- `GET /stats/stats/global` - Statistiques globales
- `GET /stats/stats/bankroll` - Stats bankroll
- `GET /stats/stats/bookmakers` - Stats par bookmaker
- `GET /stats/stats/analytics/comprehensive` - Analytics complet

#### Bets (`/bets/`)
- `GET /bets/bets/` - Liste des paris
- `POST /bets/bets/` - Créer un pari
- `GET /bets/bets/{id}` - Détails d'un pari
- `PUT /bets/bets/{id}` - Mettre à jour un pari

#### Odds (`/odds/`)
- `GET /odds/odds/` - Liste des cotes
- `GET /odds/latest` - Dernières cotes collectées

#### Opportunities (`/opportunities/`)
- `GET /opportunities/` - Opportunités d'arbitrage détectées

### Base de Données

**Tables principales** :
- `bets` - Historique des paris
- `odds_history` - Historique des cotes (TimescaleDB)
- `settings` - Configuration (JSONB)
- `collection_logs` - Logs de collecte
- `prometheus_metrics` - Métriques système

## Architecture Frontend

### Pages

1. **Dashboard** (`/`) - Vue d'ensemble
2. **Analytics** (`/analytics`) - Analyses détaillées avec graphiques
3. **Settings** (`/settings`) - Configuration système
4. **Bets** (`/bets`) - Gestion des paris
5. **Opportunities** (`/opportunities`) - Opportunités détectées

### Hooks React Query

- `useSettings()` - Gestion paramètres
- `useGlobalStats()` - Stats globales
- `useBankrollStats()` - Stats bankroll
- `useBookmakerStats()` - Stats bookmakers
- `useBets()` - Gestion paris
- `useOdds()` - Récupération cotes
- `useOpportunities()` - Opportunités

### Composants Business

- `BetCard` - Carte d'affichage pari
- `BetForm` - Formulaire création pari
- `BetsTable` - Tableau des paris
- `OpportunityCard` - Carte opportunité
- `StatsWidget` - Widget statistiques

## Sécurité

- ✅ Accès VPN uniquement (WireGuard)
- ✅ Pas d'exposition publique
- ✅ GitHub privé
- ✅ Variables d'environnement sécurisées
- ✅ CORS configuré

## Monitoring

- **Grafana** : Dashboards personnalisés
- **Prometheus** : Métriques temps réel
- **Uptime Kuma** : Monitoring disponibilité
- **Email Alerts** : Alertes critiques

## Performance

- Collecte odds : Toutes les 2-4h (optimisé 98.3%)
- Cache intelligent : 230 minutes
- API Response : <100ms (moyenne)
- Database : TimescaleDB pour séries temporelles

## Versions Stables

- `v1.2-settings-complete` - Page Settings fonctionnelle
- `v1.3-cleanup-toFixed-complete` - Code refactoré
- `v1.4-analytics-complete` - Analytics avec graphiques
