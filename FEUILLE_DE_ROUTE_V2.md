# 🎯 FEUILLE DE ROUTE Mon_PS - v2.0
**Dernière mise à jour : 19 Novembre 2025**

---

## 📊 ÉTAT ACTUEL - CE QUI FONCTIONNE

### ✅ Infrastructure (100%)
- Hetzner CCX23 (4 vCPU, 16GB RAM)
- Docker Compose (Postgres, Backend, Frontend)
- Monitoring Grafana + Prometheus
- WireGuard VPN sécurisé
- Alerting Alertmanager

### ✅ Backend API (95%)
- 18+ endpoints FastAPI opérationnels
- PostgreSQL + TimescaleDB
- Redis cache
- **Cron jobs actifs** (Settlement 2x/jour, CLV 4x/jour)
- Scripts Python settlement automatique

### ✅ Base de Données (100%)
- Table `bets` : 29 colonnes
- Table `odds_h2h` : 400,000+ entrées
- Table `opportunities` : ML agents
- Vue `bets_stats` pour analytics
- Index optimisés

### ✅ Frontend (90%)
- Page `/opportunities` - 50 opportunités brutes
- Page `/manual-bets` - **P&L Dashboard avec colonne CLV**
- Page `/analytics` - Graphiques basiques
- Navigation globale
- Design glassmorphism violet/bleu

### ✅ Agents ML (80%)
- 4 agents opérationnels :
  - Agent A : Anomaly Detector
  - Agent B : Spread Optimizer (202% ROI backtest)
  - Agent C : Pattern Matcher  
  - Agent D : Backtest Engine
- Système de scoring PRUDENCE/ANALYSER

### ✅ Paris & Tracking (100%)
- **8 paris placés (107€)**
- Settlement automatique configuré
- Calcul CLV automatique (0 API supplémentaire)
- Dashboard P&L temps réel

---

## 🎯 PRIORITÉS - PAR ORDRE D'IMPORTANCE

### 🔴 URGENT (Cette semaine)

#### 1. Merger les branches Git (1h)
```bash
Branches à merger :
- feature/auto-settlement-clv → main
- feature/frontend-clv-column → main

Actions :
✓ Tester en production avant merge
✓ Créer Pull Requests sur GitHub
✓ Review code
✓ Merger vers main
✓ Supprimer branches obsolètes
```

#### 2. Documentation finale (30min)
```bash
✓ Mettre à jour README.md
✓ Documenter architecture settlement/CLV
✓ Guide utilisateur page P&L
✓ Documenter cron jobs
```

#### 3. Vérifier premiers settlements (48h)
```bash
✓ Attendre demain 8h pour premier settlement auto
✓ Vérifier logs : docker exec monps_backend cat /var/log/settlement.log
✓ Observer premiers CLV calculés
✓ Valider que tout fonctionne automatiquement
```

---

### 🟡 IMPORTANT (2-4 semaines)

#### 4. Page Compare Agents (2-3h)
```typescript
Route : /compare-agents
Objectif : Comparer performances 4 agents ML

Contenu :
- Tableau comparatif (ROI, Sharpe, Win Rate, CLV)
- Graphiques Recharts performance temporelle
- Historique décisions par agent
- Vote consensus vs résultats réels

Données disponibles :
- Agent B : 202% ROI en backtest
- Métriques dans table opportunities
```

#### 5. Page Analytics Avancées (2-3h)
```typescript
Route : /analytics (améliorer existant)
Objectif : Visualisation données approfondies

Ajouter :
- Graphique évolution bankroll (Recharts LineChart)
- ROI par bookmaker (BarChart)
- Win rate par période (AreaChart)
- Heatmap meilleurs jours/heures
- Filtres dates (7j, 30j, 90j, tout)
```

#### 6. Page Settings (1-2h)
```typescript
Route : /settings
Objectif : Configuration plateforme

Contenu :
- Bankroll initial
- API Key The Odds API
- Fréquence collecte odds
- Seuils Kelly Criterion
- Activation/désactivation agents
- Préférences alertes email
```

---

### 🟢 MOYEN TERME (1-2 mois)

#### 7. Améliorer Agents ML
```python
Objectifs :
- Calibrer seuils de confiance
- Ajouter consensus vote majoritaire
- Pondération par performance historique
- Nouveaux patterns à détecter
- Agent ML XGBoost prédictif
```

#### 8. Dashboard Principal
```typescript
Route : / (améliorer)
Ajouter :
- Widget opportunités urgentes (< 24h)
- Mini-graphiques temps réel
- Alertes visuelles importantes
- Performance journalière/hebdo
- ROI global clignotant
```

#### 9. Notifications Temps Réel
```bash
Technologies :
- WebSocket pour updates live
- Notifications push navigateur
- Alertes Telegram/Discord
- Email haute priorité

Use cases :
- Nouvelle opportunité Edge > 10%
- Match commence dans 30min
- Settlement automatique effectué
```

---

### 🔵 LONG TERME (3-6 mois)

#### 10. Multi-Sports
- Tennis (ATP, WTA)
- Basketball (NBA, EuroLeague)
- Baseball (MLB)
- Hockey (NHL)
- E-Sports (LoL, CS:GO)

#### 11. Authentification & Multi-Users
- JWT tokens
- Rôles (admin, user, viewer)
- API publique rate-limited
- Partage opportunités

#### 12. Mobile App
- React Native / PWA
- Notifications push natives
- Interface optimisée mobile
- Offline mode

#### 13. ML Avancé
- XGBoost prédictions
- Sentiment analysis news
- Corrélation météo/résultats
- Détection line movement

---

## 📈 MÉTRIQUES DE SUCCÈS

### Court Terme (1-2 semaines)
- [ ] ROI positif validé sur 20+ paris
- [ ] CLV moyen > 1%
- [ ] 0 downtime production
- [ ] Settlement automatique 100% fiable

### Moyen Terme (1-2 mois)
- [ ] 100+ paris trackés
- [ ] ROI > 3% constant
- [ ] 5+ sports couverts
- [ ] Frontend mobile-responsive

### Long Terme (3-6 mois)
- [ ] ROI > 5% constant sur 6 mois
- [ ] 500+ paris analysés
- [ ] Système 100% automatisé
- [ ] Business model validé

---

## 🔧 DETTE TECHNIQUE

### Code
- [ ] Refactoring agents (réduire duplication)
- [ ] Error handling uniformisé
- [ ] TypeScript strict mode
- [ ] Tests unitaires (coverage > 80%)

### Infrastructure
- [ ] CI/CD GitHub Actions
- [ ] Backup automatique PostgreSQL
- [ ] SSL/HTTPS Let's Encrypt
- [ ] Rate limiting API

### Documentation
- [ ] README complet
- [ ] API OpenAPI documentation
- [ ] Guide développeur
- [ ] Architecture diagram

---

## 📝 CHANGELOG

### v2.0 - 19 Nov 2025 - Settlement & CLV Automatique ✅
- Settlement automatique avec scripts Python
- Calcul CLV (0 requête API supplémentaire)
- Cron jobs actifs (2x/jour settlement, 4x/jour CLV)
- Page P&L avec colonne CLV
- 8 paris trackés (107€)

### v1.9 - 18 Nov 2025 - Page P&L Complete ✅
- Dashboard P&L 4 KPIs
- Tableau historique avec filtres
- Modal PlaceBetModal
- Navigation globale
- 8 paris placés

### v1.8 - 15 Nov 2025 - Agents ML ✅
- 4 agents opérationnels
- 460 opportunités détectées
- Agent B : 202% ROI backtest
- Système scoring PRUDENCE/ANALYSER

---

## 🎯 PROCHAINE SESSION - ACTIONS IMMÉDIATES

1. **Merger vers main** (30-45min)
2. **Créer tag v2.0** 
3. **Attendre premiers settlements** (demain 8h)
4. **Choisir prochaine feature** :
   - Option A : Page Compare Agents
   - Option B : Analytics Avancées
   - Option C : Page Settings
   - Option D : Dashboard amélioré

---

**📌 Focus actuel : Valider settlement automatique en conditions réelles**
