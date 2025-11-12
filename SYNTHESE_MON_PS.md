# 📊 SYNTHÈSE COMPLÈTE - PROJET MON_PS

**Projet:** Plateforme quantitative de paris sportifs
**Date:** 12 Novembre 2025
**Status:** Production (alertes opérationnelles)

---

## 🎯 VUE D'ENSEMBLE

Mon_PS est un système de trading sportif hybride combinant:
- Paris manuels ("Tabac"): Analyse humaine
- Paris automatisés ("Ligne"): Algorithmes quantitatifs
- Monitoring temps réel avec alertes email

---

## 🏗️ INFRASTRUCTURE

### Serveur
```
Provider: Hetzner
Plan: CCX23
CPU: 4 vCPU AMD
RAM: 8 GB
Storage: 80 GB NVMe
OS: Ubuntu 24.04
IP: 91.98.131.218
```

### Docker Services (6)
```
monps_postgres      PostgreSQL 16 + TimescaleDB
monps_backend       FastAPI Python 3.11
monps_frontend      Next.js 14
monps_prometheus    Monitoring métriques
monps_grafana       Dashboards visuels
monps_alertmanager  Alertes email ⭐
```

---

## 💾 BASE DE DONNÉES
```sql
Type: PostgreSQL 16 + TimescaleDB
Database: monps_db
Tables principales:
  - odds_history (143,000 rows)
  - bets (8 rows)
  - v_current_opportunities (view)

Dernière collecte: 11 Nov 2025 21:00
Rétention: 30 jours
```

---

## 🚀 BACKEND API
```python
Framework: FastAPI
Port: 8001
Endpoints: 18

Routes principales:
  GET  /health
  GET  /odds/
  GET  /odds/matches
  GET  /opportunities/
  POST /bets/
  GET  /stats/global
  GET  /metrics (Prometheus)
```

---

## 💻 FRONTEND
```javascript
Framework: Next.js 14 + React
Port: 3001
Pages:
  / - Dashboard principal
  /opportunities - Liste opportunités
  /bets - Gestion paris
  /analytics - Analytics avancées
  /settings - Paramètres
```

---

## 🔔 SYSTÈME D'ALERTES

### Configuration
```yaml
Service: Alertmanager
Email: karouche.myriam@gmail.com
SMTP: Gmail (smtp.gmail.com:587)
Status: ✅ OPÉRATIONNEL (testé 12 Nov 16:56)
```

### Alertes configurées (6)
```
1. BankrollCritique
   Condition: Bankroll < 900€
   Fréquence: 1 email puis 24h

2. ROINegatif
   Condition: ROI < 0% pendant 10min
   Fréquence: 1 email puis 24h

3. WinRateFaible
   Condition: Win rate < 50% pendant 30min
   Fréquence: 1 email puis 24h

4. BackendDown
   Condition: API down > 1min
   Fréquence: Immédiat puis 30min

5. NewOpportunitySpike
   Condition: Nouvelles opportunités détectées
   Fréquence: 1 email par 24h

6. NoDataCollection
   Condition: Pas de collecte depuis 4h
   Fréquence: 1 email puis 24h
```

---

## 📊 MONITORING

### Prometheus
```
Port: 9090
Scrape interval: 15s
Rétention: 30 jours
Métriques collectées:
  - monps_bankroll
  - monps_roi
  - monps_win_rate
  - monps_opportunities_detected_total
  - System metrics (CPU, RAM, etc.)
```

### Grafana
```
Port: 3000
Admin: admin / SuperSecure2025Grafana19
Dashboards: 6 configurés
Datasource: Prometheus
```

---

## 🎲 DONNÉES TRADING

### Métriques actuelles
```
Bankroll:    1030€
ROI:         37.5%
Total Paris: 8
Gagnés:      5
Perdus:      3
Win Rate:    62.5%
```

### Collecte données
```
Source: The Odds API
Fréquence: Toutes les 2-4h (intelligent)
Sports: EPL, La Liga, Ligue 1
Bookmakers: 20+
Total cotes: 143,000
```

---

## ❌ PROBLÈMES CONNUS

### 1. Collector inactif
```
Status: ❌ Arrêté
Cause: API Key invalide (401)
Dernière collecte: 11 Nov 21:00 (19h ago)
Impact: Pas de nouvelles opportunités
Fix: Nouvelle API key requise
```

### 2. Conteneur collector manquant
```
Status: ❌ Pas dans docker-compose.yml
Impact: run_collector.sh échoue
Fix: Recréer conteneur ou lancer en local
```

---

## 📁 ARCHITECTURE FICHIERS
```
/home/Mon_ps/
├── backend/
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/ (18 endpoints)
│   │   ├── models/
│   │   └── services/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/ (Next.js 14 App Router)
│   ├── components/
│   └── Dockerfile
├── monitoring/
│   ├── docker-compose.yml ⭐
│   ├── config/
│   │   ├── alertmanager/
│   │   │   └── alertmanager.yml ⭐
│   │   ├── prometheus/
│   │   │   ├── prometheus.yml
│   │   │   └── rules/alerts.yml ⭐
│   │   └── grafana/
│   └── collector/
│       ├── odds_collector.py
│       ├── .env
│       └── logs/
├── PLAN_ACTION_MON_PS.md
└── SYNTHESE_MON_PS.md
```

---

## 🔧 MAINTENANCE

### Logs
```
Alertmanager: docker logs monps_alertmanager
Backend: docker logs monps_backend
Prometheus: docker logs monps_prometheus
Collector: monitoring/collector/logs/
```

### Backups
```
Status: ❌ Pas de backups automatiques
À faire: Cron job PostgreSQL
```

---

## 🚀 PROCHAINES ÉTAPES

1. Fixer collector (nouvelle API key)
2. Backups automatiques
3. Agent CLV Calculator
4. Tests automatisés
5. Documentation complète

---

## 📈 HISTORIQUE
```
Phase 1-6:   Infrastructure + API
Phase 7-10:  Monitoring + Data Collection
Phase 11:    Corrections backend
Phase 12:    Agents ML (planifié)
Phase 13:    Frontend Next.js
Phase 14:    Alertes email ⭐ TERMINÉ
```

---

**Dernière mise à jour:** 12 Novembre 2025 16:30
**Prochaine action:** Obtenir nouvelle API key The Odds
