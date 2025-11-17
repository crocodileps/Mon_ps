# MON_PS - FEUILLE DE ROUTE V2.0
## Plan d'Action Scientifique & Méthodique

**Version :** 2.0.0  
**Date :** 17 Novembre 2025  
**Horizon :** 6 mois  
**Philosophie :** Qualité > Rapidité | Science > Intuition

---

## 📊 STATUT ACTUEL : 9.1/10

| Composant | Score | Statut |
|-----------|-------|--------|
| Infrastructure | 10/10 | ✅ Production-ready |
| Backend API | 9.5/10 | ✅ 19 endpoints |
| Frontend | 9/10 | ✅ Modal ML + Dashboard |
| ML Agents | 8/10 | ⚠️ Heuristiques |
| Monitoring | 9/10 | ✅ Grafana + Alerting |
| Tests | 4/10 | ❌ Coverage 45% |

---

## 🎯 PHASE 1 : TESTS & CONSOLIDATION (1-2 semaines)
**Priorité : HAUTE**

### 1.1 Tests Backend
- [ ] Coverage 45% → 80%
- [ ] Tests unitaires endpoints
- [ ] Tests intégration DB
- [ ] Tests 4 agents ML
- [ ] CI/CD GitHub Actions

### 1.2 Tests Frontend
- [ ] Jest + React Testing Library
- [ ] Tests composants
- [ ] Tests hooks
- [ ] Coverage > 70%

### 1.3 Documentation
- [ ] API OpenAPI/Swagger
- [ ] README mis à jour
- [ ] Guides développeur

**Critères de Succès :**
- ✅ Coverage backend > 80%
- ✅ Coverage frontend > 70%
- ✅ CI/CD vert
- ✅ Documentation complète

---

## 🧠 PHASE 2 : ML RÉEL (2-3 semaines)
**Priorité : HAUTE**

### 2.1 Agent A05 - XGBoost (1 semaine)
- [ ] Feature engineering (historique cotes)
- [ ] Collecte 5000+ matchs
- [ ] PurgedKFoldCV (anti-leakage)
- [ ] Entraînement XGBoost
- [ ] Optuna hyperparameters
- [ ] Endpoint /agents/predict/{match_id}

**Métriques Cibles :**
- ECE < 3%
- ROC-AUC > 0.65
- Pas d'overfitting

### 2.2 Agent A22 - Calibrateur (3-4 jours)
- [ ] Isotonic Regression
- [ ] Calibration plot
- [ ] Validation ECE

### 2.3 Agent A19 - CLV Calculator (3-4 jours)
- [ ] Tracking odds_close
- [ ] CLV = (odds_placed/odds_close - 1) * 100
- [ ] Dashboard Grafana CLV
- [ ] Alertes si CLV < 0%

**Critères de Succès :**
- ✅ Modèle XGBoost entraîné
- ✅ ECE < 3%
- ✅ CLV tracking opérationnel

---

## ⚡ PHASE 3 : OPTIMISATION (1-2 semaines)
**Priorité : MOYENNE**

### 3.1 Performance
- [ ] React Query caching
- [ ] Lazy loading
- [ ] Bundle size reduction
- [ ] Lighthouse > 90

### 3.2 UX
- [ ] WebSocket temps réel
- [ ] Notifications
- [ ] Dark/Light mode
- [ ] Accessibilité

### 3.3 Mobile
- [ ] UI responsive optimisée
- [ ] PWA manifest
- [ ] Touch gestures

---

## 🔐 PHASE 4 : SÉCURITÉ & AUTH (1-2 semaines)
**Priorité : MOYENNE**

### 4.1 Authentification
- [ ] NextAuth.js v5
- [ ] JWT tokens
- [ ] TOTP (Google Auth)
- [ ] Sessions sécurisées
- [ ] Login page /login

### 4.2 Sécurité
- [ ] CSRF protection
- [ ] Rate limiting
- [ ] Input validation (Zod)
- [ ] Security headers

### 4.3 Audit
- [ ] Audit logs
- [ ] Traçabilité actions
- [ ] RGPD check

---

## 📈 PHASE 5 : PAPER TRADING (2-3 semaines)
**Priorité : HAUTE (après Phase 2)**

### 5.1 Backtesting
- [ ] Simulation 5000+ paris
- [ ] Multi-scénarios
- [ ] ROI, MaxDrawdown, Sharpe
- [ ] Kelly simulation

### 5.2 Live Paper Trading
- [ ] Mode simulation (pas d'argent)
- [ ] Tracking temps réel
- [ ] Dashboard performance
- [ ] Alertes drawdown > 15%

**Métriques Cibles :**
- CLV > 1% sur 100+ paris
- ROI net > 0%
- Max Drawdown < 15%
- Sharpe Ratio > 1.0

---

## 🎲 PHASE 6 : STRATÉGIE HYBRIDE (2-3 semaines)
**Priorité : MOYENNE**

### 6.1 Interface Tabac
- [ ] Page "Ordres du Jour"
- [ ] Liste 10 paris manuels
- [ ] Export PDF
- [ ] Checkbox "Placé"

### 6.2 Saisie Manuelle
- [ ] Formulaire paris tabac
- [ ] Table manual_bets
- [ ] Validation données

### 6.3 Dashboard Hybride
- [ ] Auto vs Manuel
- [ ] CLV comparatif
- [ ] ROI par stratégie

---

## 💰 PHASE 7 : LIVE TRADING (3-4 semaines)
**Priorité : BASSE (dépend phases précédentes)**

### 7.1 Connexion Bookmakers
- [ ] API Pinnacle
- [ ] API Betfair
- [ ] Circuit breakers
- [ ] Retry backoff

### 7.2 Exécution Auto
- [ ] Smart Order Router
- [ ] Slippage monitoring
- [ ] Latence < 100ms

### 7.3 Risk Management
- [ ] Kill-switches auto
- [ ] MaxDrawdown 18%
- [ ] Daily loss limit

---

## 📅 TIMELINE
```
NOV 2025     DEC 2025      JAN 2026      FEB 2026      MAR 2026
   |            |             |             |             |
   ✅          P1            P2            P3-P4         P5-P6
 Actuel      Tests        ML Réel      Optimisation   Paper Trading
```

---

## 🎯 MÉTRIQUES QUANTIFIABLES

### Court Terme (1 mois)
| Métrique | Actuel | Cible |
|----------|--------|-------|
| Test Coverage Backend | 45% | 80% |
| Test Coverage Frontend | 0% | 70% |
| ECE | N/A | < 3% |
| ML Agents réels | 0 | 2 |

### Moyen Terme (3 mois)
| Métrique | Actuel | Cible |
|----------|--------|-------|
| CLV Tracking | Non | Oui |
| Paper Trading | Non | 30 jours |
| Auth Sécurisée | Non | Oui |
| Lighthouse | ~70 | > 90 |

### Long Terme (6 mois)
| Métrique | Actuel | Cible |
|----------|--------|-------|
| Live Trading | Non | Oui |
| CLV Rolling 100 | N/A | > 1% |
| Sharpe Ratio | N/A | > 1.0 |
| Uptime | 99.9% | 99.99% |

---

## 🔄 WORKFLOW GIT
```bash
# Feature branch
git checkout -b feature/nom-feature
# ... travail ...
git add -A
git commit -m "feat: description"
git push origin feature/nom-feature

# Merge sur main
git checkout main
git merge feature/nom-feature
git push origin main

# Tag si release
git tag -a vX.Y.Z -m "Release notes"
git push origin vX.Y.Z
```

---

## ⚠️ RISQUES

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Overfitting ML | Haut | PurgedKFoldCV |
| Data leakage | Critique | Tests anti-leakage |
| Bookmaker ban | Haut | Camouflage |
| Drawdown | Haut | Kill-switches |

---

## 🎯 PROCHAINE ACTION

**MAINTENANT :**
1. ✅ Commit sur main (FAIT)
2. ✅ Tag v2.0.0 (FAIT)
3. ✅ Créer documentation (EN COURS)
4. [ ] Session récap
5. [ ] Nettoyer fichiers obsolètes

**PROCHAINE SESSION :**
- Phase 1.1 : Tests Backend
- Objectif : Coverage 80%
- Durée : 3-5 jours

---

**Philosophie : Qualité > Rapidité | Science > Intuition | Méthodique > Précipité**

**Document créé : 17 Novembre 2025**
