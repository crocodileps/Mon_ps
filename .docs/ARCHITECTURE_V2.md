# 🏗️ ARCHITECTURE Mon_PS - Documentation Complète

**Version : 2.0**  
**Date : 19 Novembre 2025**

---

## 📐 VUE D'ENSEMBLE

Mon_PS est une plateforme de trading quantitatif pour paris sportifs combinant :
- Settlement automatique des paris
- Calcul CLV (Closing Line Value) sans coût API
- 4 agents ML pour détection d'opportunités
- Dashboard P&L temps réel

---

## 🎯 ARCHITECTURE SYSTÈME
```
┌─────────────────────────────────────────────────────────┐
│                    HETZNER CCX23                         │
│                  4 vCPU, 16GB RAM                        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   WIREGUARD VPN                          │
│              Sécurité : Pas d'exposition publique        │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐      ┌──────────┐      ┌──────────┐
   │Frontend │      │ Backend  │      │Postgres  │
   │Next.js  │◄────►│ FastAPI  │◄────►│TimescaleDB
   │Port 3001│      │Port 8001 │      │Port 5432 │
   └─────────┘      └──────────┘      └──────────┘
        │                  │                  │
        │                  ▼                  │
        │           ┌──────────┐             │
        │           │  Redis   │             │
        │           │  Cache   │             │
        │           └──────────┘             │
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                  ┌────────────────┐
                  │   Monitoring   │
                  │ Grafana:3000   │
                  │Prometheus:9090 │
                  │Alertmanager    │
                  └────────────────┘
```

---

## 🗄️ BASE DE DONNÉES

### Tables Principales

#### 1. `bets` (29 colonnes)
```sql
-- Informations match
match_id, home_team, away_team, sport, league, commence_time

-- Pari
outcome, odds, stake, bookmaker

-- ML & Analytics
edge_pct, patron_score, patron_confidence, agent_recommended

-- Settlement
status (pending/won/lost), result, final_score, payout, profit

-- CLV & Automation
closing_odds, clv_percent, settled_by (auto/manual)

-- Timestamps
placed_at, settled_at, created_at, updated_at
```

#### 2. `odds_h2h` (400,000+ entrées)
```sql
-- Cotes collectées en temps réel
match_id, home_odds, away_odds, draw_odds, bookmaker, collected_at
```

#### 3. `opportunities`
```sql
-- Opportunités détectées par agents ML
match_id, edge_value, confidence_score, agent_name, detected_at
```

#### 4. Vue `bets_stats`
```sql
-- Analytics temps réel
SELECT 
    COUNT(*) as total_bets,
    SUM(CASE WHEN status='won' THEN 1 ELSE 0 END) as wins,
    SUM(stake) as total_staked,
    SUM(profit) as total_profit,
    AVG(clv_percent) as avg_clv
FROM bets;
```

---

## 🔧 BACKEND - FASTAPI

### Routes Principales

#### `/bets/*`
```python
POST   /bets/place          # Placer un pari
GET    /bets/history        # Historique (limite, status, sport)
GET    /bets/stats          # Statistiques agrégées
PATCH  /bets/{id}/update    # Mettre à jour statut
```

#### `/settlement/*`
```python
POST   /settlement/run-clv           # Force calcul CLV
POST   /settlement/run-settlement    # Force settlement
GET    /settlement/stats             # Stats settlement
```

#### `/opportunities/*`
```python
GET    /opportunities/brute          # Top opportunités ML
GET    /opportunities/patron-scores  # Scoring patron
```

### Cron Jobs

**Fichier** : `/etc/cron.d/settlement-cron`
```cron
# Settlement automatique (8h et 20h)
0 8 * * * cd /app && bash scripts/daily_settlement.sh

# CLV automatique (toutes les 4h)
0 */4 * * * cd /app && python3 scripts/auto_clv.py
```

### Scripts Python

#### `auto_settlement.py`
```python
Fonction : Régler automatiquement les paris terminés
1. Détecter matchs terminés (commence_time + 3h)
2. Récupérer scores via The Odds API
3. Déterminer outcome (home/away/draw)
4. Mettre à jour bets : status, result, profit, settled_by='auto'

Optimisation : 1 requête API par match (10-20/jour max)
```

#### `auto_clv.py`
```python
Fonction : Calculer CLV sans requête API supplémentaire
1. Récupérer dernière cote enregistrée (closing odds)
2. Calculer CLV = (closing_odds / obtained_odds - 1) * 100
3. Mettre à jour bets : closing_odds, clv_percent

Coût API : 0 (réutilise flux de collecte existant)
```

---

## 🎨 FRONTEND - NEXT.JS 14

### Pages
```typescript
/                      # Dashboard principal (à améliorer)
/opportunities         # 50 opportunités ML (table filtrable)
/manual-bets          # P&L Dashboard avec CLV ✅
/analytics            # Graphiques basiques (à améliorer)
```

### Page `/manual-bets` - Structure
```typescript
Components :
├── Dashboard Stats (4 cards)
│   ├── Mise Totale (107€)
│   ├── Profit Net (+0.00€)
│   ├── Taux de Réussite (0.0%)
│   └── Paris Actifs (8)
│
├── Filters (Tous/En attente/Gagnés/Perdus)
│
└── Table Historique
    ├── Colonnes : Match, Sélection, Cote, Mise, Bookmaker
    ├── Edge, CLV, Patron, Statut, P&L
    └── Tri/Filtrage dynamique

Hooks utilisés :
- useBets() → récupère /bets/history
- useBetsStats() → récupère /bets/stats
```

### Colonne CLV - Affichage
```typescript
{bet.clv_percent !== null ? (
  <Badge className={bet.clv_percent >= 0 
    ? 'bg-green-500/20 text-green-400'  // CLV positif (bon)
    : 'bg-red-500/20 text-red-400'      // CLV négatif (mauvais)
  }>
    {bet.clv_percent >= 0 ? '+' : ''}{bet.clv_percent.toFixed(2)}%
  </Badge>
) : '--'}  // Pas encore calculé
```

---

## 🤖 AGENTS ML

### Agent A : Anomaly Detector
```python
Détecte cotes anormales par rapport à la moyenne du marché
Threshold : écart > 15%
Output : opportunités avec edge_value
```

### Agent B : Spread Optimizer (Kelly Criterion)
```python
Calcule sizing optimal des paris via Kelly
Performance backtest : 202% ROI
Output : stake recommandé, edge_pct
```

### Agent C : Pattern Matcher
```python
Détecte patterns historiques (favoris, underdogs)
Basé sur données historiques matchs similaires
```

### Agent D : Backtest Engine
```python
Simule performances sur données passées
Validation stratégies avant déploiement
```

---

## 📊 MONITORING

### Grafana Dashboards
```
Port : 3000 (VPN uniquement)

Dashboards :
1. Opportunities Monitor
   - Nombre opportunités par jour
   - Distribution par bookmaker
   - Edge moyen

2. System Health
   - CPU, RAM, Disk
   - API response times
   - Database queries

3. Betting Performance (à créer)
   - ROI temps réel
   - Win rate
   - CLV évolution
```

### Prometheus Metrics
```yaml
# Métriques collectées
- monps_opportunities_total
- monps_bets_placed_total
- monps_api_requests_total
- monps_collector_duration_seconds
```

---

## 🔐 SÉCURITÉ

### Pare-feu UFW
```bash
Ports ouverts :
- 22 (SSH via VPN uniquement)
- 51820 (WireGuard)
- Tous services internes exposés uniquement sur VPN
```

### Secrets Management
```bash
Variables sensibles dans .env :
- POSTGRES_PASSWORD
- ODDS_API_KEY
- REDIS_PASSWORD

⚠️ Ne JAMAIS commit .env dans Git
```

---

## 🚀 DÉPLOIEMENT

### Docker Compose Services
```yaml
services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    ports: 5432:5432
    volumes: postgres_data:/var/lib/postgresql/data
    
  backend:
    build: ./backend
    ports: 8001:8000  # Externe:Interne
    depends_on: postgres
    command: |
      service cron start &&
      uvicorn api.main:app --host 0.0.0.0 --port 8000
      
  frontend:
    build: ./frontend
    ports: 3001:3000
    depends_on: backend
```

### Commandes Déploiement
```bash
# Build & Deploy
cd /home/Mon_ps/monitoring
docker compose build --no-cache
docker compose up -d

# Vérifier logs
docker logs monps_backend --tail 50
docker logs monps_frontend --tail 50

# Vérifier cron
docker exec monps_backend crontab -l
```

---

## 📈 FLUX DE DONNÉES

### 1. Collecte Odds (Toutes les 4h)
```
The Odds API → Backend → PostgreSQL odds_h2h
                    ↓
              Agents ML analysent
                    ↓
              Opportunités détectées
```

### 2. Placement Paris (Manuel)
```
Frontend Modal → POST /bets/place → PostgreSQL bets (status=pending)
```

### 3. Settlement Automatique (2x/jour)
```
Cron 8h/20h → auto_settlement.py
    ↓
Détecte matchs terminés (commence_time + 3h)
    ↓
The Odds API (récupère scores)
    ↓
Calcule résultat (home/away/draw)
    ↓
UPDATE bets SET status, profit, settled_by='auto'
```

### 4. CLV Automatique (Toutes les 4h)
```
Cron 4h/8h/12h/16h/20h/0h → auto_clv.py
    ↓
Récupère dernière cote enregistrée (closing odds)
    ↓
Calcule CLV = (closing/obtained - 1) * 100
    ↓
UPDATE bets SET closing_odds, clv_percent
```

---

## 🎯 OPTIMISATIONS

### Requêtes API - Coûts
```
Collecte odds : 1 req/4h × 24h = 6 req/jour
Settlement : 1 req/match terminé ≈ 10-20 req/jour
CLV : 0 req (réutilise données)

Total : ~25 req/jour (quota 500/mois OK)
```

### Cache Redis
```python
# Cotes récentes
ttl = 300s  # 5 minutes

# Opportunités
ttl = 600s  # 10 minutes

# Stats dashboard
ttl = 60s   # 1 minute
```

---

## 📝 LOGS

### Emplacements
```bash
# Settlement
/var/log/settlement.log

# CLV
/var/log/clv.log

# Backend
docker logs monps_backend

# Frontend
docker logs monps_frontend
```

---

## 🔄 WORKFLOW GIT
```
main
├── feature/auto-settlement-clv (à merger)
└── feature/frontend-clv-column (à merger)

Prochaine étape :
1. Pull Request vers main
2. Review & merge
3. Tag v2.0
4. Supprimer branches
```

---

**📌 Cette architecture supporte 100+ paris/jour sans modification**
